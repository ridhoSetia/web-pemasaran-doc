from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from unittest.mock import patch
from io import BytesIO
from PIL import Image
import json

from .models import Product, Order, OrderItem, OrderStatus

# ===================================================================
# 1. PENGUJIAN LOGIKA TRANSAKSI & ATOMIC CHECKOUT (SEBELUMNYA)
# ===================================================================
class StoreLogicAndCheckoutTest(TestCase):
    """Pengujian komprehensif untuk validasi model, kalkulasi, dan atomic checkout."""
    
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            nama="Ayam KUB DOC", kode_unik="DOC-001", kategori="DOC",
            harga=Decimal('50000.00'), stok=100
        )

    @patch('store.views.requests.post') # Mencegah pesan WA sungguhan terkirim
    def test_checkout_reduces_stock_atomically(self, mock_requests_post):
        """Memastikan stok berkurang saat checkout metode Ambil Sendiri sukses"""
        initial_stock = self.product.stok
        self.client.post(reverse('store:checkout'), {
            'nama': 'Test User', 'hp': '081234567890',
            'pengiriman': 'AMB', 'pembayaran': 'COD',
            'cart_data': f'[{{"id": {self.product.id}, "qty": 5}}]'
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.stok, initial_stock - 5)

    @patch('store.views.requests.post')
    def test_checkout_calculates_ongkos_kirim_correctly(self, mock_requests_post):
        """Memastikan metode pengiriman (ANT) mengakumulasikan ongkir Rp 5.000/km"""
        self.client.post(reverse('store:checkout'), {
            'nama': 'Test Delivery', 'hp': '081234567891',
            'pengiriman': 'ANT', 'alamat': 'Jl. Kebenaran', 'jarak_km': '10',
            'pembayaran': 'TF', 'cart_data': f'[{{"id": {self.product.id}, "qty": 2}}]'
        })
        order = Order.objects.first()
        # 2 produk x 50.000 + (10 km x 5.000) = 150.000
        self.assertEqual(order.total_harga, Decimal('150000.00'))
        
    def test_checkout_rejects_invalid_distance(self):
        """Memastikan sistem menolak checkout jika jarak lebih dari 500 km"""
        self.client.post(reverse('store:checkout'), {
            'nama': 'Test Jarak Jauh', 'hp': '081234567892',
            'pengiriman': 'ANT', 'jarak_km': '600', # Melebihi 500
            'cart_data': f'[{{"id": {self.product.id}, "qty": 1}}]'
        })
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_fails_if_insufficient_stock(self):
        """Memastikan checkout ditolak secara aman jika qty melebihi stok"""
        response = self.client.post(reverse('store:checkout'), {
            'nama': 'Test Stok Kurang', 'hp': '081234567893',
            'pengiriman': 'AMB', 'pembayaran': 'COD',
            'cart_data': f'[{{"id": {self.product.id}, "qty": 150}}]'
        })
        # Harus ter-redirect kembali ke checkout, stok utuh, order tidak terbuat
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stok, 100)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_item_stores_historical_price(self):
        """OrderItem harus menyimpan harga historis meski master Product diubah"""
        order = Order.objects.create(order_id='TEST003', nama_pembeli='X', total_harga=Decimal('50000'))
        item = OrderItem.objects.create(order=order, product=self.product, kuantitas=1, harga_saat_beli=Decimal('50000'))
        
        self.product.harga = Decimal('60000.00') # Admin mengubah harga
        self.product.save()
        
        item.refresh_from_db()
        self.assertEqual(item.harga_saat_beli, Decimal('50000.00')) # Harga pesanan masa lalu tetap


