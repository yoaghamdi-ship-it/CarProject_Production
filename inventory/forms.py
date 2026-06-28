from django import forms
from .models import Car  # الاستيراد الصحيح للموديل من نفس المجلد

class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        # لإظهار كافة الحقول القديمة والجديدة تلقائياً في صفحة إضافة سيارة
        fields = '__all__'