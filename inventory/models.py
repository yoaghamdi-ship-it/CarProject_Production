from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# 1. موديل الوكيل أو المخزن
class Inventory(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم الوكيل")
    location = models.CharField(max_length=200, verbose_name="الموقع / العنوان")
    phone = models.CharField(max_length=20, verbose_name="رقم الهاتف")
    email = models.EmailField(verbose_name="البريد الإلكتروني")
    image = models.ImageField(upload_to='inventory/', null=True, blank=True, verbose_name="صورة الوكالة")

    class Meta:
        verbose_name = "وكيل / مخزن"
        verbose_name_plural = "الوكلاء والمخازن"

    def __str__(self):
        return self.name

# 2. موديل التعليقات
class Comment(models.Model):
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='comments', verbose_name="الوكيل")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="المستخدم")
    text = models.TextField(verbose_name="التعليق")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التعليق")
    
    # 🌟 الحقول الجديدة للرد
    reply = models.TextField(blank=True, null=True, verbose_name="رد الإدارة")
    replied_at = models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الرد")

    class Meta:
        verbose_name = "تعليق"
        verbose_name_plural = "التعليقات"

    def __str__(self):
        return f"تعليق من {self.user.username} على {self.inventory.name}"

# 3. موديل المفضلة
class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="المستخدم")
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, verbose_name="الوكيل المفضّل")

    class Meta:
        verbose_name = "مفضلة"
        verbose_name_plural = "المفضلات"
        unique_together = ('user', 'inventory')

# 4. موديل الرسائل
class Message(models.Model):
    name = models.CharField(max_length=100, verbose_name="الاسم")
    email = models.EmailField(verbose_name="البريد الإلكتروني")
    subject = models.CharField(max_length=200, verbose_name="الموضوع")
    message = models.TextField(verbose_name="نص الرسالة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإرسال")
    
    # 🌟 الحقول الجديدة للرد
    reply = models.TextField(blank=True, null=True, verbose_name="رد الإدارة")
    replied_at = models.DateTimeField(blank=True, null=True, verbose_name="تاريخ الرد")

    class Meta:
        verbose_name = "رسالة"
        verbose_name_plural = "الرسائل"

    def __str__(self):
        return f"{self.subject} - من: {self.name}"

