import os
import json
import uuid
import requests
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, datetime

import re
from django.utils.html import strip_tags

from django.contrib.auth import update_session_auth_hash

import random

# Impor tambahan DeliveryMethod dan PaymentMethod untuk validasi keamanan
from .models import Product, Order, OrderItem, OrderStatus, DeliveryMethod, PaymentMethod, StoreSetting
from .tasks import convert_product_image_to_webp, convert_order_payment_proof_to_webp

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django import forms
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

admin_only = user_passes_test(lambda u: u.is_superuser, login_url='/pengelola/login/')

class AdminLoginForm(AuthenticationForm):
    """Form login admin khusus dengan validasi Cloudflare Turnstile Backend"""
    
    def clean(self):
        cleaned_data = super().clean()
        
        request = self.request
        turnstile_token = request.POST.get('cf-turnstile-response')
        
        if not turnstile_token:
            raise forms.ValidationError("Verifikasi keamanan Captcha wajib diisi.")
            
        try:
            response = requests.post(
                'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                data={
                    'secret': settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
                    'response': turnstile_token,
                },
                timeout=5 
            )
            result = response.json()
            
            if not result.get('success'):
                raise forms.ValidationError("Verifikasi Captcha gagal. Deteksi aktivitas mencurigakan.")
                
        except requests.exceptions.RequestException:
            raise forms.ValidationError("Gagal menghubungi server verifikasi. Silakan coba sesaat lagi.")
            
        return cleaned_data


@method_decorator([
    ratelimit(key='ip', rate='10/m', method='POST', block=True),
    ratelimit(key='post:username', rate='5/15m', method='POST', block=True)
], name='dispatch')
class CustomAdminLoginView(LoginView):
    """View Login Admin yang dilindungi Cloudflare Turnstile & Multi-Key Rate Limiting"""
    form_class = AdminLoginForm
    template_name = 'pengelola/login.html'
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['turnstile_site_key'] = settings.CLOUDFLARE_TURNSTILE_SITE_KEY
        return context

@admin_only
def inventory_list(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Product.objects.values_list('kategori', flat=True).distinct()
    
    q = request.GET.get('q', '')
    kategori = request.GET.get('kategori', 'ALL')
    stok = request.GET.get('stok', 'ALL')
    
    if q:
        products = products.filter(
            Q(nama__icontains=q) | 
            Q(kode_unik__icontains=q)
        )
        
    if kategori != 'ALL':
        products = products.filter(kategori=kategori)
        
    if stok == 'SAFE':
        products = products.filter(stok__gte=10)
    elif stok == 'LOW':
        products = products.filter(stok__lt=10)
        
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    query = request.GET.copy()
    if 'page' in query:
        del query['page']

    context = {
        'products': page_obj,
        'query_string': query.urlencode(),
        'category_choices': categories,
        'current_q': q,
        'current_kategori': kategori,
        'current_stok': stok,
    }
    return render(request, 'store/admin/inventory.html', context)

@admin_only
def overview_dashboard(request):
    sales_aggregation = Order.objects.filter(status=OrderStatus.SELESAI).aggregate(total_sales=Sum('total_harga'))
    total_sales = sales_aggregation['total_sales'] or 0
    total_orders = Order.objects.count()
    low_stock_count = Product.objects.filter(stok__lt=10).count()
    recent_orders = Order.objects.order_by('-order_date')[:4]

    top_products = Product.objects.annotate(
        total_sold=Sum('order_items__kuantitas')
    ).exclude(
        total_sold=None
    ).order_by('-total_sold')[:4]

    now_local = timezone.localtime(timezone.now())
    seven_days_ago_date = now_local.date() - timedelta(days=6)
    
    start_datetime = timezone.make_aware(datetime.combine(seven_days_ago_date, datetime.min.time()))
    
    raw_orders = Order.objects.filter(
        status='SLS',
        order_date__gte=start_datetime
    ).values('order_date', 'total_harga')
    
    date_labels = [(seven_days_ago_date + timedelta(days=i)).strftime('%d %b') for i in range(7)]
    revenue_data = [0.0] * 7
    
    for order in raw_orders:
        local_order_time = timezone.localtime(order['order_date'])
        date_str = local_order_time.strftime('%d %b')
        if date_str in date_labels:
            index = date_labels.index(date_str)
            revenue_data[index] += float(order['total_harga'])

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'low_stock_count': low_stock_count,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'chart_labels': json.dumps(date_labels),
        'chart_data': json.dumps(revenue_data),
    }

    return render(request, 'store/admin/overview.html', context)

