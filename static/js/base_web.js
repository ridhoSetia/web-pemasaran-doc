document.addEventListener('DOMContentLoaded', function () {
    const toasts = document.querySelectorAll('.toast-message')
    toasts.forEach((toast, index) => {
        setTimeout(() => {
            toast.classList.remove('translate-x-0', 'opacity-100')
            toast.classList.add('translate-x-full', 'opacity-0')
            setTimeout(() => toast.remove(), 500)
        }, 4000 + index * 500) // Tampil selama 4 detik
    })
})

// 1. Fungsi Memperbarui Angka di Icon Keranjang
function updateCartBadge() {
let cart = JSON.parse(localStorage.getItem('doc_cart')) || [];
let totalItems = 0;
cart.forEach((item) => {
    totalItems += item.qty;
});

const badge = document.getElementById('cart-badge');
if (badge) {
    if (totalItems > 0) {
        badge.innerText = totalItems > 99 ? '99+' : totalItems;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}
}

// 2. Fungsi Memunculkan Notifikasi ala Kelompok Tani Melati (Dipanggil dari JS lain)
function showToast(message, type = 'error') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    const bgClass = type === 'error' ? 'bg-error text-white' : 'bg-primary text-white';
    const iconName = type === 'error' ? 'error' : 'check_circle';

    toast.className = `flex items-center gap-3 p-4 rounded-xl shadow-xl transition-all duration-500 transform translate-x-[120%] opacity-0 pointer-events-auto w-80 ${bgClass}`;
    
    toast.innerHTML = `
        <span class="material-symbols-outlined text-[24px]">${iconName}</span>
        <p class="text-sm font-bold leading-tight">${message}</p>
    `;

    container.appendChild(toast);

    // Animasi Masuk
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-[120%]', 'opacity-0');
        });
    });

    // Animasi Keluar Otomatis setelah 3.5 detik
    setTimeout(() => {
        toast.classList.add('translate-x-[120%]', 'opacity-0');
        setTimeout(() => toast.remove(), 500);
    }, 3500);
}

// 3. Menghilangkan Notifikasi Bawaan Django secara otomatis
document.addEventListener('DOMContentLoaded', function() {
    updateCartBadge(); // Update keranjang saat halaman dimuat

    const djangoToasts = document.querySelectorAll('.toast-message');
    djangoToasts.forEach(toast => {
        setTimeout(() => {
            toast.classList.add('translate-x-[120%]', 'opacity-0');
            setTimeout(() => toast.remove(), 500);
        }, 3500);
    });
});