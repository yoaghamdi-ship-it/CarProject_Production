from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from inventory import views as inventory_views
from . import views

urlpatterns = [
    # 1. لوحة التحكم الإدارية
    path('admin/', admin.site.urls),
    
    # 2. الصفحة الرئيسية المباشرة للموقع
    path('', inventory_views.index, name='index'), 
    
    # 🌟 التضمين السليم والوحيد لتطبيق الـ inventory (يمنع أي تضارب أو أخطاء)
    path('', include('inventory.urls')),
    path('messages/', inventory_views.messages_view, name='messages'),
    #path('comments/', include('comments.urls')),
    
    # 3. روابط الحماية الجاهزة وتسجيل الدخول/الخروج والتسجيل
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', inventory_views.register, name='register'),

    # 4. روابط نظام "نسيت كلمة السر" العامة
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
]

# 5. دعم ملفات الصور (Media) والثابتة
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)