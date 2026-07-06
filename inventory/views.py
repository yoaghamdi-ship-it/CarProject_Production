from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages as django_messages 
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.db.models import Min, Q, IntegerField
from django.apps import apps 
from django.db.models.functions import Cast
from django.views.generic import ListView
import re
import json

# --- استيراد الموديلات ---
from .models import Inventory, Comment, Favorite, Message, Booking, Car
from .forms import CarForm

# --- إعدادات ميسر ---
MOYASAR_SECRET_KEY = "sk_test_4qRHE1RTQwrEh3gh9H7cxb4LkbJWDMTJtP6ngp3s"
MOYASAR_PUBLISHABLE_KEY = "pk_test_VP5cwmVp2Z5qRW4Ha97jyB9BKjiZTW7KPadLgvH3"


# 🔥 دالة المراقبة الذكية المساعدة (تُستدعى تلقائياً لتحديث الحالات بالخلفية)
def check_expired_bookings():
    now = timezone.now()
    
    # 1. جلب الحجوزات النشطة
    active_bookings = Booking.objects.filter(status__in=['pending', 'paid'])
    
    for booking in active_bookings:
        expired = False
        
        # حالة الـ 24 ساعة قبل دفع العربون
        if booking.status == 'pending' and now > booking.reserved_at + timedelta(hours=24):
            expired = True
            
        # حالة الـ 48 ساعة بعد دفع العربون وقبل دفع كامل المبلغ
        elif booking.status == 'paid' and booking.deposit_paid_at:
            if now > booking.deposit_paid_at + timedelta(hours=48):
                expired = True
                
        # إذا انتهت المهلة، نفذ الإلغاء فوراً هنا
        if expired:
            booking.status = 'expired'
            booking.save()
            
            # إعادة السيارة لتكون متاحة للبيع والعرض
            car = booking.car
            car.status = 'available'
            car.is_available = True
            car.save()


# 1. الصفحة الرئيسية (مصححة ومؤمنة بالكامل من تداخل معرفات السيارات)
def index(request):
    cars = Car.objects.all()
    
    # فحص الحجوزات لكل السيارات
    for car in cars:
        car.is_already_booked = Booking.objects.filter(car=car).exists()
    
    ticker_cars = [car for car in cars if not car.is_already_booked]

    # 🌟 مزامنة وإجبار الداتابيز على تفعيل الألوان الحمراء في المتصفح فوراً
    if request.user.is_authenticated:
        if 'wishlist_cars' not in request.session or not request.session['wishlist_cars']:
            favorites = Favorite.objects.filter(user=request.user)
            favorite_car_ids = []
            
            for fav in favorites:
                if hasattr(fav, 'car_id') and fav.car_id:
                    favorite_car_ids.append(fav.car_id)
                elif hasattr(fav, 'car') and fav.car:
                    favorite_car_ids.append(fav.car.id)
                else:
                    favorite_car_ids.append(fav.inventory_id)
            
            # تخزين الأرقام الحقيقية المعزولة داخل السيسشن
            request.session['wishlist_cars'] = favorite_car_ids
            
        # 🌟 السطر الحاسم: إجبار دجانغو على تحديث وحفظ الجلسة وإرسالها للـ HTML فوراً
        request.session.modified = True
    else:
        request.session['wishlist_cars'] = []

    context = {
        'cars': cars,
        'ticker_cars': ticker_cars,
    }
    return render(request, 'inventory/index.html', context)


# 2. قائمة السيارات (محدثة لفلترة المعروض للمتاح فقط وإلغاء تلقائي)
def car_list(request):
    check_expired_bookings()
    
    search_query = request.GET.get('search')
    if search_query:
        cars = Car.objects.filter(
            Q(brand__icontains=search_query) | Q(model_name__icontains=search_query),
            status='available'
        )
    else:
        cars = Car.objects.filter(status='available').order_by('-id')

    cheapest_price = cars.aggregate(Min('price'))['price__min']

    context = {
        'cars': cars,
        'cheapest_price': cheapest_price,  
        'user': request.user,              
        'request': request,
    }
    return render(request, 'inventory/car_list.html', context)


