import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stroke_clinical.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and default users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- Admin, Doctor, Receptionist
            status TEXT NOT NULL DEFAULT 'Active', -- Active, Deactivated
            created_at TEXT NOT NULL
        )
    ''')
    
    # 2. Patients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            dob TEXT NOT NULL,
            blood_group TEXT,
            mobile TEXT,
            email TEXT,
            address TEXT,
            doctor_id INTEGER,
            symptoms TEXT,
            notes TEXT,
            emergency_contact TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    ''')
    
    # 3. Predictions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            mri_filename TEXT NOT NULL,
            prediction_result TEXT NOT NULL,
            confidence REAL NOT NULL,
            prediction_time REAL NOT NULL, -- in seconds
            predicted_at TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
        )
    ''')
    
    # 4. Doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            contact TEXT,
            email TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL
        )
    ''')
    
    # 5. Activity Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 6. Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''''')
    
    conn.commit()
    
    # Seed default settings
    default_settings = {
        'hospital_name': 'Brain Stroke AI Diagnostic Center',
        'hospital_address': 'Medical Science Park, Neurological Wing, Block-C',
        'hospital_logo': '/static/images/bezier.svg',
        'app_version': '1.0',
        'model_version': 'CNN-v1.0',
        'prediction_threshold': '0.5'
    }
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    
    # Seed default users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        users_to_seed = [
            ('admin', generate_password_hash('password'), 'Admin', 'Active', now),
            ('doctor', generate_password_hash('password'), 'Doctor', 'Active', now),
            ('receptionist', generate_password_hash('password'), 'Receptionist', 'Active', now)
        ]
        cursor.executemany(
            "INSERT INTO users (username, password_hash, role, status, created_at) VALUES (?, ?, ?, ?, ?)",
            users_to_seed
        )
        
    # Seed default doctors if empty
    cursor.execute("SELECT COUNT(*) FROM doctors")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doctors_to_seed = [
            ('Dr. Gregory House', 'Neurology', '555-0199', 'house@hospital.org', 'Active', now),
            ('Dr. Allison Cameron', 'Radiology', '555-0120', 'cameron@hospital.org', 'Active', now),
            ('Dr. Robert Chase', 'Intensive Care', '555-0144', 'chase@hospital.org', 'Active', now)
        ]
        cursor.executemany(
            "INSERT INTO doctors (name, specialization, contact, email, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            doctors_to_seed
        )
    
    conn.commit()
    conn.close()

# Users Operations
def get_user(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def create_user(username, password, role, status='Active'):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, generate_password_hash(password), role, status, now)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def update_user_status(username, status):
    conn = get_db_connection()
    conn.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))
    conn.commit()
    conn.close()

def update_user_password(username, new_password):
    conn = get_db_connection()
    conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (generate_password_hash(new_password), username))
    conn.commit()
    conn.close()

def list_users():
    conn = get_db_connection()
    users = conn.execute("SELECT id, username, role, status, created_at FROM users").fetchall()
    conn.close()
    return users

# Doctors Operations
def get_doctors():
    conn = get_db_connection()
    docs = conn.execute("SELECT * FROM doctors").fetchall()
    conn.close()
    return docs

def create_doctor(name, specialization, contact, email):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO doctors (name, specialization, contact, email, status, created_at) VALUES (?, ?, ?, ?, 'Active', ?)",
        (name, specialization, contact, email, now)
    )
    conn.commit()
    conn.close()

def update_doctor(doctor_id, name, specialization, contact, email, status):
    conn = get_db_connection()
    conn.execute(
        "UPDATE doctors SET name = ?, specialization = ?, contact = ?, email = ?, status = ? WHERE id = ?",
        (name, specialization, contact, email, status, doctor_id)
    )
    conn.commit()
    conn.close()

