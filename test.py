from flask import Flask, request, jsonify
import easyocr
import re
from PIL import Image, ImageEnhance
import numpy as np
import cv2
import io

app = Flask(__name__)

def enhance_image(image):
    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    img = enhancer.enhance(2)  # Increase contrast by a factor of 2

    # Convert the image to a format suitable for OpenCV
    img = np.array(img)

    # Convert RGB to BGR (OpenCV format)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Apply sharpening kernel
    kernel = np.array([[0, -1, 0],
                       [-1, 5,-1],
                       [0, -1, 0]])
    img = cv2.filter2D(img, -1, kernel)

    # Convert BGR to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply denoising
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)

    # Apply adaptive thresholding
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                 cv2.THRESH_BINARY, 11, 2)

    # Apply histogram equalization
    gray = cv2.equalizeHist(gray)

    # Convert the image back to RGB (Pillow format)
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    img = Image.fromarray(img)

    return img

def check_image_properties(image):
    image_bytes = io.BytesIO(image.read())
    file_size = image_bytes.getbuffer().nbytes
    if file_size > 2 * 1024 * 1024:  # 2 MB limit
        return False, "File size exceeds 2 MB."

    image.seek(0)
    img = Image.open(image)
    width, height = img.size
    if width > 1500 or height > 1500:
        img.thumbnail((1500, 1500))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format=img.format)
        img_bytes.seek(0)
        return True, img_bytes, img.format

    image.seek(0)
    return True, image_bytes, img.format

def extract_number(image, num_digits, enhance=False):
    is_valid, processed_image, img_format = check_image_properties(image)
    if not is_valid:
        return None, None, processed_image

    processed_image.seek(0)
    img = Image.open(processed_image)

    if enhance:
        img = enhance_image(img)

    img_bytes = io.BytesIO()
    img.save(img_bytes, format=img_format)  # Explicitly specify the format
    img_bytes.seek(0)

    reader = easyocr.Reader(['en'])
    result = reader.readtext(img_bytes.getvalue())
    pattern = re.compile(rf'^\d{{{num_digits}}}$')

    for (bbox, text, prob) in result:
        if pattern.match(text):
            return f'pv{text}', prob, None

    return None, None, f"No {num_digits}-digit number found."

@app.route('/extract8', methods=['POST'])
def extract8():
    if 'file' not in request.files:
        return jsonify({'error': 'File is required'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    text, prob, error = extract_number(file, 8)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'text': text, 'probability': prob}), 200

@app.route('/extract6', methods=['POST'])
def extract6():
    if 'file' not in request.files:
        return jsonify({'error': 'File is required'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    text, prob, error = extract_number(file, 6, enhance=True)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'text': text, 'probability': prob}), 200

if __name__ == '__main__':
    app.run(debug=True)
