
class CameraSimulator {
    constructor() {
        this.detectionBox = document.getElementById('detection-box');
        if (this.detectionBox) {
            this.isDetecting = false;
            this.start();
        }
    }

    simulateDetection() {
        if (!this.detectionBox || this.isDetecting) return;
        
        this.isDetecting = true;
        const width = Math.random() * 30 + 20;
        const height = Math.random() * 10 + 5;
        const left = Math.random() * (100 - width);
        const top = Math.random() * (100 - height);

        this.detectionBox.style.display = 'block';
        this.detectionBox.style.width = `${width}%`;
        this.detectionBox.style.height = `${height}%`;
        this.detectionBox.style.left = `${left}%`;
        this.detectionBox.style.top = `${top}%`;

        setTimeout(() => {
            this.detectionBox.style.display = 'none';
            this.isDetecting = false;
        }, 1000);
    }

    start() {
        setInterval(() => this.simulateDetection(), 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CameraSimulator();
});
