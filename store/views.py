import os
import json
import uuid
import requests
import random
from datetime import datetime, timedelta

from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Q
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django_ratelimit.decorators import ratelimit

import openpyxl
# from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
# from openpyxl.worksheet.datavalidation import DataValidation

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
import io
import sys

# Menggunakan CustomUser baru
from .models import CustomUser, Product, Order, OrderItem, OrderStatus, StoreSetting, Ekspedisi
from .utils import generate_order_id, get_posisi_antrean

# Perlindungan akses khusus Admin (diarahkan ke /login/ umum)
admin_only = user_passes_test(lambda u: u.is_superuser or u.is_staff, login_url='/login/')


# ==========================================
# 1. HALAMAN PUBLIK
# ==========================================
def index(request):
    toko = StoreSetting.load()
    produk_telur = Product.objects.filter(kategori__icontains='Telur').order_by('-created_at')
    produk_doc = Product.objects.filter(kategori__icontains='DOC').order_by('-created_at')
    
    context = {
        'toko': toko,
        'produk_telur': produk_telur,
        'produk_doc': produk_doc,
    }
    return render(request, 'store/web/index.html', context)


# ==========================================
# 2. SISTEM OTENTIKASI & PROFIL
# ==========================================
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            # KEMBALI KE DASBOR CUSTOM KITA
            return redirect('store:overview') 
        else:
            return redirect('store:customer_dashboard')

    if request.method == 'POST':
        nomor_wa = request.POST.get('nomor_wa', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, nomor_wa=nomor_wa, password=password)
        
        if user is not None:
            login(request, user)
            if user.is_staff:
                # KEMBALI KE DASBOR CUSTOM KITA
                return redirect('store:overview') 
            else:
                if not user.nama_lengkap:
                    messages.warning(request, "Silakan lengkapi identitas Anda sebelum memesan.")
                    return redirect('store:lengkapi_profil')
                return redirect('store:customer_dashboard')
        else:
            messages.error(request, "Nomor WA atau Password salah!")

    return render(request, 'store/web/login.html')

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('store:customer_dashboard')

    if request.method == 'POST':
        # Data Otentikasi
        nomor_wa = request.POST.get('whatsapp', '').strip()
        password = request.POST.get('password', '')
        password_confirmation = request.POST.get('password_confirmation', '')
        otp_input = request.POST.get('otp', '').strip() # Pastikan field name ini sesuai dengan input OTP di HTML
        
        # Data Profil & Alamat (Terpisah)
        nama = request.POST.get('name', '').strip()
        provinsi = request.POST.get('provinsi_nama', '')
        kabupaten = request.POST.get('kabupaten_nama', '')
        kecamatan = request.POST.get('kecamatan_nama', '')
        kelurahan = request.POST.get('kelurahan_nama', '')
        alamat_detail = request.POST.get('address', '').strip()
        
        # 1. Validasi Password
        if password != password_confirmation:
            messages.error(request, "Pendaftaran Gagal: Password dan Ulangi Password tidak cocok!")
            return redirect('store:register')
            
        # 2. Validasi Kelengkapan Data
        if not nomor_wa or not password or not nama or not provinsi:
            messages.error(request, "Harap isi semua kolom yang bertanda bintang (*).")
            return redirect('store:register')

        # 3. Validasi OTP (Keamanan Fonnte)
        session_otp = request.session.get('register_otp')
        session_hp = request.session.get('register_hp')
        
        # Jika Anda sudah mengaktifkan input OTP di HTML, blok ini akan memastikannya valid
        if session_otp:
            if not otp_input:
                messages.error(request, "Silakan masukkan kode OTP yang telah dikirim ke WA Anda.")
                return redirect('store:register')
            if otp_input != session_otp:
                messages.error(request, "Kode OTP salah atau tidak valid.")
                return redirect('store:register')
            if nomor_wa != session_hp:
                messages.error(request, "Nomor WhatsApp yang didaftarkan berbeda dengan nomor tujuan OTP.")
                return redirect('store:register')
            
        # 4. Cek Duplikasi WA
        if CustomUser.objects.filter(nomor_wa=nomor_wa).exists():
            messages.error(request, "Nomor WA sudah terdaftar. Silakan Login.")
            return redirect('store:login')

        try:
            user = CustomUser.objects.create_user(
                nomor_wa=nomor_wa, 
                password=password,
                nama_lengkap=nama,
                provinsi=provinsi,
                kabupaten=kabupaten,
                kecamatan=kecamatan,
                kelurahan=kelurahan,
                alamat=alamat_detail
            )
            login(request, user)
            
            # Bersihkan session OTP setelah sukses daftar
            if 'register_otp' in request.session:
                del request.session['register_otp']
                del request.session['register_hp']
                
            messages.success(request, "Pendaftaran berhasil! Selamat datang di Dasbor Anda.")
            return redirect('store:customer_dashboard')
        except Exception as e:
            messages.error(request, f"Pendaftaran Gagal: {str(e)}")
            
    return render(request, 'store/web/register.html')