# ===================================================================
# 2. PENGUJIAN KEAMANAN AKSES (OTORISASI)
# ===================================================================
class SecurityAccessTest(TestCase):
    """Pengujian untuk memastikan rute Admin tidak bisa dibobol."""
    
    def setUp(self):
        self.client = Client()
        self.normal_user = User.objects.create_user(username='pelanggan', password='rahasia123')
        self.admin_user = User.objects.create_superuser(username='bos_admin', password='rahasia123')

    def test_admin_dashboard_blocks_anonymous_users(self):
        """Memastikan pengunjung anonim tanpa login ditendang ke halaman login"""
        response = self.client.get(reverse('store:overview'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/pengelola/login/' in response.url)

    def test_admin_dashboard_blocks_normal_users(self):
        """Memastikan user login tapi BUKAN superuser tetap ditolak"""
        self.client.login(username='pelanggan', password='rahasia123')
        response = self.client.get(reverse('store:inventory'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/pengelola/login/' in response.url)

    def test_admin_dashboard_allows_superusers(self):
        """Memastikan admin sesungguhnya (superuser) diizinkan masuk"""
        self.client.login(username='bos_admin', password='rahasia123')
        response = self.client.get(reverse('store:overview'))
        self.assertEqual(response.status_code, 200)


# ===================================================================
# 3. PENGUJIAN ANTI-SPAM (RATE LIMITING)
# ===================================================================
class RateLimitAntiSpamTest(TestCase):
    """Memvalidasi modul django-ratelimit mencegah serangan Brute Force."""
    
    def setUp(self):
        self.client = Client()
        cache.clear() # Bersihkan riwayat IP sebelum tes berjalan

    def test_track_order_rate_limit(self):
        """Halaman cek pesanan dilimit 20x/jam. Eksekusi ke-21 harus diblokir (403)"""
        url = reverse('store:track_order')
        
        # Kirim 20 request berturut-turut (Seharusnya lolos/200 OK)
        for _ in range(20):
            response = self.client.post(url, {'order_id': 'DOC-123', 'hp': '0812'})
            self.assertNotEqual(response.status_code, 403)

        # Request ke-21 menembus batas spam!
        response_blocked = self.client.post(url, {'order_id': 'DOC-123', 'hp': '0812'})
        self.assertEqual(response_blocked.status_code, 403) # 403 Forbidden


# ===================================================================
# 4. PENGUJIAN INTEGRASI (DASHBOARD & PENCARIAN)
# ===================================================================
class DashboardIntegrationTest(TestCase):
    """Memastikan kalkulasi analitik dan filter berjalan akurat."""
    
    def setUp(self):
        self.client = Client()
        User.objects.create_superuser(username='admin', password='123')
        self.client.login(username='admin', password='123')

    def test_dashboard_sales_calculation_ignores_process_status(self):
        """Pendapatan dashboard HANYA boleh menghitung pesanan bersatus SELESAI"""
        # Order Selesai (Sah)
        Order.objects.create(order_id='O-001', nama_pembeli='A', total_harga=100000, status=OrderStatus.SELESAI)
        # Order Proses (Belum dibayar/selesai, harus diabaikan)
        Order.objects.create(order_id='O-002', nama_pembeli='B', total_harga=50000, status=OrderStatus.PROSES)

        response = self.client.get(reverse('store:overview'))
        # Total Sales harus sama persis dengan pesanan Selesai (100.000)
        self.assertEqual(response.context['total_sales'], Decimal('100000'))

    def test_inventory_search_filter_works(self):
        """Memastikan fitur pencarian (Search) di inventaris merespons teks dengan benar"""
        Product.objects.create(nama="Bebek Peking", kode_unik="BP-01", kategori="BEBEK", harga=60000, stok=50)
        Product.objects.create(nama="Ayam Broiler", kode_unik="AB-01", kategori="AYAM", harga=40000, stok=50)

        # Mencari kata "Peking"
        response = self.client.get(reverse('store:inventory'), {'q': 'Peking'})
        products_in_context = response.context['products']
        
        self.assertEqual(len(products_in_context), 1)
        self.assertEqual(products_in_context[0].nama, "Bebek Peking")


# ===================================================================
# 5. PENGUJIAN MEDIA & BACKGROUND PROCESSING (WEBP)
# ===================================================================
class MediaProcessingTest(TestCase):
    """Memastikan konversi otomatis JPEG/PNG ke WebP berjalan mulus."""
    
    def test_image_converted_to_webp_on_save(self):
        """Gambar JPEG yang diunggah harus berubah ekstensi jadi .webp di database"""
        # Membuat gambar JPEG palsu (dummy) di dalam RAM (Memory)
        image_io = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(image_io, format='JPEG')
        
        dummy_image = SimpleUploadedFile(
            "foto_palsu.jpg", image_io.getvalue(), content_type="image/jpeg"
        )
        
        product = Product.objects.create(
            nama="Ayam KUB Keren", kode_unik="WEBP-01", kategori="TEST",
            harga=10000, stok=10, gambar=dummy_image
        )
        
        # Validasi: Nama file yang tersimpan HARUS berakhiran .webp
        self.assertTrue(product.gambar.name.endswith('.webp'))
        self.assertTrue('ayam-kub-keren' in product.gambar.name)