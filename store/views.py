import os
import json
import uuid
import requests
from django.http import JsonResponse, HttpResponse
from django.conf import settings

from django.shortcuts import render, redirect
from django.db.models import Sum
from django.contrib.auth.decorators import user_passes_test
from .models import Product, Order, OrderItem
from .models import Product, Order, OrderStatus
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError, transaction

from django.db.models import Q

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

from django.core.paginator import Paginator

# Fungsi lambda ini akan memeriksa: "Apakah user ini adalah superuser?"
# Jika True, View dijalankan. Jika False, user ditendang ke halaman login.
admin_only = user_passes_test(lambda u: u.is_superuser, login_url='/admin/login/')

@admin_only
def inventory_list(request):
    products = Product.objects.all().order_by('-created_at')
    
    # Ambil semua kategori unik untuk dropdown filter
    categories = Product.objects.values_list('kategori', flat=True).distinct()
    
    # Tangkap parameter dari URL
    q = request.GET.get('q', '')
    kategori = request.GET.get('kategori', 'ALL')
    stok = request.GET.get('stok', 'ALL')
    
    # Filter Pencarian Teks (Nama atau SKU)
    if q:
        products = products.filter(
            Q(nama__icontains=q) | 
            Q(kode_unik__icontains=q)
        )
        
    # Filter Kategori
    if kategori != 'ALL':
        products = products.filter(kategori=kategori)
        
    # Filter Stok
    if stok == 'SAFE':
        products = products.filter(stok__gte=10)
    elif stok == 'LOW':
        products = products.filter(stok__lt=10)
        
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Ambil parameter URL saat ini (kecuali 'page') agar filter tidak hilang saat pindah halaman
    query = request.GET.copy()
    if 'page' in query:
        del query['page']

    context = {
        'products': page_obj,
        'query_string': query.urlencode(), # Kirim sisa parameter ke template
        'category_choices': categories,
        'current_q': q,
        'current_kategori': kategori,
        'current_stok': stok,
    }
    return render(request, 'store/admin/inventory.html', context)

@admin_only
def overview_dashboard(request):
    """
    Logika bisnis untuk halaman utama (Overview/Dashboard).
    Fokus pada efisiensi ORM Query.
    """
    
    # Agregasi Total Penjualan (Setara SQL: SELECT SUM(total_amount) FROM store_order)
    # aggregate() mengembalikan dictionary, misal: {'total_amount__sum': 4250.00}
    sales_aggregation = Order.objects.filter(status=OrderStatus.SELESAI).aggregate(total_sales=Sum('total_harga'))
    # Jika database kosong, Sum mengembalikan None, jadi kita set default ke 0
    total_sales = sales_aggregation['total_sales'] or 0

    # Agregasi Total Pesanan (Setara SQL: SELECT COUNT(*) FROM store_order)
    total_orders = Order.objects.count()

    # Menghitung produk yang stoknya menipis (misal di bawah 10 unit)
    # Filter dieksekusi di level database, bukan di Python.
    low_stock_count = Product.objects.filter(stok__lt=10).count()

    # Mengambil 4 pesanan terbaru
    # Penggunaan slice [:4] pada ORM setara dengan klausa "LIMIT 4" di SQL.
    # Ini memastikan kita tidak memuat ribuan data pesanan ke dalam memori.
    recent_orders = Order.objects.order_by('-order_date')[:4]

    # KOMPUTASI TOP PRODUCTS
    # Kita ambil semua Product.
    # .annotate(total_sold=Sum('order_items__quantity')) -> Untuk setiap produk, jumlahkan field 'quantity' dari relasi 'order_items'.
    # .exclude(total_sold=None) -> Abaikan produk yang belum pernah terjual (total_sold bernilai Null).
    # .order_by('-total_sold') -> Urutkan dari jumlah penjualan terbanyak (tanda minus = descending).
    # [:4] -> Ambil 4 teratas (LIMIT 4).
    
    top_products = Product.objects.annotate(
        total_sold=Sum('order_items__kuantitas')
    ).exclude(
        total_sold=None
    ).order_by('-total_sold')[:4]

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'low_stock_count': low_stock_count,
        'recent_orders': recent_orders,
        'top_products': top_products
    }

    return render(request, 'store/admin/overview.html', context)

