from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib import messages as django_messages 
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.db.models import Min, Q, IntegerField
from django.apps import apps 
from django.db.models.functions import Cast
from django.views.generic import TemplateView
import re
import json
import logging
logger = logging.getLogger(__name__)

# --- استيراد الموديلات ---
from .models import Inventory, Comment, Favorite, Message, Booking, Car
from .forms import CarForm

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

# --- إعدادات ميسر ---
MOYASAR_SECRET_KEY = "sk_test_4qRHE1RTQwrEh3gh9H7cxb4LkbJWDMTJtP6ngp3s"
MOYASAR_PUBLISHABLE_KEY = "pk_test_VP5cwmVp2Z5qRW4Ha97jyB9BKjiZTW7KPadLgvH3"


# 🔥 دالة المراقبة الذكية المساعدة (تُستدعى تلقائياً لتحديث الحالات بالخلفية)
def check_expired_bookings():
    now = timezone.now()
    active_bookings = Booking.objects.filter(status__in=['pending', 'paid'])
    
    for booking in active_bookings:
        expired = False
        if booking.status == 'pending' and now > booking.reserved_at + timedelta(hours=24):
            expired = True
        elif booking.status == 'paid' and booking.deposit_paid_at:
            if now > booking.deposit_paid_at + timedelta(hours=48):
                expired = True
                
        if expired:
            booking.status = 'expired'
            booking.save()
            car = booking.car
            car.status = 'available'
            car.is_available = True
            car.save()


# 1. الصفحة الرئيسية
def index(request):
    cars = Car.objects.all()
    
    for car in cars:
        car.is_already_booked = Booking.objects.filter(car=car, status='paid').exists()
    
    ticker_cars = [car for car in cars if not car.is_already_booked]

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
            
            request.session['wishlist_cars'] = favorite_car_ids
            
        request.session.modified = True
    else:
        request.session['wishlist_cars'] = []

    context = {
        'cars': cars,
        'ticker_cars': ticker_cars,
    }
    return render(request, 'inventory/index.html', context)


# 2. قائمة السيارات
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


# 3. تفاصيل السيارة
def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    request.session['pending_car_id'] = car.id
    
    inventory_item = Inventory.objects.filter(inventory_cars=car).first()
    comments = inventory_item.comments.all() if inventory_item else []
    
    is_booked = car.status == 'booked' or Booking.objects.filter(car=car, status='paid').exists()
    
    context = {
        'car': car,
        'comments': comments,
        'is_booked': is_booked
    }
    return render(request, 'inventory/detail.html', context)


# 4. إضافة تعليق جديد
@login_required
def add_comment(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    
    if request.method == 'POST':
        comment_content = request.POST.get('content')
        
        if comment_content:
            inventory_item = Inventory.objects.filter(inventory_cars=car).first()
            
            if inventory_item:
                Comment.objects.create(
                    inventory=inventory_item,
                    user=request.user,
                    text=comment_content
                )
            
    return redirect('inventory:car_detail', car_id=car.id)


# 5. عرض كافة التعليقات كـ Class-based View
class AllCommentsView(TemplateView):
    template_name = 'inventory/all_comments.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = Comment.objects.all().order_by('-created_at')
        return context


# 6. إضافة سيارة (محمية للمسؤولين فقط مع توجيه آمن)
@user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser), login_url='inventory:index')
def add_car(request):
    if request.method == "POST":
        form = CarForm(request.POST, request.FILES)
        if form.is_valid():
            car = form.save()
            django_messages.success(request, f"تم إضافة السيارة {car.brand} بنجاح!")
            return redirect('inventory:car_list')
    else:
        form = CarForm()
    return render(request, 'inventory/add_car.html', {'form': form, 'user': request.user})


# 7. إجراءات الحجز المبدئي وتحضير الجلسة
@login_required(login_url='inventory:login')
def book_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    
    # 1. التأكد من أن السيارة غير مدفوعة ومحجوزة نهائياً من قبل شخص آخر
    if Booking.objects.filter(car=car, status='paid').exists():
        messages.error(request, "عذراً، هذه السيارة تم حجزها بالكامل وسداد عربونها مسبقاً.")
        return redirect('inventory:car_detail', car_id=car.id)

    deposit_amount = 1000 

    # 2. إنشاء الحجز أو تحديثه مباشرة إلى حالة المدفوع/المحجوز بنجاح (Paid)
    booking, created = Booking.objects.get_or_create(
        user=request.user,
        car=car,
        defaults={'status': 'paid', 'amount_paid': deposit_amount}
    )

    # إذا كان هناك حجز معلق سابق لنفس المستخدم، قم بتأكيده وتغيير حالته إلى paid
    if not created and booking.status != 'paid':
        booking.status = 'paid'
        booking.amount_paid = deposit_amount
        booking.save()

    # 3. حفظ بيانات الجلسة إن كنت تحتاجها
    request.session['pending_car_id'] = car.id
    request.session['deposit_amount'] = deposit_amount
    request.session.modified = True

    messages.success(request, f"تهانينا! تم تأكيد حجز السيارة {car.brand} {car.model_name} بنجاح.")
    
    # التوجيه لصفحة تأكيد نجاح الدفع والحجز
    return redirect('inventory:payment_success', booking_id=booking.id)


# 8. معالجة نجاح الدفع وعرض الفاتورة
def payment_success(request, booking_id):
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        context = {
            'booking': booking,
            'car': booking.car, 
        }
        return render(request, 'inventory/payment_success.html', context)
    except Exception as e:
        logger.error(f"Error in payment_success: {str(e)}")
        messages.success(request, "تم تأكيد الحجز بنجاح!")
        return redirect('inventory:index')