def logout_view(request):
    logout(request)
    return redirect('store:index')


@login_required(login_url='/login/')
def lengkapi_profil(request):
    if request.user.nama_lengkap and request.user.alamat:
        return redirect('store:customer_dashboard')

    if request.method == 'POST':
        nama_lengkap = request.POST.get('nama_lengkap', '').strip()
        alamat = request.POST.get('alamat_lengkap', '').strip()

        if not nama_lengkap or not alamat:
            messages.error(request, "Nama dan Alamat Lengkap wajib diisi!")
        else:
            user = request.user
            user.nama_lengkap = nama_lengkap
            user.alamat = alamat
            user.save()
            messages.success(request, "Profil disimpan. Selamat datang!")
            return redirect('store:customer_dashboard')

    return render(request, 'store/web/lengkapi_profil.html')

@login_required(login_url='/login/')
def customer_dashboard(request):
    if request.user.is_staff:
        # UBAH MENJADI STORE:OVERVIEW
        return redirect('store:overview') 
        
    if not request.user.nama_lengkap:
        return redirect('store:lengkapi_profil')
    
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    context = {
        'orders': orders,
        'toko': StoreSetting.load()
    }
    return render(request, 'store/web/customer_dashboard.html', context)

@login_required(login_url='/login/')
def profil_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        user = request.user
        
        # 1. LOGIKA BARU: UPDATE NAMA & WA
        if action == 'update_main_profile':
            user.nama_lengkap = request.POST.get('nama_lengkap')
            user.nomor_wa = request.POST.get('nomor_wa')
            user.save()
            messages.success(request, 'Informasi utama akun berhasil diperbarui!')
            return redirect('store:profil')
            
        # 2. LOGIKA LAMA: UPDATE ALAMAT
        elif action == 'update_profile':
            user.provinsi = request.POST.get('provinsi')
            user.kabupaten = request.POST.get('kabupaten')
            user.kecamatan = request.POST.get('kecamatan')
            user.kelurahan = request.POST.get('kelurahan')
            user.alamat = request.POST.get('alamat')
            user.save()
            messages.success(request, 'Informasi alamat berhasil diperbarui!')
            return redirect('store:profil')
            
        # 3. LOGIKA LAMA: UBAH PASSWORD
        elif action == 'update_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not user.check_password(old_password):
                messages.error(request, 'Password lama tidak sesuai! Perubahan dibatalkan.')
            elif new_password != confirm_password:
                messages.error(request, 'Konfirmasi password baru tidak cocok!')
            elif len(new_password) < 8:
                messages.error(request, 'Password baru harus minimal 8 karakter.')
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password berhasil diubah dengan aman!')
                
            return redirect('store:profil')

    return render(request, 'store/web/profil.html')