@admin_only
def order_management(request):
    orders = Order.objects.all().order_by('-order_date')

    status_filter = request.GET.get('status', 'ALL')
    date_filter = request.GET.get('date', '')
    q = request.GET.get('q', '')

    if q:
        orders = orders.filter(
            Q(order_id__icontains=q) | 
            Q(nama_pembeli__icontains=q)
        )

    if status_filter != 'ALL':
        valid_statuses = [choice[0] for choice in OrderStatus.choices]
        if status_filter in valid_statuses:
            orders = orders.filter(status=status_filter)
            
    if date_filter:
        orders = orders.filter(order_date__date=date_filter)

    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    query = request.GET.copy()
    if 'page' in query:
        del query['page']

    context = {
        'orders': page_obj,
        'query_string': query.urlencode(),
        'current_status': status_filter,
        'status_choices': OrderStatus.choices,
        'current_q': q,
        'current_date': date_filter,
    }
    return render(request, 'store/admin/orders.html', context)

@admin_only
def export_orders_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Laporan Pesanan"
    
    ws.views.sheetView[0].showGridLines = True
    
    HEADER_FILL = PatternFill(start_color="143D11", end_color="143D11", fill_type="solid")
    CARD_FILL = PatternFill(start_color="F1F8E9", end_color="F1F8E9", fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color="F9FBE7", end_color="F9FBE7", fill_type="solid")
    
    FONT_TITLE = Font(name="Arial", size=15, bold=True, color="143D11")
    FONT_HEADER = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    FONT_CARD_LABEL = Font(name="Arial", size=9, bold=False, color="555555")
    FONT_CARD_VALUE = Font(name="Arial", size=13, bold=True, color="143D11")
    FONT_BODY = Font(name="Arial", size=10)
    
    THIN_BORDER = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    )
    
    ws['A1'] = f"LAPORAN MANAJEMEN PESANAN - {pengaturan.nama_toko.upper()}"
    ws['A1'].font = FONT_TITLE
    
    ws.merge_cells('A3:C3')
    ws.merge_cells('A4:C4')
    ws['A3'] = "TOTAL PENDAPATAN REALISASI (STATUS: SELESAI)"
    ws['A3'].font = FONT_CARD_LABEL
    ws['A3'].fill = CARD_FILL
    ws['A3'].alignment = Alignment(horizontal="center", vertical="center")
    
    ws['A4'] = '=SUMIF(I6:I500, "Selesai", J6:J500)'
    ws['A4'].font = FONT_CARD_VALUE
    ws['A4'].fill = CARD_FILL
    ws['A4'].number_format = '"Rp"#,##0'
    ws['A4'].alignment = Alignment(horizontal="center", vertical="center")
    
    for r in range(3, 5):
        for c in range(1, 4):
            ws.cell(row=r, column=c).border = THIN_BORDER

    headers = [
        "No", "Order ID", "Nama Pembeli", "No WhatsApp", 
        "Pengiriman", "Alamat Detail", "Jarak (KM)", 
        "Pembayaran", "Status", "Total Harga", "Tanggal Order"
    ]
    
    header_row = 5
    for col_num, header_title in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num)
        cell.value = header_title
        cell.font = FONT_HEADER
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        
    orders = Order.objects.all().order_by('-order_date')
    start_data_row = 6
    
    status_dv = DataValidation(type="list", formula1='"Proses,Selesai,Batal"', allow_blank=True)
    ws.add_data_validation(status_dv)
    
    status_map = {
        'PRO': 'Proses',
        'SLS': 'Selesai',
        'BTL': 'Batal'
    }
    
    for idx, order in enumerate(orders, 1):
        current_row = start_data_row + idx - 1
        
        status_label = status_map.get(order.status, 'Proses')
        metode_png = order.get_metode_pengiriman_display()
        metode_pemb = order.get_metode_pembayaran_display()
        tanggal_str = timezone.localtime(order.order_date).strftime('%d-%m-%Y %H:%M') if order.order_date else ''
        
        row_data = [
            idx,
            order.order_id,
            order.nama_pembeli,
            order.nomor_hp,
            metode_png,
            order.alamat or '-',
            float(order.jarak_km) if order.jarak_km else 0,
            metode_pemb,
            status_label,
            float(order.total_harga),
            tanggal_str
        ]
        
        for col_num, val in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_num)
            cell.value = val
            cell.font = FONT_BODY
            cell.border = THIN_BORDER
            
            if col_num in [1, 2, 4, 7, 8, 9, 11]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
            if col_num == 7:
                cell.number_format = '0.00'
            elif col_num == 10:
                cell.number_format = '"Rp"#,##0'
                
            if idx % 2 == 0:
                cell.fill = ZEBRA_FILL
        
        status_dv.add(ws.cell(row=current_row, column=9))
        
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.row < 5:
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 5, 12)
        
    ws.row_dimensions[5].height = 26
    
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    nama_file_aman = pengaturan.nama_toko.replace(' ', '_')
    response["Content-Disposition"] = f"attachment; filename=Laporan_Penjualan_{nama_file_aman}.xlsx"
    wb.save(response)
    return response


