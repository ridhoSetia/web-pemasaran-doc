import os
from io import BytesIO
from PIL import Image
from django.db import models
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator

# ==========================================
# 1. MANAJEMEN AKUN (CUSTOM USER WA)
# ==========================================
class CustomUserManager(BaseUserManager):
    def create_user(self, nomor_wa, password=None, **extra_fields):
        if not nomor_wa:
            raise ValueError('Nomor WhatsApp wajib diisi!')
        
        # Keamanan: Membersihkan spasi di awal/akhir
        nomor_wa = nomor_wa.strip()
        user = self.model(nomor_wa=nomor_wa, **extra_fields)
        user.set_password(password) # Enkripsi password secara otomatis
        user.save(using=self._db)
        return user

    def create_superuser(self, nomor_wa, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(nomor_wa, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    # KEAMANAN: Memaksa format input hanya berupa angka 10-15 digit
    wa_regex = RegexValidator(
        regex=r'^\d{10,15}$', 
        message="Format tidak valid. Nomor WA harus berupa angka 10-15 digit."
    )
    
    # Identitas Utama pengganti Username
    nomor_wa = models.CharField(validators=[wa_regex], max_length=15, unique=True)
    
    # Data Profil Pelanggan (Wajib diisi setelah login pertama)
    nama_lengkap = models.CharField(max_length=150, blank=True, null=True)
    
    provinsi = models.CharField(max_length=100, blank=True, null=True)
    kabupaten = models.CharField(max_length=100, blank=True, null=True)
    kecamatan = models.CharField(max_length=100, blank=True, null=True)
    kelurahan = models.CharField(max_length=100, blank=True, null=True)
    alamat = models.TextField(blank=True, null=True, help_text="Nama jalan, nomor rumah, RT/RW")

    # Property ini agar bagian web lain tidak error saat memanggil alamat_lengkap
    @property
    def alamat_lengkap(self):
        """Merangkai alamat secara otomatis untuk ditampilkan"""
        # Format persis seperti gaya Anda sebelumnya
        if self.provinsi and self.kabupaten:
            return f"{self.alamat}, Kel. {self.kelurahan}, Kec. {self.kecamatan}, {self.kabupaten}, Prov. {self.provinsi}"
        return self.alamat or ""
    
    # Status & Role
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) # True = Admin, False = Pelanggan
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'nomor_wa' # Login hanya menggunakan WA
    REQUIRED_FIELDS = [] 

    def __str__(self):
        return f"{self.nomor_wa} - {self.nama_lengkap or 'User Baru'}"


# ==========================================
# 2. PENGATURAN TOKO & PRODUK
# ==========================================
class StoreSetting(models.Model):
    nama_toko = models.CharField(max_length=100, default="Kelompok Tani Melati")
    nomor_admin = models.CharField(max_length=20, default="08123456789", help_text="WA Notifikasi Fonnte")
    alamat_toko = models.TextField(blank=True, default="Bukit Pinang, Samarinda")
    hero_title = models.CharField(max_length=255, default="Inkubator DOC Berkualitas")
    hero_description = models.TextField(default="Penyedia DOC dan Telur Tetas terbaik...")
    rekening_bank = models.CharField(max_length=100, blank=True, null=True)
    rekening_nama = models.CharField(max_length=100, blank=True, null=True)
    biaya_per_km = models.IntegerField(default=5000)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    jam_operasional = models.TextField(blank=True, default="Senin - Sabtu: 08.00 - 17.00 WITA")
    hero_image = models.ImageField(upload_to='settings/', null=True, blank=True)

    # --- KONTEN DASHBOARD PELANGGAN ---
    dashboard_welcome_title = models.CharField(max_length=255, default="Selamat datang di Web Portal Kelompok Tani Melati.")
    dashboard_intro_text = models.TextField(default="Aplikasi web ini dibuat dengan sangat KILAT, demi memfasilitasi antusias rekan-rekan dalam melakukan pemesanan Telur ataupun DoC.\nHarap dimaklumkan dengan tampilan yang sangat sederhana, karena kami mengedepankan fungsionalitas.")
    dashboard_outro_text = models.TextField(default="Di kemudian hari, aplikasi ini akan dikembangkan untuk mendukung aktivitas kalian dalam beternak\ntentu pengembangan akan dilakukan secara bertahap.")
    
    syarat_telur = models.TextField(default="- per 1kg kiriman, berisi 16 butir. boleh mix\n- pengiriman dari Banyuwangi, Jawa Timur\n- Garansi Pengiriman, simak Video berikut\n- Ekspedisi yang digaransi : Kantorpos atau Tiki\n- tidak ada ready stock instant, semua dalam kondisi antrian")
    syarat_doc = models.TextField(default="- Eceran minimal 10 ekor\n- Jenis Kelamin RANDOM.\n- yang dikirimkan anak ayam usia 3-7 hari, sudah di vaksin ND-IB.\n- sementara hanya dilayani untuk pulau jawa saja\n- ekspedisi KaLog Express atau Kantorpos layanan NextDay\n- tidak ada ready stock instant, semua dalam kondisi antrian")

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        if self.hero_image and not self.hero_image.name.lower().endswith('.webp'):
            try:
                img = Image.open(self.hero_image)
                output = BytesIO()
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(output, format='WEBP', quality=80)
                output.seek(0)
                file_name = os.path.splitext(self.hero_image.name)[0] + '.webp'
                self.hero_image.save(file_name, ContentFile(output.read()), save=False)
            except Exception:
                pass
        super().save(*args, **kwargs)

class Product(models.Model):
    nama = models.CharField(max_length=255)
    kode_unik = models.CharField(max_length=50, unique=True)
    kategori = models.CharField(max_length=100)
    harga = models.DecimalField(max_digits=10, decimal_places=2)
    stok = models.PositiveIntegerField(help_text="Kapasitas produksi per periode")
    gambar = models.ImageField(upload_to='produk_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.gambar and getattr(self.gambar, 'name', None) and not self.gambar.name.lower().endswith('.webp'):
            img = Image.open(self.gambar)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            output = BytesIO()
            img.save(output, format='WEBP', quality=80)
            output.seek(0)
            filename = f"{slugify(self.nama)}.webp"
            self.gambar.save(filename, ContentFile(output.read()), save=False)
        super().save(*args, **kwargs)

class Ekspedisi(models.Model):
    nama = models.CharField(max_length=100, help_text="Contoh: KaLog Express, Ambil Sendiri")
    biaya = models.IntegerField(default=0, help_text="Isi 0 jika gratis (Ambil Sendiri)")
    is_active = models.BooleanField(default=True, help_text="Centang untuk menampilkan di halaman pemesanan")

    def __str__(self):
        if self.biaya == 0:
            return f"{self.nama} (Gratis)"
        return f"{self.nama} (Rp {self.biaya})"

# ==========================================
# 3. TRANSAKSI & SISTEM ANTRIAN (PRE-ORDER)
# ==========================================
class OrderStatus(models.TextChoices):
    MENUNGGU_DP = 'MENUNGGU_DP', 'Menunggu DP'
    KONFIRMASI_DP = 'KONFIRMASI_DP', 'Menunggu Konfirmasi Pembayaran'
    ANTRIAN = 'ANTRIAN', 'Masuk Daftar Antrean (PO)'
    PERSIAPAN = 'PERSIAPAN', 'Persiapan Pengiriman'
    DIKIRIM = 'DIKIRIM', 'Sedang Dikirim'
    SELESAI = 'SELESAI', 'Selesai'
    BATAL = 'BATAL', 'Dibatalkan'

class DeliveryMethod(models.TextChoices):
    AMBIL = 'AMB', 'Ambil di Kandang'
    ANTAR = 'ANT', 'Diantar ke Lokasi'

class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Bayar di Tempat (Tunai)'
    TRANSFER = 'TRF', 'Transfer Bank'

class Order(models.Model):
    order_id = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.MENUNGGU_DP, db_index=True)
    
    # Pengiriman & Pembayaran
    metode_pengiriman = models.CharField(max_length=100, choices=DeliveryMethod.choices, default=DeliveryMethod.AMBIL)
    metode_pembayaran = models.CharField(max_length=100, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    alamat_pengiriman = models.TextField(blank=True, null=True) # Renamed dari 'alamat'
    biaya_ongkir = models.IntegerField(default=0)

    total_harga = models.DecimalField(max_digits=12, decimal_places=2)
    items_summary = models.CharField(max_length=255) 

    # --- KONSEP BARU: PO & DP ---
    tagihan_dp = models.IntegerField(default=0, help_text="Total DP yang harus dibayar")
    batas_waktu_dp = models.DateTimeField(null=True, blank=True)
    
    # --- DATA KONFIRMASI PEMBAYARAN ---
    nominal_dibayar = models.IntegerField(default=0)
    bank_pengirim = models.CharField(max_length=50, null=True, blank=True)
    nama_rekening_pengirim = models.CharField(max_length=100, null=True, blank=True)
    bukti_transfer = models.ImageField(upload_to='bukti_transfer/', null=True, blank=True)
    waktu_bayar = models.DateTimeField(null=True, blank=True)

    @property
    def masked_name(self):
        nama = self.user.nama_lengkap
        if not nama: return "Hamba Allah"
        nama = nama.strip()
        if len(nama) <= 2: return nama
        return f"{nama[0]}{'*' * (len(nama)-2)}{nama[-1]}"

    def save(self, *args, **kwargs):
        # Optimasi gambar hanya untuk kolom bukti_transfer
        if self.bukti_transfer and getattr(self.bukti_transfer, 'name', None) and not self.bukti_transfer.name.lower().endswith('.webp'):
            try:
                img = Image.open(self.bukti_transfer)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                output = BytesIO()
                img.save(output, format='WEBP', quality=80)
                output.seek(0)
                filename = f"{self.order_id}.webp"
                self.bukti_transfer.save(filename, ContentFile(output.read()), save=False)
            except Exception:
                pass 
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    kuantitas = models.PositiveIntegerField()
    harga_saat_beli = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.kuantitas * self.harga_saat_beli

    def __str__(self):
        return f"{self.kuantitas}x {self.product.nama}"

class OrderCounter(models.Model):
    tanggal = models.DateField(unique=True)
    counter = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.tanggal} - {self.counter}"