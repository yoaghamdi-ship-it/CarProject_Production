#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. تثبيت كافة المكتبات المطلوبة
pip install -r requirements.txt

# 2. إنشاء مجلد static لتفادي تحذير وخطأ STATICFILES_DIRS (500 Error)
mkdir -p static

# 3. تجميع الملفات الثابتة (CSS/JS)
python manage.py collectstatic --no-input

# 4. تطبيق تحديثات قاعدة البيانات
python manage.py migrate

# 5. إنشاء وتحديث حساب الأدمن تلقائياً وتأكيد كلمة المرور والصلاحيات
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); u, _ = User.objects.get_or_create(username='admin'); u.set_password('123456'); u.is_staff = True; u.is_superuser = True; u.is_active = True; u.save(); print('ADMIN ACCOUNT CREATED/UPDATED SUCCESSFULLY!')"