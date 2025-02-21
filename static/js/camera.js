class CameraSimulator {
    constructor() {
        this.detectionBox = document.getElementById('detection-box');
        this.isDetecting = false;
    }

    simulateDetection() {
        if (this.isDetecting) return;
        
        this.isDetecting = true;
        const width = Math.random() * 30 + 20; // 20-50% of width
        const height = Math.random() * 10 + 5;  // 5-15% of height
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
    const camera = new CameraSimulator();
    camera.start();
});