# ==========================================
# 3. FITUR ADMIN (PENGELOLA)
# ==========================================
@admin_only
def overview_dashboard(request):
    sales_aggregation = Order.objects.filter(status=OrderStatus.SELESAI).aggregate(total_sales=Sum('total_harga'))
    total_sales = sales_aggregation['total_sales'] or 0
    total_orders = Order.objects.count()
    low_stock_count = Product.objects.filter(stok__lt=10).count()
    recent_orders = Order.objects.order_by('-order_date')[:4]

    top_products = Product.objects.annotate(
        total_sold=Sum('order_items__kuantitas')
    ).exclude(total_sold=None).order_by('-total_sold')[:4]

    now_local = timezone.localtime(timezone.now())
    seven_days_ago_date = now_local.date() - timedelta(days=6)
    start_datetime = timezone.make_aware(datetime.combine(seven_days_ago_date, datetime.min.time()))
    
    raw_orders = Order.objects.filter(status=OrderStatus.SELESAI, order_date__gte=start_datetime).values('order_date', 'total_harga')
    
    date_labels = [(seven_days_ago_date + timedelta(days=i)).strftime('%d %b') for i in range(7)]
    revenue_data = [0.0] * 7
    
    for order in raw_orders:
        local_order_time = timezone.localtime(order['order_date'])
        date_str = local_order_time.strftime('%d %b')
        if date_str in date_labels:
            index = date_labels.index(date_str)
            revenue_data[index] += float(order['total_harga'])

    context = {
        'total_sales': total_sales, 'total_orders': total_orders,
        'low_stock_count': low_stock_count, 'recent_orders': recent_orders,
        'top_products': top_products, 'chart_labels': json.dumps(date_labels),
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
        orders = orders.filter(Q(order_id__icontains=q) | Q(user__nama_lengkap__icontains=q) | Q(user__nomor_wa__icontains=q))

    if status_filter != 'ALL':
        valid_statuses = [c[0] for c in OrderStatus.choices]
        if status_filter in valid_statuses:
            orders = orders.filter(status=status_filter)
            
    if date_filter:
        orders = orders.filter(order_date__date=date_filter)

    paginator = Paginator(orders, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    query = request.GET.copy()
    if 'page' in query: del query['page']

    context = {
        'orders': page_obj, 'query_string': query.urlencode(),
        'current_status': status_filter, 'status_choices': OrderStatus.choices,
        'current_q': q, 'current_date': date_filter,
    }
    return render(request, 'store/admin/orders.html', context)


@admin_only
def inventory_list(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Product.objects.values_list('kategori', flat=True).distinct()
    q = request.GET.get('q', '')
    kategori = request.GET.get('kategori', 'ALL')
    stok = request.GET.get('stok', 'ALL')
    
    if q: products = products.filter(Q(nama__icontains=q) | Q(kode_unik__icontains=q))
    if kategori != 'ALL': products = products.filter(kategori=kategori)
    if stok == 'SAFE': products = products.filter(stok__gte=10)
    elif stok == 'LOW': products = products.filter(stok__lt=10)
        
    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    query = request.GET.copy()
    if 'page' in query: del query['page']

    context = {
        'products': page_obj, 'query_string': query.urlencode(),
        'category_choices': categories, 'current_q': q,
        'current_kategori': kategori, 'current_stok': stok,
    }
    return render(request, 'store/admin/inventory.html', context)


@admin_only
def add_product(request):
    existing_categories = Product.objects.values_list('kategori', flat=True).distinct()
    if request.method == 'POST':
        nama = request.POST.get('nama', '').strip()
        kode_unik = request.POST.get('kode_unik', '').strip().upper()
        kategori_pilihan = request.POST.get('kategori', '').strip()
        kategori_baru = request.POST.get('kategori_baru', '').strip()
        
        try:
            harga = float(request.POST.get('harga', 0))
            stok = int(request.POST.get('stok', 0))
            if harga < 0 or stok < 0: raise ValueError()
        except ValueError:
            messages.error(request, "Input Harga/Stok tidak valid.")
            return redirect('store:add_product')
            
        gambar_upload = request.FILES.get('gambar')
        kategori_final = kategori_baru if kategori_pilihan == 'BARU' and kategori_baru else kategori_pilihan
        if not kategori_final: kategori_final = "Uncategorized"
            
        try:
            Product.objects.create(nama=nama, kode_unik=kode_unik, kategori=kategori_final, harga=harga, stok=stok, gambar=gambar_upload)
            messages.success(request, f"Produk '{nama}' ditambahkan!")
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
        
        try:
            product.harga = float(request.POST.get('harga', product.harga))
            product.stok = int(request.POST.get('stok', product.stok))
        except ValueError:
            messages.error(request, "Input Harga/Stok tidak valid.")
            return redirect('store:edit_product', product_id=product.id)
        
        gambar_upload = request.FILES.get('gambar')
        if gambar_upload: product.gambar = gambar_upload
        
        try:
            product.save()
            messages.success(request, "Produk diperbarui!")
            return redirect('store:inventory')
        except IntegrityError:
            messages.error(request, "Kode Unik bertabrakan!")
            
    return render(request, 'store/admin/edit_product.html', {'product': product, 'categories': existing_categories})


@admin_only
def delete_product(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        product.delete()
        messages.success(request, "Produk dihapus.")
    return redirect('store:inventory')


@admin_only
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in [c[0] for c in OrderStatus.choices]:
            order.status = new_status
            order.save()
            messages.success(request, "Status pesanan diperbarui!")
    return redirect('store:orders')

@admin_only
def admin_settings(request):
    setting = StoreSetting.load()
    password_form = PasswordChangeForm(request.user)
    
    # Ambil semua data ekspedisi untuk ditampilkan di tabel HTML
    ekspedisi_list = Ekspedisi.objects.all().order_by('-id')

    if request.method == 'POST':
        # --- LOGIKA FORM PENGATURAN WEB & KONTEN DASHBOARD ---
        if 'save_web_settings' in request.POST:
            setting.nama_toko = request.POST.get('nama_toko', '').strip()
            setting.nomor_admin = request.POST.get('nomor_admin', '').strip()
            setting.hero_title = request.POST.get('hero_title')
            setting.hero_description = request.POST.get('hero_description')
            setting.rekening_bank = request.POST.get('rekening_bank')
            setting.rekening_nama = request.POST.get('rekening_nama')
            setting.biaya_per_km = int(float(request.POST.get('biaya_per_km', 5000)))
            setting.latitude = request.POST.get('latitude')
            setting.longitude = request.POST.get('longitude')
            setting.alamat_toko = request.POST.get('alamat_toko')
            setting.jam_operasional = request.POST.get('jam_operasional')
            
            # --- TANGKAP INPUT KONTEN DASHBOARD ---
            setting.dashboard_welcome_title = request.POST.get('dashboard_welcome_title', '').strip()
            setting.dashboard_intro_text = request.POST.get('dashboard_intro_text', '').strip()
            setting.dashboard_outro_text = request.POST.get('dashboard_outro_text', '').strip()
            setting.syarat_doc = request.POST.get('syarat_doc', '').strip()

            if 'hero_image' in request.FILES:
                setting.hero_image = request.FILES['hero_image']
            setting.save()
            
            messages.success(request, "Pengaturan toko diperbarui!")
            return redirect('store:settings')
            
        # --- LOGIKA UBAH PASSWORD ---
        elif 'save_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password administrator diubah!")
                return redirect('store:settings') 
                
        # ====================================================
        # TAMBAHAN BARU: LOGIKA TAMBAH EKSPEDISI
        # ====================================================
        elif 'add_ekspedisi' in request.POST:
            nama = request.POST.get('nama_ekspedisi')
            biaya = request.POST.get('biaya_ekspedisi')
            
            if nama and biaya:
                Ekspedisi.objects.create(
                    nama=nama,
                    biaya=int(biaya),
                    is_active=True # Default langsung aktif
                )
                messages.success(request, f"Ekspedisi {nama} berhasil ditambahkan.")
            return redirect('store:settings')
            
        # ====================================================
        # TAMBAHAN BARU: LOGIKA HAPUS EKSPEDISI
        # ====================================================
        elif 'delete_ekspedisi' in request.POST:
            eks_id = request.POST.get('ekspedisi_id')
            ekspedisi = get_object_or_404(Ekspedisi, id=eks_id)
            ekspedisi.delete()
            messages.success(request, "Data ekspedisi berhasil dihapus.")
            return redirect('store:settings')

    # Jangan lupa kirim 'ekspedisi_list' ke context agar bisa dilooping di HTML
    context = {
        'setting': setting, 
        'password_form': password_form,
        'ekspedisi_list': ekspedisi_list,
    }
    return render(request, 'store/admin/settings.html', context)

@admin_only
def export_orders_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Laporan Pesanan"
    
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = "attachment; filename=Laporan_Penjualan.xlsx"
    wb.save(response)
    return response


@admin_only
def order_invoice(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    return render(request, 'store/admin/invoice.html', {'order': order})


def public_invoice(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_id=order_id)
    posisi = get_posisi_antrean(order)
    
    context = {
        'order': order,
        'is_public': True,
        'posisi_antrean': posisi
    }
    return render(request, 'store/admin/invoice.html', context)


@admin_only
def api_pending_orders(request):
    orders = Order.objects.filter(status=OrderStatus.ANTRIAN).order_by('-order_date')[:5]
    total_proses = Order.objects.filter(status=OrderStatus.ANTRIAN).count()
    data = [{'id': o.order_id, 'nama': o.user.nama_lengkap, 'total': f"Rp{o.total_harga:,.0f}", 'waktu': timezone.localtime(o.order_date).strftime('%d %b %H:%M')} for o in orders]
    return JsonResponse({'count': total_proses, 'orders': data})


# ==========================================
# 4. SISTEM TRANSAKSI & ANTREAN
# ==========================================
@login_required(login_url='/login/')
def daftar_antrean(request):
    if request.method == 'POST':
        produk_id = request.POST.get('produk_id')
        product = get_object_or_404(Product, id=produk_id)
        
        with transaction.atomic():
            order = Order.objects.create(
                order_id=f"PO-{uuid.uuid4().hex[:6].upper()}",
                user=request.user,
                status=OrderStatus.ANTRIAN,
                total_harga=product.harga
            )
            OrderItem.objects.create(
                order=order, product=product, kuantitas=1, harga_saat_beli=product.harga
            )
        
        messages.success(request, "Anda berhasil masuk daftar tunggu! Cek status di halaman Antrean.")
        return redirect('store:daftar_antrean_view')
    
    orders = Order.objects.filter(status=OrderStatus.ANTRIAN).order_by('order_date')
    context = {'orders': orders}
    return render(request, 'store/web/daftar_antrean.html', context)


@ratelimit(key='ip', rate='10/h', method='POST')
@login_required(login_url='/login/')
def proses_po(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        qty_str = request.POST.get('kuantitas')
        ekspedisi_id = request.POST.get('pengiriman') # Sekarang menangkap ID ekspedisi
        
        if not product_id or not qty_str or not ekspedisi_id:
            messages.error(request, "Data pesanan tidak lengkap.")
            return redirect('store:order_doc')

        qty = int(qty_str)
        product = get_object_or_404(Product, id=product_id)
        
        # Ambil objek ekspedisi dari database
        ekspedisi = get_object_or_404(Ekspedisi, id=ekspedisi_id)
        
        with transaction.atomic():
            order_id = generate_order_id()
            alamat_user = getattr(request.user, 'alamat', 'Alamat tidak tersedia')
            
            # Kalkulasi total = (harga produk * qty) + ongkir
            total_produk = product.harga * qty
            total_semua = total_produk + ekspedisi.biaya
            
            order = Order.objects.create(
                order_id=order_id,
                user=request.user,
                status=OrderStatus.MENUNGGU_DP,
                total_harga=int(total_semua), # Total sudah termasuk ongkir
                biaya_ongkir=int(ekspedisi.biaya), # Simpan nominal ongkir
                tagihan_dp=int(50000 + random.randint(1, 999)),
                alamat_pengiriman=alamat_user,
                metode_pengiriman=ekspedisi.nama # Simpan nama ekspedisinya
            )
            
            OrderItem.objects.create(
                order=order, 
                product=product, 
                kuantitas=qty, 
                harga_saat_beli=product.harga
            )
        
        return redirect('store:public_invoice', order_id=order.order_id)
        
    return redirect('store:order_doc')

def info_antrian(request):
    ringkasan_kuantitas = OrderItem.objects.filter(
        order__status=OrderStatus.ANTRIAN
    ).values('product__kategori').annotate(
        total_qty=Sum('kuantitas')
    ).order_by('product__kategori')

    filter_kategori = request.GET.get('kategori', 'ALL')
    
    antrean_list = Order.objects.filter(
        status=OrderStatus.ANTRIAN
    ).order_by('order_date').prefetch_related('items__product', 'user')

    if filter_kategori != 'ALL':
        antrean_list = antrean_list.filter(items__product__kategori=filter_kategori).distinct()

    posisi_saya = {}
    if request.user.is_authenticated:
        pesanan_saya = antrean_list.filter(user=request.user)
        for p in pesanan_saya:
            posisi = get_posisi_antrean(p)
            posisi_saya[p.order_id] = posisi

    context = {
        'ringkasan_kuantitas': ringkasan_kuantitas,
        'antrean_list': antrean_list,
        'posisi_saya': posisi_saya,
        'filter_kategori': filter_kategori,
        'kategori_choices': Product.objects.values_list('kategori', flat=True).distinct()
    }
    return render(request, 'store/web/info_antrian.html', context)


@login_required(login_url='/login/')
def order_doc(request):
    produk_doc = Product.objects.all() 
    ekspedisi = Ekspedisi.objects.filter(is_active=True).order_by('biaya')
    
    context = {
        'produk': produk_doc,
        'ekspedisi': ekspedisi,
    }

    return render(request, 'store/web/order_kategori.html', context)


# ==========================================
# 5. API / WEBHOOK LOGIC
# ==========================================
def send_otp_wa(request):
    """ Endpoint API untuk mengirimkan OTP via WhatsApp menggunakan Fonnte """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            hpInput = data.get('hp', '').strip()
            
            if not hpInput:
                return JsonResponse({'status': 'error', 'message': 'Nomor WhatsApp tidak boleh kosong.'}, status=400)

            otp_code = str(random.randint(100000, 999999))
            request.session['register_otp'] = otp_code
            request.session['register_hp'] = hpInput
            
            token_fonnte = os.getenv("TOKEN_FONNTE")
            if not token_fonnte:
                return JsonResponse({'status': 'error', 'message': 'Sistem gagal: Token Fonnte tidak ditemukan di env.'}, status=500)

            headers = {
                'Authorization': token_fonnte
            }
            
            pesan_wa = (
                f"*Kelompok Tani Melati*\n\n"
                f"Kode OTP Pendaftaran Anda adalah: *{otp_code}*\n\n"
                f"JANGAN berikan kode ini kepada siapapun demi keamanan akun Anda."
            )
            
            payload = {
                'target': hpInput,
                'message': pesan_wa,
                'countryCode': '62', 
            }

            response = requests.post('https://api.fonnte.com/send', headers=headers, data=payload)
            res_json = response.json()

            if res_json.get('status') == True:
                return JsonResponse({
                    'status': 'success', 
                    'message': f'Kode OTP telah dikirim ke WhatsApp Anda.'
                })
            else:
                pesan_error = res_json.get("reason", "Kegagalan pada server WhatsApp")
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Gagal mengirim OTP: {pesan_error}'
                }, status=400)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Terjadi kesalahan internal: {str(e)}'}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Metode request tidak diizinkan.'}, status=405)

@login_required(login_url='/login/')
def konfirmasi_pembayaran(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if request.method == 'POST':
        order.bank_pengirim = request.POST.get('bank')
        order.nama_rekening_pengirim = request.POST.get('nama_pemilik')
        order.no_rekening_pengirim = request.POST.get('no_rekening')
        
        # Bersihkan nominal
        nominal_mentah = request.POST.get('nominal', '0')
        nominal_bersih = nominal_mentah.strip().replace('.', '').replace(',', '')
        if nominal_bersih.isdigit():
            order.nominal_dibayar = int(nominal_bersih)
        else:
            order.nominal_dibayar = 0 

        # ====================================================
        # PROSES KONVERSI GAMBAR KE WEBP (SINKRON)
        # ====================================================
        bukti_file = request.FILES.get('bukti_transfer')
        if bukti_file:
            try:
                # 1. Buka gambar menggunakan Pillow
                img = Image.open(bukti_file)
                
                # 2. Konversi format warna jika perlu (buang alpha channel transparan jika ada)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                    
                # 3. Siapkan wadah memori untuk gambar baru
                output = io.BytesIO()
                
                # 4. Simpan ke wadah memori dengan format WebP, kualitas 80% (sangat hemat size)
                img.save(output, format='WEBP', quality=80)
                output.seek(0)
                
                # 5. Ubah ekstensi nama file aslinya menjadi .webp
                nama_file_baru = bukti_file.name.rsplit('.', 1)[0] + '.webp'
                
                # 6. Bungkus kembali menjadi format file Django
                webp_file = InMemoryUploadedFile(
                    output, 'ImageField', nama_file_baru, 'image/webp',
                    sys.getsizeof(output), None
                )
                
                # 7. Simpan ke database
                order.bukti_transfer = webp_file
                
            except Exception as e:
                messages.error(request, "File gambar tidak valid atau rusak. Silakan coba gambar lain.")
                return redirect('store:public_invoice', order_id=order.order_id)
        # ====================================================

        order.waktu_bayar = timezone.now()
        order.status = OrderStatus.KONFIRMASI_DP
        order.save()
        
        messages.success(request, "Konfirmasi pembayaran berhasil dikirim. Menunggu verifikasi admin.")
        return redirect('store:public_invoice', order_id=order.order_id)

    return redirect('store:public_invoice', order_id=order.order_id)

@login_required(login_url='/login/')
def daftar_pesanan_saya(request):
    """ Halaman 'Pesanan Saya Sendiri' - Menampilkan tabel riwayat pesanan user """
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'store/web/pesanan_saya.html', {'orders': orders})

def info_antrian_publik(request):
    """ Halaman 'Informasi Antrian' - Menampilkan total kuantitas per produk """
    # Menghitung total item yang sedang dalam antrean (Sudah DP / Valid)
    valid_statuses = [OrderStatus.MENUNGGU_DP, OrderStatus.KONFIRMASI_DP, OrderStatus.ANTRIAN, OrderStatus.PERSIAPAN]
    
    rekap_antrian = OrderItem.objects.filter(
        order__status__in=valid_statuses
    ).values(
        'product__nama', 'product__kategori'
    ).annotate(
        total_qty=Sum('kuantitas')
    ).order_by('product__nama')

    context = {
        'rekap_antrian': rekap_antrian
    }
    return render(request, 'store/web/info_antrian_publik.html', context)

@login_required(login_url='/login/')
def customer_dashboard(request):
    if request.user.is_staff:
        return redirect('store:overview') 
        
    if not request.user.nama_lengkap:
        return redirect('store:lengkapi_profil')
    
    # Ambil SEMUA produk dari database untuk di-looping di template
    produk_list = Product.objects.all().order_by('kategori', 'nama')
    
    context = {
        'toko': StoreSetting.load(),
        'produk_list': produk_list,
    }
    return render(request, 'store/web/customer_dashboard.html', context)