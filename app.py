from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from urllib.parse import unquote
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key_for_dev_only')

# Configuration for file uploads
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    metadata = load_metadata()
    return render_template('index.html', images=metadata)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'adminpassword':  # Replace 'adminpassword' with your secure password
            session['logged_in'] = True
            return redirect(url_for('upload_file'))
        else:
            return 'Unauthorized', 401
    return render_template('admin_login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        file = request.files['file']
        title = request.form['title']
        description = request.form['description']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Save metadata
            metadata = load_metadata()
            new_image_metadata = {
                'filename': filename,
                'title': title,
                'description': description,
                'upload_date': datetime.now().strftime('%Y-%m-%d'),
                'likes': 0
            }
            metadata.append(new_image_metadata)
            save_metadata(metadata)

            return redirect(url_for('gallery'))

    # Render the upload form when method is GET
    return render_template('upload.html')


def load_metadata():
    metadata_path = 'metadata.json'
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            try:
                metadata = json.load(f)
            except json.JSONDecodeError:
                metadata = []
    else:
        metadata = []
    return metadata

def save_metadata(metadata):
    metadata_path = 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)

@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    search_query = request.form.get('search', '').lower() if request.method == 'POST' else ''
    orientation = request.form.get('orientation', 'all')
    size = request.form.get('size', 'all')
    color = request.form.get('color', '').lower()

    metadata = load_metadata()

    filtered_images = []

    for img in metadata:
        # Filter by search query
        if search_query and search_query not in img['title'].lower():
            continue
        
        filtered_images.append(img)

    return render_template('gallery.html', images=filtered_images)


@app.route('/like/<filename>', methods=['POST'])
def like_image(filename):
    filename = unquote(filename)
    metadata = load_metadata()

    img = None
    for img in metadata:
        if img['filename'] == filename:
            img['likes'] += 1
            break

    if img:
        save_metadata(metadata)
        return jsonify({'likes': img['likes']})
    else:
        return jsonify({'error': 'Image not found'}), 404

@app.route('/download/<filename>/<resolution>', methods=['GET'])
def download_file(filename, resolution):
    filename = unquote(filename)
    if resolution == 'original':
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    else:
        parts = resolution.split('x')
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            width, height = map(int, parts)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img = Image.open(image_path)
            img_resized = img.resize((width, height), Image.ANTIALIAS)
            resized_filename = f'resized_{width}x{height}_{filename}'
            resized_path = os.path.join(app.config['UPLOAD_FOLDER'], resized_filename)
            img_resized.save(resized_path)
            return send_from_directory(app.config['UPLOAD_FOLDER'], resized_filename, as_attachment=True)
        return 'Invalid resolution format', 400

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
