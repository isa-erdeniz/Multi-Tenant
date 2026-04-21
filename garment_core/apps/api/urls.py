"""
FAZ 24: REST API & Webhook'lar
"""
from django.urls import path, include

app_name = "api"

urlpatterns = [
    path("", include("apps.api.v1.urls")),
]
