"""
Garment Core — pytest genel konfigürasyonu.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")
django.setup()
