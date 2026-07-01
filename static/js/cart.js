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
                <div class="flex gap-3 sm:gap-4 bg-surface-container-lowest p-3 sm:p-4 rounded-xl border border-outline-variant shadow-sm relative group">
                    
                    <img src="${item.gambar}" alt="${item.nama}" class="w-20 h-20 sm:w-24 sm:h-24 object-cover rounded-lg bg-surface-variant shrink-0">
                    
                    <div class="flex flex-col flex-1 min-w-0 justify-between py-0.5">
                        
                        <div class="flex justify-between items-start gap-2">
                            <div class="min-w-0">
                                <h3 class="font-bold text-sm sm:text-body-lg text-on-surface truncate">${item.nama}</h3>
                                <p class="text-primary font-bold text-xs sm:text-sm mt-0.5">${formatRupiah(item.harga)}</p>
                            </div>
                            
                            <button onclick="removeItem(${index})" class="text-on-surface-variant hover:text-error transition-colors bg-error/10 w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center shrink-0">
                                <span class="material-symbols-outlined text-[16px] sm:text-[18px]">delete</span>
                            </button>
                        </div>
                        
                        <div class="flex flex-wrap items-center justify-between gap-3 mt-3 w-full">
                            
                            <div class="flex items-center gap-2">
                                <div class="flex items-center bg-surface-container rounded-lg border border-outline-variant overflow-hidden">
                                    <button onclick="updateQty(${index}, -1)" class="w-9 sm:w-10 h-8 sm:h-10 flex items-center justify-center hover:bg-surface-variant transition-colors text-on-surface-variant font-bold">-</button>
                                    
                                    <input type="number" 
                                        value="${item.qty}" 
                                        min="1" 
                                        max="${item.max_stok}" 
                                        onchange="setQty(${index}, this.value)" 
                                        class="w-10 sm:w-12 h-8 sm:h-10 text-center text-xs sm:text-sm font-bold bg-transparent border-none focus:ring-0 outline-none p-0 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" />
                                    
                                    <button onclick="updateQty(${index}, 1)" class="w-9 sm:w-10 h-8 sm:h-10 flex items-center justify-center hover:bg-surface-variant transition-colors text-on-surface-variant font-bold">+</button>
                                </div>
                                <span class="text-[10px] sm:text-xs text-on-surface-variant leading-tight">Max:<br>${item.max_stok}</span>
                            </div>
                            
                            <div class="font-bold text-on-surface text-sm sm:text-base text-right shrink-0">
                                ${formatRupiah(subtotal)}
                            </div>
                            
                        </div>
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