# 5. تعريف السيارة (يجب أن يكون قبل Booking)
class Car(models.Model):
    STATUS_CHOICES = [
        ('available', 'متاحة للبيع'),
        ('reserved', 'محجوزة مؤقتاً'),
        ('sold', 'مباعة بالكامل'),
    ]

    # 🌟 الحقل الجديد: ربط السيارة بالمعرض / الوكيل (صاحب السيارة)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='cars',
        null=True, 
        blank=True,
        verbose_name="صاحب السيارة / المعرض"
    )

    # الربط مع الوكيل
    inventory = models.ForeignKey(
        Inventory, 
        on_delete=models.CASCADE, 
        related_name="inventory_cars", 
        verbose_name="الوكيل المسؤول"
    )

    # --- المعلومات الأساسية ---
    brand = models.CharField(max_length=50, verbose_name="الماركة")
    model_name = models.CharField(max_length=100, verbose_name="طراز السيارة")
    year = models.PositiveIntegerField(verbose_name="سنة الصنع")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="السعر")
    condition = models.CharField(
        max_length=20, 
        choices=[('New', 'جديد'), ('Used', 'مستعمل')], 
        verbose_name="حالة السيارة"
    )

    # --- الأداء والمحرك ---
    engine_type = models.CharField(max_length=50, verbose_name="نوع المحرك", null=True, blank=True)
    engine_capacity = models.CharField(max_length=20, verbose_name="سعة المحرك", null=True, blank=True)
    horsepower = models.PositiveIntegerField(verbose_name="القوة الحصانية", null=True, blank=True)
    transmission = models.CharField(
        max_length=50, 
        choices=[('Auto', 'أوتوماتيك'), ('Manual', 'يدوي')], 
        verbose_name="ناقل الحركة", null=True, blank=True
    )
    drive_train = models.CharField(max_length=50, verbose_name="نظام الدفع", null=True, blank=True)
    fuel_type = models.CharField(max_length=50, verbose_name="نوع الوقود", null=True, blank=True)
    mileage = models.PositiveIntegerField(verbose_name="الممشى (كيلومتر)", null=True, blank=True)

    # --- المواصفات الخارجية ---
    exterior_color = models.CharField(max_length=50, verbose_name="اللون الخارجي", null=True, blank=True)
    body_style = models.CharField(max_length=50, verbose_name="نوع الهيكل", null=True, blank=True)
    rims_size = models.PositiveIntegerField(verbose_name="مقاس الجنوط", null=True, blank=True)
    sunroof = models.CharField(
        max_length=50, 
        choices=[('None', 'بدون'), ('Standard', 'فتحة سقف'), ('Panoramic', 'بانوراما')], 
        verbose_name="فتحة السقف", null=True, blank=True
    )
    lighting = models.CharField(max_length=50, verbose_name="نوع الإضاءة", null=True, blank=True)
    sensors = models.CharField(max_length=100, verbose_name="الحساسات الخارجية", null=True, blank=True)
    trunk_system = models.CharField(max_length=50, verbose_name="نظام الشنطة", null=True, blank=True)

    # --- المواصفات الداخلية ---
    interior_color = models.CharField(max_length=50, verbose_name="اللون الداخلي", null=True, blank=True)
    seat_material = models.CharField(max_length=50, verbose_name="نوع المقاعد", null=True, blank=True)
    seat_features = models.CharField(max_length=100, verbose_name="ميزات المقاعد", null=True, blank=True)
    screen_size = models.FloatField(verbose_name="حجم الشاشة", null=True, blank=True)
    sound_system = models.CharField(max_length=100, verbose_name="النظام الصوتي", null=True, blank=True)
    airbags_count = models.PositiveIntegerField(verbose_name="عدد الوسائد الهوائية", null=True, blank=True)

    # --- التقنيات والوصف ---
    cruise_control = models.CharField(max_length=50, verbose_name="مثبت السرعة", null=True, blank=True)
    cameras = models.CharField(max_length=100, verbose_name="نظام الكاميرات", null=True, blank=True)
    description = models.TextField(verbose_name="وصف إضافي", null=True, blank=True)
    image = models.ImageField(upload_to='cars/', null=True, blank=True, verbose_name="صورة السيارة")
    
    # حقل التحكم الذكي بحالة ظهور السيارة وإخفائها (متاحة، محجوزة، مباعة)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='available', 
        verbose_name="حالة العرض والبيع"
    )
    
    is_available = models.BooleanField(default=True, verbose_name="متاحة للعرض") 
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    class Meta:
        db_table = 'cars_car' 
        verbose_name = "سيارة"
        verbose_name_plural = "السيارات"

    def __str__(self):
        return f"{self.brand} {self.model_name} ({self.year})"

# 6. موديل الحجز (النسخة المطورة والموحدة)
class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'انتظار دفع العربون'),
        ('paid', 'تم دفع العربون'),  
        ('fully_paid', 'تم دفع كامل المبلغ'),
        ('expired', 'منتهي الصلاحية'),
        ('canceled', 'ملغي'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="المستخدم")
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="bookings", verbose_name="السيارة")
    reserved_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الحجز")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="حالة الدفع")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="المبلغ المدفوع")
    transaction_id = models.CharField(max_length=100, null=True, blank=True, unique=True, verbose_name="رقم العملية")
    deposit_paid_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ دفع العربون")

    class Meta:
        verbose_name = "حجز"
        verbose_name_plural = "الحجوزات"

    def __str__(self):
        return f"{self.user.username if self.user else 'زائر'} - {self.car.brand} ({self.get_status_display()})"

    def has_expired(self):
        now = timezone.now()
        
        # حالة الـ 24 ساعة قبل دفع العربون
        if self.status == 'pending' and now > self.reserved_at + timedelta(hours=24):
            return True
            
        # حالة الـ 48 ساعة بعد دفع العربون وقبل دفع كامل المبلغ
        if self.status == 'paid' and self.deposit_paid_at:
            if now > self.deposit_paid_at + timedelta(hours=48):
                return True
                
        return False