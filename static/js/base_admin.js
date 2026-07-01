document.addEventListener("DOMContentLoaded", function() {
    // ==========================================
    // 1. SISTEM SIDEBAR MOBILE
    // ==========================================
    const sidebar = document.getElementById("admin-sidebar");
    const overlay = document.getElementById("mobile-overlay");
    const openBtn = document.getElementById("hamburger-btn");
    const closeBtn = document.getElementById("close-sidebar-btn");

    function openSidebar() {
        if(sidebar) sidebar.classList.remove("-translate-x-full");
        if(overlay) overlay.classList.remove("hidden");
        setTimeout(() => { if(overlay) overlay.classList.remove("opacity-0") }, 10);
    }

    function closeSidebar() {
        if(sidebar) sidebar.classList.add("-translate-x-full");
        if(overlay) overlay.classList.add("opacity-0");
        setTimeout(() => { if(overlay) overlay.classList.add("hidden") }, 300);
    }

    if(openBtn) openBtn.addEventListener("click", openSidebar);
    if(closeBtn) closeBtn.addEventListener("click", closeSidebar);
    if(overlay) overlay.addEventListener("click", closeSidebar);

    // ==========================================
    // 2. AUTO-HIDE PESAN TOAST (DJANGO MESSAGES)
    // ==========================================
    const toasts = document.querySelectorAll(".toast-message");
    toasts.forEach((toast, index) => {
        setTimeout(() => {
            toast.classList.remove("translate-x-0", "opacity-100");
            toast.classList.add("translate-x-full", "opacity-0");
            setTimeout(() => toast.remove(), 500);
        }, 3000 + index * 500); 
    });

    // ==========================================
    // 3. SISTEM NOTIFIKASI DROPDOWN (LONCENG)
    // ==========================================
    const notifBtn = document.getElementById('notif-btn');
    const notifDropdown = document.getElementById('notif-dropdown');
    const notifBadge = document.getElementById('notif-badge');
    const notifCountText = document.getElementById('notif-count-text');
    const notifList = document.getElementById('notif-list');

    // Hentikan jika elemen lonceng tidak ada di halaman ini
    if (!notifBtn || !notifDropdown) return; 

    function fetchNotifs() {
        fetch("/pengelola/api/pending-orders/")
        .then(res => {
            if (!res.ok) throw new Error("Gagal mengambil data dari API.");
            return res.json();
        })
        .then(data => {
            if(data.count > 0) {
                notifBadge.classList.remove('hidden');
                notifCountText.innerText = data.count + ' Baru';
                notifCountText.classList.replace('bg-outline-variant', 'bg-error'); 
                
                let html = '';
                data.orders.forEach(o => {
                    // SANITASI HTML: Mencegah eksekusi tag ilegal dari sisa data testing lama
                    let safeNama = o.nama ? String(o.nama).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;") : "Pelanggan";

                    html += `
                    <a href="/pengelola/orders/?q=${o.id}" class="block p-4 border-b border-outline-variant hover:bg-surface-container transition-colors">
                        <div class="flex justify-between items-start mb-1">
                            <span class="font-bold text-xs text-primary">${o.id}</span>
                            <span class="text-[10px] text-on-surface-variant font-semibold">${o.waktu}</span>
                        </div>
                        <p class="text-sm font-semibold text-on-surface truncate">${safeNama}</p>
                        <p class="text-xs text-on-surface-variant mt-1">Total: <span class="font-bold text-error">${o.total}</span></p>
                    </a>
                    `;
                });
                notifList.innerHTML = html;
            } else {
                notifBadge.classList.add('hidden');
                notifCountText.innerText = '0 Baru';
                notifCountText.classList.replace('bg-error', 'bg-outline-variant'); 
                notifList.innerHTML = '<div class="p-6 text-center text-sm font-medium text-on-surface-variant">Hore! Semua pesanan sudah diproses.</div>';
            }
        })
        .catch(err => {
            console.error("Error Notifikasi:", err);
            notifList.innerHTML = '<div class="p-4 text-center text-xs text-error font-medium">Gagal memuat data pesanan. Periksa koneksi server.</div>';
        });
    }

    // Muat data saat pertama kali halaman dibuka
    fetchNotifs(); 
    setInterval(fetchNotifs, 120000); // Auto-refresh setiap 2 menit

    // Logika Klik Tombol Lonceng
    notifBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (notifDropdown.classList.contains('hidden')) {
            notifDropdown.classList.remove('hidden');
            setTimeout(() => notifDropdown.classList.remove('opacity-0', 'scale-95'), 10);
            fetchNotifs(); // Segarkan data saat dibuka
        } else {
            notifDropdown.classList.add('opacity-0', 'scale-95');
            setTimeout(() => notifDropdown.classList.add('hidden'), 150);
        }
    });

    // Menutup dropdown jika klik di tempat kosong
    document.addEventListener('click', function(e) {
        if (!notifBtn.contains(e.target) && !notifDropdown.contains(e.target)) {
            notifDropdown.classList.add('opacity-0', 'scale-95');
            setTimeout(() => notifDropdown.classList.add('hidden'), 150);
        }
    });
});