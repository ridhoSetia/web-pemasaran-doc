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