@admin_only
def order_management(request):
    orders = Order.objects.all().order_by('-order_date')

    status_filter = request.GET.get('status', 'ALL')
    date_filter = request.GET.get('date', '')
    q = request.GET.get('q', '')

    # Filter Pencarian Teks (ID Pesanan atau Nama Pembeli)
    if q:
        orders = orders.filter(
            Q(order_id__icontains=q) | 
            Q(nama_pembeli__icontains=q)
        )

    # Filter Status
    if status_filter != 'ALL':
        valid_statuses = [choice[0] for choice in OrderStatus.choices]
        if status_filter in valid_statuses:
            orders = orders.filter(status=status_filter)
            
    # Filter Tanggal
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
    """
    Ekspor data pesanan ke file Excel (.xlsx) dengan styling profesional,
    Dropdown Data Validation, dan Rumus SUMIF Dinamis untuk Pendapatan.
    """
    # 1. Inisialisasi Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Laporan Pesanan"
    
    # Pastikan garis kisi (gridlines) bawaan Excel tetap terlihat
    ws.views.sheetView[0].showGridLines = True
    
    # 2. Definisikan Palet Warna & Font (Tema Hijau DOC Mart)
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
    
    # 3. Desain Header Judul Dokumen
    ws['A1'] = "LAPORAN MANAJEMEN PESANAN - DOC MART"
    ws['A1'].font = FONT_TITLE
    
    # 4. MEMBUAT KARTU RINGKASAN REVENUE (DENGAN RUMUS EXCEL DIGITAL)
    ws.merge_cells('A3:C3')
    ws.merge_cells('A4:C4')
    ws['A3'] = "TOTAL PENDAPATAN REALISASI (STATUS: SELESAI)"
    ws['A3'].font = FONT_CARD_LABEL
    ws['A3'].fill = CARD_FILL
    ws['A3'].alignment = Alignment(horizontal="center", vertical="center")
    
    # Rumus SUMIF: Cari kata "Selesai" di Kolom I (Status), lalu jumlahkan nilai di Kolom J (Total Harga)
    # Batas pencarian diatur dinamis hingga 500 baris pertama data pesanan
    ws['A4'] = '=SUMIF(I6:I500, "Selesai", J6:J500)'
    ws['A4'].font = FONT_CARD_VALUE
    ws['A4'].fill = CARD_FILL
    ws['A4'].number_format = '"Rp"#,##0' # Format Rupiah Akuntansi
    ws['A4'].alignment = Alignment(horizontal="center", vertical="center")
    
    # Beri bingkai border tipis pada kartu ringkasan pendapatan
    for r in range(3, 5):
        for c in range(1, 4):
            ws.cell(row=r, column=c).border = THIN_BORDER

    # 5. Susun Header Tabel Utama (Baris ke-5)
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
        
    # 6. Ambil Data dari Database Django
    orders = Order.objects.all().order_by('-order_date')
    start_data_row = 6
    
    # KONFIGURASI DROPDOWN DATA VALIDATION UNTUK EXCEL
    status_dv = DataValidation(type="list", formula1='"Proses,Selesai,Batal"', allow_blank=True)
    ws.add_data_validation(status_dv)
    
    status_map = {
        'PRO': 'Proses',
        'SLS': 'Selesai',
        'BTL': 'Batal'
    }
    
    for idx, order in enumerate(orders, 1):
        current_row = start_data_row + idx - 1
        
        # Format translasi data agar mudah dipahami di Excel
        status_label = status_map.get(order.status, 'Proses')
        metode_png = order.get_metode_pengiriman_display()
        metode_pemb = order.get_metode_pembayaran_display()
        tanggal_str = order.order_date.strftime('%d-%m-%Y %H:%M') if order.order_date else ''
        
        row_data = [
            idx,
            order.order_id,
            order.nama_pembeli,
            order.nomor_hp,
            metode_png,
            order.alamat or '-',
            float(order.jarak_km) if order.jarak_km else 0,
            metode_pemb,
            status_label, # Ini akan masuk ke kolom I (Status)
            float(order.total_harga), # Ini akan masuk ke kolom J (Total Harga)
            tanggal_str
        ]
        
        for col_num, val in enumerate(row_data, 1):
            cell = ws.cell(row=current_row, column=col_num)
            cell.value = val
            cell.font = FONT_BODY
            cell.border = THIN_BORDER
            
            # Pengaturan Penyelarasan Posisi (Alignment)
            if col_num in [1, 2, 4, 7, 8, 9, 11]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
            # Pemformatan Angka Spesifik
            if col_num == 7: # Jarak KM
                cell.number_format = '0.00'
            elif col_num == 10: # Format Mata Uang Rupiah di Kolom J
                cell.number_format = '"Rp"#,##0'
                
            # Efek Estetika Zebra Striping (Baris Genap Diberi Warna Berbeda)
            if idx % 2 == 0:
                cell.fill = ZEBRA_FILL
        
        # IKAT DROPDOWN KE KOLOM STATUS (Kolom 9 / Huruf I)
        status_dv.add(ws.cell(row=current_row, column=9))
        
    # 7. Auto-fit Ukuran Lebar Kolom Secara Proporsional
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.row < 5: # Abaikan baris judul dan kartu atas dari kalkulasi lebar
                continue
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 5, 12)
        
    # Set Tinggi Baris Spesifik agar Tampak Proporsional
    ws.row_dimensions[5].height = 26 # Tinggi baris header tabel
    
    # 8. Set Judul File dan Return File Binary Excel ke Browser Admin
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=Laporan_Penjualan_DOC_Mart.xlsx"
    wb.save(response)
    return response

