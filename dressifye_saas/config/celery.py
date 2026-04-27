import os
from celery import Celery
from django.conf import settings

# ÖNEMLİ: Django ayar dosyanızın yolunu buraya ekleyin. 
# Eğer settings.py 'config' klasöründeyse 'config.settings' kalsın.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("config")

# Namespace 'CELERY' ise settings.py içinde ayarlar CELERY_ ile başlamalıdır.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Django'daki tüm kayıtlı taskları otomatik bulur.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
