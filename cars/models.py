from django.db import models

# هذا الكود فارغ تماماً ومغير اسم الجدول لمنع التصادم مع التطبيق الأساسي
class OldCarDummy(models.Model):
    pass
    class Meta:
        db_table = 'old_cars_backup_table'