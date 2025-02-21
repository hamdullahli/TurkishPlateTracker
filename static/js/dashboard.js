class Dashboard {
    constructor() {
        this.platesContainer = document.getElementById('latest-plates');
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
                    label: 'Detections per hour',
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
                        beginAtZero: true
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
            console.error('Error fetching plates:', error);
        }
    }

    updatePlatesList(plates) {
        const latest = plates.slice(-5).reverse();
        this.platesContainer.innerHTML = latest.map(plate => `
            <div class="plate-entry">
                <div class="plate-number">${plate.plate_number}</div>
                <div class="plate-confidence">Confidence: ${plate.confidence.toFixed(1)}%</div>
                <div class="plate-timestamp">${new Date(plate.timestamp).toLocaleString()}</div>
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

    simulateNewDetection() {
        const mockPlate = {
            plate_number: 'simulated',
            confidence: Math.random() * 15 + 85,
            timestamp: new Date().toISOString()
        };

        fetch('/api/plates', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(mockPlate)
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new Dashboard();
    
    // Simulate new detections periodically
    setInterval(() => dashboard.simulateNewDetection(), 10000);
});
