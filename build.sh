#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# 🌟 إنشاء حساب الأدمن تلقائياً إن لم يكن موجوداً
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); u, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'}); u.set_password('123456'); u.is_staff = True; u.is_superuser = True; u.save()"