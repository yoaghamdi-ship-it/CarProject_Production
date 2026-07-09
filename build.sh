#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# 🌟 إعادة ضبط وتحديث حساب الأدمن وتأكيد الصلاحيات وكلمة المرور
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); u, _ = User.objects.get_or_create(username='admin'); u.set_password('123456'); u.is_staff = True; u.is_superuser = True; u.is_active = True; u.save(); print('ADMIN ACCOUNT UPDATED SUCCESSFULLY!')"