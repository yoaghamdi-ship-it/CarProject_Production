from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # 1. الصفحة الرئيسية وتفاصيل السيارة
    path('', views.index, name='index'),
    path('car/<int:car_id>/', views.car_detail, name='car_detail'),
    
    # 2. الحجز والدفع والإضافة
    path('car/book/<int:car_id>/', views.book_car, name='book_car'),
    path('payment-success/<int:booking_id>/', views.payment_success, name='payment_success'),
    path('add/', views.add_car, name='add_car'),
    
    # 🌟 الرابط الذكي والمحمي للمفضلة لإنهاء مشكلة النيسان باترول فوراً
    path('wishlist/toggle/<int:car_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('car/<int:car_id>/comment/', views.add_comment, name='add_comment'),
]