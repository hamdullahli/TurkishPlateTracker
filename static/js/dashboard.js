class Dashboard {
    constructor() {
        this.platesContainer = document.getElementById('latestPlates');
        this.chart = null;
        this.initChart();
        this.startDataPolling();
    }

    initChart() {
        const ctx = document.getElementById('detectionChart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Saatlik Algılama',
                    data: [],
                    borderColor: '#0066CC',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Algılama Sayısı'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Saat'
                        }
                    }
                }
            }
        });
    }

    async fetchPlates() {
        try {
            const response = await fetch('/api/plates');
            const plates = await response.json();
            this.updatePlatesList(plates);
            this.updateChart(plates);
        } catch (error) {
            console.error('Plaka verisi alınamadı:', error);
        }
    }

    updatePlatesList(plates) {
        const latest = plates.slice(-5).reverse();
        this.platesContainer.innerHTML = latest.map(plate => `
            <div class="plate-entry">
                <div class="plate-number">${plate.plate_number}</div>
                <div class="plate-confidence">Doğruluk: %${plate.confidence.toFixed(1)}</div>
                <div class="plate-timestamp">${new Date(plate.timestamp).toLocaleString('tr-TR')}</div>
                <div class="plate-status ${plate.is_authorized ? 'text-success' : 'text-danger'}">
                    ${plate.is_authorized ? 'Yetkili' : 'Yetkisiz'}
                </div>
            </div>
        `).join('');
    }

    updateChart(plates) {
        const hourlyData = new Map();

        plates.forEach(plate => {
            const hour = new Date(plate.timestamp).getHours();
            hourlyData.set(hour, (hourlyData.get(hour) || 0) + 1);
        });

        const sortedHours = Array.from(hourlyData.keys()).sort((a, b) => a - b);

        this.chart.data.labels = sortedHours.map(hour => `${hour}:00`);
        this.chart.data.datasets[0].data = sortedHours.map(hour => hourlyData.get(hour));
        this.chart.update();
    }

    startDataPolling() {
        this.fetchPlates();
        setInterval(() => this.fetchPlates(), 5000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const cameraStream = document.getElementById('cameraStream');
    if (cameraStream) {
        cameraStream.src = '/video_feed';
    }
    new Dashboard();
});