def delete_doctor(doctor_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    conn.commit()
    conn.close()

# Patient Operations
def get_patients(search_query=None):
    conn = get_db_connection()
    if search_query:
        query = f"%{search_query}%"
        patients = conn.execute(
            """SELECT p.*, d.name as doctor_name FROM patients p 
               LEFT JOIN doctors d ON p.doctor_id = d.id 
               WHERE p.name LIKE ? OR p.patient_id LIKE ? OR p.mobile LIKE ?""",
            (query, query, query)
        ).fetchall()
    else:
        patients = conn.execute(
            "SELECT p.*, d.name as doctor_name FROM patients p LEFT JOIN doctors d ON p.doctor_id = d.id ORDER BY p.created_at DESC"
        ).fetchall()
    conn.close()
    return patients

def get_patient(patient_id):
    conn = get_db_connection()
    patient = conn.execute(
        "SELECT p.*, d.name as doctor_name FROM patients p LEFT JOIN doctors d ON p.doctor_id = d.id WHERE p.patient_id = ?",
        (patient_id,)
    ).fetchone()
    conn.close()
    return patient

def create_patient(patient_id, name, age, gender, dob, blood_group, mobile, email, address, doctor_id, symptoms, notes, emergency_contact):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO patients (patient_id, name, age, gender, dob, blood_group, mobile, email, address, doctor_id, symptoms, notes, emergency_contact, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (patient_id, name, age, gender, dob, blood_group, mobile, email, address, doctor_id or None, symptoms, notes, emergency_contact, now)
    )
    conn.commit()
    conn.close()

def update_patient(patient_id, name, age, gender, dob, blood_group, mobile, email, address, doctor_id, symptoms, notes, emergency_contact):
    conn = get_db_connection()
    conn.execute(
        """UPDATE patients SET name = ?, age = ?, gender = ?, dob = ?, blood_group = ?, mobile = ?, email = ?, address = ?, doctor_id = ?, symptoms = ?, notes = ?, emergency_contact = ?
           WHERE patient_id = ?""",
        (name, age, gender, dob, blood_group, mobile, email, address, doctor_id or None, symptoms, notes, emergency_contact, patient_id)
    )
    conn.commit()
    conn.close()

def delete_patient(patient_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
    conn.execute("DELETE FROM predictions WHERE patient_id = ?", (patient_id,))
    conn.commit()
    conn.close()

# Predictions Operations
def create_prediction(patient_id, mri_filename, prediction_result, confidence, prediction_time):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO predictions (patient_id, mri_filename, prediction_result, confidence, prediction_time, predicted_at) VALUES (?, ?, ?, ?, ?, ?)",
        (patient_id, mri_filename, prediction_result, confidence, prediction_time, now)
    )
    conn.commit()
    conn.close()

def get_predictions(search_query=None):
    conn = get_db_connection()
    if search_query:
        query = f"%{search_query}%"
        preds = conn.execute(
            """SELECT pr.*, p.name as patient_name, d.name as doctor_name FROM predictions pr
               JOIN patients p ON pr.patient_id = p.patient_id
               LEFT JOIN doctors d ON p.doctor_id = d.id
               WHERE p.name LIKE ? OR pr.patient_id LIKE ? OR pr.prediction_result LIKE ?
               ORDER BY pr.predicted_at DESC""",
            (query, query, query)
        ).fetchall()
    else:
        preds = conn.execute(
            """SELECT pr.*, p.name as patient_name, d.name as doctor_name FROM predictions pr
               JOIN patients p ON pr.patient_id = p.patient_id
               LEFT JOIN doctors d ON p.doctor_id = d.id
               ORDER BY pr.predicted_at DESC"""
        ).fetchall()
    conn.close()
    return preds

def get_predictions_by_patient(patient_id):
    conn = get_db_connection()
    preds = conn.execute("SELECT * FROM predictions WHERE patient_id = ? ORDER BY predicted_at DESC", (patient_id,)).fetchall()
    conn.close()
    return preds

# Logs & Activity
def log_activity(username, action, details=None):
    conn = get_db_connection()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO activity_logs (username, action, details, created_at) VALUES (?, ?, ?, ?)",
        (username, action, details, now)
    )
    conn.commit()
    conn.close()

def list_activity_logs(limit=100):
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return logs

