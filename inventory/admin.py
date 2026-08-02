from django.contrib import admin
from .models import Car, Inventory, Comment, Favorite, Message, Booking

# دالة مساعدة لمنع تكرار التسجيل (تجنب خطأ AlreadyRegistered)
def safe_register(model, admin_class=None):
    try:
        if admin.site.is_registered(model):
            admin.site.unregister(model)
        if admin_class:
            admin.site.register(model, admin_class)
        else:
            admin.site.register(model)
    except Exception:
        pass

# 1. تخصيص عرض السيارات في لوحة التحكم
class CarAdmin(admin.ModelAdmin):
    # الحقول التي تظهر في القائمة الرئيسية
    list_display = ('brand', 'model_name', 'year', 'price', 'is_available')
    
    # إضافة فلاتر في الجانب
    list_filter = ('brand', 'year', 'is_available')
    
    # إضافة خاصية البحث
    search_fields = ('brand', 'model_name', 'dealer_name')
    
    # جعل حقل "متاح" قابل للتعديل مباشرة من القائمة دون دخول الصفحة
    list_editable = ('is_available',)

# 2. تخصيص عرض الحجوزات
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'car', 'status', 'amount_paid', 'reserved_at')
    list_filter = ('status', 'reserved_at')

# 3. تسجيل الموديلات في لوحة التحكم بشكل آمن
safe_register(Car, CarAdmin)
safe_register(Booking, BookingAdmin)
safe_register(Inventory)
safe_register(Comment)
safe_register(Favorite)
safe_register(Message)