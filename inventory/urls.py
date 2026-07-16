from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'inventory'

urlpatterns = [
    # 1. الصفحة الرئيسية وتفاصيل السيارة
    path('', views.index, name='index'),
    path('cars/', views.index, name='car_list'),
    path('car/<int:car_id>/', views.car_detail, name='car_detail'),
    
    # 2. الحجز والدفع والإضافة
    path('car/book/<int:car_id>/', views.book_car, name='book_car'),
    path('payment-success/<int:booking_id>/', views.payment_success, name='payment_success'),
    path('add/', views.add_car, name='add_car'),
    
    # 3. المفضلة والتعليقات والرسائل
    path('wishlist/toggle/<int:car_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('car/<int:car_id>/comment', views.add_comment, name='add_comment_no_slash'),
    path('car/<int:car_id>/comment/', views.add_comment, name='add_comment'),
    
    # 🌟 تم ضبط الاسم إلى 'comments' وإضافة مسار 'messages'
    path('comments/', views.AllCommentsView.as_view(), name='comments'),
    path('messages/', views.messages_view, name='messages'),
    
    path('my-cars/', views.my_cars, name='my_cars'),

    # 4. الحسابات وتسجيل الدخول
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.admin_logout_view, name='logout'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('checkout/<int:booking_id>/', views.checkout, name='checkout'),

    # 5. استعادة كلمة المرور
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # 6. لوحة المتابعة والردود الخاصة بالـ Staff
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('comment/<int:comment_id>/reply/', views.reply_comment, name='reply_comment'),
    path('message/<int:message_id>/reply/', views.reply_message, name='reply_message'),
]