# Settings Operations
def get_settings():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def update_setting(key, value):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# Analytics Dashboard Calculations
def get_dashboard_stats():
    conn = get_db_connection()
    stats = {}
    
    # 1. Total Patients
    stats['total_patients'] = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    
    # 2. Total Predictions
    stats['total_predictions'] = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    
    # 3. Today's Predictions
    today = datetime.now().strftime("%Y-%m-%d")
    stats['today_predictions'] = conn.execute("SELECT COUNT(*) FROM predictions WHERE predicted_at LIKE ?", (f"{today}%",)).fetchone()[0]
    
    # 4. Stroke Cases Count
    stats['stroke_cases'] = conn.execute("SELECT COUNT(*) FROM predictions WHERE prediction_result LIKE '%Stroke%'").fetchone()[0]
    
    # 5. Normal Cases Count
    stats['normal_cases'] = conn.execute("SELECT COUNT(*) FROM predictions WHERE prediction_result NOT LIKE '%Stroke%'").fetchone()[0]
    
    # 6. Total Doctors
    stats['total_doctors'] = conn.execute("SELECT COUNT(*) FROM doctors WHERE status = 'Active'").fetchone()[0]
    
    # 7. Averages
    avg_conf_row = conn.execute("SELECT AVG(confidence) FROM predictions").fetchone()[0]
    stats['avg_confidence'] = round(avg_conf_row, 2) if avg_conf_row is not None else 0.0
    
    avg_time_row = conn.execute("SELECT AVG(prediction_time) FROM predictions").fetchone()[0]
    stats['avg_time'] = round(avg_time_row, 3) if avg_time_row is not None else 0.000
    
    # 8. Recent predictions (limit 5)
    stats['recent_predictions'] = conn.execute(
        """SELECT pr.*, p.name as patient_name FROM predictions pr
           JOIN patients p ON pr.patient_id = p.patient_id
           ORDER BY pr.predicted_at DESC LIMIT 5"""
    ).fetchall()

    # 9. Charts Data
    # 9a. Predictions by Day (last 7 days)
    days_data = conn.execute(
        """SELECT date(predicted_at) as pred_date, count(*) as count 
           FROM predictions 
           GROUP BY pred_date 
           ORDER BY pred_date DESC LIMIT 7"""
    ).fetchall()
    stats['chart_daily_labels'] = [d['pred_date'] for d in reversed(days_data)]
    stats['chart_daily_values'] = [d['count'] for d in reversed(days_data)]
    
    # 9b. Predictions by Month (Current Year)
    year = datetime.now().year
    months_data = conn.execute(
        f"""SELECT strftime('%m', predicted_at) as month_val, count(*) as count 
           FROM predictions 
           WHERE strftime('%Y', predicted_at) = '{year}' 
           GROUP BY month_val"""
    ).fetchall()
    month_names = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr', '05': 'May', '06': 'Jun',
        '07': 'Jul', '08': 'Aug', '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
    }
    stats['chart_monthly_labels'] = [month_names.get(m['month_val'], m['month_val']) for m in months_data]
    stats['chart_monthly_values'] = [m['count'] for m in months_data]
    
    # 9c. Gender Distribution
    gender_data = conn.execute(
        """SELECT gender, count(*) as count FROM patients GROUP BY gender"""
    ).fetchall()
    stats['chart_gender_labels'] = [g['gender'] for g in gender_data]
    stats['chart_gender_values'] = [g['count'] for g in gender_data]
    
    # 9d. Age Distribution (0-18, 19-35, 36-50, 51-65, 66+)
    ages = conn.execute("SELECT age FROM patients").fetchall()
    brackets = {'0-18': 0, '19-35': 0, '36-50': 0, '51-65': 0, '66+': 0}
    for row in ages:
        age = row['age']
        if age <= 18: brackets['0-18'] += 1
        elif age <= 35: brackets['19-35'] += 1
        elif age <= 50: brackets['36-50'] += 1
        elif age <= 65: brackets['51-65'] += 1
        else: brackets['66+'] += 1
    stats['chart_age_labels'] = list(brackets.keys())
    stats['chart_age_values'] = list(brackets.values())

    conn.close()
    return stats
