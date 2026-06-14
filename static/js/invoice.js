// Fungsi Penanganan Modal Bukti Pembayaran
function openModal() {
    const modal = document.getElementById('buktiModal');
    const content = document.getElementById('modalContent');
    if(!modal) return;
    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        content.classList.remove('scale-95');
    }, 10);
}

function closeModal() {
    const modal = document.getElementById('buktiModal');
    const content = document.getElementById('modalContent');
    if(!modal) return;
    modal.classList.add('opacity-0');
    content.classList.add('scale-95');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}