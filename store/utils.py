from django.db import transaction
from django.utils import timezone
from .models import OrderCounter, Order, OrderStatus

def generate_order_id():
    """ Menghasilkan ID: KTM-YYYYMMDD-NNNN secara atomik dan aman dari duplikat """
    with transaction.atomic():
        today = timezone.now().date()
        # select_for_update() mengunci baris ini selama transaksi berjalan (mencegah race condition)
        counter_obj, created = OrderCounter.objects.select_for_update().get_or_create(
            tanggal=today,
            defaults={'counter': 0}
        )
        
        counter_obj.counter += 1
        counter_obj.save()
        
        date_str = today.strftime("%Y%m%d")
        return f"KTM-{date_str}-{counter_obj.counter:04d}"

def get_posisi_antrean(order):
    """ Menghitung ada berapa antrean di depan pesanan ini untuk kategori yang sama """
    if order.status != OrderStatus.ANTRIAN:
        return None
        
    first_item = order.items.first()
    if not first_item:
        return None
        
    kategori_pesanan = first_item.product.kategori
    
    # Hitung jumlah order dengan status ANTRIAN, kategori yang sama, dan masuk LEBIH DULU
    antrean_di_depan = Order.objects.filter(
        status=OrderStatus.ANTRIAN,
        items__product__kategori=kategori_pesanan,
        order_date__lt=order.order_date
    ).distinct().count()
    
    # Jika di depan ada 5 orang, berarti posisi kita adalah 6
    return antrean_di_depan + 1