// Form Submit — injeksi cart dari LocalStorage
document.getElementById('checkoutForm').addEventListener('submit', function (e) {
    let cart = localStorage.getItem('doc_cart')
    if (!cart || cart === '[]') {
        e.preventDefault()
        showToast('Keranjang Anda kosong! Silakan belanja terlebih dahulu.', 'error');
        window.location.href = "/market/" 
        return
    }
    document.getElementById('cart_data_input').value = cart
})

// Toggle Pembayaran
function togglePembayaran() {
    const isTransfer = document.querySelector('input[name="pembayaran"]:checked').value === 'TF'
    document.getElementById('transferContainer').classList.toggle('hidden', !isTransfer)
    document.getElementById('buktiInput').required = isTransfer
}

// Kalkulasi Harga
function formatRupiah(angka) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(angka)
}

let cartSubtotal = 0

document.addEventListener('DOMContentLoaded', () => {
    const cart = JSON.parse(localStorage.getItem('doc_cart')) || []
    cartSubtotal = cart.reduce((sum, item) => sum + item.harga * item.qty, 0)
    updateTotalUI(0)
})

function updateTotalUI(ongkir) {
    const grandTotal = cartSubtotal + ongkir
    document.getElementById('subtotalDisplay').innerText = formatRupiah(cartSubtotal)
    document.getElementById('ongkirDisplay').innerText = formatRupiah(ongkir)
    document.getElementById('grandTotalDisplay').innerText = formatRupiah(grandTotal)
}

// Peta & Logistik
let map, routingControl, userMarker
const farmLat = -0.44875377355076096
const farmLng = 117.09608147598206

function togglePengiriman() {
    const isAntar = document.querySelector('input[name="pengiriman"]:checked').value === 'ANT'
    const mapContainer = document.getElementById('mapContainer')
    const alamatInput = document.getElementById('alamatInput')

    if (isAntar) {
        mapContainer.classList.remove('hidden')
        alamatInput.required = true

        if (!map) {
            setTimeout(() => {
                const batasIndonesia = L.latLngBounds(L.latLng(-11.0, 94.0), L.latLng(6.0, 141.0))

                map = L.map('map', {
                    maxBounds: batasIndonesia,
                    maxBoundsViscosity: 1.0,
                    minZoom: 5
                }).setView([farmLat, farmLng], 12)

                L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' + '&copy; <a href="https://carto.com/attributions">CARTO</a>'
                }).addTo(map)

                L.marker([farmLat, farmLng]).addTo(map).bindPopup('<b>Peternakan Kelompok Tani Melati</b>').openPopup()

                map.on('click', function (e) {
                    updateLokasiPengiriman(e.latlng.lat, e.latlng.lng)
                })
            }, 100)
        }
    } else {
        mapContainer.classList.add('hidden')
        alamatInput.required = false
        updateTotalUI(0) 
    }
}

function updateLokasiPengiriman(lat, lng) {
    if (!map) return 

    document.getElementById('latInput').value = lat
    document.getElementById('lngInput').value = lng

    if (userMarker) map.removeLayer(userMarker)
    userMarker = L.marker([lat, lng]).addTo(map).bindPopup('Lokasi Tujuan').openPopup()

    if (routingControl) {
        map.removeControl(routingControl)
        routingControl = null
    }

    routingControl = L.Routing.control({
        waypoints: [L.latLng(farmLat, farmLng), L.latLng(lat, lng)],
        routeWhileDragging: false,
        addWaypoints: false,
        fitSelectedRoutes: true,
        show: false
    }).addTo(map)

    routingControl.on('routesfound', function (e) {
        const distanceKm = (e.routes[0].summary.totalDistance / 1000).toFixed(2)
        document.getElementById('jarakInput').value = distanceKm

        const biayaOngkir = Math.round(distanceKm * 5000) 
        updateTotalUI(biayaOngkir)

        const infoJarak = document.getElementById('infoJarak')
        infoJarak.innerHTML = `<span class="material-symbols-outlined text-[18px]">route</span> ` + `Jarak: <strong>${distanceKm} km</strong> (Ongkir: ${formatRupiah(biayaOngkir)})`
        infoJarak.classList.remove('hidden')
    })

    routingControl.on('routingerror', function () {
        const distanceKm = (map.distance([farmLat, farmLng], [lat, lng]) / 1000).toFixed(2)
        document.getElementById('jarakInput').value = distanceKm

        const biayaOngkir = Math.round(distanceKm * 5000)
        updateTotalUI(biayaOngkir)

        const infoJarak = document.getElementById('infoJarak')
        infoJarak.innerHTML = `<span class="material-symbols-outlined text-[18px]">route</span> ` + `Jarak estimasi: <strong>${distanceKm} km</strong> (Ongkir: ${formatRupiah(biayaOngkir)})`
        infoJarak.classList.remove('hidden')
    })
}