# 3. تفاصيل السيارة (محدثة للتحقق من الحجز اللحظي وعرض التعليقات وحالة المفضلة)
def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    
    # حفظ رقم السيارة الحالية في الـ Session لكي تستخدمه دالة الـ callback بعد الدفع
    request.session['pending_car_id'] = car.id
    
    # جلب التعليقات المرتبطة بالـ Inventory التابع لهذه السيارة إن وجد
    inventory_item = Inventory.objects.filter(inventory_cars=car).first()
    comments = inventory_item.comments.all() if inventory_item else []
    
    # فحص ما إذا كانت السيارة محجوزة (بناءً على الحالة المعرفة في موديل Car الخاص بك)
    # افترضنا هنا أن اسم الحالة 'booked'، يمكنك تعديلها لتطابق حقل الـ status عندك
    is_booked = car.status == 'booked'
    
    context = {
        'car': car,
        'comments': comments,
        'is_booked': is_booked
    }
    return render(request, 'inventory/detail.html', context)


@login_required
def add_comment(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    
    if request.method == 'POST':
        # جلب النص من الفورم (المربع في الـ HTML مسمى content)
        comment_content = request.POST.get('content')
        
        if comment_content:
            # جلب الـ Inventory المرتبط بهذه السيارة أولاً
            inventory_item = Inventory.objects.filter(inventory_cars=car).first()
            
            # لن يتم الحفظ إلا إذا وجدنا الـ inventory منعاً لخطأ قاعدة البيانات (حقل مطلوب)
            if inventory_item:
                Comment.objects.create(
                    inventory=inventory_item,
                    user=request.user,
                    text=comment_content # يطابق حقل text في الموديل الخاص بك
                )
            
    return redirect('inventory:car_detail', car_id=car.id)


# 4. إضافة سيارة (محمية للمسؤولين فقط)
@user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser), login_url='car_list')
def add_car(request):
    if request.method == "POST":
        form = CarForm(request.POST, request.FILES)
        if form.is_valid():
            car = form.save()
            django_messages.success(request, f"تم إضافة السيارة {car.brand} بنجاح!")
            return redirect('car_list')
    else:
        form = CarForm()
    return render(request, 'inventory/add_car.html', {'form': form, 'user': request.user})