@admin_only
def add_product(request):
    existing_categories = Product.objects.values_list('kategori', flat=True).distinct()
    
    if request.method == 'POST':
        nama = request.POST.get('nama')
        kode_unik = request.POST.get('kode_unik')
        kategori_pilihan = request.POST.get('kategori')
        kategori_baru = request.POST.get('kategori_baru')
        harga = request.POST.get('harga')
        stok = request.POST.get('stok')
        
        # TANGKAP GAMBAR DARI REQUEST FILES
        gambar_upload = request.FILES.get('gambar')
        
        kategori_final = kategori_baru.strip() if kategori_pilihan == 'BARU' and kategori_baru else kategori_pilihan
        
        try:
            Product.objects.create(
                nama=nama.strip(),
                kode_unik=kode_unik.strip().upper(),
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
        product.nama = request.POST.get('nama').strip()
        product.kode_unik = request.POST.get('kode_unik').strip().upper()
        
        kategori_pilihan = request.POST.get('kategori')
        kategori_baru = request.POST.get('kategori_baru')
        product.kategori = kategori_baru.strip() if kategori_pilihan == 'BARU' and kategori_baru else kategori_pilihan
        
        product.harga = request.POST.get('harga')
        product.stok = request.POST.get('stok')
        
        if 'gambar' in request.FILES:
            product.gambar = request.FILES.get('gambar')
        
        try:
            product.save()
            messages.success(request, f"Produk '{product.nama}' berhasil diperbarui!")
            return redirect('store:inventory')
        except IntegrityError:
            messages.error(request, "Gagal! Kode Unik bertabrakan dengan produk lain.")
            
    return render(request, 'store/admin/edit_product.html', {'product': product, 'categories': existing_categories})

@admin_only
def delete_product(request, product_id):
    # PENGAMANAN: Penghapusan hanya boleh dilakukan via metode POST
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
        
        # Validasi keamanan: Pastikan status yang dikirim valid
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
    # Mengambil order sekaligus relasi item-itemnya untuk efisiensi kueri
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    
    context = {
        'order': order,
    }
    # Halaman ini tidak menggunakan base.html admin agar layoutnya bersih (khusus cetak kertas)
    return render(request, 'store/admin/invoice.html', context)


def index(request):
    """
    Menampilkan halaman utama website untuk pelanggan.
    Kita bisa mengambil beberapa produk unggulan (Top Products) untuk ditampilkan.
    """
    featured_products = Product.objects.all()
    return render(request, 'store/web/index.html', {'featured_products': featured_products})

def product_list(request):
    # Ambil semua produk secara default
    products = Product.objects.all()
    
    # Ambil daftar kategori yang unik (distinct) untuk ditampilkan di sidebar
    # Ini mencegah munculnya kategori ganda di checkbox
    categories = Product.objects.values_list('kategori', flat=True).distinct()
    
    # Tangkap kategori yang dicentang oleh user (bisa lebih dari satu)
    selected_cats = request.GET.getlist('cat')
    
    # Jika ada kategori yang dipilih, filter produknya
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
    """
    Hanya merender kerangka halaman. 
    Isi keranjang akan dirender oleh JavaScript menggunakan data LocalStorage.
    """
    return render(request, 'store/web/cart.html')

def checkout_process(request):
    if request.method == 'GET':
        return render(request, 'store/web/checkout.html')
        
    if request.method == 'POST':
        try:
            nama = request.POST.get('nama')
            hp = request.POST.get('hp')
            pengiriman = request.POST.get('pengiriman')
            pembayaran = request.POST.get('pembayaran')
            alamat = request.POST.get('alamat', '')
            lat = request.POST.get('lat', '')
            lng = request.POST.get('lng', '')
            
            # FITUR BARU: Tangkap jarak (konversi ke float jika ada)
            jarak_raw = request.POST.get('jarak_km', '')
            jarak_km = float(jarak_raw) if jarak_raw else None
            
            bukti_tf = request.FILES.get('bukti_pembayaran')
            cart_data = json.loads(request.POST.get('cart_data', '[]'))
            
            if not cart_data:
                messages.error(request, "Keranjang Anda kosong.")
                return redirect('store:market')

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
                    total_harga=0, # Akan di-update di bawah
                    items_summary="Menunggu..."
                )

                for item in cart_data:
                    product_id = item.get('id')
                    kuantitas = int(item.get('qty', 0))
                    
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

                # FITUR BARU: KALKULASI ONGKIR (Rp 5.000 / km)
                ongkos_kirim = 0
                if pengiriman == 'ANT' and jarak_km:
                    ongkos_kirim = int(jarak_km * 5000)
                    rincian_item.append(f"Ongkir ({jarak_km} km)")

                # Gabungkan subtotal barang + ongkos kirim
                order.total_harga = total_kalkulasi_sistem + ongkos_kirim
                order.items_summary = ", ".join(rincian_item)[:250]
                order.save()

            # INTEGRASI WHATSAPP FONNTE
            fonnte_token = settings.FONNTE_TOKEN
            nomor_admin = '0895704050703' 
            
            # Buat URL Faktur yang bisa di-klik
            domain = request.get_host()
            link_faktur = f"http://{domain}/invoice/{order.order_id}/"
            
            maps_url = f"https://www.google.com/maps?q={lat},{lng}" if pengiriman == 'ANT' else "Diambil sendiri."

            pesan_admin = (
                f"*PESANAN BARU MASUK!*\n\n"
                f"Order ID: {order.order_id}\n"
                f"Pembeli: {order.nama_pembeli}\n"
                f"No HP: {order.nomor_hp}\n"
                f"Total Akhir: Rp{order.total_harga:,.0f}\n\n"
                f"🔗 *Buka Faktur Lengkap:*\n{link_faktur}\n\n"
                f"Lokasi Peta: {maps_url}"
            )

            pesan_pelanggan = (
                f"Halo *{order.nama_pembeli}*,\n\n"
                f"Terima kasih telah berbelanja di *DOC Mart*! 🐣\n"
                f"Pesanan Anda dengan ID *{order.order_id}* telah kami terima dan sedang kami proses.\n\n"
                f"Total Tagihan: *Rp{order.total_harga:,.0f}*\n\n"
                f"📄 *CEK STATUS & FAKTUR PESANAN ANDA DI SINI:*\n"
                f"{link_faktur}\n\n"
            )

            pesan_pelanggan += "Jika Anda merasa tidak memesan, tolong chat nomor ini untuk konfirmasi. Terima kasih! 🙏"

            # Eksekusi Pengiriman Pesan
            try:
                # Tembak API ke nomor Admin
                requests.post(
                    "https://api.fonnte.com/send", 
                    headers={"Authorization": fonnte_token}, 
                    data={"target": nomor_admin, "message": pesan_admin}
                )
                
                # Tembak API ke nomor Pelanggan (menggunakan variabel 'hp' dari input form)
                requests.post(
                    "https://api.fonnte.com/send", 
                    headers={"Authorization": fonnte_token}, 
                    data={"target": hp, "message": pesan_pelanggan}
                )
            except Exception as e:
                # Menangkap error agar jika Fonnte sedang gangguan, 
                # transaksi checkout pelanggan di website tetap berhasil
                print(f"Peringatan: Gagal mengirim WhatsApp. {str(e)}")

            return render(request, 'store/web/order_success.html', {'order_id': order.order_id})
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('store:checkout')
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan: {str(e)}")
            return redirect('store:checkout')
        
def track_order(request):
    """ Halaman Cek Pesanan """
    if request.method == 'POST':
        order_id = request.POST.get('order_id', '').strip()
        hp = request.POST.get('hp', '').strip()
        
        try:
            # Wajib cocok antara ID Pesanan dan Nomor HP
            order = Order.objects.get(order_id=order_id, nomor_hp=hp)
            # Jika cocok, lemparkan ke halaman faktur publik
            return redirect('store:public_invoice', order_id=order.order_id)
        except Order.DoesNotExist:
            messages.error(request, "Pesanan tidak ditemukan. Periksa kembali ID Pesanan dan Nomor WA Anda.")
            
    return render(request, 'store/web/track_order.html')

def public_invoice(request, order_id):
    """ Halaman Faktur Publik (Read-Only) """
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_id=order_id)
    
    context = {
        'order': order,
        # Variabel penanda bahwa ini dilihat oleh publik, bukan admin
        'is_public': True 
    }
    # Kita menggunakan template admin/invoice.html yang sudah Anda buat sebelumnya agar desainnya konsisten
    return render(request, 'store/admin/invoice.html', context)