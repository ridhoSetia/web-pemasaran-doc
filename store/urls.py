from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from . import views

app_name = 'store'

urlpatterns = [
    # AREA PUBLIK (STOREFRONT)
    path('', views.index, name='index'), 
    path('market/', views.product_list, name='market'),
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout_process, name='checkout'),
    path('api/send-otp/', views.send_otp_wa, name='send_otp'),

    # RUTE UNTUK FAKTUR DAN PELACAKAN
    path('track/', views.track_order, name='track_order'),
    path('invoice/<str:order_id>/', views.public_invoice, name='public_invoice'),
    
    # AREA ADMIN KUSTOM

    # RUTE OTENTIKASI (diletakkan sebelum rute dashboard)
    path('pengelola/login/', views.CustomAdminLoginView.as_view(), name='login'),
    
    path('pengelola/logout/', auth_views.LogoutView.as_view(
        next_page='/pengelola/login/' # Setelah logout, kembalikan ke halaman login
    ), name='logout'),

    path('pengelola/', RedirectView.as_view(url='/pengelola/overview/', permanent=False), name='admin_index'),
    path('pengelola/overview/', views.overview_dashboard, name='overview'),
    path('pengelola/inventory/', views.inventory_list, name='inventory'),
    path('pengelola/orders/', views.order_management, name='orders'),
    path('pengelola/orders/export/', views.export_orders_excel, name='export_orders_excel'),
    
    # Rute Aksi Pesanan
    path('pengelola/orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('pengelola/orders/<int:order_id>/invoice/', views.order_invoice, name='order_invoice'),

    path('pengelola/inventory/', views.inventory_list, name='inventory'),
    path('pengelola/inventory/add/', views.add_product, name='add_product'),
    path('pengelola/inventory/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('pengelola/inventory/delete/<int:product_id>/', views.delete_product, name='delete_product'),

    path('pengelola/settings/', views.admin_settings, name='admin_settings'),
    path('pengelola/api/pending-orders/', views.api_pending_orders, name='api_pending_orders'),
]