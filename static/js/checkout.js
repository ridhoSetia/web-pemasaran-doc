
// Form Submit — injeksi cart dari LocalStorage
document.getElementById('checkoutForm').addEventListener('submit', function (e) {
    let cart = localStorage.getItem('doc_cart')
    if (!cart || cart === '[]') {
        e.preventDefault()
        alert('Keranjang Anda kosong! Silakan belanja terlebih dahulu.')
        window.location.href = "{% url 'store:market' %}"
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

// Peta & Logistik — satu definisi bersih
let map, routingControl, userMarker
const farmLat = -0.44875377355076096
const farmLng = 117.09608147598206

// Satu-satunya definisi togglePengiriman
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

                L.marker([farmLat, farmLng]).addTo(map).bindPopup('<b>Peternakan DOC Mart</b>').openPopup()

                // Click listener didaftarkan SETELAH map siap
                map.on('click', function (e) {
                    updateLokasiPengiriman(e.latlng.lat, e.latlng.lng)
                })
            }, 100)
        }
    } else {
        mapContainer.classList.add('hidden')
        alamatInput.required = false
        updateTotalUI(0) // Reset ongkir saat pilih Ambil Sendiri
    }
}

// routingControl.on() ada DI DALAM fungsi ini, bukan di luar
function updateLokasiPengiriman(lat, lng) {
    if (!map) return // Guard: abaikan jika peta belum siap

    document.getElementById('latInput').value = lat
    document.getElementById('lngInput').value = lng

    if (userMarker) map.removeLayer(userMarker)
    userMarker = L.marker([lat, lng]).addTo(map).bindPopup('Lokasi Tujuan').openPopup()

    if (routingControl) {
        map.removeControl(routingControl)
        routingControl = null
    }

    // .addTo(map) dichain langsung — routingControl langsung valid
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

        const biayaOngkir = Math.round(distanceKm * 5000) // Rp5.000/km
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

// Geocoding pencarian alamat
function cariLokasi() {
    const query = document.getElementById('searchAlamat').value
    if (!query) {
        alert('Silakan masukkan nama jalan atau daerah terlebih dahulu.')
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
                alert('Lokasi tidak ditemukan. Coba gunakan nama kecamatan atau kota.')
            }
        })
        .catch((err) => {
            console.error('Error Geocoding:', err)
            alert('Gagal menghubungi server pencarian peta.')
        })
        .finally(() => {
            btnCari.innerHTML = originalText
            btnCari.disabled = false
        })
}