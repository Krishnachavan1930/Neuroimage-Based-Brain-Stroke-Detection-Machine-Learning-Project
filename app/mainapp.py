# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, redirect, url_for
from tensorflow.keras.models import load_model
import cv2
import os
import numpy as np
import pickle
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

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
        return "Model loading error. Please check server logs."
    
    try:
        logging.info(f"Running prediction for image: {img_path}")
        image = cv2.imread(img_path)
        if image is None:
            logging.error(f"Failed to read image at {img_path}")
            return "Error: Invalid or corrupted image."
            
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (224, 224))
        image = np.resize(image, (1, image.shape[0], image.shape[1], image.shape[2]))
        image = image / 255.0
        
        pred = model.predict(image)
        pred_decoded = le.inverse_transform(pred)
        
        predicted_class = pred_decoded[0] if len(pred_decoded) > 0 else "Unknown"
        logging.info(f"Prediction result: {predicted_class}")
        return f"The prediction is {predicted_class}!"
        
    except Exception as e:
        logging.error(f"Prediction exception: {e}")
        return f"Error during prediction: {e}"


# Routes
@app.route("/", methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        if 'username' in request.form and 'password' in request.form:
            username = request.form['username']
            password = request.form['password']
            if username == 'admin' and password == 'password':
                msg = 'you have successfully logged-in'
                logging.info(f"User '{username}' logged in successfully.")
                return render_template('index.html', msg=msg)
            else:
                msg = 'Please enter correct credentials !'
                logging.warn(f"Failed login attempt for user '{username}'.")
                return render_template('sign-in.html', msg=msg)
    return render_template('sign-in.html', msg="")


@app.route("/submit", methods=['POST'])
def get_output():
    if request.method == 'POST':
        if 'my_image' not in request.files:
            logging.warn("No file uploaded in the request.")
            p = "No file chosen"
            return render_template("index.html", prediction=p)
            
        img = request.files['my_image']
        if img.filename == '':
            logging.warn("Empty filename uploaded.")
            p = "No file selected"
            return render_template("index.html", prediction=p)
            
        if img:
            filename = img.filename
            img_disk_path = os.path.join(upload_folder, filename)
            
            try:
                img.save(img_disk_path)
                logging.info(f"Uploaded file saved to {img_disk_path}")
            except Exception as e:
                logging.error(f"Failed to save uploaded file: {e}")
                p = f"Error saving upload: {e}"
                return render_template("index.html", prediction=p)
                
            p = predict_label(img_disk_path)
            img_web_path = f"static/{filename}"
            return render_template("index.html", prediction=p, img_path=img_web_path)
            
    p = "Choose appropriate file"
    return render_template("index.html", prediction=p)


@app.route("/logout")
def log_out():
    logging.info("User logged out.")
    return redirect(url_for('main'))


if __name__ == '__main__':
    app.run(debug=True)
