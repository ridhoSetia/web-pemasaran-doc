from django.contrib import admin
from .models import Product, Order, OrderItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Menggunakan nama kolom baru (nama, kode_unik, kategori, dll)
    # is_active dan max_stock dihapus karena sudah tidak ada di model
    list_display = ('kode_unik', 'nama', 'kategori', 'harga', 'stok', 'created_at')
    
    # Filter di sidebar admin
    list_filter = ('kategori',)
    
    # Kolom pencarian
    search_fields = ('nama', 'kode_unik')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Menggunakan nama kolom baru (nama_pembeli, total_harga)
    list_display = ('order_id', 'nama_pembeli', 'total_harga', 'status', 'order_date')
    list_filter = ('status', 'order_date')
    search_fields = ('order_id', 'nama_pembeli')
    
    # Menampilkan item pesanan langsung di dalam form Order
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'kuantitas', 'harga_saat_beli')
    search_fields = ('order__order_id', 'product__nama')