function cariLokasi() {
    const query = document.getElementById('searchAlamat').value
    if (!query) {
        showToast('Silakan masukkan nama jalan atau daerah terlebih dahulu.', 'error');
        return
    }

    const btnCari = document.querySelector('button[onclick="cariLokasi()"]')
    const originalText = btnCari.innerHTML
    btnCari.innerHTML = 'Mencari...'
    btnCari.disabled = true

    fetch(`https://nominatim.openstreetmap.org/search?format=json` + `&q=${encodeURIComponent(query)}&countrycodes=id`)
        .then((res) => res.json())
        .then((data) => {
            if (data && data.length > 0) {
                const lat = parseFloat(data[0].lat)
                const lng = parseFloat(data[0].lon)
                map.setView([lat, lng], 15)
                updateLokasiPengiriman(lat, lng)
            } else {
                showToast('Lokasi tidak ditemukan. Coba gunakan nama kecamatan atau kota.', 'error');
            }
        })
        .catch((err) => {
            console.error('Error Geocoding:', err)
            showToast('Gagal menghubungi server pencarian peta.', 'error');
        })
        .finally(() => {
            btnCari.innerHTML = originalText
            btnCari.disabled = false
        })
}

async function requestOTP() {
    const hpInput = document.getElementById('hp').value;
    const btnOtp = document.getElementById('btn-otp');
    const otpMessage = document.getElementById('otp-message');

    // 1. Validasi Input Kosong
    if (!hpInput || hpInput.length < 10) {
        if (typeof showToast === 'function') {
            showToast('Silakan masukkan nomor WhatsApp yang valid terlebih dahulu.', 'error');
        } else {
            alert('Silakan masukkan nomor WhatsApp yang valid terlebih dahulu.');
        }
        document.getElementById('hp').focus();
        return;
    }

    // Ambil token CSRF Django dari form (Wajib untuk request POST agar tidak di-blokir keamanan Django)
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // 2. Simpan tampilan awal tombol
    const originalContent = btnOtp.innerHTML;

    // 3. Ubah tombol menjadi mode Loading / Memproses
    btnOtp.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">refresh</span> Mengirim...`;
    btnOtp.disabled = true;
    btnOtp.classList.add('opacity-70', 'cursor-not-allowed');

    try {
        // 4. Kirim Request Data ke API Django
        const response = await fetch('/api/send-otp/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken // Token Keamanan
            },
            body: JSON.stringify({ hp: hpInput })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            // JIKA BERHASIL MENGIRIM OTP
            btnOtp.innerHTML = `<span class="material-symbols-outlined text-[18px]">check_circle</span> Terkirim`;
            btnOtp.classList.replace('bg-primary', 'bg-green-600'); 
            
            otpMessage.innerHTML = `<span class="material-symbols-outlined text-[14px] text-green-600">mark_email_read</span> OTP telah dikirim ke <b>${hpInput}</b>. Cek WhatsApp Anda.`;
            otpMessage.classList.add('text-green-700');

            if (typeof showToast === 'function') {
                // Pastikan fungsi showToast mendukung notif sukses (di base_web.html)
                showToast(data.message || 'Kode OTP berhasil dikirim ke WhatsApp Anda.', 'success');
            }

            document.getElementById('otp').focus();

            // Hitung Mundur (Cooldown 60 detik) sebelum bisa kirim ulang OTP
            let countdown = 60;
            const interval = setInterval(() => {
                countdown--;
                btnOtp.innerHTML = `<span class="material-symbols-outlined text-[18px]">timer</span> Tunggu (${countdown}s)`;
                if (countdown <= 0) {
                    clearInterval(interval);
                    btnOtp.innerHTML = originalContent; // Kembalikan tombol seperti semula
                    btnOtp.disabled = false;
                    btnOtp.classList.remove('opacity-70', 'cursor-not-allowed');
                    btnOtp.classList.replace('bg-green-600', 'bg-primary');
                }
            }, 1000);

        } else {
            // JIKA API MERESPON DENGAN ERROR (Misal: Batas limit pengiriman tercapai / nomor tidak valid)
            throw new Error(data.message || "Gagal mengirim pesan dari sistem.");
        }

    } catch (error) {
        // Tangkap Error (Baik dari API maupun gangguan jaringan)
        console.error("OTP Error:", error);
        
        // Kembalikan tombol ke bentuk semula agar user bisa coba lagi
        btnOtp.innerHTML = originalContent;
        btnOtp.disabled = false;
        btnOtp.classList.remove('opacity-70', 'cursor-not-allowed');
        
        if (typeof showToast === 'function') {
            showToast(error.message || 'Gagal terhubung ke server untuk mengirim OTP.', 'error');
        } else {
            alert(error.message || 'Gagal terhubung ke server.');
        }
    }
}