# 9. استقبال رد بوابة الدفع ميسر
def payment_callback(request):
    payment_id = request.GET.get('id')
    status = request.GET.get('status')
    message = request.GET.get('message')
    car_id = request.session.get('pending_car_id')
    
    try:
        if status == 'paid':
            if not car_id:
                booking = Booking.objects.filter(status='pending').order_by('-id').first()
                car = booking.car if booking else None
            else:
                car = Car.objects.filter(id=car_id).first()
            
            if car:
                car.status = 'booked'
                car.is_available = False
                car.save()
                
                booking = Booking.objects.filter(car=car, status='pending').last()
                if booking:
                    booking.status = 'paid'
                    booking.deposit_paid_at = timezone.now()
                    booking.save()
                else:
                    user = request.user if request.user.is_authenticated else None
                    if not user:
                        last_b = Booking.objects.filter(car=car).last()
                        user = last_b.user if last_b else None
                    
                    booking = Booking.objects.create(
                        user=user,
                        car=car,
                        status='paid',
                        amount_paid=1000,
                        deposit_paid_at=timezone.now()
                    )
                
                request.session.pop('pending_car_id', None)
                return redirect('inventory:payment_success', booking_id=booking.id)
                
    except Exception as e:
        logger.error(f"Payment callback failed: {str(e)}")
        messages.success(request, "تم الدفع وتأكيد حجز السيارة بنجاح!")
        return redirect('inventory:index')

    return render(request, 'inventory/payment_failed.html', {'message': message})


# 10. التحكم الذكي بالمفضلة 
@login_required(login_url='login')
def toggle_wishlist(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    favorite_query = Favorite.objects.filter(user=request.user, inventory=car.inventory)
    wishlist_session = request.session.get('wishlist_cars', [])
    
    if car.id in wishlist_session:
        wishlist_session.remove(car.id)
        if not Car.objects.filter(id__in=wishlist_session, inventory=car.inventory).exists():
            favorite_query.delete()
    else:
        wishlist_session.append(car.id)
        if not favorite_query.exists():
            Favorite.objects.create(user=request.user, inventory=car.inventory)
            
    request.session['wishlist_cars'] = wishlist_session
    request.session.modified = True
        
    return redirect(request.META.get('HTTP_REFERER', 'inventory:index'))


@login_required
def toggle_favorite(request, car_id):
    return toggle_wishlist(request, car_id)


@login_required(login_url='inventory:login')
def favorites_view(request):
    # 1. محاولة جلب المفضلة من الجلسة (Session) أولاً
    wishlist_session = request.session.get('wishlist_cars', [])
    favorite_cars = Car.objects.filter(id__in=wishlist_session)
    
    # 2. إذا لم تكن موجودة في الجلسة، نأتي بها من قاعدة البيانات بحسب الحقل الصحيح (inventory_id)
    if not favorite_cars.exists():
        fav_car_ids = Favorite.objects.filter(user=request.user).values_list('inventory_id', flat=True)
        favorite_cars = Car.objects.filter(id__in=fav_car_ids)
    
    context = {
        'cars': favorite_cars,
    }
    return render(request, 'inventory/favorites.html', context)


# 11. صفحة الرسائل والاتصال بالإدارة
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


# 12. تسجيل مستخدم جديد
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'تم إنشاء الحساب بنجاح للمستخدم {username}! يمكنك الآن تسجيل الدخول.')
            return redirect('inventory:login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# 13. صفحة لوحة تحكم المعرض
@login_required(login_url='login')
def my_cars(request):
    cars = Car.objects.filter(owner=request.user).order_by('-id')
    return render(request, 'inventory/my_cars.html', {'cars': cars})


# 🔒 14. دالة تسجيل الخروج الآمنة وتدمير الجلسة تماماً (تغطي ثغرة البقاء مسجلاً)
def admin_logout_view(request):
    logout(request)
    request.session.flush()  # 👈 تدمير كافة الكوكيز والجلسة تماماً لمنع بقاء حساب الأدمن متصلاً
    response = redirect('inventory:index')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# 🔒 15. كلاس تسجيل الدخول المعدل لمنع التوجيه الخاطئ لـ /admin/
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    next_page = reverse_lazy('inventory:index')

@staff_member_required
def admin_dashboard(request):
    """لوحة متابعة الرسائل والتعليقات غير المجاب عليها"""
    pending_comments = Comment.objects.filter(reply__isnull=True).order_by('-created_at')
    pending_messages = Message.objects.filter(reply__isnull=True).order_by('-created_at')
    
    context = {
        'pending_comments': pending_comments,
        'pending_messages': pending_messages,
    }
    return render(request, 'inventory/admin_dashboard.html', context)

@staff_member_required
def reply_comment(request, comment_id):
    """حفظ رد الموظف على تعليق محدد"""
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id)
        reply_text = request.POST.get('reply_text', '').strip()
        if reply_text:
            comment.reply = reply_text
            comment.replied_at = timezone.now()
            comment.save()
            messages.success(request, "تم تسجيل الرد على التعليق بنجاح.")
        else:
            messages.error(request, "لا يمكن إرسال رد فارغ.")
    return redirect('inventory:admin_dashboard')

@staff_member_required
def reply_message(request, message_id):
    """حفظ رد الموظف على رسالة محددة"""
    if request.method == "POST":
        msg = get_object_or_404(Message, id=message_id)
        reply_text = request.POST.get('reply_text', '').strip()
        if reply_text:
            msg.reply = reply_text
            msg.replied_at = timezone.now()
            msg.save()
            messages.success(request, "تم تسجيل الرد على الرسالة بنجاح.")
        else:
            messages.error(request, "لا يمكن إرسال رد فارغ.")
    return redirect('inventory:admin_dashboard')