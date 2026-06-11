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

    # RUTE UNTUK FAKTUR DAN PELACAKAN
    path('track/', views.track_order, name='track_order'),
    path('invoice/<str:order_id>/', views.public_invoice, name='public_invoice'),
    
    # AREA ADMIN KUSTOM

    # RUTE OTENTIKASI (diletakkan sebelum rute dashboard)
    path('admin/login/', auth_views.LoginView.as_view(
        template_name='admin/login.html',
        redirect_authenticated_user=True # Mencegah user yang sudah login melihat form ini lagi
    ), name='login'),
    
    path('admin/logout/', auth_views.LogoutView.as_view(
        next_page='/admin/login/' # Setelah logout, kembalikan ke halaman login
    ), name='logout'),

    path('admin/', RedirectView.as_view(url='/admin/overview/', permanent=False), name='admin_index'),
    path('admin/overview/', views.overview_dashboard, name='overview'),
    path('admin/inventory/', views.inventory_list, name='inventory'),
    path('admin/orders/', views.order_management, name='orders'),
    
    # Rute Aksi Pesanan
    path('admin/orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('admin/orders/<int:order_id>/invoice/', views.order_invoice, name='order_invoice'),

    path('admin/inventory/', views.inventory_list, name='inventory'),
    path('admin/inventory/add/', views.add_product, name='add_product'),
    path('admin/inventory/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('admin/inventory/delete/<int:product_id>/', views.delete_product, name='delete_product'),
]