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
    check_expired_bookings()

    car = get_object_or_404(Car, id=car_id) 
    is_booked = car.status == 'reserved' or Booking.objects.filter(car=car, status='paid').exists()
    
    deposit_amount_halalas = 1000 * 100

    inventory_item = Inventory.objects.filter(inventory_cars=car).first()
    comments = []
    is_favorite = False
    
    if inventory_item:
        comments = Comment.objects.filter(inventory=inventory_item).order_by('-id')
        
        if request.user.is_authenticated:
            try:
                FavoriteModel = apps.get_model('inventory', 'Favorite')
                is_favorite = FavoriteModel.objects.filter(inventory=inventory_item, user=request.user).exists()
            except Exception:
                is_favorite = False

    context = {
        'car': car,
        'is_booked': is_booked, 
        'publishable_key': MOYASAR_PUBLISHABLE_KEY.strip(),
        'amount': deposit_amount_halalas, 
        'comments': comments,
        'is_favorite': is_favorite, 
        'user': request.user,
    }
    return render(request, 'inventory/detail.html', context)


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
        comment_content = request.POST.get('content') or request.POST.get('text')
        if comment_content:
            # سنقوم بإنشاء التعليق وتعبئة الحقول يدوياً لتفادي رفض قاعدة البيانات
            comment = Comment()
            comment.user = request.user
            comment.text = comment_content
            
            # هنا التعديل السحري: جرب ربطه بالسيارة، وإذا رفضت قاعدة البيانات اربطه بالوكيل الخاص بها
            if hasattr(comment, 'car'):
                comment.car = car
            elif hasattr(comment, 'inventory'):
                comment.inventory = car.inventory # أو الحقل المربوط بالوكيل عندك
            
            comment.save() # حفظ التعديل بأمان
            
    return redirect('inventory:car_detail', car_id=car.id)

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
    payment_id = request.GET.get('id')
    status_response = request.GET.get('status')
    message_text = request.GET.get('message')

    if status_response == 'paid' or message_text == 'APPROVED':
        booking = Booking.objects.filter(user=request.user, status='pending').last()
        
        if not booking:
            booking = Booking.objects.filter(user=request.user).exclude(status='paid').last()
            
        if booking:
            booking.status = 'paid'
            booking.transaction_id = payment_id  
            booking.amount_paid = 1000  
            booking.deposit_paid_at = timezone.now()  
            booking.reserved_at = timezone.now()
            booking.save()
            
            car = booking.car
            car.status = 'reserved'
            car.is_available = False 
            car.save()
            
            messages.success(request, "تمت عملية دفع العربون وتأكيد الحجز بنجاح!")
            return redirect('payment_success', booking_id=booking.id)
            
        else:
            car_id = request.session.get('pending_car_id')
            if car_id:
                try:
                    car = Car.objects.get(id=car_id)
                    new_booking = Booking.objects.create(
                        user=request.user,
                        car=car,
                        status='paid',
                        amount_paid=1000,
                        transaction_id=payment_id,
                        deposit_paid_at=timezone.now(),
                        reserved_at=timezone.now()
                    )
                    messages.success(request, "تم دفع العربون وإنشاء الحجز بنجاح!")
                    return redirect('payment_success', booking_id=new_booking.id)
                except Car.DoesNotExist:
                    pass

            last_any_booking = Booking.objects.filter(user=request.user).last()
            if last_any_booking:
                last_any_booking.status = 'paid'
                last_any_booking.transaction_id = payment_id
                last_any_booking.amount_paid = 1000
                last_any_booking.deposit_paid_at = timezone.now()
                last_any_booking.reserved_at = timezone.now()
                last_any_booking.save()
                return redirect('payment_success', booking_id=last_any_booking.id)

        messages.warning(request, "تم الدفع، ولكن لم نتمكن من ربط الحجز بالسيارة تلقائياً. يرجى مراجعة الإدارة.")
        return redirect('index')
    else:
        messages.error(request, "فشلت عملية الدفع أو تم إلغاؤها.")
        return redirect('index')
    
class AllCommentsView(ListView):
    model = Comment
    template_name = 'inventory/all_comments.html'  # تأكد من إنشاء هذا الملف في الـ templates
    context_object_name = 'comments'
    ordering = ['-id']