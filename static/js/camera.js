class CameraManager {
    constructor() {
        this.cameraContainer = document.getElementById('camera-feed');
        this.currentCameraId = null;
        this.streamImg = null;
        this.init();
    }

    async init() {
        try {
            // Get active cameras
            const response = await fetch('/api/active_cameras');
            const cameras = await response.json();

            if (cameras && cameras.length > 0) {
                this.setupCameraStream(cameras[0].id);
            } else {
                this.showNoActiveCameras();
            }
        } catch (error) {
            console.error('Kamera bilgileri alınamadı:', error);
            this.showError();
        }
    }

    setupCameraStream(cameraId) {
        this.currentCameraId = cameraId;

        // Clear existing content
        this.cameraContainer.innerHTML = '';

        // Create image element for the stream
        this.streamImg = document.createElement('img');
        this.streamImg.style.width = '100%';
        this.streamImg.style.height = '100%';
        this.streamImg.style.objectFit = 'contain';
        this.streamImg.src = `/video_feed/${cameraId}`;

        this.cameraContainer.appendChild(this.streamImg);
    }

    showNoActiveCameras() {
        this.cameraContainer.innerHTML = `
            <div class="alert alert-warning">
                Aktif kamera bulunamadı. Lütfen kamera ayarlarından bir kamera ekleyin ve aktifleştirin.
            </div>
        `;
    }

    showError() {
        this.cameraContainer.innerHTML = `
            <div class="alert alert-danger">
                Kamera görüntüsü alınamadı. Lütfen bağlantıyı kontrol edin.
            </div>
        `;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const cameraManager = new CameraManager();
});