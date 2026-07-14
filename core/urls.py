from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from inventory import views as inventory_views

urlpatterns = [
    # 1. لوحة تحكم الأدمن والمسؤولين فقط
    path('admin/', admin.site.urls),

    # 2. تضمين كافة روابط تطبيق inventory (يشمل الصفحة الرئيسية، تسجيل الدخول، التسجيل، والحجز)
    path('', include('inventory.urls')),

    # 3. روابط مستقلة إضافية (إن وجدت)
    path('messages/', inventory_views.messages_view, name='messages'),
    path('payment/callback/', inventory_views.payment_callback, name='payment_callback'),
]

# 4. دعم رفع ملفات الصور والملفات الثابتة
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)