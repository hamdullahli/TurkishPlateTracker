class CameraManager {
    constructor() {
        this.cameraContainer = document.getElementById('camera-feed');
        this.currentCameraId = null;
        this.streamImg = null;
        this.init();
    }

    async init() {
        try {
            console.log('Kamera yöneticisi başlatılıyor...');
            // Get active cameras
            const response = await fetch('/api/active_cameras');
            const cameras = await response.json();
            console.log('Aktif kameralar:', cameras);

            if (cameras && cameras.length > 0) {
                console.log('İlk kamera seçildi:', cameras[0]);
                this.setupCameraStream(cameras[0].id);
            } else {
                console.warn('Aktif kamera bulunamadı');
                this.showNoActiveCameras();
            }
        } catch (error) {
            console.error('Kamera bilgileri alınamadı:', error);
            this.showError();
        }
    }

    setupCameraStream(cameraId) {
        this.currentCameraId = cameraId;
        console.log(`${cameraId} ID'li kamera için stream ayarlanıyor`);

        // Clear existing content
        this.cameraContainer.innerHTML = '';

        // Create image element for the stream
        this.streamImg = document.createElement('img');
        this.streamImg.style.width = '100%';
        this.streamImg.style.height = '100%';
        this.streamImg.style.objectFit = 'contain';
        this.streamImg.src = `/video_feed/${cameraId}`;

        // Add error handling for stream
        this.streamImg.onerror = (error) => {
            console.error('Kamera stream yüklenirken hata:', error);
            this.showError();
        };

        // Add load event to confirm stream starts
        this.streamImg.onload = () => {
            console.log('Kamera stream başarıyla başlatıldı');
        };

        this.cameraContainer.appendChild(this.streamImg);
    }

    showNoActiveCameras() {
        console.warn('Aktif kamera bulunamadı uyarısı gösteriliyor');
        this.cameraContainer.innerHTML = `
            <div class="alert alert-warning">
                Aktif kamera bulunamadı. Lütfen kamera ayarlarından bir kamera ekleyin ve aktifleştirin.
            </div>
        `;
    }

    showError() {
        console.error('Kamera hatası gösteriliyor');
        this.cameraContainer.innerHTML = `
            <div class="alert alert-danger">
                Kamera görüntüsü alınamadı. Lütfen bağlantıyı kontrol edin.
            </div>
        `;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('CameraManager başlatılıyor...');
    const cameraManager = new CameraManager();
});