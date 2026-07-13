from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('send-otp-wa/', views.send_otp_wa, name='send_otp_wa'),
    path('logout/', views.logout_view, name='logout'),
    path('lengkapi-profil/', views.lengkapi_profil, name='lengkapi_profil'),
    path('antrian/', views.info_antrian, name='info_antrian'),
    path('order/doc/', views.order_doc, name='order_doc'),
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('profil/', views.profil_view, name='profil'),

    path('proses-po/', views.proses_po, name='proses_po'),
    path('invoice/<str:order_id>/konfirmasi/', views.konfirmasi_pembayaran, name='konfirmasi_pembayaran'),
    path('invoice/<str:order_id>/', views.public_invoice, name='public_invoice'),
    path('pesanan-saya/', views.daftar_pesanan_saya, name='pesanan_saya'),
    path('info-antrian/', views.info_antrian_publik, name='info_antrian'),

    path('pengelola/', views.overview_dashboard, name='overview'),
    path('pengelola/orders/', views.order_management, name='orders'),
    path('pengelola/orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('pengelola/orders/<int:order_id>/invoice/', views.order_invoice, name='order_invoice'),
    path('pengelola/orders/export/', views.export_orders_excel, name='export_orders_excel'),
    path('pengelola/inventory/', views.inventory_list, name='inventory'),
    path('pengelola/inventory/add/', views.add_product, name='add_product'),
    path('pengelola/inventory/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('pengelola/inventory/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('pengelola/settings/', views.admin_settings, name='settings'), # <-- Ubah nama menjadi 'settings'
    path('api/pengelola/pending-orders/', views.api_pending_orders, name='api_pending_orders'),
]