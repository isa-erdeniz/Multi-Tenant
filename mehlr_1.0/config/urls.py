"""
URL configuration for mehlr_1.0.
"""
from django.contrib import admin
from django.urls import path, include

from apps.tenant.views import tenant_landing

urlpatterns = [
    path('', tenant_landing, name='tenant_landing'),
    path('admin/', admin.site.urls),
    path('mehlr/', include('mehlr.urls')),
]

try:
    from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
    urlpatterns.insert(1, path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'))
    urlpatterns.insert(1, path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain'))
except ImportError:
    pass
