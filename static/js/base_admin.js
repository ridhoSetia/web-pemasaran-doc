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

    document.addEventListener('DOMContentLoaded', function() {
    const notifBtn = document.getElementById('notif-btn');
    const notifDropdown = document.getElementById('notif-dropdown');
    const notifBadge = document.getElementById('notif-badge');
    const notifCountText = document.getElementById('notif-count-text');
    const notifList = document.getElementById('notif-list');

    // Peringatan jika HTML lonceng belum terpasang dengan benar
    if (!notifBtn || !notifDropdown) {
        console.error("Tombol Lonceng tidak ditemukan! Pastikan HTML lonceng sudah menggunakan id='notif-btn'.");
        return;
    }

    function fetchNotifs() {
        fetch("{% url 'store:api_pending_orders' %}")
        .then(res => {
            if (!res.ok) throw new Error("Gagal mengambil data dari API.");
            return res.json();
        })
        .then(data => {
            if(data.count > 0) {
                notifBadge.classList.remove('hidden');
                notifCountText.innerText = data.count + ' Baru';
                notifCountText.classList.replace('bg-outline-variant', 'bg-error'); // Warnai merah
                
                let html = '';
                data.orders.forEach(o => {
                    html += `
                    <a href="/pengelola/orders/?q=${o.id}" class="block p-4 border-b border-outline-variant hover:bg-surface-container transition-colors">
                        <div class="flex justify-between items-start mb-1">
                            <span class="font-bold text-xs text-primary">${o.id}</span>
                            <span class="text-[10px] text-on-surface-variant font-semibold">${o.waktu}</span>
                        </div>
                        <p class="text-sm font-semibold text-on-surface truncate">${o.nama}</p>
                        <p class="text-xs text-on-surface-variant mt-1">Total: <span class="font-bold text-error">${o.total}</span></p>
                    </a>
                    `;
                });
                notifList.innerHTML = html;
            } else {
                notifBadge.classList.add('hidden');
                notifCountText.innerText = '0 Baru';
                notifCountText.classList.replace('bg-error', 'bg-outline-variant'); // Warnai abu-abu
                notifList.innerHTML = '<div class="p-6 text-center text-sm font-medium text-on-surface-variant">Hore! Semua pesanan sudah diproses.</div>';
            }
        })
        .catch(err => {
            console.error("Error Notifikasi:", err);
            notifList.innerHTML = '<div class="p-4 text-center text-xs text-error font-medium">Gagal memuat data pesanan. Periksa koneksi atau log server.</div>';
        });
    }

    fetchNotifs(); // Muat data pertama kali
    setInterval(fetchNotifs, 120000); // Auto-refresh setiap 2 menit

    notifBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (notifDropdown.classList.contains('hidden')) {
            notifDropdown.classList.remove('hidden');
            setTimeout(() => notifDropdown.classList.remove('opacity-0', 'scale-95'), 10);
            fetchNotifs(); // Segarkan isi saat dibuka
        } else {
            notifDropdown.classList.add('opacity-0', 'scale-95');
            setTimeout(() => notifDropdown.classList.add('hidden'), 150);
        }
    });

    // Tutup otomatis jika klik di luar area
    document.addEventListener('click', function(e) {
        if (!notifBtn.contains(e.target) && !notifDropdown.contains(e.target)) {
            notifDropdown.classList.add('opacity-0', 'scale-95');
            setTimeout(() => notifDropdown.classList.add('hidden'), 150);
        }
    });
});