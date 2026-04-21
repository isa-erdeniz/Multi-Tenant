"""
MEHLR 1.0 — DRF Serializers
API endpoint'leri için veri doğrulama ve serileştirme.
"""
from rest_framework import serializers
from mehlr.models import Project, Conversation, Message, AnalysisReport
from mehlr.prompts.project_prompts import PROJECT_PROMPTS


class ProjectSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    domain       = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    report_types = serializers.SerializerMethodField()

    class Meta:
        model  = Project
        fields = [
            "id", "name", "slug", "description", "project_type",
            "api_endpoint", "is_active", "created_at",
            "display_name", "domain", "capabilities", "report_types",
        ]
        read_only_fields = ["id", "created_at"]

    def get_display_name(self, obj):
        return PROJECT_PROMPTS.get(obj.slug, {}).get("display_name", obj.name)

    def get_domain(self, obj):
        return PROJECT_PROMPTS.get(obj.slug, {}).get("domain", "")

    def get_capabilities(self, obj):
        return PROJECT_PROMPTS.get(obj.slug, {}).get("capabilities", [])

    def get_report_types(self, obj):
        return PROJECT_PROMPTS.get(obj.slug, {}).get(
            "analytics_config", {}
        ).get("report_types", [])


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Message
        fields = [
            "id", "role", "content", "tokens_used",
            "processing_time", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    messages      = MessageSerializer(many=True, read_only=True)
    project_slug  = serializers.CharField(source="project.slug",  read_only=True)
    project_name  = serializers.CharField(source="project.name",  read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model  = Conversation
        fields = [
            "id", "title", "project_slug", "project_name",
            "message_count", "created_at", "updated_at", "messages",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationListSerializer(serializers.ModelSerializer):
    """Listeler için hafif versiyon — messages dahil değil."""
    project_slug  = serializers.CharField(source="project.slug", read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model  = Conversation
        fields = ["id", "title", "project_slug", "message_count", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.messages.count()


class AnalysisReportSerializer(serializers.ModelSerializer):
    project_slug    = serializers.CharField(source="project.slug", read_only=True)
    confidence      = serializers.SerializerMethodField()
    tokens_used     = serializers.SerializerMethodField()
    generation_time = serializers.SerializerMethodField()
    has_error       = serializers.SerializerMethodField()

    class Meta:
        model  = AnalysisReport
        fields = [
            "id", "title", "report_type", "project_slug",
            "confidence", "tokens_used", "generation_time", "has_error",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def _snap(self, obj, key, default=None):
        return (obj.data_snapshot or {}).get(key, default)

    def get_confidence(self, obj):
        return self._snap(obj, "confidence_score", "BELİRTİLMEDİ")

    def get_tokens_used(self, obj):
        return self._snap(obj, "tokens_used", 0)

    def get_generation_time(self, obj):
        return self._snap(obj, "generation_time", 0)

    def get_has_error(self, obj):
        return self._snap(obj, "has_error", False)


class ChatSendSerializer(serializers.Serializer):
    """POST /api/chat/send/ için."""
    message          = serializers.CharField(max_length=2000)
    project_slug     = serializers.CharField(max_length=100, required=False, default="general")
    conversation_id  = serializers.IntegerField(required=False, allow_null=True)

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Mesaj boş olamaz.")
        return value.strip()


class ReportGenerateSerializer(serializers.Serializer):
    """POST /api/reports/generate/ için."""
    REPORT_TYPES = ["summary", "trend_report", "audit_report", "performance", "custom"]

    project_slug = serializers.CharField(max_length=100)
    report_type  = serializers.ChoiceField(choices=REPORT_TYPES, default="summary")
    custom_query = serializers.CharField(max_length=1000, required=False, default="")

    def validate(self, data):
        if data.get("report_type") == "custom" and not data.get("custom_query", "").strip():
            raise serializers.ValidationError({"custom_query": "Özel rapor için sorgu zorunludur."})
        return data
