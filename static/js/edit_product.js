function toggleKategoriBaru() {
    const select = document.getElementById('kategori')
    const container = document.getElementById('kategori_baru_container')
    const inputBaru = document.getElementById('kategori_baru')

    if (select.value === 'BARU') {
        container.classList.remove('hidden')
        inputBaru.setAttribute('required', 'true')
        inputBaru.focus()
    } else {
        container.classList.add('hidden')
        inputBaru.removeAttribute('required')
    }
}

// Validasi inisial saat halaman dimuat
document.addEventListener('DOMContentLoaded', toggleKategoriBaru)