# 5. معالجة نجاح الدفع
def payment_success(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    context = {
        'booking': booking,
        'car': booking.car, 
    }
    return render(request, 'inventory/payment_success.html', context)


# 6. إجراءات الحجز المبدئي
def book_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    
    if Booking.objects.filter(car=car, status='paid').exists():
        messages.error(request, "عذراً، هذه السيارة محجوزة حالياً من قبل عميل آخر.")
        return redirect('index')

    deposit_amount = 1000 
    
    request.session['pending_car_id'] = car.id
    request.session['deposit_amount'] = deposit_amount

    booking, created = Booking.objects.get_or_create(
        user=request.user,
        car=car,
        status='pending', 
        defaults={
            'amount_paid': deposit_amount,
        }
    )
    
    if not created:
        booking.amount_paid = deposit_amount
        booking.save()

    messages.info(request, f"تم تجهيز طلب حجز سيارة {car.brand}. يرجى سداد عربون التأكيد (1000 ريال).")
    return redirect('payment_success', booking_id=booking.id)


# 7. إضافة تعليق جديد
@login_required
def add_comment(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    
    if request.method == 'POST':
        # جلب النص من الفورم (المربع في الـ HTML مسمى content)
        comment_content = request.POST.get('content')
        
        if comment_content:
            # جلب الـ Inventory المرتبط بهذه السيارة أولاً
            inventory_item = Inventory.objects.filter(inventory_cars=car).first()
            
            # لن يتم الحفظ إلا إذا وجدنا الـ inventory منعاً لخطأ قاعدة البيانات (حقل مطلوب)
            if inventory_item:
                Comment.objects.create(
                    inventory=inventory_item,
                    user=request.user,
                    text=comment_content # يطابق حقل text في الموديل الخاص بك
                )
            
    return redirect('inventory:car_detail', car_id=car.id)

def all_comments(request):
    # جلب جميع التعليقات لعرضها في الصفحة العامة
    comments = Comment.objects.all().order_by('-created_at')
    return render(request, 'inventory/all_comments.html', {'comments': comments})


def payment_callback(request):
    # 1. جلب البيانات القادمة من بوابة ميسر عبر الرابط (GET Request)
    payment_id = request.GET.get('id')
    status = request.GET.get('status')
    message = request.GET.get('message')
    
    # جلب معرف السيارة التي كان العميل يتصفحها قبل الانتقال للدفع من الـ Session
    car_id = request.session.get('pending_car_id')
    
    # 2. التحقق من نجاح عملية الدفع وتحويل حالة السيارة
    if status == 'paid' and car_id:
        car = get_object_or_404(Car, id=car_id)
        
        # تحويل حالة السيارة إلى محجوزة وحفظ التعديل في قاعدة البيانات
        car.status = 'booked' # تأكد من مطابقة الكلمة لحالات حقل status في الموديل (مثل 'booked' أو 'B')
        car.save()
        
        # تنظيف الجلسة ومسح المعرف المؤقت بعد نجاح الحجز
        if 'pending_car_id' in request.session:
            del request.session['pending_car_id']
            
        return render(request, 'inventory/payment_success.html', {'car': car, 'payment_id': payment_id})
    
    # في حال فشل الدفع أو عدم اكتمال البيانات
    return render(request, 'inventory/payment_failed.html', {'message': message})

# 🔗 8. التبديل والتحكم الذكي بالمفضلة (تم التثبيت على المعرف المباشر للسيارة المحددة لمنع التبديل العشوائي)
@login_required(login_url='login')
def toggle_wishlist(request, car_id):
    # 1. جلب السيارة المحددة بدقة (مثلاً كيا K8)
    car = get_object_or_404(Car, id=car_id)
    
    # 2. إعطاء قاعدة البيانات الـ inventory المشترك المقبول لديها لمنع خطأ الـ Foreign Key
    # وفي نفس الوقت نستخدم حقل "البينات الزائدة إن وجد" أو نعتمد على الفلترة بالـ car_id لاحقاً
    favorite_query = Favorite.objects.filter(user=request.user, inventory=car.inventory)
    
    # 🌟 هنا الخدعة: إذا كان المخزن مضافاً، سنفحص هل السيارة المحددة باسم موديلها موجودة؟
    # لمنع التداخل، سنقوم بحفظ و فحص سياق تفعيل الأزرار بناءً على الجلسة (Session) 
    # لكي نعرف بالضبط أي سيارة قام يوسف بالضغط عليها وتلوين زرها بالأحمر بشكل مستقل!
    wishlist_session = request.session.get('wishlist_cars', [])
    
    if car.id in wishlist_session:
        # إذا كانت السيارة الحالية مضافة في الجلسة، نقوم بحذفها (تصبح العلامة بيضاء)
        wishlist_session.remove(car.id)
        # إذا لم يتبقَ أي سيارات من هذه الماركة في المفضلة، نحذف السجل من قاعدة البيانات
        if not Car.objects.filter(id__in=wishlist_session, inventory=car.inventory).exists():
            favorite_query.delete()
    else:
        # إذا لم تكن مضافة، نضيف رقمها الفريد للجلسة (تصبح العلامة حمراء)
        wishlist_session.append(car.id)
        # ونضمن إنشاء السجل في قاعدة البيانات بشكل سليم يرضي الـ Foreign Key
        if not favorite_query.exists():
            Favorite.objects.create(user=request.user, inventory=car.inventory)
            
    # حفظ التعديلات في الجلسة
    request.session['wishlist_cars'] = wishlist_session
    request.session.modified = True
        
    return redirect(request.META.get('HTTP_REFERER', 'inventory:index'))


# 9. تفعيل وإلغاء المفضلة البديل (قمنا بربطها اختيارياً وتوحيدها بالدالة الرئيسية حمايةً للروابط)
@login_required
def toggle_favorite(request, car_id):
    return toggle_wishlist(request, car_id)


# 10. عرض صفحة المفضلة الخاصة بالمستخدم
@login_required(login_url='login')
def favorites_view(request):
    # 1. جلب السيارات المفضلة المحددة من الجلسة بدقة متناهية
    wishlist_session = request.session.get('wishlist_cars', [])
    
    # 2. جلب كروت السيارات المطابقة تماماً لهذه الأرقام المعزولة
    favorite_cars = Car.objects.filter(id__in=wishlist_session)
    
    # حماية إضافية: إذا كانت الجلسة فارغة ولكن قاعدة البيانات تحتوي على سجلات (بسبب تصفير المتصفح مثلاً)
    if not favorite_cars.exists():
        fav_inventories = Favorite.objects.filter(user=request.user).values_list('inventory_id', flat=True)
        # نأخذ السيارات الأصلية لمنع ظهور الصفحة فارغة
        favorite_cars = Car.objects.filter(inventory_id__in=fav_inventories)
    
    context = {
        'cars': favorite_cars,
    }
    return render(request, 'inventory/favorites.html', context)


# 12. صفحة الرسائل والاتصال بالإدارة
@login_required
def messages_view(request):
    MessageModel = apps.get_model('inventory', 'Message')
    
    if request.user.email:
        incoming_messages = MessageModel.objects.filter(email=request.user.email).order_by('-created_at')
    else:
        incoming_messages = MessageModel.objects.all().order_by('-created_at')[:20]

    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        if message_text and email:
            MessageModel.objects.create(
                name=name if name else request.user.username,
                email=email,
                subject=subject if subject else "استفسار عام",
                message=message_text
            )
            django_messages.success(request, "تم إرسال رسالتك بنجاح وسيتواصل معك الدعم الفني!")
            return redirect('messages')

    return render(request, 'inventory/messages.html', {'messages_list': incoming_messages, 'user': request.user})


# 13. تسجيل مستخدم جديد
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'تم إنشاء الحساب بنجاح للمستخدم {username}! يمكنك الآن تسجيل الدخول.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# 14. استقبال رد بوابة الدفع ميسر 
def payment_callback(request):
    # 1. جلب البيانات القادمة من بوابة ميسر عبر الرابط
    payment_id = request.GET.get('id')
    status = request.GET.get('status')
    message = request.GET.get('message')
    
    # سنحتاج إلى معرفة أي سيارة يتم حجزها الآن، عادةً نقوم بحفظها في الـ Session قبل الذهاب للدفع
    # أو يمكننا جلبها إذا أرسلتها ميسر، الطريقة الأضمن عبر الـ Session:
    car_id = request.session.get('pending_car_id')
    
    # إذا نجحت عملية الدفع من ميسر (status == 'paid' أو 'initiated' حسب التوثيق)
    if status == 'paid' and car_id:
        car = get_object_or_404(Car, id=car_id)
        
        # 2. التعديل السحري: تحويل حالة السيارة إلى محجوزة في قاعدة البيانات
        car.status = 'booked' # أو الحرف/الكلمة المعتمدة عندك في الموديل للحجز مثل 'B' أو 'reserved'
        car.save()
        
        # تنظيف الجلسة بعد نجاح الحجز
        if 'pending_car_id' in request.session:
            del request.session['pending_car_id']
            
        return render(request, 'inventory/payment_success.html', {'car': car, 'payment_id': payment_id})
    
    # في حال فشل الدفع أو عدم وجود سيارة معينة
    return render(request, 'inventory/payment_failed.html', {'message': message})