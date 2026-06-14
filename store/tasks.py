"""
Celery tasks for DOC Mart async operations.
Used for: Image processing, email sending, background jobs.
"""
from celery import shared_task
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def convert_product_image_to_webp(self, product_id):
    """
    Async task to convert product image to WebP format.
    Prevents blocking checkout request.
    
    Args:
        product_id: ID of the product to process
    """
    try:
        from .models import Product
        
        product = Product.objects.get(id=product_id)
        
        if not product.gambar or product.gambar.name.lower().endswith('.webp'):
            return f"Product {product_id} image already WebP or missing"
        
        # Open and convert image
        img = Image.open(product.gambar)
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        output = BytesIO()
        img.save(output, format='WEBP', quality=80)
        output.seek(0)
        
        filename = f"{slugify(product.nama)}.webp"
        
        with transaction.atomic():
            product.gambar.save(filename, ContentFile(output.read()), save=True)
        
        logger.info(f"Product {product_id} image converted to WebP successfully")
        return f"Product {product_id} image converted successfully"
        
    except Product.DoesNotExist:
        logger.error(f"Product {product_id} not found")
        return f"Product {product_id} not found"
    except Exception as exc:
        logger.error(f"Error converting product {product_id} image: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(bind=True, max_retries=3)
def convert_order_payment_proof_to_webp(self, order_id):
    """
    Async task to convert order payment proof image to WebP format.
    
    Args:
        order_id: ID of the order to process
    """
    try:
        from .models import Order
        
        order = Order.objects.get(id=order_id)
        
        if not order.bukti_pembayaran or order.bukti_pembayaran.name.lower().endswith('.webp'):
            return f"Order {order_id} proof image already WebP or missing"
        
        # Open and convert image
        img = Image.open(order.bukti_pembayaran)
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        output = BytesIO()
        img.save(output, format='WEBP', quality=80)
        output.seek(0)
        
        filename = f"{order.order_id}.webp"
        
        with transaction.atomic():
            order.bukti_pembayaran.save(filename, ContentFile(output.read()), save=True)
        
        logger.info(f"Order {order_id} proof image converted to WebP successfully")
        return f"Order {order_id} proof image converted successfully"
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return f"Order {order_id} not found"
    except Exception as exc:
        logger.error(f"Error converting order {order_id} proof image: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
