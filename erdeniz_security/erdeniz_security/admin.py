from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages

from .models import SecurityAuditLog, ErdenizAPIKey


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp",
        "event_type_badge",
        "project",
        "resource_short",
        "success_badge",
        "ip_address",
        "user",
        "duration_ms",
    ]
    list_filter = ["event_type", "project", "success", "timestamp"]
    search_fields = ["resource", "ip_address", "user__username", "project"]
    readonly_fields = [
        "timestamp",
        "event_type",
        "user",
        "ip_address",
        "user_agent",
        "resource",
        "project",
        "success",
        "details",
        "duration_ms",
    ]
    ordering = ["-timestamp"]
    list_per_page = 50
    date_hierarchy = "timestamp"

    verbose_name = "Güvenlik Denetim Kaydı"
    verbose_name_plural = "Güvenlik Denetim Kayıtları"

    change_list_template = "admin/erdeniz_security/securityauditlog/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        info = self.opts.app_label, self.opts.model_name
        prefix = "%s_%s_" % info
        custom_urls = [
            path(
                "turkce-mod-ac/",
                self.admin_site.admin_view(self.turkce_mod_ac),
                name=prefix + "turkce_mod_ac",
            ),
            path(
                "turkce-mod-kapat/",
                self.admin_site.admin_view(self.turkce_mod_kapat),
                name=prefix + "turkce_mod_kapat",
            ),
            path(
                "guvenlik-raporu/",
                self.admin_site.admin_view(self.guvenlik_raporu),
                name=prefix + "guvenlik_raporu",
            ),
            path(
                "loglari-temizle/",
                self.admin_site.admin_view(self.loglari_temizle),
                name=prefix + "loglari_temizle",
            ),
        ]
        return custom_urls + urls

    def turkce_mod_ac(self, request):
        """Oturumu Türkçe dile ayarla."""
        from django.utils import translation

        translation.activate("tr")
        request.session["_language"] = "tr"
        request.session["erdeniz_dil"] = "tr"
        messages.success(
            request,
            "✅ Türkçe mod etkinleştirildi. Tüm mesajlar Türkçe gösterilecek.",
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "../"))

    def turkce_mod_kapat(self, request):
        """Dili varsayılana döndür."""
        from django.conf import settings
        from django.utils import translation

        default_lang = getattr(settings, "LANGUAGE_CODE", "tr")
        translation.activate(default_lang)
        request.session["_language"] = default_lang
        request.session.pop("erdeniz_dil", None)
        messages.info(
            request, f"ℹ️ Dil varsayılana döndürüldü: {default_lang}"
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "../"))

    def guvenlik_raporu(self, request):
        """Güvenlik istatistiklerini göster."""
        from .audit import get_alerts, get_stats

        stats = get_stats(days=7)
        alerts = get_alerts(hours=24)
        messages.info(
            request,
            f"📊 Son 7 gün: {stats['total']} kayıt | "
            f"{stats['failed']} başarısız | "
            f"{stats['auth_fail']} giriş hatası | "
            f"Son 24 saat: {len(alerts)} uyarı",
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "../"))

    def loglari_temizle(self, request):
        """30 günden eski logları sil."""
        from datetime import timedelta

        from django.utils import timezone

        sinir = timezone.now() - timedelta(days=30)
        silinen, _ = SecurityAuditLog.objects.filter(timestamp__lt=sinir).delete()
        messages.success(
            request,
            f"🗑️ {silinen} eski güvenlik kaydı silindi (30 günden eski).",
        )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "../"))

    def event_type_badge(self, obj):
        renkler = {
            "ENCRYPT": "#28a745",
            "DECRYPT": "#17a2b8",
            "AUTH_SUCCESS": "#28a745",
            "AUTH_FAIL": "#dc3545",
            "SECURITY_ALERT": "#dc3545",
            "API_KEY_CREATE": "#007bff",
            "API_KEY_REVOKE": "#ffc107",
            "RATE_LIMIT_HIT": "#fd7e14",
            "WEBHOOK_VERIFIED": "#20c997",
            "WEBHOOK_REJECTED": "#dc3545",
            "KEY_ROTATE": "#6f42c1",
        }
        etiketler = {
            "ENCRYPT": "🔒 Şifrele",
            "DECRYPT": "🔓 Çöz",
            "AUTH_SUCCESS": "✅ Giriş OK",
            "AUTH_FAIL": "❌ Giriş Hata",
            "SECURITY_ALERT": "🚨 Uyarı",
            "API_KEY_CREATE": "🔑 Key Oluştur",
            "API_KEY_REVOKE": "⛔ Key İptal",
            "RATE_LIMIT_HIT": "⏱️ Limit Aşıldı",
            "WEBHOOK_VERIFIED": "✅ Webhook OK",
            "WEBHOOK_REJECTED": "❌ Webhook Ret",
            "KEY_ROTATE": "🔄 Key Rotasyon",
        }
        renk = renkler.get(obj.event_type, "#6c757d")
        etiket = etiketler.get(obj.event_type, obj.event_type)
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            renk,
            etiket,
        )

    event_type_badge.short_description = "Olay Tipi"

    def success_badge(self, obj):
        if obj.success:
            return format_html(
                '<span style="color:#28a745;font-weight:bold;">✅ Başarılı</span>'
            )
        return format_html(
            '<span style="color:#dc3545;font-weight:bold;">❌ Başarısız</span>'
        )

    success_badge.short_description = "Durum"

    def resource_short(self, obj):
        r = obj.resource or ""
        return r[:40] + "..." if len(r) > 40 else r

    resource_short.short_description = "Kaynak"


@admin.register(ErdenizAPIKey)
class ErdenizAPIKeyAdmin(admin.ModelAdmin):
    list_display = [
        "prefix",
        "project",
        "permissions_display",
        "is_active_badge",
        "usage_count",
        "expires_at",
        "created_at",
    ]
    list_filter = ["project", "is_active"]
    search_fields = ["prefix", "project"]
    readonly_fields = [
        "key_id",
        "prefix",
        "hashed_key",
        "created_at",
        "last_used_at",
        "usage_count",
    ]
    ordering = ["-created_at"]
    verbose_name = "API Anahtarı"
    verbose_name_plural = "API Anahtarları"

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:#28a745;font-weight:bold;">✅ Aktif</span>'
            )
        return format_html(
            '<span style="color:#dc3545;font-weight:bold;">⛔ İptal</span>'
        )

    is_active_badge.short_description = "Durum"

    def permissions_display(self, obj):
        perms = obj.permissions or []
        if not isinstance(perms, list):
            perms = []
        perms = [str(p) for p in perms[:3]]
        return ", ".join(perms) + ("..." if len(obj.permissions or []) > 3 else "")

    permissions_display.short_description = "İzinler"


# Admin site Türkçe başlıkları
admin.site.site_header = "ErdenizTech Güvenlik Paneli"
admin.site.site_title = "ErdenizTech Admin"
admin.site.index_title = "Güvenlik Yönetim Merkezi"
