import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
u, _ = User.objects.get_or_create(username='isa')
u.is_staff = True
u.is_superuser = True
u.set_password('Isa2026!')
u.save()
print('Superuser OK')
