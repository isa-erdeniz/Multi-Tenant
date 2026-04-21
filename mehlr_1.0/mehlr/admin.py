"""
mehlr_1.0 — Admin Panel
9 proje için gelişmiş yönetim arayüzü (mevcut modellere uyumlu).
"""
from django.contrib import admin
from django.utils.html import format_html
from mehlr.models import Project, Conversation, Message, AnalysisReport, ModuleRegistry
from mehlr.prompts.project_prompts import PROJECT_PROMPTS


def _project_meta(slug):
    if not slug:
        return {}
    return PROJECT_PROMPTS.get(slug) or PROJECT_PROMPTS.get(slug.replace("_", "-")) or {}


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "name", "slug", "project_type", "capabilities_count",
        "has_prompt", "is_active", "created_at",
    ]
    list_filter = ["is_active", "project_type"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "prompt_preview"]

    fieldsets = (
        ("Temel Bilgiler", {"fields": ("name", "slug", "description", "project_type", "is_active")}),
        ("MEHLR Konfigürasyonu", {"fields": ("context_prompt", "data_schema", "api_endpoint")}),
        ("Prompt Önizleme", {"fields": ("prompt_preview",), "classes": ("collapse",)}),
        ("Tarihler", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def capabilities_count(self, obj):
        meta = _project_meta(obj.slug)
        return format_html('<span style="color:#2563eb;font-weight:bold">{}</span>', len(meta.get("capabilities", [])))
    capabilities_count.short_description = "Capability"

    def has_prompt(self, obj):
        exists = obj.slug in PROJECT_PROMPTS or obj.slug.replace("_", "-") in PROJECT_PROMPTS
        return format_html("{}", "✅" if exists else "❌")
    has_prompt.short_description = "Prompt"

    def prompt_preview(self, obj):
        meta = _project_meta(obj.slug)
        if not meta:
            return "Bu proje için PROJECT_PROMPTS girişi yok."
        sp = (meta.get("system_prompt") or "")[:300]
        caps = ", ".join(meta.get("capabilities", []))
        return format_html("<b>Domain:</b> {}<br><b>Capabilities:</b> {}<br><pre style=\"background:#f5f5f5;padding:8px\">{}</pre>", meta.get("domain", "-"), caps, sp)
    prompt_preview.short_description = "Prompt Önizleme"


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["role", "content_preview", "tokens_used", "created_at"]
    can_delete = False
    max_num = 20

    def content_preview(self, obj):
        return (obj.content[:100] + "...") if len(obj.content) > 100 else obj.content
    content_preview.short_description = "İçerik"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "project", "message_count", "total_tokens", "created_at", "updated_at"]
    list_filter = ["project", "created_at"]
    search_fields = ["title", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [MessageInline]

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "Mesaj"

    def total_tokens(self, obj):
        total = sum(m.tokens_used or 0 for m in obj.messages.all())
        return format_html('<span style="color:#059669">{}</span>', total)
    total_tokens.short_description = "Token"


@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display = [
        "title", "project", "get_confidence",
        "get_tokens", "get_generation_time",
        "get_has_error", "created_at",
    ]
    list_filter = ["project", "report_type"]
    search_fields = ["title", "content"]
    readonly_fields = ["created_at", "content_preview"]

    def _snap(self, obj, key, default="—"):
        return (obj.data_snapshot or {}).get(key, default)

    def get_confidence(self, obj):
        val = self._snap(obj, "confidence_score", "—")
        colors = {"YÜKSEK": "#16a34a", "ORTA": "#d97706", "DÜŞÜK": "#dc2626"}
        color = colors.get(val, "#9ca3af")
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, val)
    get_confidence.short_description = "Güven"

    def get_tokens(self, obj):
        return format_html(
            '<span style="color:#2563eb">{}</span>',
            self._snap(obj, "tokens_used", 0),
        )
    get_tokens.short_description = "Token"

    def get_generation_time(self, obj):
        val = self._snap(obj, "generation_time", 0)
        try:
            return f"{float(val):.2f}s"
        except (ValueError, TypeError):
            return "—"
    get_generation_time.short_description = "Süre"

    def get_has_error(self, obj):
        has_err = self._snap(obj, "has_error", False)
        return format_html("{}", "❌" if has_err else "✅")
    get_has_error.short_description = "Durum"

    def content_preview(self, obj):
        snap = obj.data_snapshot or {}
        confidence = snap.get("confidence_score", "—")
        tokens = snap.get("tokens_used", "—")
        gen_time = snap.get("generation_time", "—")
        has_error = snap.get("has_error", False)
        error_msg = snap.get("error_message", "")
        response_preview = str(snap.get("response", ""))[:400]
        try:
            gen_str = f"{float(gen_time):.2f}s" if gen_time != "—" else "—"
        except (ValueError, TypeError):
            gen_str = "—"
        pre_style = "background:#f9fafb;padding:8px;border-radius:4px;white-space:pre-wrap;max-height:200px;overflow-y:auto"
        hata_str = "Evet — " + error_msg if has_error else "Hayır"
        html = (
            f"<b>Güven:</b> {confidence} | <b>Token:</b> {tokens} | "
            f"<b>Süre:</b> {gen_str} | <b>Hata:</b> {hata_str}<br><br>"
            f'<pre style="{pre_style}">{response_preview}</pre>'
        )
        if has_error and error_msg:
            html += f'<p style="color:red">{error_msg}</p>'
        from django.utils.safestring import mark_safe
        return mark_safe(html)
    content_preview.short_description = "İçerik & Snapshot"

    fieldsets = (
        ("Rapor Bilgileri", {"fields": ("title", "project", "report_type")}),
        ("İçerik & AI Sonuçları", {"fields": ("content_preview",)}),
        ("Tarihler", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(ModuleRegistry)
class ModuleRegistryAdmin(admin.ModelAdmin):
    list_display = ["name", "module_path", "version", "is_enabled", "created_at"]
    list_filter = ["is_enabled"]
    filter_horizontal = ["supported_projects"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]


admin.site.site_header = "mehlr_1.0 — ErdenizTech AI Engine"
admin.site.site_title = "MEHLR Admin"
admin.site.index_title = "Yönetim Paneli"
