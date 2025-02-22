// Kamera görüntüsü işleme ve gösterme
let cameraStream = null;

function startStream() {
    const img = document.getElementById('cameraStream');
    if (img) {
        img.src = '/video_feed';
    }
}

function stopStream() {
    const img = document.getElementById('cameraStream');
    if (img) {
        img.src = '';
    }
}

// Sayfa yüklendiğinde stream'i başlat
document.addEventListener('DOMContentLoaded', () => {
    startStream();
});