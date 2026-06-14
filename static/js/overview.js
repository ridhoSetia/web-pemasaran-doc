document.addEventListener("DOMContentLoaded", function() {
    const ctx = document.getElementById('revenueChart').getContext('2d');
    
    // Parsing data aman dari Django JSON
    const labels = JSON.parse('{{ chart_labels|safe }}');
    const data = JSON.parse('{{ chart_data|safe }}');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Pendapatan (Rp)',
                data: data,
                borderColor: '#143D11', // Warna Hijau Primary DOC Mart
                backgroundColor: 'rgba(20, 61, 17, 0.1)', // Efek gradient bawah
                borderWidth: 2,
                pointBackgroundColor: '#143D11',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.3 // Membuat garis sedikit melengkung elegan
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Penting agar tinggi grafik mengikuti div pembungkusnya
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let value = context.raw;
                            return new Intl.NumberFormat('id-ID', { 
                                style: 'currency', currency: 'IDR', minimumFractionDigits: 0 
                            }).format(value);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false } // Hilangkan garis vertikal agar lebih bersih
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            // Format sumbu Y (contoh: 1.000.000 menjadi 1Jt)
                            if (value >= 1000000) return 'Rp ' + (value / 1000000) + 'Jt';
                            if (value >= 1000) return 'Rp ' + (value / 1000) + 'k';
                            return value;
                        }
                    }
                }
            }
        }
    });
});