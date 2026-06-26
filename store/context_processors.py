from .models import StoreSetting

def store_settings(request):
    """Mengirim pengaturan toko ke semua template HTML secara otomatis"""
    return {
        'toko': StoreSetting.load()
    }