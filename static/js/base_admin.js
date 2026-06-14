document.addEventListener("DOMContentLoaded", function() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const openBtn = document.getElementById('open-sidebar-btn');
    const closeBtn = document.getElementById('close-sidebar-btn');

    // Fungsi Buka Sidebar
    function openSidebar() {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; // Kunci scroll layar belakang
    }

    // Fungsi Tutup Sidebar
    function closeSidebar() {
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
        document.body.style.overflow = ''; // Buka kembali scroll
    }

    // Sambungkan event listener ke tombol jika elemennya ada di layar
    if (openBtn) openBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);
});

// Logika Auto-Hide (Menghilangkan pesan secara otomatis)
document.addEventListener("DOMContentLoaded", function () {
const toasts = document.querySelectorAll(".toast-message");
toasts.forEach((toast, index) => {
    // Tahan pesan selama 3 detik (3000ms), lalu jalankan animasi memudar
    setTimeout(
    () => {
        toast.classList.remove("translate-x-0", "opacity-100");
        toast.classList.add("translate-x-full", "opacity-0");

        // Setelah animasi selesai (500ms), hapus elemen dari memori browser
        setTimeout(() => toast.remove(), 500);
    },
    3000 + index * 500,
    ); // Tambahan jeda jika ada lebih dari 1 pesan
});
});