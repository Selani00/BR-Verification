from flask import Flask, request, jsonify
import easyocr
import re
import os
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def check_image_properties(image_path):
    file_size = os.path.getsize(image_path)
    if file_size > 2 * 1024 * 1024:  # 2 MB limit
        return False, "File size exceeds 2 MB."

    with Image.open(image_path) as img:
        width, height = img.size
        if width > 1500 or height > 1500:
            img.thumbnail((1500, 1500))
            img.save(image_path)

    return True, None

def extract_8_digit_number(image_path):
    is_valid, error_message = check_image_properties(image_path)
    if not is_valid:
        return None, None, error_message

    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path)
    pattern = re.compile(r'^\d{8}$')

    for (bbox, text, prob) in result:
        if pattern.match(text):
            return f'pv{text}', prob, None

    return None, None, "No 8-digit number found."

@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        text, prob, error = extract_8_digit_number(file_path)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'text': text, 'probability': prob}), 200

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
