function addToCart(buttonElement) {
    const id = buttonElement.getAttribute('data-id');
    const nama = buttonElement.getAttribute('data-nama');
    const harga = parseInt(buttonElement.getAttribute('data-harga'));
    const stok = parseInt(buttonElement.getAttribute('data-stok'));
    const gambar_url = buttonElement.getAttribute('data-gambar').trim();

    if (stok < 1) {
        showToast('Maaf, stok produk ini sedang habis.', 'error');
        return;
    }

    let cart = JSON.parse(localStorage.getItem('doc_cart')) || [];
    let existingItemIndex = cart.findIndex((item) => item.id === id);

    if (existingItemIndex !== -1) {
        if (cart[existingItemIndex].qty < stok) {
            cart[existingItemIndex].qty += 1;
        } else {
            showToast('Anda sudah mencapai batas maksimum stok untuk produk ini.', 'error');
            return;
        }
    } else {
        cart.push({
            id: id,
            nama: nama,
            harga: harga,
            qty: 1,
            max_stok: stok,
            gambar: gambar_url
        });
    }

    localStorage.setItem('doc_cart', JSON.stringify(cart));

    if (typeof updateCartBadge === 'function') {
        updateCartBadge();
    }

    // Menggunakan Toast Hijau (Success)
    showToast(`${nama} berhasil ditambahkan ke keranjang!`, 'success');
}

function openFilter() {
    const filterMenu = document.getElementById('filter-menu');
    if (filterMenu) {
        filterMenu.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; 
    }
}

function closeFilter() {
    const filterMenu = document.getElementById('filter-menu');
    if (filterMenu) {
        filterMenu.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }
}