"""
URL configuration for mehlr_1.0.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('mehlr/', include('mehlr.urls')),
]
