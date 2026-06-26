// Format mata uang Rupiah
function formatRupiah(angka) {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(angka);
}

// Render isi keranjang
function renderCart() {
    let cart = JSON.parse(localStorage.getItem('doc_cart')) || [];
    const container = document.getElementById('cart-items-container');
    const emptyMessage = document.getElementById('empty-cart-message');
    const summaryCard = document.getElementById('order-summary-card');

    container.innerHTML = '';
    let grandTotal = 0;
    let totalItems = 0;

    if (cart.length === 0) {
        if (emptyMessage) emptyMessage.classList.remove('hidden');
        if (summaryCard) summaryCard.classList.add('hidden');
        return;
    }

    if (emptyMessage) emptyMessage.classList.add('hidden');
    if (summaryCard) summaryCard.classList.remove('hidden');

    cart.forEach((item, index) => {
        const subtotal = item.harga * item.qty;
        grandTotal += subtotal;
        totalItems += item.qty;

        container.innerHTML += `
                <div class="flex items-center gap-4 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-sm relative group">
                    <img src="${item.gambar}" alt="${item.nama}" class="w-24 h-24 object-cover rounded-lg bg-surface-variant">
                    
                    <div class="flex-1">
                        <h3 class="font-bold text-body-lg text-on-surface">${item.nama}</h3>
                        <p class="text-primary font-bold text-sm mb-3">${formatRupiah(item.harga)}</p>
                        
                        <div class="flex items-center gap-3">
                            <div class="flex items-center bg-surface-container rounded-lg border border-outline-variant overflow-hidden">
                                <button onclick="updateQty(${index}, -1)" class="w-8 h-8 flex items-center justify-center hover:bg-surface-variant transition-colors text-on-surface-variant font-bold">-</button>
                                <input type="number" 
                                    value="${item.qty}" 
                                    min="1" 
                                    max="${item.max_stok}" 
                                    onchange="setQty(${index}, this.value)" 
                                    class="w-12 text-center text-sm font-bold bg-transparent border-none focus:ring-0 outline-none p-0 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
                                <button onclick="updateQty(${index}, 1)" class="w-8 h-8 flex items-center justify-center hover:bg-surface-variant transition-colors text-on-surface-variant font-bold">+</button>
                            </div>
                            <span class="text-xs text-on-surface-variant">Max: ${item.max_stok}</span>
                        </div>
                    </div>
                    
                    <div class="text-right flex flex-col justify-between items-end h-24">
                        <button onclick="removeItem(${index})" class="text-on-surface-variant hover:text-error transition-colors bg-error/10 w-8 h-8 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100">
                            <span class="material-symbols-outlined text-[18px]">delete</span>
                        </button>
                        <p class="font-bold text-on-surface">${formatRupiah(subtotal)}</p>
                    </div>
                </div>
            `;
    });

    const summaryItemsEl = document.getElementById('summary-items');
    if (summaryItemsEl) summaryItemsEl.innerText = totalItems;
    
    const summaryTotalEl = document.getElementById('summary-total');
    if (summaryTotalEl) summaryTotalEl.innerText = formatRupiah(grandTotal);

    if (typeof updateCartBadge === 'function') updateCartBadge();
}

function updateQty(index, change) {
    let cart = JSON.parse(localStorage.getItem('doc_cart'));
    let newQty = cart[index].qty + change;

    if (newQty > 0 && newQty <= cart[index].max_stok) {
        cart[index].qty = newQty;
        localStorage.setItem('doc_cart', JSON.stringify(cart));
        renderCart();
    } else if (newQty > cart[index].max_stok) {
        showToast('Melebihi batas stok maksimal yang tersedia!', 'error');
    }
}

function setQty(index, newValue) {
    let cart = JSON.parse(localStorage.getItem('doc_cart'));
    let parsedValue = parseInt(newValue);

    if (isNaN(parsedValue) || parsedValue < 1) {
        parsedValue = 1;
    } 
    else if (parsedValue > cart[index].max_stok) {
        showToast('Melebihi batas stok maksimal yang tersedia!', 'error');
        parsedValue = cart[index].max_stok;
    }

    cart[index].qty = parsedValue;
    localStorage.setItem('doc_cart', JSON.stringify(cart));
    renderCart();
}

function removeItem(index) {
    if (confirm('Hapus produk ini dari keranjang?')) {
        let cart = JSON.parse(localStorage.getItem('doc_cart'));
        cart.splice(index, 1); 
        localStorage.setItem('doc_cart', JSON.stringify(cart));
        renderCart();
        showToast('Produk berhasil dihapus.', 'success');
    }
}

document.addEventListener('DOMContentLoaded', renderCart);