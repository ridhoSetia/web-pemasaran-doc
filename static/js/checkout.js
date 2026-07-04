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
// ==========================================
let map, routingControl, userMarker;

// 1. Fungsi penarik koordinat dan harga dari HTML (Pengaturan Admin)
const getStoreLat = () => parseFloat(document.getElementById('store_lat_setting')?.value) || -0.5020;
const getStoreLng = () => parseFloat(document.getElementById('store_lng_setting')?.value) || 117.1530;
const getBiayaKm = () => parseInt(document.getElementById('biaya_per_km_setting')?.value) || 5000;

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

                // Inisialisasi Peta (Titik tengah mengikuti data dinamis getStoreLat & getStoreLng)
                map = L.map('map').setView([getStoreLat(), getStoreLng()], 13);

                // Tambahkan Tombol Full Screen
                if (L.control.fullscreen) {
                    L.control.fullscreen({
                        position: 'topleft',
                        title: 'Layar Penuh',
                        titleCancel: 'Keluar Layar Penuh'
                    }).addTo(map);
                }

                // Layer Satelit
                L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
                    maxZoom: 20,
                    attribution: '© <a href="https://maps.google.com">Google Maps</a>'
                }).addTo(map);

                // Marker Toko (Juga mengikuti koordinat dinamis)
                L.marker([getStoreLat(), getStoreLng()]).addTo(map).bindPopup('<b>Titik Peternakan / Toko</b>').openPopup()

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

    // Tarik Garis Rute (Dari koordinat toko dinamis ke titik klik)
    routingControl = L.Routing.control({
        waypoints: [L.latLng(getStoreLat(), getStoreLng()), L.latLng(lat, lng)],
        routeWhileDragging: false,
        addWaypoints: false,
        fitSelectedRoutes: true,
        show: false
    }).addTo(map)

    routingControl.on('routesfound', function (e) {
        const distanceKm = (e.routes[0].summary.totalDistance / 1000).toFixed(2)
        document.getElementById('jarakInput').value = distanceKm

        // Ongkir dinamis
        const biayaOngkir = Math.round(distanceKm * getBiayaKm()) 
        updateTotalUI(biayaOngkir)

        const infoJarak = document.getElementById('infoJarak')
        infoJarak.innerHTML = `<span class="material-symbols-outlined text-[18px]">route</span> Jarak: <strong>${distanceKm} km</strong> (Ongkir: ${formatRupiah(biayaOngkir)})`
        infoJarak.classList.remove('hidden')
    })

    routingControl.on('routingerror', function () {
        // Fallback jarak lurus jika rute jalan tidak ditemukan (Menggunakan titik toko dinamis)
        const distanceKm = (map.distance([getStoreLat(), getStoreLng()], [lat, lng]) / 1000).toFixed(2)
        document.getElementById('jarakInput').value = distanceKm

        // Ongkir dinamis
        const biayaOngkir = Math.round(distanceKm * getBiayaKm())
        updateTotalUI(biayaOngkir)

        const infoJarak = document.getElementById('infoJarak')
        infoJarak.innerHTML = `<span class="material-symbols-outlined text-[18px]">route</span> Jarak estimasi lurus: <strong>${distanceKm} km</strong> (Ongkir: ${formatRupiah(biayaOngkir)})`
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

    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=id`)
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

    if (!hpInput || hpInput.length < 10) {
        if (typeof showToast === 'function') {
            showToast('Silakan masukkan nomor WhatsApp yang valid terlebih dahulu.', 'error');
        } else {
            alert('Silakan masukkan nomor WhatsApp yang valid terlebih dahulu.');
        }
        document.getElementById('hp').focus();
        return;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const originalContent = btnOtp.innerHTML;

    btnOtp.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">refresh</span> Mengirim...`;
    btnOtp.disabled = true;
    btnOtp.classList.add('opacity-70', 'cursor-not-allowed');

    try {
        const response = await fetch('/api/send-otp/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ hp: hpInput })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            btnOtp.innerHTML = `<span class="material-symbols-outlined text-[18px]">check_circle</span> Terkirim`;
            btnOtp.classList.replace('bg-primary', 'bg-green-600'); 
            
            otpMessage.innerHTML = `<span class="material-symbols-outlined text-[14px] text-green-600">mark_email_read</span> OTP telah dikirim ke <b>${hpInput}</b>. Cek WhatsApp Anda.`;
            otpMessage.classList.add('text-green-700');

            if (typeof showToast === 'function') {
                showToast(data.message || 'Kode OTP berhasil dikirim ke WhatsApp Anda.', 'success');
            }

            document.getElementById('otp').focus();

            let countdown = 60;
            const interval = setInterval(() => {
                countdown--;
                btnOtp.innerHTML = `<span class="material-symbols-outlined text-[18px]">timer</span> Tunggu (${countdown}s)`;
                if (countdown <= 0) {
                    clearInterval(interval);
                    btnOtp.innerHTML = originalContent;
                    btnOtp.disabled = false;
                    btnOtp.classList.remove('opacity-70', 'cursor-not-allowed');
                    btnOtp.classList.replace('bg-green-600', 'bg-primary');
                }
            }, 1000);

        } else {
            throw new Error(data.message || "Gagal mengirim pesan dari sistem.");
        }

    } catch (error) {
        console.error("OTP Error:", error);
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