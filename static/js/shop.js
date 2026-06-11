// Fungsi baru ini menangkap "buttonElement" (tombol yang diklik)
function addToCart(buttonElement) {
    // Ekstraksi data secara aman dari atribut data-* milik tombol
    const id = buttonElement.getAttribute('data-id')
    const nama = buttonElement.getAttribute('data-nama')
    const harga = parseInt(buttonElement.getAttribute('data-harga'))
    const stok = parseInt(buttonElement.getAttribute('data-stok'))
    const gambar_url = buttonElement.getAttribute('data-gambar').trim()

    // Validasi stok awal
    if (stok < 1) {
        alert('Maaf, stok produk ini sedang habis.')
        return
    }

    // Logika Keranjang (Local Storage)
    let cart = JSON.parse(localStorage.getItem('doc_cart')) || []
    let existingItemIndex = cart.findIndex((item) => item.id === id)

    if (existingItemIndex !== -1) {
        if (cart[existingItemIndex].qty < stok) {
            cart[existingItemIndex].qty += 1
        } else {
            alert('Anda sudah mencapai batas maksimum stok untuk produk ini.')
            return
        }
    } else {
        cart.push({
            id: id,
            nama: nama, // Nama sekarang dijamin ada isinya
            harga: harga,
            qty: 1,
            max_stok: stok,
            gambar: gambar_url
        })
    }

    // Simpan & Perbarui UI
    localStorage.setItem('doc_cart', JSON.stringify(cart))

    if (typeof updateCartBadge === 'function') {
        updateCartBadge()
    }

    // Menampilkan nama produk asli, bukan undefined lagi
    alert(`${nama} berhasil ditambahkan ke keranjang!`)
}

  document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.getElementById("toggleFilterBtn");
    const closeBtn = document.getElementById("closeFilterBtn");
    const filterContainer = document.getElementById("filterContainer");

    // Buka filter saat tombol ditekan
    toggleBtn.addEventListener("click", () => {
      filterContainer.classList.remove("hidden");
      // Mencegah background di-scroll saat filter terbuka (opsional)
      filterContainer.scrollIntoView({ behavior: "smooth" });
    });

    // Tutup filter
    closeBtn.addEventListener("click", () => {
      filterContainer.classList.add("hidden");
    });
  });

    function openFilter() {
      const filterMenu = document.getElementById('filter-menu');
      filterMenu.classList.remove('hidden');
      // Mencegah halaman utama di-scroll saat menu terbuka di HP
      document.body.style.overflow = 'hidden'; 
    }

    function closeFilter() {
      const filterMenu = document.getElementById('filter-menu');
      filterMenu.classList.add('hidden');
      // Mengembalikan fungsi scroll saat ditutup
      document.body.style.overflow = 'auto';
    }