document.addEventListener('DOMContentLoaded', function () {
    const toasts = document.querySelectorAll('.toast-message')
    toasts.forEach((toast, index) => {
        setTimeout(() => {
            toast.classList.remove('translate-x-0', 'opacity-100')
            toast.classList.add('translate-x-full', 'opacity-0')
            setTimeout(() => toast.remove(), 500)
        }, 4000 + index * 500) // Tampil selama 4 detik
    })
})