from rest_framework import serializers
from .models import Inventory  # استيراد Inventory من نفس المجلد
from cars.models import Car    # استيراد Car من تطبيق cars الصحيح

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = '__all__' # تحويل كل المواصفات (المحرك، الفئة، إلخ) إلى JSON

class InventorySerializer(serializers.ModelSerializer):
    car = CarSerializer() # تضمين بيانات السيارة داخل العرض
    class Meta:
        model = Inventory
        fields = ['id', 'car', 'price', 'stock_count', 'dealer']