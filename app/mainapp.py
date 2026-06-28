from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, Response
from tensorflow.keras.models import load_model
import cv2
import os
import numpy as np
import pickle
import logging
import random
import time
import io
import csv
from datetime import datetime
from werkzeug.security import check_password_hash

# Import database manager functions
from database.db_manager import (
    init_db, get_user, create_user, update_user_status, update_user_password, list_users,
    get_doctors, create_doctor, update_doctor, delete_doctor,
    get_patients, get_patient, create_patient, update_patient, delete_patient,
    create_prediction, get_predictions, log_activity, list_activity_logs,
    get_settings, update_setting, get_dashboard_stats
)
from report_generator import generate_pdf

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'brain_stroke_clinical_app_secret_key_2026_x'

# Base directory setup for robust path handling
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
modelpath = os.path.join(BASE_DIR, 'model-cnn.h5')
labelspath = os.path.join(BASE_DIR, 'labels-cnn.h5')
upload_folder = os.path.join(BASE_DIR, 'static')

# Initialize DB on startup
try:
    logging.info("Initializing database...")
    init_db()
    logging.info("Database initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize database: {e}")

# Load model and labels once at startup
logging.info("Loading Keras model...")
try:
    model = load_model(modelpath)
    logging.info("Model loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load model from {modelpath}: {e}")
    model = None

logging.info("Loading label encoder...")
try:
    le = pickle.loads(open(labelspath, "rb").read())
    logging.info("Label encoder loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load label encoder from {labelspath}: {e}")
    le = None


def predict_label(img_path):
    if model is None or le is None:
        logging.error("Model or label binarizer not loaded.")
        return "Error: Model not loaded.", None
    
    try:
        logging.info(f"Running prediction for image: {img_path}")
        image = cv2.imread(img_path)
        if image is None:
            logging.error(f"Failed to read image at {img_path}")
            return "Error: Invalid image.", None
            
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (224, 224))
        image = np.resize(image, (1, image.shape[0], image.shape[1], image.shape[2]))
        image = image / 255.0
        
        pred = model.predict(image)
        pred_decoded = le.inverse_transform(pred)
        
        predicted_class = pred_decoded[0] if len(pred_decoded) > 0 else "Unknown"
        
        # Calculate confidence from Sigmoid output probability
        prob = float(pred[0][0])
        is_stroke = "Stroke" in predicted_class
        confidence = prob * 100 if is_stroke else (1 - prob) * 100
        
        logging.info(f"Prediction: {predicted_class}, Confidence: {confidence:.2f}%")
        return predicted_class, confidence
        
    except Exception as e:
        logging.error(f"Prediction exception: {e}")
        return f"Error: {e}", None


