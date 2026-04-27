#!/usr/bin/env python
"""Django's manage.py — proje kökünden çalıştırın: python manage.py runserver"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "erdeniz_security.tests.settings",
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django yüklü değil. Kurmak için: pip install -e ."
        ) from exc
    execute_from_command_line(sys.argv)
