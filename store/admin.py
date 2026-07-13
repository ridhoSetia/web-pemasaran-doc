from django.contrib import admin
from .models import CustomUser, StoreSetting, Product, Order, OrderItem, Ekspedisi

# ==========================================
# 1. ADMIN UNTUK AKUN PENGGUNA (WA)
# ==========================================
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('nomor_wa', 'nama_lengkap', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('nomor_wa', 'nama_lengkap')
    list_filter = ('is_staff', 'is_active')
    ordering = ('-date_joined',)

# ==========================================
# 2. ADMIN UNTUK PENGATURAN TOKO
# ==========================================
@admin.register(StoreSetting)
class StoreSettingAdmin(admin.ModelAdmin):
    list_display = ('nama_toko', 'nomor_admin', 'jam_operasional')

# ==========================================
# 3. ADMIN UNTUK PRODUK
# ==========================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('nama', 'kode_unik', 'kategori', 'harga', 'stok')
    search_fields = ('nama', 'kode_unik', 'kategori')
    list_filter = ('kategori',)
    ordering = ('-created_at',)

# ==========================================
# 4. ADMIN UNTUK PESANAN (PRE-ORDER)
# ==========================================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('harga_saat_beli',) # Harga riwayat tidak boleh diubah

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Mengambil nama dan WA dari relasi tabel CustomUser
    list_display = ('order_id', 'get_nama_pembeli', 'get_nomor_wa', 'status', 'total_harga', 'order_date')
    
    # Pencarian menembus relasi ke tabel User menggunakan double underscore (__)
    search_fields = ('order_id', 'user__nomor_wa', 'user__nama_lengkap')
    
    list_filter = ('status', 'metode_pengiriman', 'metode_pembayaran', 'order_date')
    inlines = [OrderItemInline]
    ordering = ('-order_date',)

    # Fungsi kustom untuk menampilkan data dari CustomUser di tabel Order
    def get_nama_pembeli(self, obj):
        return obj.user.nama_lengkap or "Belum Lengkap"
    get_nama_pembeli.short_description = 'Nama Pembeli'

    def get_nomor_wa(self, obj):
        return obj.user.nomor_wa
    get_nomor_wa.short_description = 'Nomor WA'

@admin.register(Ekspedisi)
class EkspedisiAdmin(admin.ModelAdmin):
    list_display = ('nama', 'biaya', 'is_active')
    list_editable = ('biaya', 'is_active')