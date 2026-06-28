from flask import Flask, render_template, request, redirect, url_for, session, send_file
from tensorflow.keras.models import load_model
import cv2
import os
import numpy as np
import pickle
import logging
import random
from datetime import datetime
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

# Ensure static upload directory exists
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)
    logging.info(f"Created upload directory at {upload_folder}")

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


# Routes
@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form:
            username = request.form['username']
            password = request.form['password']
            if username == 'admin' and password == 'password':
                # Clear any leftover report details on new login
                session.pop('patient_report_data', None)
                logging.info(f"User '{username}' logged in successfully.")
                return render_template('index.html', msg="you have successfully logged-in")
            else:
                msg = 'Please enter correct credentials !'
                logging.warn(f"Failed login attempt for user '{username}'.")
                return render_template('sign-in.html', msg=msg)
    
    # Reset session data when visiting login/registration page fresh
    session.pop('patient_report_data', None)
    return render_template('sign-in.html', msg="")


@app.route("/submit", methods=['POST'])
def get_output():
    if request.method == 'POST':
        # 1. Parse Patient Registration Details
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        dob = request.form.get('dob', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip()
        hospital_id = request.form.get('hospital_id', '').strip()
        doctor = request.form.get('doctor', '').strip()
        symptoms = request.form.get('symptoms', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Validation for required patient fields
        if not name or not age or not gender or not dob:
            logging.warn("Required patient registration fields are missing.")
            return render_template("index.html", error="Error: Patient Name, Age, Gender, and DOB are required.")
            
        # Generate Hospital ID if missing
        if not hospital_id:
            hospital_id = f"HOSP-{datetime.now().year}-{random.randint(1000, 9999)}"
            
        # 2. File Upload Validation
        if 'my_image' not in request.files:
            logging.warn("No file uploaded in the request.")
            return render_template("index.html", error="Error: No file uploaded.")
            
        img = request.files['my_image']
        if img.filename == '':
            logging.warn("Empty filename uploaded.")
            return render_template("index.html", error="Error: No file selected.")
            
        # Extension validation
        allowed_extensions = {'.jpg', '.jpeg', '.png'}
        _, ext = os.path.splitext(img.filename.lower())
        if ext not in allowed_extensions:
            logging.warn(f"Unsupported file type uploaded: {ext}")
            return render_template("index.html", error="Error: Unsupported file format. Please upload JPG, JPEG, or PNG.")
            
        # File Size validation (limit to 10MB)
        img.seek(0, os.SEEK_END)
        file_size = img.tell()
        img.seek(0)  # Reset pointer
        max_size = 10 * 1024 * 1024  # 10 MB
        if file_size > max_size:
            logging.warn(f"Uploaded file size too large: {file_size} bytes")
            return render_template("index.html", error="Error: File size exceeds the 10 MB limit.")
            
        # Save file
        filename = img.filename
        img_disk_path = os.path.join(upload_folder, filename)
        try:
            img.save(img_disk_path)
            logging.info(f"Uploaded file saved to {img_disk_path}")
        except Exception as e:
            logging.error(f"Failed to save uploaded file: {e}")
            return render_template("index.html", error=f"Error saving upload: {e}")
            
        # 3. Model Prediction
        predict_class, confidence = predict_label(img_disk_path)
        
        if confidence is None:
            # Prediction failed
            return render_template("index.html", error=predict_class)
            
        # 4. Save details to session
        session['patient_report_data'] = {
            'name': name,
            'age': age,
            'gender': gender,
            'dob': dob,
            'mobile': mobile or 'N/A',
            'email': email or 'N/A',
            'hospital_id': hospital_id,
            'doctor': doctor or 'N/A',
            'symptoms': symptoms or 'None',
            'notes': notes or 'None',
            'prediction': predict_class,
            'confidence': confidence,
            'img_web_path': f"static/{filename}",
            'img_disk_path': img_disk_path,
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'model_name': 'CNN'
        }
        
        return render_template("index.html", patient_data=session['patient_report_data'])
        
    return render_template("index.html", error="Invalid request method.")


@app.route("/download_report")
def download_report():
    data = session.get('patient_report_data', None)
    if not data:
        logging.warn("Attempted report download with no patient session data.")
        return "Error: No patient diagnostic report found in this session.", 400
        
    pdf_filename = f"Brain_Stroke_Report_{data['hospital_id']}.pdf"
    pdf_path = os.path.join(upload_folder, pdf_filename)
    
    try:
        logging.info(f"Generating diagnostic report PDF at {pdf_path}")
        generate_pdf(data, pdf_path)
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)
    except Exception as e:
        logging.error(f"Failed to generate diagnostic report PDF: {e}")
        return f"Error generating PDF report: {e}", 500


@app.route("/logout")
def log_out():
    session.pop('patient_report_data', None)
    logging.info("User logged out.")
    return redirect(url_for('main'))


if __name__ == '__main__':
    app.run(debug=True)
