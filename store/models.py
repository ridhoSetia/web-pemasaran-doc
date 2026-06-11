import os
from io import BytesIO
from PIL import Image
from django.db import models
from django.core.files.base import ContentFile

class Product(models.Model):
    nama = models.CharField(max_length=255)
    kode_unik = models.CharField(max_length=50, unique=True)
    kategori = models.CharField(max_length=100)
    harga = models.DecimalField(max_digits=10, decimal_places=2)
    stok = models.PositiveIntegerField()
    
    # Kolom gambar
    gambar = models.ImageField(upload_to='produk_images/', null=True, blank=True)
        
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nama

    # LOGIKA KEAMANAN & KONVERSI WEBP
    def save(self, *args, **kwargs):
        # Jika ada gambar yang diunggah dan gambar tersebut belum berformat WebP
        if self.gambar and getattr(self.gambar, 'name', None) and not self.gambar.name.lower().endswith('.webp'):
            img = Image.open(self.gambar)
            
            # Jika gambar transparan, ubah ke mode RGB
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            output = BytesIO()
            img.save(output, format='WEBP', quality=80)
            output.seek(0)
            
            # Ambil nama dasar file (hindari duplikasi path)
            base_name = os.path.basename(self.gambar.name)
            filename = os.path.splitext(base_name)[0] + '.webp'
            
            # PERBAIKAN KRUSIAL: Gunakan self.gambar.save() agar upload_to tetap bekerja!
            self.gambar.save(filename, ContentFile(output.read()), save=False)
            
        super().save(*args, **kwargs)

class DeliveryMethod(models.TextChoices):
    AMBIL = 'AMB', 'Ambil Sendiri'
    ANTAR = 'ANT', 'Diantar ke Lokasi'

class PaymentMethod(models.TextChoices):
    COD = 'COD', 'Bayar di Tempat'
    TF = 'TF', 'Transfer'

class OrderStatus(models.TextChoices):
    PROSES = 'PRO', 'Proses'
    SELESAI = 'SLS', 'Selesai'
    BATAL = 'BTL', 'Batal'

class Order(models.Model):
    order_id = models.CharField(max_length=20, unique=True)
    nama_pembeli = models.CharField(max_length=200)
    nomor_hp = models.CharField(max_length=20)
    
    # Detail Pengiriman
    metode_pengiriman = models.CharField(max_length=3, choices=DeliveryMethod.choices, default=DeliveryMethod.AMBIL)
    alamat = models.TextField(blank=True, null=True)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)

    jarak_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Detail Pembayaran
    metode_pembayaran = models.CharField(max_length=3, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    bukti_pembayaran = models.ImageField(upload_to='bukti_transfer/', null=True, blank=True)
    
    total_harga = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=3, choices=OrderStatus.choices, default=OrderStatus.PROSES)
    items_summary = models.CharField(max_length=255) 
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_id} - {self.nama_pembeli}"

class OrderItem(models.Model):
    """
    Tabel perantara (Bridge Table) yang merelasikan Order dan Product.
    Ini mencatat secara spesifik produk apa saja yang dibeli dalam satu pesanan
    beserta kuantitas dan harga historisnya.
    """
    # Relasi ke Order. CASCADE berarti jika Order dihapus, OrderItem ini ikut terhapus.
    # related_name='items' mengizinkan kita memanggil pesanan.items.all() nantinya.
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    
    # Relasi ke Product. 
    # related_name='order_items' sangat krusial untuk fitur "Top Product" kita nanti.
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    
    # Berapa banyak produk ini dibeli dalam pesanan
    kuantitas = models.PositiveIntegerField()
    
    # Mengapa kita menyimpan harga lagi di sini? 
    # KEAMANAN DATA HISTORIS: Harga produk di master 'Product' bisa berubah besok. 
    # Faktur pesanan hari ini tidak boleh ikut berubah mengikuti harga besok.
    harga_saat_beli = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.kuantitas}x {self.product.nama} (Order: {self.order.order_id})"
    
    @property
    def subtotal(self):
        return self.kuantitas * self.harga_saat_beli