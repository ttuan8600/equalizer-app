from flask import Flask, render_template, request, send_file
import os
from pydub import AudioSegment
from pydub.effects import equalizer

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"

        file = request.files['file']
        if file.filename == '':
            return "No selected file"

        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Example: apply some basic equalization (placeholder logic)
            audio = AudioSegment.from_file(file_path)
            # Process the audio (e.g., increase bass, mid, treble)
            processed_path = os.path.join(app.config['PROCESSED_FOLDER'], 'processed_' + file.filename)
            audio.export(processed_path, format="mp3")

            return send_file(processed_path, as_attachment=True)
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
