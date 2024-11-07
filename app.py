from flask import Flask, request, render_template, redirect, url_for, send_from_directory, jsonify
import os
import numpy as np
import scipy.signal as signal
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.io import wavfile
import librosa
import librosa.display
from werkzeug.utils import secure_filename
import wave
from pydub import AudioSegment
import io

app = Flask(__name__, static_folder="static")
UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

bands = {
    'sub_bass': [20, 60],
    'bass': [60, 250],
    'low_mid': [250, 500],
    'mid': [500, 2000],
    'upper_mid': [2000, 4000],
    'presence': [4000, 6000],
}

@app.route("/", methods=["GET", "POST"])
def index():
    ranges = {
        "sub_bass_gain": "20–60 Hz",
        "bass_gain": "60–250 Hz",
        "low_mid_gain": "250–500 Hz",
        "mid_gain": "500–2000 Hz",
        "upper_mid_gain": "2000–4000 Hz",
        "presence_gain": "4000–6000 Hz",
        "brilliance_gain": "6000–22000 Hz"
    }
    return render_template("index.html", ranges=ranges)


@app.route("/upload", methods=["POST"])
def upload():
    gains = [
        int(request.form["sub_bass_gain"]),
        int(request.form["bass_gain"]),
        int(request.form["low_mid_gain"]),
        int(request.form["mid_gain"]),
        int(request.form["upper_mid_gain"]),
        int(request.form["presence_gain"]),
        int(request.form["brilliance_gain"]),
    ]

    gains_str = ",".join(map(str, gains))
    
    file = request.files["file"]
    if not file:
        file = request.files.get("audio_recorded")
        return redirect(url_for("process_audio", filename=secure_filename(file.filename), gains=gains_str))
        
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    return redirect(url_for("process_audio", filename=filename, gains=gains_str))


@app.route("/process/<filename>")
def process_audio(filename):
    gains_str = request.args.get("gains", "0,0,0,0,0,0,0")
    gains = list(map(int, gains_str.split(",")))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    rate, data = wavfile.read(file_path)
    print (f"Rate: {rate}")

    if rate <= 22500:
        bands['brilliance'] = [6000, 11024]
    else:
        bands['brilliance'] = [6000, 22000]

    filtered_data = apply_equalizer(data, rate, gains)
    fn = "filtered_" + filename
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
    wavfile.write(output_path, rate, filtered_data.astype(np.int16))

    plt.figure(figsize=(10, 4))
    plt.plot(data, label="Original Signal", color="blue", alpha=0.7)
    plt.plot(filtered_data, label="Equalized Signal", color="red", alpha=0.7)
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper right')
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.savefig("static/output.png")

    y, sr = librosa.load(file_path)
    plt.figure(figsize=(10, 4))
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    S_dB = librosa.power_to_db(S, ref=np.max)
    librosa.display.specshow(S_dB, sr=sr, fmax=8000, x_axis='time', y_axis='mel')
    plt.colorbar(format='%+2.0f dB')
    plt.savefig("static/spectrogram.png")

    plot_frequency_domain_comparison(data, filtered_data, rate)
    plot_filter_response()

    return render_template("result.html",
                           audio=fn,
                           filename="output.png",
                           spectrogram="spectrogram.png",
                           filter_response="filter_response.png",
                           frequency_comparison="frequency_comparison.png")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def apply_equalizer(data, rate, gains):
    if data.size == 0:
        return np.array([], dtype=np.int16)
    if all(gain == 0 for gain in gains):
        return data

    gains_dict = {
        'sub_bass': gains[0],
        'bass': gains[1],
        'low_mid': gains[2],
        'mid': gains[3],
        'upper_mid': gains[4],
        'presence': gains[5],
        'brilliance': gains[6],
    }

    print(gains_dict)

    filtered_data = np.zeros_like(data, dtype=np.float32)

    for band, gain in gains_dict.items():
        low, high = bands[band]
        sos = signal.butter(4, [low, high], btype='bandpass', fs=rate, output='sos')
        filtered_band = signal.sosfilt(sos, data)

        linear_gain = 10 ** (gain / 20)
        print(f"Band: {band}, Gain (dB): {gain}, Linear Gain: {linear_gain}")

        filtered_data += linear_gain * filtered_band

    filtered_data = np.clip(filtered_data, -32767, 32767)
    return filtered_data.astype(np.int16)

def plot_filter_response():

    plt.figure(figsize=(10, 4))

    for band, (low, high) in bands.items():
        sos = signal.butter(4, [low, high], btype='bandpass', fs=44100, output='sos')
        w, h = signal.sosfreqz(sos, worN=2000, fs=44100)
        plt.plot(w, 20 * np.log10(abs(h)), label=f'{band.capitalize()} Band')

    plt.title('Frequency Response of Equalizer Bands')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Amplitude (dB)')
    plt.grid()
    plt.legend()
    plt.xlim(20, 11000)
    plt.ylim(-30, 5)
    plt.savefig("static/filter_response.png")
    plt.close()

def plot_frequency_domain_comparison(original_data, filtered_data, rate):
    plt.figure(figsize=(10, 4))

    original_freq_data = np.fft.fft(original_data)
    original_freq = np.fft.fftfreq(len(original_freq_data), 1 / rate)
    plt.plot(original_freq[:len(original_freq) // 2],
             np.abs(original_freq_data)[:len(original_freq) // 2],
             label="Original Signal", color="blue")

    filtered_freq_data = np.fft.fft(filtered_data)
    filtered_freq = np.fft.fftfreq(len(filtered_freq_data), 1 / rate)
    plt.plot(filtered_freq[:len(filtered_freq) // 2],
             np.abs(filtered_freq_data)[:len(filtered_freq) // 2],
             label="Filtered Signal", color="red", alpha=0.7)

    plt.title("Frequency Domain Comparison of Original and Filtered Signals")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), loc='upper right')
    plt.grid()
    plt.savefig("static/frequency_comparison.png")
    plt.close()

@app.route('/rec_audio', methods=['POST'])
def rec_audio():
    if 'audio_data' not in request.files:
        return jsonify({"error": "No audio file found"}), 400

    audio_file = request.files['audio_data']

    audio = AudioSegment.from_file(io.BytesIO(audio_file.read()), format="wav")
    audio = audio.set_channels(1)
    wav_data = io.BytesIO()
    audio.export(wav_data, format="wav")
    wav_data.seek(0)

    waveform_data = extract_waveform_data(wav_data)
    return jsonify(waveform_data)

def extract_waveform_data(file_path):
    with wave.open(file_path, 'rb') as wf:
        n_frames = wf.getnframes()
        frame_rate = wf.getframerate()
        audio_data = wf.readframes(n_frames)
        audio_data = np.frombuffer(audio_data, dtype=np.int16)

        downsample_factor = max(1, len(audio_data) // 1000)
        audio_data = audio_data[::downsample_factor]

        return {
            "frame_rate": frame_rate,
            "data": audio_data.tolist()
        }

@app.route('/upload_rec', methods=['POST'])
def upload_rec():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file in request'}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    webm_file_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_file.filename)
    audio_file.save(webm_file_path)
    
    audio = AudioSegment.from_file(webm_file_path)
    wav_path = os.path.splitext(webm_file_path)[0] + '.wav'
    audio.export(wav_path, format='wav')

    return jsonify({'message': 'File uploaded successfully', 'wav_path': wav_path})

@app.route("/get_recording", methods=["GET"])
def get_recording():
    filename = "recording.wav"
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True)
