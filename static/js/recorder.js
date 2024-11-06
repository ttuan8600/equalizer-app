let mediaRecorder;
let audioChunks = [];
let audioContext;
let analyser;
let dataArray;
let canvas;
let canvasCtx;
let animationId;

function setCanvasResolution(canvas) {
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * ratio;
    canvas.height = canvas.offsetHeight * ratio;
    canvas.getContext('2d').scale(ratio, ratio);
}

document.getElementById('start-recording').addEventListener('click', async (event) => {
    event.preventDefault();
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    analyser.fftSize = 2048;
    const bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);

    canvas = document.getElementById('waveform');
    setCanvasResolution(canvas);
    canvasCtx = canvas.getContext('2d');

    drawRealTimeWaveform();

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        // console.log(audioUrl)
        // const a = document.createElement('a');
        // a.href = audioUrl;
        // a.download = 'recording.webm';
        // document.body.appendChild(a);
        // a.click();
        // document.body.removeChild(a);
        // const audio = document.getElementById('audioPlayback');
        // audio.src = audioUrl;

        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        await fetch('/upload_rec', {
            method: 'POST',
            body: formData
        });

        cancelAnimationFrame(animationId);
        drawRecordedWaveform(audioBlob);

        document.getElementById('start-recording').disabled = false;
        document.getElementById('stop-recording').disabled = true;
    };

    mediaRecorder.start();
    document.getElementById('start-recording').disabled = true;
    document.getElementById('stop-recording').disabled = false;
});

document.getElementById('stop-recording').addEventListener('click', (event) => {
    event.preventDefault();
    mediaRecorder.stop();
    // document.getElementById("process-button").disabled = false;
});

function drawRealTimeWaveform() {
    animationId = requestAnimationFrame(drawRealTimeWaveform);

    analyser.getByteTimeDomainData(dataArray);

    canvasCtx.fillStyle = '#fff';
    canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = '#3DD74A';

    canvasCtx.beginPath();

    const sliceWidth = canvas.width * 1.0 / analyser.fftSize;
    let x = 0;

    for (let i = 0; i < analyser.fftSize; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * canvas.height / 2;

        if (i === 0) {
            canvasCtx.moveTo(x, y);
        } else {
            canvasCtx.lineTo(x, y);
        }

        x += sliceWidth;
    }

    canvasCtx.lineTo(canvas.width, canvas.height / 2);
    canvasCtx.stroke();
}

function drawRecordedWaveform(audioBlob) {
    const fileReader = new FileReader();
    fileReader.onload = function() {
        audioContext.decodeAudioData(fileReader.result, function(buffer) {
            const rawData = buffer.getChannelData(0); // Get the first channel
            const samples = 500; // Number of samples to plot
            const blockSize = Math.floor(rawData.length / samples); // Number of samples in each subdivision
            const filteredData = [];
            for (let i = 0; i < samples; i++) {
                filteredData.push(rawData[i * blockSize]);
            }
            drawWaveForm(filteredData);
        });
    };
    fileReader.readAsArrayBuffer(audioBlob);
}

function drawWaveForm(data) {
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = '#FF5F40';
    canvasCtx.beginPath();

    const sliceWidth = canvas.width * 1.0 / data.length;
    let x = 0;

    for (let i = 0; i < data.length; i++) {
        const v = data[i] * 0.5 + 0.5;
        const y = v * canvas.height;

        if (i === 0) {
            canvasCtx.moveTo(x, y);
        } else {
            canvasCtx.lineTo(x, y);
        }

        x += sliceWidth;
    }

    canvasCtx.lineTo(canvas.width, canvas.height / 2);
    canvasCtx.stroke();
}