"""
MEHLR Admin panel konfigürasyonu.
"""
from django.contrib import admin
from .models import Project, Conversation, Message, AnalysisReport, ModuleRegistry


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'project_type', 'is_active', 'created_at')
    list_filter = ('is_active', 'project_type')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'project', 'is_active', 'created_at')
    list_filter = ('is_active', 'project')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'project')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'content_preview', 'tokens_used', 'created_at')
    list_filter = ('role',)
    search_fields = ('content',)
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        return (obj.content[:60] + '...') if len(obj.content) > 60 else obj.content
    content_preview.short_description = 'İçerik'


@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'report_type', 'is_active', 'created_at')
    list_filter = ('report_type', 'is_active', 'project')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at',)
    raw_id_fields = ('project', 'generated_by')


@admin.register(ModuleRegistry)
class ModuleRegistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'module_path', 'is_enabled', 'updated_at')
    list_filter = ('is_enabled',)
    filter_horizontal = ('supported_projects',)
    readonly_fields = ('created_at', 'updated_at')
