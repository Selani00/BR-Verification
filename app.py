from flask import Flask, request, jsonify
import easyocr
import re
from PIL import Image
import io

app = Flask(__name__)

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
        return True, img_bytes

    image.seek(0)
    return True, image_bytes

def extract_8_digit_number(image):
    is_valid, processed_image = check_image_properties(image)
    if not is_valid:
        return None, None, processed_image

    reader = easyocr.Reader(['en'])
    result = reader.readtext(processed_image.getvalue())
    pattern = re.compile(r'^\d{6,8}$')

    for (bbox, text, prob) in result:
        if pattern.match(text):
            return f'pv{text}', prob, None

    return None, None, "No Company Number found."

@app.route('/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    text, prob, error = extract_8_digit_number(file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'text': text, 'probability': prob}), 200

if __name__ == '__main__':
    app.run(debug=True)
