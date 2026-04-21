"""Proje paketi — Celery uygulaması yüklenir."""
from .celery import app as celery_app

__all__ = ("celery_app",)