@admin_only
def add_product(request):
    existing_categories = Product.objects.values_list('kategori', flat=True).distinct()
    
    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        kode_unik = request.POST.get('kode_unik', '').strip().upper()
        kategori_pilihan = request.POST.get('kategori', '').strip()
        kategori_baru = request.POST.get('kategori_baru', '').strip()
        
        # Validasi Harga dan Stok (Mencegah huruf dan angka minus)
        try:
            harga = float(request.POST.get('harga', 0))
            stok = int(request.POST.get('stok', 0))
            if harga < 0 or stok < 0:
                raise ValueError("Harga dan Stok tidak boleh bernilai negatif.")
        except ValueError:
            messages.error(request, "Input Harga atau Stok tidak valid. Pastikan hanya memasukkan angka positif.")
            return redirect('store:add_product')
            
        gambar_upload = request.FILES.get('gambar')
        
        # Validasi Gambar (Maks 5 MB & format aman)
        if gambar_upload:
            if gambar_upload.size > 5242880:
                messages.error(request, "Ukuran gambar maksimal 5 MB.")
                return redirect('store:add_product')
            ext = os.path.splitext(gambar_upload.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                messages.error(request, "Format file gambar tidak didukung.")
                return redirect('store:add_product')
                
        kategori_final = kategori_baru if kategori_pilihan == 'BARU' and kategori_baru else kategori_pilihan
        if not kategori_final:
            kategori_final = "Uncategorized"
            
        try:
            Product.objects.create(
                nama=nama,
                kode_unik=kode_unik,
                kategori=kategori_final,
                harga=harga,
                stok=stok,
                gambar=gambar_upload
            )
            messages.success(request, f"Produk '{nama}' berhasil ditambahkan!")
            return redirect('store:inventory')
        except IntegrityError:
            messages.error(request, f"Kode Unik '{kode_unik}' sudah digunakan!")
            
    return render(request, 'store/admin/add_product.html', {'categories': existing_categories})

@admin_only
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    existing_categories = Product.objects.values_list('kategori', flat=True).distinct()
    
    if request.method == 'POST':
        product.nama = request.POST.get('nama', '').strip()
        product.kode_unik = request.POST.get('kode_unik', '').strip().upper()
        
        kategori_pilihan = request.POST.get('kategori', '').strip()
        kategori_baru = request.POST.get('kategori_baru', '').strip()
        product.kategori = kategori_baru if kategori_pilihan == 'BARU' and kategori_baru else kategori_pilihan
        
        # Validasi Harga dan Stok
        try:
            product.harga = float(request.POST.get('harga', product.harga))
            product.stok = int(request.POST.get('stok', product.stok))
            if product.harga < 0 or product.stok < 0:
                raise ValueError("Harga dan Stok tidak boleh bernilai negatif.")
        except ValueError:
            messages.error(request, "Input Harga atau Stok tidak valid. Pastikan hanya memasukkan angka positif.")
            return redirect('store:edit_product', product_id=product.id)
        
        gambar_upload = request.FILES.get('gambar')
        if gambar_upload:
            if gambar_upload.size > 5242880:
                messages.error(request, "Ukuran gambar maksimal 5 MB.")
                return redirect('store:edit_product', product_id=product.id)
            ext = os.path.splitext(gambar_upload.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                messages.error(request, "Format file gambar tidak didukung.")
                return redirect('store:edit_product', product_id=product.id)
            product.gambar = gambar_upload
        
        try:
            product.save()
            messages.success(request, f"Produk '{product.nama}' berhasil diperbarui!")
            return redirect('store:inventory')
        except IntegrityError:
            messages.error(request, "Gagal! Kode Unik bertabrakan dengan produk lain.")
            
    return render(request, 'store/admin/edit_product.html', {'product': product, 'categories': existing_categories})

@admin_only
def delete_product(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        nama_produk = product.nama
        product.delete()
        messages.success(request, f"Produk '{nama_produk}' telah dihapus dari sistem.")
    return redirect('store:inventory')

@admin_only
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        
        valid_statuses = [choice[0] for choice in OrderStatus.choices]
        if new_status in valid_statuses:
            order.status = new_status
            order.save()
            messages.success(request, f"Status pesanan {order.order_id} berhasil diperbarui!")
        else:
            messages.error(request, "Aksi ditolak: Status tidak valid.")
            
    return redirect('store:orders')

@admin_only
def order_invoice(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    
    context = {
        'order': order,
    }
    return render(request, 'store/admin/invoice.html', context)


def index(request):
    featured_products = Product.objects.all()
    return render(request, 'store/web/index.html', {'featured_products': featured_products})

def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Product.objects.values_list('kategori', flat=True).distinct()
    selected_cats = request.GET.getlist('cat')
    
    if selected_cats:
        products = products.filter(kategori__in=selected_cats)
        
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    query = request.GET.copy()
    if 'page' in query:
        del query['page']
        
    context = {
        'products': page_obj,
        'query_string': query.urlencode(),
        'categories': categories,        
        'selected_cats': selected_cats,  
    }
    
    return render(request, 'store/web/shop.html', context)

def cart_view(request):
    return render(request, 'store/web/cart.html')

@ratelimit(key='ip', rate='10/h', method='POST')
def checkout_process(request):
    if request.method == 'GET':
        return render(request, 'store/web/checkout.html')
        
    if request.method == 'POST':
        try:
            # 1. PEMBERSIHAN STRING DASAR (Cegah Spasi Kosong)
            nama = strip_tags(request.POST.get('nama', '')).strip()
            hp = strip_tags(request.POST.get('hp', '')).strip()
            pengiriman = strip_tags(request.POST.get('pengiriman', '')).strip()
            pembayaran = strip_tags(request.POST.get('pembayaran', '')).strip()
            alamat = strip_tags(request.POST.get('alamat', '')).strip()
            lat = strip_tags(request.POST.get('lat', '')).strip()
            lng = strip_tags(request.POST.get('lng', '')).strip()
            
            # 2. VALIDASI KEAMANAN DATA TEKS & NOMOR
            if not nama or not hp:
                messages.error(request, "Nama dan Nomor HP wajib diisi.")
                return redirect('store:checkout')
                
            if len(nama) > 50:
                messages.error(request, "Nama terlalu panjang. Silakan gunakan nama panggilan.")
                return redirect('store:checkout')
                
            if any(char.isdigit() for char in nama):
                messages.error(request, "Nama tidak boleh mengandung angka.")
                return redirect('store:checkout')
                
            spam_keywords = ['jasa', 'pembuatan', 'website', 'aplikasi', 'promo', 'http', 'www', '.com', '.id', 'slot', 'gacor']
            if any(keyword in nama.lower() for keyword in spam_keywords):
                messages.error(request, "Sistem mendeteksi indikasi spam. Transaksi ditolak.")
                return redirect('store:checkout')
                
            # Pemblokir Simbol Ilegal (Payload XSS)
            if re.search(r'[<>={\}\[\];]', nama):
                messages.error(request, "Nama mengandung simbol ilegal. Harap masukkan nama yang valid.")
                return redirect('store:checkout')

            if not hp.isdigit() or len(hp) < 10 or len(hp) > 15:
                messages.error(request, "Nomor HP tidak valid. Gunakan 10-15 angka tanpa spasi/simbol.")
                return redirect('store:checkout')

            # E. VALIDASI KODE OTP
            input_otp = request.POST.get('otp', '').strip()
            session_otp = request.session.get('otp_code')
            session_hp = request.session.get('otp_phone')

            if not input_otp:
                messages.error(request, "Anda wajib melakukan verifikasi Nomor HP dengan meminta kode OTP.")
                return redirect('store:checkout')

            # Periksa apakah OTP salah, ATAU user nakal mengubah nomor HP-nya setelah meminta OTP
            if input_otp != session_otp or hp != session_hp:
                messages.error(request, "Kode OTP salah atau tidak cocok dengan Nomor HP. Silakan minta OTP ulang.")
                return redirect('store:checkout')

            # Hancurkan memori OTP di server agar tidak bisa dipakai 2 kali (Replay Attack)
            del request.session['otp_code']
            del request.session['otp_phone']

            # 3. VALIDASI PILIHAN (CHOICES)
            valid_pengiriman = [choice[0] for choice in DeliveryMethod.choices]
            valid_pembayaran = [choice[0] for choice in PaymentMethod.choices]
            
            if pengiriman not in valid_pengiriman:
                messages.error(request, "Metode pengiriman tidak valid.")
                return redirect('store:checkout')
                
            if pembayaran not in valid_pembayaran:
                messages.error(request, "Metode pembayaran tidak valid.")
                return redirect('store:checkout')

            # 4. VALIDASI FILE GAMBAR
            bukti_tf = request.FILES.get('bukti_pembayaran')
            if bukti_tf:
                if bukti_tf.size > 5242880:
                    messages.error(request, "Ukuran gambar terlalu besar. Maksimal 5 MB.")
                    return redirect('store:checkout')
                
                ext = os.path.splitext(bukti_tf.name)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                    messages.error(request, "Format file tidak didukung. Gunakan JPG, PNG, atau WEBP.")
                    return redirect('store:checkout')

            jarak_raw = request.POST.get('jarak_km', '')
            jarak_km = None
            if jarak_raw:
                try:
                    jarak_km = float(jarak_raw)
                    if jarak_km < 0 or jarak_km > 500:
                        messages.error(request, "Jarak harus antara 0-500 km.")
                        return redirect('store:checkout')
                except ValueError:
                    messages.error(request, "Format jarak tidak valid.")
                    return redirect('store:checkout')
            
            cart_data = json.loads(request.POST.get('cart_data', '[]'))
            
            if not cart_data:
                messages.error(request, "Keranjang Anda kosong.")
                return redirect('store:checkout')

            with transaction.atomic():
                total_kalkulasi_sistem = 0
                rincian_item = []
                order_id_generate = f"DOC-{uuid.uuid4().hex[:6].upper()}"
                
                order = Order.objects.create(
                    order_id=order_id_generate,
                    nama_pembeli=nama,
                    nomor_hp=hp,
                    metode_pengiriman=pengiriman,
                    alamat=alamat if pengiriman == 'ANT' else 'Ambil di Kandang',
                    latitude=lat,
                    longitude=lng,
                    jarak_km=jarak_km,
                    metode_pembayaran=pembayaran,
                    bukti_pembayaran=bukti_tf,
                    total_harga=0, 
                    items_summary="Menunggu..."
                )

                for item in cart_data:
                    product_id = item.get('id')
                    
                    # 5. VALIDASI ANTI-HACK KUANTITAS MINUS/NOL
                    try:
                        kuantitas = int(item.get('qty', 0))
                    except ValueError:
                        raise ValueError("Format kuantitas barang rusak.")
                        
                    if kuantitas <= 0:
                        raise ValueError("Terdeteksi anomali pada keranjang (kuantitas tidak boleh nol/minus)!")
                    
                    product = Product.objects.select_for_update().get(id=product_id)
                    if product.stok < kuantitas:
                        raise ValueError(f"Checkout gagal: Stok '{product.nama}' tersisa {product.stok}.")
                        
                    product.stok -= kuantitas
                    product.save()
                    
                    subtotal = product.harga * kuantitas
                    total_kalkulasi_sistem += subtotal
                    
                    OrderItem.objects.create(
                        order=order, product=product, kuantitas=kuantitas, harga_saat_beli=product.harga
                    )
                    rincian_item.append(f"{kuantitas}x {product.nama}")

                ongkos_kirim = 0
                if pengiriman == 'ANT' and jarak_km:
                    ongkos_kirim = int(jarak_km * 5000)
                    rincian_item.append(f"Ongkir ({jarak_km} km)")

                order.total_harga = total_kalkulasi_sistem + ongkos_kirim
                order.items_summary = ", ".join(rincian_item)[:250]
                order.save()

            fonnte_token = settings.FONNTE_TOKEN
            # Ambil nomor dari database pengaturan
            pengaturan_toko = StoreSetting.load()
            nomor_admin = pengaturan_toko.nomor_admin
            
            allowed_domains = settings.ALLOWED_HOSTS
            domain = allowed_domains[0] if allowed_domains else 'localhost'
            protocol = 'https' if not settings.DEBUG else 'http'

            link_faktur_admin = f"{protocol}://{domain}/pengelola/orders/{order.id}/invoice/"
            link_faktur_pelanggan = f"{protocol}://{domain}/track/"

            maps_url = f"https://www.google.com/maps?q={lat},{lng}" if pengiriman == 'ANT' else "Diambil sendiri."

            pesan_admin = (
                f"*PESANAN BARU MASUK!*\n\n"
                f"Order ID: {order.order_id}\n"
                f"Pembeli: {order.nama_pembeli}\n"
                f"No HP: {order.nomor_hp}\n"
                f"Total Akhir: Rp{order.total_harga:,.0f}\n\n"
                f"Buka Faktur Lengkap:\n{link_faktur_admin}\n\n"
                f"Lokasi Peta: {maps_url}"
            )

            pesan_pelanggan = (
                f"Halo *{order.nama_pembeli}*,\n\n"
                f"Terima kasih telah berbelanja di *{pengaturan_toko.nama_toko}*! \n"
                f"Pesanan Anda dengan ID *{order.order_id}* telah kami terima dan sedang kami proses.\n\n"
                f"Total Tagihan: *Rp{order.total_harga:,.0f}*\n\n"
                f"CEK STATUS & FAKTUR PESANAN ANDA DI SINI:\n"
                f"{link_faktur_pelanggan}\n\n"
            )

            pesan_pelanggan += "Tolong ketika tidak, jika merasa tidak memesan, dan ya jikga memesan. Terima kasih!"

            try:
                requests.post(
                    "https://api.fonnte.com/send", 
                    headers={"Authorization": fonnte_token}, 
                    data={"target": nomor_admin, "message": pesan_admin}
                )
                requests.post(
                    "https://api.fonnte.com/send", 
                    headers={"Authorization": fonnte_token}, 
                    data={"target": hp, "message": pesan_pelanggan}
                )
            except Exception as e:
                print(f"Peringatan: Gagal mengirim WhatsApp. {str(e)}")

            return render(request, 'store/web/order_success.html', {'order_id': order.order_id})
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('store:checkout')
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan: {str(e)}")
            return redirect('store:checkout')
         
@ratelimit(key='ip', rate='20/h', method='POST')
def track_order(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id', '').strip()
        hp = request.POST.get('hp', '').strip()
        
        try:
            order = Order.objects.get(order_id=order_id, nomor_hp=hp)
            return redirect('store:public_invoice', order_id=order.order_id)
        except Order.DoesNotExist:
            messages.error(request, "Pesanan tidak ditemukan. Periksa kembali ID Pesanan dan Nomor WA Anda.")
            
    return render(request, 'store/web/track_order.html')

def public_invoice(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_id=order_id)
    
    context = {
        'order': order,
        'is_public': True 
    }
    return render(request, 'store/admin/invoice.html', context)

@ratelimit(key='ip', rate='5/h', method='POST') # Batasi 1 IP maksimal minta OTP 5x per jam
def send_otp_wa(request):
    """ API untuk mengirim OTP ke WhatsApp pelanggan via AJAX """
    if request.method == 'POST':
        # Mendukung pembacaan data JSON dari Fetch API JavaScript
        try:
            body = json.loads(request.body)
            hp = body.get('hp', '').strip()
        except:
            hp = request.POST.get('hp', '').strip()
            
        hp = strip_tags(hp)
        if not hp.isdigit() or len(hp) < 10 or len(hp) > 15:
            return JsonResponse({'status': 'error', 'message': 'Nomor HP tidak valid. Gunakan angka 10-15 digit.'}, status=400)

        # 1. Hasilkan 6 digit angka acak
        otp = str(random.randint(100000, 999999))
        
        # 2. Simpan OTP dan Nomor HP ke dalam Session (Ingatan Server)
        request.session['otp_code'] = otp
        request.session['otp_phone'] = hp

        # 3. Pesan yang dikirim ke Pelanggan
        pesan = (
            f"*VERIFIKASI Kelompok Tani Melati*\n\n"
            f"Kode Rahasia (OTP) Anda adalah: *{otp}*\n\n"
            f"Kode ini digunakan untuk verifikasi pesanan. *JANGAN* berikan kode ini kepada siapapun."
        )

        # 4. Eksekusi Pengiriman via Fonnte
        try:
            fonnte_token = settings.FONNTE_TOKEN
            response = requests.post(
                "https://api.fonnte.com/send", 
                headers={"Authorization": fonnte_token}, 
                data={"target": hp, "message": pesan},
                timeout=5
            )
            if response.status_code == 200:
                return JsonResponse({'status': 'success', 'message': 'OTP berhasil dikirim ke WhatsApp!'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Gagal mengirim pesan dari sisi gateway.'}, status=500)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Gagal koneksi ke server Fonnte.'}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Method tidak diizinkan.'}, status=405)

@admin_only
def admin_settings(request):
    setting = StoreSetting.load()
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        # Jika Admin menyimpan profil/info web
        if 'save_web_settings' in request.POST:
            setting.nama_toko = request.POST.get('nama_toko', '').strip()
            setting.nomor_admin = request.POST.get('nomor_admin', '').strip()
            setting.hero_title = request.POST.get('hero_title')
            setting.hero_description = request.POST.get('hero_description')
            setting.rekening_bank = request.POST.get('rekening_bank')
            setting.rekening_nama = request.POST.get('rekening_nama')
            setting.biaya_per_km = request.POST.get('biaya_per_km', 5000)
            setting.latitude = request.POST.get('latitude')
            setting.longitude = request.POST.get('longitude')
            setting.alamat_toko = request.POST.get('alamat_toko')
            if 'hero_image' in request.FILES:
                setting.hero_image = request.FILES['hero_image']
                
            setting.save()
            messages.success(request, "Pengaturan toko berhasil diperbarui!")
            return redirect('store:admin_settings')
            
        # Jika Admin mengubah password
        elif 'save_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Cegah admin otomatis logout
                messages.success(request, "Password administrator berhasil diubah!")
                return redirect('store:admin_settings')
            else:
                messages.error(request, "Gagal mengubah password. Pastikan input sudah benar.")

    context = {
        'setting': setting,
        'password_form': password_form
    }
    return render(request, 'store/admin/settings.html', context)

@admin_only
def api_pending_orders(request):
    """ API Ringan untuk mensuplai data Dropdown Notifikasi """
    # Ambil 5 pesanan terbaru yang berstatus PROSES
    orders = Order.objects.filter(status=OrderStatus.PROSES).order_by('-order_date')[:5]
    total_proses = Order.objects.filter(status=OrderStatus.PROSES).count()
    
    data = []
    for o in orders:
        data.append({
            'id': o.order_id,
            'nama': o.nama_pembeli,
            'total': f"Rp{o.total_harga:,.0f}",
            'waktu': timezone.localtime(o.order_date).strftime('%d %b %H:%M')
        })
    return JsonResponse({'count': total_proses, 'orders': data})