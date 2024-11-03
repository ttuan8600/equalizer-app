from flask import Flask, request, render_template, redirect, url_for
import os
import numpy as np
import scipy.signal as signal
import matplotlib
matplotlib.use('Agg')  # Chỉ định sử dụng back-end không cần GUI
import matplotlib.pyplot as plt
from scipy.io import wavfile
import librosa
import librosa.display
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Trang chủ để tải file và chọn bộ lọc
@app.route("/", methods=["GET", "POST"])
def index():
    ranges = {
        "sub_bass_gain": "20–60 Hz",
        "bass_gain": "60–250 Hz",
        "low_mid_gain": "250–500 Hz",
        "mid_gain": "500–2000 Hz",
        "upper_mid_gain": "2000–4000 Hz",
        "presence_gain": "4000–6000 Hz",
        "brilliance_gain": "6000–20000 Hz"
    }
    return render_template("index.html", ranges=ranges)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Đọc giá trị của các thanh trượt equalizer từ form
    gains = [
        int(request.form["sub_bass_gain"]),
        int(request.form["bass_gain"]),
        int(request.form["low_mid_gain"]),
        int(request.form["mid_gain"]),
        int(request.form["upper_mid_gain"]),
        int(request.form["presence_gain"]),
        int(request.form["brilliance_gain"]),
    ]

    # Chuyển hướng đến hàm process_audio để xử lý file
    gains_str = ",".join(map(str, gains))  # Chuyển đổi danh sách gains thành chuỗi
    return redirect(url_for("process_audio", filename=filename, gains=gains_str))

@app.route("/process/<filename>")
def process_audio(filename):
    # Đọc giá trị từ query parameters
    gains_str = request.args.get("gains", "0,0,0,0,0,0,0")
    gains = list(map(int, gains_str.split(",")))  # Chuyển đổi chuỗi thành danh sách các số nguyên

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    rate, data = wavfile.read(file_path)

    # Nếu có gain khác 0, tiến hành xử lý equalizer
    filtered_data = apply_equalizer(data, rate, gains)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], "filtered_" + filename)
    wavfile.write(output_path, rate, filtered_data.astype(np.int16))

    # Render biểu đồ phổ và waveform
    plt.figure(figsize=(10, 4))
    plt.plot(data, label="Original Signal", color="blue", alpha=0.7)
    plt.plot(filtered_data, label="Equalized Signal", color="red", alpha=0.7)
    plt.legend()
    plt.savefig("static/output.png")

    # Biểu đồ phổ (Spectrogram)
    y, sr = librosa.load(file_path)
    plt.figure(figsize=(10, 4))
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    S_dB = librosa.power_to_db(S, ref=np.max)
    librosa.display.specshow(S_dB, sr=sr, fmax=8000, x_axis='time', y_axis='mel')
    plt.colorbar(format='%+2.0f dB')
    plt.savefig("static/spectrogram.png")

    # Vẽ biểu đồ so sánh tín hiệu đầu vào và đầu ra ở miền tần số
    plot_frequency_domain_comparison(data, filtered_data, rate)

    # Gọi hàm vẽ đáp ứng tần số của các bộ lọc
    plot_filter_response()
    
    return render_template("result.html",
                           filename="output.png",
                           spectrogram="spectrogram.png",
                           filter_response="filter_response.png",
                           frequency_comparison="frequency_comparison.png")

def apply_equalizer(data, rate, gains):
    if all(gain == 0 for gain in gains):
        return data
    
    # Các băng tần và độ lợi tương ứng từ form (sub_bass, bass, low_mid, mid, upper_mid, presence, brilliance)
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

    # Thiết lập các tần số cắt cho từng băng tần
    bands = {
        'sub_bass': [20, 60],
        'bass': [60, 250],
        'low_mid': [250, 500],
        'mid': [500, 2000],
        'upper_mid': [2000, 4000],
        'presence': [4000, 6000],
        'brilliance': [6000, 11024],  
    }

    # Tạo bản sao dữ liệu để áp dụng bộ lọc và điều chỉnh độ lợi
    filtered_data = np.zeros_like(data, dtype=np.float32)

    # Áp dụng từng bộ lọc band-pass cho các băng tần và cộng chúng lại
    for band, gain in gains_dict.items():
        low, high = bands[band]
        sos = signal.butter(4, [low, high], btype='bandpass', fs=rate, output='sos')
        filtered_band = signal.sosfilt(sos, data)

        # Chuyển đổi gain từ dB sang tỷ lệ tuyến tính
        linear_gain = 10 ** (gain / 20)
        filtered_data += linear_gain * filtered_band  # Điều chỉnh theo gain của băng tần

    # Chuẩn hóa dữ liệu sau khi cộng các băng tần
    filtered_data = np.clip(filtered_data, -32767, 32767)
    return filtered_data.astype(np.int16)

def plot_filter_response():
    # Định nghĩa các tần số cắt cho từng băng tần
    bands = {
        'sub_bass': [20, 60],
        'bass': [60, 250],
        'low_mid': [250, 500],
        'mid': [500, 2000],
        'upper_mid': [2000, 4000],
        'presence': [4000, 6000],
        'brilliance': [6000, 11024],
    }

    plt.figure(figsize=(12, 8))

    # Vẽ đáp ứng tần số cho từng bộ lọc
    for band, (low, high) in bands.items():
        sos = signal.butter(4, [low, high], btype='bandpass', fs=44100, output='sos')
        w, h = signal.sosfreqz(sos, worN=2000, fs=44100)
        plt.plot(w, 20 * np.log10(abs(h)), label=f'{band.capitalize()} Band')

    plt.title('Frequency Response of Equalizer Bands')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Amplitude (dB)')
    plt.grid()
    plt.legend()
    plt.xlim(20, 11000)  # Giới hạn trục x để rõ hơn
    plt.ylim(-30, 5)  # Giới hạn trục y để nhìn thấy rõ hơn
    plt.savefig("static/filter_response.png")
    plt.close()

def plot_frequency_domain_comparison(original_data, filtered_data, rate):
    plt.figure(figsize=(12, 6))

    # Biến đổi Fourier cho tín hiệu đầu vào
    original_freq_data = np.fft.fft(original_data)
    original_freq = np.fft.fftfreq(len(original_freq_data), 1 / rate)
    plt.plot(original_freq[:len(original_freq) // 2], 
             np.abs(original_freq_data)[:len(original_freq) // 2], 
             label="Original Signal", color="blue")  # Thêm alpha ở đây

    # Biến đổi Fourier cho tín hiệu sau khi lọc
    filtered_freq_data = np.fft.fft(filtered_data)
    filtered_freq = np.fft.fftfreq(len(filtered_freq_data), 1 / rate)
    plt.plot(filtered_freq[:len(filtered_freq) // 2], 
             np.abs(filtered_freq_data)[:len(filtered_freq) // 2], 
             label="Filtered Signal", color="red", alpha=0.7)  # Thêm alpha ở đây

    plt.title("Frequency Domain Comparison of Original and Filtered Signals")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid()
    plt.savefig("static/frequency_comparison.png")
    plt.close()

if __name__ == "__main__":
    app.run(debug=True)
