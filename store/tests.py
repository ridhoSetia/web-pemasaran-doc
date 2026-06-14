from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Product, Order, OrderItem, OrderStatus

class CheckoutAtomicityTest(TestCase):
    """Test atomic checkout transactions to prevent race conditions"""
    
    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            nama="Ayam KUB DOC",
            kode_unik="DOC-001",
            kategori="DOC",
            harga=Decimal('50000'),
            stok=100
        )
    
    def test_checkout_reduces_stock_atomically(self):
        """Verify stock is reduced only when checkout succeeds"""
        initial_stock = self.product.stok
        
        response = self.client.post('/checkout/', {
            'nama': 'Test User',
            'hp': '081234567890',
            'pengiriman': 'AMB',
            'pembayaran': 'COD',
            'cart_data': f'[{{"id": {self.product.id}, "qty": 5, "harga": 50000, "nama": "Ayam KUB DOC"}}]'
        })
        
        self.product.refresh_from_db()
        # Stock should be reduced by 5
        self.assertEqual(self.product.stok, initial_stock - 5)
    
    def test_order_status_initial_is_proses(self):
        """New orders should have PROSES status by default"""
        order = Order.objects.create(
            order_id='DOC-TEST001',
            nama_pembeli='Test User',
            nomor_hp='081234567890',
            metode_pengiriman='AMB',
            metode_pembayaran='COD',
            total_harga=Decimal('50000'),
            items_summary='1x Ayam KUB DOC'
        )
        self.assertEqual(order.status, OrderStatus.PROSES)
    
    def test_order_item_stores_historical_price(self):
        """OrderItem should preserve price at time of purchase"""
        order = Order.objects.create(
            order_id='DOC-TEST002',
            nama_pembeli='Test User',
            nomor_hp='081234567890',
            metode_pengiriman='AMB',
            metode_pembayaran='COD',
            total_harga=Decimal('50000'),
            items_summary='1x Ayam KUB DOC'
        )
        
        original_price = Decimal('50000')
        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            kuantitas=1,
            harga_saat_beli=original_price
        )
        
        # Change product price
        self.product.harga = Decimal('60000')
        self.product.save()
        
        # OrderItem price should remain unchanged
        item.refresh_from_db()
        self.assertEqual(item.harga_saat_beli, original_price)
