class Dashboard {
    constructor() {
        this.platesContainer = document.getElementById('latest-plates');
        this.chart = null;
        this.initChart();
        this.startDataPolling();
    }

    initChart() {
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            return;
        }

        const ctx = document.getElementById('detectionChart');
        if (!ctx) {
            console.error('Canvas element not found');
            return;
        }

        this.chart = new Chart(ctx.getContext('2d'), {
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
        if (!this.platesContainer) {
            console.error('Plates container not found');
            return;
        }

        const latest = plates.slice(-5).reverse();
        this.platesContainer.innerHTML = latest.map(plate => `
            <div class="plate-entry">
                <div class="plate-number">${plate.plate_number}</div>
                <div class="plate-confidence">Doğruluk: %${plate.confidence.toFixed(1)}</div>
                <div class="plate-timestamp">${new Date(plate.timestamp).toLocaleString('tr-TR')}</div>
            </div>
        `).join('');
    }

    updateChart(plates) {
        if (!this.chart) {
            console.error('Chart is not initialized');
            return;
        }

        const hourlyData = new Map();
        const now = new Date();
        const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        // Initialize all hours with 0
        for (let i = 0; i < 24; i++) {
            hourlyData.set(i, 0);
        }

        plates.forEach(plate => {
            const plateTime = new Date(plate.timestamp);
            if (plateTime >= dayStart) {
                const hour = plateTime.getHours();
                hourlyData.set(hour, (hourlyData.get(hour) || 0) + 1);
            }
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

// Wait for DOM and Chart.js to load
window.addEventListener('load', () => {
    if (document.getElementById('detectionChart')) {
        const dashboard = new Dashboard();
        setInterval(() => dashboard.simulateNewDetection(), 10000);
    }
});