from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # حذفنا سطر الـ admin من هنا لأنه موجود في الملف الرئيسي
    path('', include('inventory.urls')),  # استدعاء تطبيق المعرض
    path('accounts/', include('django.contrib.auth.urls')), # روابط الحسابات
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)