"""
Garment Core URL Configuration
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include

from apps.legal.views import hakkimizda_view

urlpatterns = [
    path("hesap/giris/", lambda r: redirect("/hesap/login/", permanent=False)),
    path("hesap/kayit/", lambda r: redirect("/hesap/signup/", permanent=False)),
    path("hesap/cikis/", lambda r: redirect("/hesap/logout/", permanent=False)),
    path("", include("apps.core.urls", namespace="core")),
    path("legal/", include("apps.legal.urls", namespace="legal")),
    path("hakkimizda/", hakkimizda_view, name="hakkimizda"),
    path("analitik/", include("apps.analytics.urls", namespace="analytics")),
    path("admin/", admin.site.urls),
    path("hesap/", include("allauth.urls")),
    path("hesap/", include("apps.accounts.urls", namespace="accounts")),
    path("profil/", include("apps.profiles.urls", namespace="profiles")),
    path("gardırop/", include("apps.wardrobe.urls", namespace="wardrobe")),
    path("stil/", include("apps.styling.urls", namespace="styling")),
    path("tryon/", include("apps.tryon.urls", namespace="tryon")),
    path("duzenle/", include("apps.editor.urls", namespace="editor")),
    path("makyaj/", include("apps.beauty.urls", namespace="beauty")),
    path("sac/", include("apps.hair.urls", namespace="hair")),
    path("avatar/", include("apps.avatar.urls", namespace="avatar")),
    path("gorunumler/", include("apps.looks.urls", namespace="looks")),
    path("topluluk/", include("apps.social.urls", namespace="social")),
    path("katalog/", include("apps.catalog.urls", namespace="catalog")),
    path("api/v1/", include("apps.api.urls", namespace="api")),
    path("webhooks/ai/", include("apps.ai_integrations.urls")),
    path("odemeler/", include("apps.payments.urls", namespace="payments")),
    path("abonelik/", include("apps.subscriptions.urls", namespace="subscriptions")),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns.insert(0, path("__debug__/", include("debug_toolbar.urls")))

# erdeniz_security paketi kuruluysa ingest endpoint'ini aç
if "erdeniz_security" in settings.INSTALLED_APPS:
    urlpatterns += [
        path(
            "erdeniz-security/",
            include("erdeniz_security.urls", namespace="erdeniz_security"),
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Production: media dosyaları (S3 kullanılmıyorsa)
    if not getattr(settings, "USE_S3", False):
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