# Helper decorator to protect routes
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('main'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or session.get('role') != 'Admin':
            flash('Error: Access denied. Administrator privilege required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# 1. Login Routes
@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = get_user(username)
        if user:
            if user['status'] != 'Active':
                return render_template('sign-in.html', msg="Account deactivated. Please contact your system Administrator.")
            
            if check_password_hash(user['password_hash'], password):
                session['username'] = user['username']
                session['role'] = user['role']
                
                # Fetch settings for branding
                settings = get_settings()
                session['hospital_name'] = settings.get('hospital_name', 'Brain Stroke AI Diagnostic Center')
                
                log_activity(user['username'], 'User Logged In', f"Role: {user['role']}")
                logging.info(f"User '{username}' logged in successfully as {user['role']}.")
                
                if user['role'] == 'Receptionist':
                    return redirect(url_for('patients_panel'))
                return redirect(url_for('dashboard'))
        
        logging.warn(f"Failed login attempt for user '{username}'.")
        return render_template('sign-in.html', msg="Please enter correct credentials !")
        
    if 'username' in session:
        if session.get('role') == 'Receptionist':
            return redirect(url_for('patients_panel'))
        return redirect(url_for('dashboard'))
        
    return render_template('sign-in.html', msg="")


@app.route("/dashboard")
@login_required
def dashboard():
    if session.get('role') == 'Receptionist':
        flash('Access Denied. Redirected to Patients Panel.', 'warning')
        return redirect(url_for('patients_panel'))
        
    stats = get_dashboard_stats()
    audit_logs = list_activity_logs(10)
    return render_template('dashboard.html', stats=stats, audit_logs=audit_logs, active_page='dashboard')


# 2. Patients Routes
@app.route("/patients")
@login_required
def patients_panel():
    search_query = request.args.get('search', '').strip()
    patients = get_patients(search_query)
    doctors = get_doctors()
    return render_template('patients.html', patients=patients, doctors=doctors, search_query=search_query, active_page='patients')


@app.route("/patients/register", methods=['POST'])
@login_required
def register_patient():
    name = request.form.get('name', '').strip()
    age = request.form.get('age', '').strip()
    gender = request.form.get('gender', '').strip()
    dob = request.form.get('dob', '').strip()
    blood_group = request.form.get('blood_group', '').strip()
    mobile = request.form.get('mobile', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    doctor_id = request.form.get('doctor_id', '').strip()
    symptoms = request.form.get('symptoms', '').strip()
    notes = request.form.get('notes', '').strip()
    emergency_contact = request.form.get('emergency_contact', '').strip()

    if not name or not age or not gender or not dob:
        flash('Error: Patient Name, Age, Gender, and DOB are required fields.', 'danger')
        return redirect(url_for('patients_panel'))

    # Generate patient ID
    patient_id = f"PAT-{datetime.now().year}-{random.randint(1000, 9999)}"
    
    try:
        create_patient(patient_id, name, age, gender, dob, blood_group, mobile, email, address, doctor_id, symptoms, notes, emergency_contact)
        log_activity(session['username'], 'Patient Registered', f"Patient: {name} (ID: {patient_id})")
        flash('Patient Registered Successfully!', 'success')
    except Exception as e:
        logging.error(f"Failed to register patient: {e}")
        flash(f"Error: {e}", 'danger')
        
    return redirect(url_for('patients_panel'))


@app.route("/patients/edit", methods=['POST'])
@login_required
def edit_patient():
    if session.get('role') == 'Receptionist':
        flash('Error: Receptionist role cannot modify patient data.', 'danger')
        return redirect(url_for('patients_panel'))
        
    patient_id = request.form.get('patient_id')
    name = request.form.get('name', '').strip()
    age = request.form.get('age', '').strip()
    gender = request.form.get('gender', '').strip()
    dob = request.form.get('dob', '').strip()
    blood_group = request.form.get('blood_group', '').strip()
    mobile = request.form.get('mobile', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()
    doctor_id = request.form.get('doctor_id', '').strip()
    symptoms = request.form.get('symptoms', '').strip()
    notes = request.form.get('notes', '').strip()
    emergency_contact = request.form.get('emergency_contact', '').strip()

    try:
        update_patient(patient_id, name, age, gender, dob, blood_group, mobile, email, address, doctor_id, symptoms, notes, emergency_contact)
        log_activity(session['username'], 'Patient Updated', f"Patient ID: {patient_id}")
        flash('Patient Details Updated Successfully!', 'success')
    except Exception as e:
        logging.error(f"Failed to update patient: {e}")
        flash(f"Error: {e}", 'danger')
        
    return redirect(url_for('patients_panel'))


@app.route("/patients/delete/<patient_id>", methods=['POST'])
@admin_required
def remove_patient(patient_id):
    try:
        delete_patient(patient_id)
        log_activity(session['username'], 'Patient Deleted', f"Patient ID: {patient_id}")
        flash('Patient and associated predictions removed successfully.', 'success')
    except Exception as e:
        logging.error(f"Failed to delete patient: {e}")
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('patients_panel'))


# 3. MRI Predict Routing
@app.route("/mri_predict")
@login_required
def predict_panel():
    selected_patient = request.args.get('patient_id', '').strip()
    patients = get_patients()
    
    # Clear any residual report details in session when loading fresh
    session.pop('patient_report_data', None)
    return render_template('predict.html', patients=patients, selected_patient=selected_patient, patient_data=None, active_page='predict')


@app.route("/submit", methods=['POST'])
@login_required
def get_output():
    # Helper support for loading past prediction records
    patient_id_direct = request.form.get('patient_id_direct')
    if patient_id_direct:
        patient = get_patient(patient_id_direct)
        if patient:
            # Reconstruct details
            preds = get_predictions()
            match = next((p for p in preds if p['patient_id'] == patient_id_direct), None)
            
            session['patient_report_data'] = {
                'name': patient['name'],
                'age': patient['age'],
                'gender': patient['gender'],
                'dob': patient['dob'],
                'mobile': patient['mobile'] or 'N/A',
                'email': patient['email'] or 'N/A',
                'hospital_id': patient['patient_id'],
                'doctor': patient['doctor_name'] or 'N/A',
                'symptoms': patient['symptoms'] or 'None',
                'notes': patient['notes'] or 'None',
                'prediction': match['prediction_result'] if match else 'Stroke',
                'confidence': match['confidence'] if match else 100.0,
                'img_web_path': f"static/{match['mri_filename']}" if match else '',
                'img_disk_path': os.path.join(upload_folder, match['mri_filename']) if match else '',
                'datetime': match['predicted_at'] if match else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model_name': 'CNN',
                'inference_time': match['prediction_time'] if match else 0.0
            }
            
            if 'action_pdf' in request.form:
                return redirect(url_for('download_report'))
            
            patients = get_patients()
            return render_template("predict.html", patients=patients, patient_data=session['patient_report_data'], active_page='predict')

    # Core upload logic
    patient_id = request.form.get('patient_id', '').strip()
    if not patient_id:
        flash('Error: Patient selection is required for MRI diagnosis.', 'danger')
        return redirect(url_for('predict_panel'))
        
    patient = get_patient(patient_id)
    if not patient:
        flash('Error: Selected patient not found in database.', 'danger')
        return redirect(url_for('predict_panel'))

    # File uploads validation
    if 'my_image' not in request.files:
        flash('Error: No image file uploaded.', 'danger')
        return redirect(url_for('predict_panel'))
        
    img = request.files['my_image']
    if img.filename == '':
        flash('Error: No file selected.', 'danger')
        return redirect(url_for('predict_panel'))
        
    # File Extension check
    allowed_extensions = {'.jpg', '.jpeg', '.png'}
    _, ext = os.path.splitext(img.filename.lower())
    if ext not in allowed_extensions:
        flash('Error: Unsupported image format. Upload JPG, JPEG or PNG.', 'danger')
        return redirect(url_for('predict_panel'))

    # File Size check (10MB limit)
    img.seek(0, os.SEEK_END)
    file_size = img.tell()
    img.seek(0)
    if file_size > 10 * 1024 * 1024:
        flash('Error: MRI scan exceeds the 10 MB limit.', 'danger')
        return redirect(url_for('predict_panel'))

    # Save
    filename = f"scan_{patient_id}_{int(time.time())}{ext}"
    img_disk_path = os.path.join(upload_folder, filename)
    try:
        img.save(img_disk_path)
    except Exception as e:
        flash(f"Error saving image upload: {e}", 'danger')
        return redirect(url_for('predict_panel'))

    # Time prediction
    start_time = time.time()
    predict_class, confidence = predict_label(img_disk_path)
    inference_time = time.time() - start_time

    if confidence is None:
        flash(f"Error during AI Model execution: {predict_class}", 'danger')
        return redirect(url_for('predict_panel'))

    # Save Prediction to Database
    create_prediction(patient_id, filename, predict_class, confidence, inference_time)
    log_activity(session['username'], 'Prediction Generated', f"Patient ID: {patient_id}, Result: {predict_class}")

    session['patient_report_data'] = {
        'name': patient['name'],
        'age': patient['age'],
        'gender': patient['gender'],
        'dob': patient['dob'],
        'mobile': patient['mobile'] or 'N/A',
        'email': patient['email'] or 'N/A',
        'hospital_id': patient['patient_id'],
        'doctor': patient['doctor_name'] or 'N/A',
        'symptoms': patient['symptoms'] or 'None',
        'notes': patient['notes'] or 'None',
        'prediction': predict_class,
        'confidence': confidence,
        'img_web_path': f"static/{filename}",
        'img_disk_path': img_disk_path,
        'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'model_name': 'CNN',
        'inference_time': inference_time
    }

    patients = get_patients()
    return render_template("predict.html", patients=patients, patient_data=session['patient_report_data'], active_page='predict')


# 4. History Logs & Export Routing
@app.route("/history")
@login_required
def history():
    search_query = request.args.get('search', '').strip()
    predictions = get_predictions(search_query)
    return render_template('history.html', predictions=predictions, search_query=search_query, active_page='history')


@app.route("/reports/export/<format_type>")
@login_required
def export_reports(format_type):
    preds = get_predictions()
    
    # Generate CSV stream
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Patient ID', 'Patient Name', 'Diagnosis Result', 'Confidence (%)', 'Inference Runtime (s)', 'Inference Date & Time', 'Referring Doctor'])
    for p in preds:
        writer.writerow([
            p['patient_id'], p['patient_name'], p['prediction_result'],
            f"{p['confidence']:.2f}", f"{p['prediction_time']:.3f}", p['predicted_at'],
            p['doctor_name'] or 'N/A'
        ])
    
    csv_data = output.getvalue()
    
    filename = f"Stroke_Diagnostic_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


# 5. PDF Generation Route
@app.route("/download_report")
@login_required
def download_report():
    data = session.get('patient_report_data', None)
    if not data:
        flash('Error: No diagnostics context in session cache to download.', 'danger')
        return redirect(url_for('predict_panel'))
        
    # Enrich with latest branding settings
    try:
        settings = get_settings()
        data['hospital_name'] = settings.get('hospital_name', 'Brain Stroke AI Diagnostic Center')
        data['hospital_address'] = settings.get('hospital_address', 'Medical Science Park, Neurological Wing, Block-C')
        logo_path = settings.get('hospital_logo', '/static/images/bezier.png')
        
        if logo_path.startswith('/'):
            logo_path = logo_path[1:]
        logo_abs_path = os.path.join(BASE_DIR, logo_path)
        
        # Fallback to PNG if SVG is specified
        if logo_abs_path.endswith('.svg'):
            png_path = logo_abs_path[:-4] + '.png'
            if os.path.exists(png_path):
                logo_abs_path = png_path
                
        data['hospital_logo_path'] = logo_abs_path
    except Exception as ex:
        logging.error(f"Failed to enrich report data with settings: {ex}")
        
    pdf_filename = f"Diagnostic_Report_{data['hospital_id']}.pdf"
    pdf_path = os.path.join(upload_folder, pdf_filename)
    
    # Ensure upload directory exists
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    try:
        generate_pdf(data, pdf_path)
        log_activity(session['username'], 'Report Downloaded', f"Patient ID: {data['hospital_id']}")
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
    except Exception as e:
        logging.error(f"Failed to generate PDF: {e}")
        flash(f"Error generating PDF report: {e}", 'danger')
        return redirect(url_for('predict_panel'))


# 6. Admin Doctors Configurations
@app.route("/doctors")
@admin_required
def doctors_panel():
    docs = get_doctors()
    return render_template('doctors.html', doctors=docs, active_page='doctors')


@app.route("/doctors/add", methods=['POST'])
@admin_required
def add_doctor():
    name = request.form.get('name', '').strip()
    specialization = request.form.get('specialization', '').strip()
    contact = request.form.get('contact', '').strip()
    email = request.form.get('email', '').strip()

    if not name or not specialization:
        flash('Error: Name and specialization are required.', 'danger')
        return redirect(url_for('doctors_panel'))

    try:
        create_doctor(name, specialization, contact, email)
        log_activity(session['username'], 'Doctor Registered', f"Doctor: {name}")
        flash('Doctor Registered Successfully!', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('doctors_panel'))


@app.route("/doctors/edit", methods=['POST'])
@admin_required
def edit_doctor_details():
    doctor_id = request.form.get('doctor_id')
    name = request.form.get('name', '').strip()
    specialization = request.form.get('specialization', '').strip()
    contact = request.form.get('contact', '').strip()
    email = request.form.get('email', '').strip()
    status = request.form.get('status', '').strip()

    try:
        update_doctor(doctor_id, name, specialization, contact, email, status)
        log_activity(session['username'], 'Doctor Modified', f"Doctor ID: {doctor_id}")
        flash('Doctor details updated successfully.', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('doctors_panel'))


@app.route("/doctors/delete/<int:doctor_id>", methods=['POST'])
@admin_required
def remove_doctor(doctor_id):
    try:
        delete_doctor(doctor_id)
        log_activity(session['username'], 'Doctor Deleted', f"Doctor ID: {doctor_id}")
        flash('Doctor removed successfully.', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
    return redirect(url_for('doctors_panel'))


# 7. Admin Users Configurations
@app.route("/users")
@admin_required
def users_panel():
    users = list_users()
    audit_logs = list_activity_logs(50)
    return render_template('users.html', users=users, audit_logs=audit_logs, active_page='users')


@app.route("/users/add", methods=['POST'])
@admin_required
def add_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', '').strip()

    if not username or not password or not role:
        flash('Error: Username, password and role are required.', 'danger')
        return redirect(url_for('users_panel'))

    if create_user(username, password, role):
        log_activity(session['username'], 'User Registered', f"Username: {username}, Role: {role}")
        flash('New User Account Registered Successfully!', 'success')
    else:
        flash('Error: Username already exists.', 'danger')
    return redirect(url_for('users_panel'))


@app.route("/users/status/<username>", methods=['POST'])
@admin_required
def toggle_user_active(username):
    user = get_user(username)
    if user:
        new_status = 'Deactivated' if user['status'] == 'Active' else 'Active'
        update_user_status(username, new_status)
        log_activity(session['username'], 'User Status Modified', f"Username: {username}, Status: {new_status}")
        flash(f"User account '{username}' is now {new_status}.", 'success')
    return redirect(url_for('users_panel'))


@app.route("/users/reset-password", methods=['POST'])
@admin_required
def reset_password():
    username = request.form.get('username')
    new_password = request.form.get('new_password')
    
    update_user_password(username, new_password)
    log_activity(session['username'], 'User Password Reset', f"Username: {username}")
    flash(f"Password reset successfully for user account '{username}'.", 'success')
    return redirect(url_for('users_panel'))


# 8. Admin Settings Configurations
@app.route("/settings")
@admin_required
def settings_panel():
    settings = get_settings()
    return render_template('settings.html', settings=settings, active_page='settings')


@app.route("/settings/save", methods=['POST'])
@admin_required
def save_settings():
    hospital_name = request.form.get('hospital_name')
    hospital_address = request.form.get('hospital_address')
    hospital_logo = request.form.get('hospital_logo')
    prediction_threshold = request.form.get('prediction_threshold')

    try:
        update_setting('hospital_name', hospital_name)
        update_setting('hospital_address', hospital_address)
        update_setting('hospital_logo', hospital_logo)
        update_setting('prediction_threshold', prediction_threshold)
        
        # Sync branding in session
        session['hospital_name'] = hospital_name
        
        log_activity(session['username'], 'Settings Modified')
        flash('Portal configuration saved successfully!', 'success')
    except Exception as e:
        flash(f"Error: {e}", 'danger')
        
    return redirect(url_for('settings_panel'))


# 9. Logout
@app.route("/logout")
def log_out():
    username = session.get('username')
    if username:
        log_activity(username, 'User Logged Out')
    session.clear()
    logging.info("User logged out successfully.")
    return redirect(url_for('main'))


if __name__ == '__main__':
    app.run(debug=True)
