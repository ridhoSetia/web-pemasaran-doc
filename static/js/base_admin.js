document.addEventListener("DOMContentLoaded", function() {
const sidebar = document.getElementById("admin-sidebar");
const overlay = document.getElementById("mobile-overlay");
const openBtn = document.getElementById("hamburger-btn");
const closeBtn = document.getElementById("close-sidebar-btn");

function openSidebar() {
    sidebar.classList.remove("-translate-x-full");
    overlay.classList.remove("hidden");
    // Jeda sedikit agar animasi fade-in Tailwind berjalan
    setTimeout(() => overlay.classList.remove("opacity-0"), 10);
}

function closeSidebar() {
    sidebar.classList.add("-translate-x-full");
    overlay.classList.add("opacity-0");
    // Sembunyikan elemen setelah animasi selesai (300ms)
    setTimeout(() => overlay.classList.add("hidden"), 300);
}

openBtn.addEventListener("click", openSidebar);
closeBtn.addEventListener("click", closeSidebar);
overlay.addEventListener("click", closeSidebar); // Tutup sidebar jika layar gelap diklik
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