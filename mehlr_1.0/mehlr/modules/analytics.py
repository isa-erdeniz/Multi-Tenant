"""
MEHLR 1.0 — Analytics Module
Gerçek DB metriklerinden analitik hesaplama.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from mehlr.modules.base_module import BaseMEHLRModule
from mehlr.models import Project, Conversation, Message, AnalysisReport

logger = logging.getLogger("mehlr")


class AnalyticsModule(BaseMEHLRModule):
    """
    Proje ve sistem geneli analitik hesaplama.
    Gemini'ye gönderilecek bağlamı zenginleştirmek için
    ham DB metriklerini yapılandırılmış dict'e çevirir.
    """

    module_name = "analytics"
    version = "1.0"

    def get_project_stats(self, project_slug: str, days: int = 30) -> dict:
        """
        Son N günde projeye ait temel metrikler.
        Döner: {conversations, messages, avg_tokens, reports, active_days}
        """
        since = timezone.now() - timedelta(days=days)

        try:
            project = Project.objects.get(slug=project_slug, is_active=True)
        except Project.DoesNotExist:
            logger.warning(f"AnalyticsModule: project not found — {project_slug}")
            return self._empty_stats()

        conversations = Conversation.objects.filter(
            project=project, created_at__gte=since
        )
        conv_count = conversations.count()

        messages = Message.objects.filter(
            conversation__project=project,
            created_at__gte=since,
        )
        msg_count    = messages.count()
        avg_tokens   = messages.filter(role="assistant").aggregate(
            avg=Avg("tokens_used")
        )["avg"] or 0
        total_tokens = messages.filter(role="assistant").aggregate(
            total=Sum("tokens_used")
        )["total"] or 0

        report_count = AnalysisReport.objects.filter(
            project=project, created_at__gte=since
        ).count()

        # Aktif gün sayısı (konuşma olan günler)
        active_days = (
            conversations.dates("created_at", "day").count()
        )

        stats = {
            "project_slug":   project_slug,
            "period_days":    days,
            "conversations":  conv_count,
            "messages":       msg_count,
            "reports":        report_count,
            "avg_tokens":     round(avg_tokens, 1),
            "total_tokens":   total_tokens,
            "active_days":    active_days,
            "msgs_per_conv":  round(msg_count / conv_count, 1) if conv_count else 0,
        }
        logger.info(f"AnalyticsModule: stats computed — {project_slug} / {days}d")
        return stats

    def get_system_stats(self, days: int = 30) -> dict:
        """
        Tüm sistem geneli özet metrikler.
        Dashboard stat kartları için kullanılır.
        """
        since = timezone.now() - timedelta(days=days)

        total_projects      = Project.objects.filter(is_active=True).count()
        total_conversations = Conversation.objects.filter(created_at__gte=since).count()
        total_messages      = Message.objects.filter(created_at__gte=since).count()
        total_reports       = AnalysisReport.objects.filter(created_at__gte=since).count()
        total_tokens        = Message.objects.filter(
            created_at__gte=since, role="assistant"
        ).aggregate(total=Sum("tokens_used"))["total"] or 0

        # En aktif proje
        top_project = (
            Conversation.objects.filter(created_at__gte=since)
            .values("project__slug", "project__name")
            .annotate(count=Count("id"))
            .order_by("-count")
            .first()
        )

        return {
            "period_days":         days,
            "total_projects":      total_projects,
            "total_conversations": total_conversations,
            "total_messages":      total_messages,
            "total_reports":       total_reports,
            "total_tokens":        total_tokens,
            "top_project":         top_project["project__slug"] if top_project else None,
        }

    def get_conversation_metrics(self, conversation_id: int) -> dict:
        """
        Tek bir konuşmanın detaylı metrikleri.
        """
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return {}

        messages = conv.messages.all()
        user_msgs = messages.filter(role="user")
        ai_msgs   = messages.filter(role="assistant")

        avg_processing = ai_msgs.aggregate(
            avg=Avg("processing_time")
        )["avg"] or 0
        total_tokens = ai_msgs.aggregate(
            total=Sum("tokens_used")
        )["total"] or 0

        return {
            "conversation_id":  conversation_id,
            "total_messages":   messages.count(),
            "user_messages":    user_msgs.count(),
            "ai_messages":      ai_msgs.count(),
            "total_tokens":     total_tokens,
            "avg_processing_s": round(avg_processing, 2),
            "started_at":       conv.created_at.isoformat(),
            "last_message_at":  conv.updated_at.isoformat(),
        }

    def format_for_context(self, project_slug: str) -> str:
        """
        AI engine bağlamına eklenecek metrik özeti üretir.
        context_manager.get_enriched_context tarafından çağrılır.
        """
        stats = self.get_project_stats(project_slug, days=7)
        return (
            f"[Son 7 gün — {project_slug}] "
            f"Konuşma: {stats['conversations']}, "
            f"Mesaj: {stats['messages']}, "
            f"Rapor: {stats['reports']}, "
            f"Ort. token: {stats['avg_tokens']}"
        )

    def _empty_stats(self) -> dict:
        return {
            "project_slug": "", "period_days": 0,
            "conversations": 0, "messages": 0, "reports": 0,
            "avg_tokens": 0, "total_tokens": 0,
            "active_days": 0, "msgs_per_conv": 0,
        }

    def analyze(self, data: dict, project: str) -> dict:
        """BaseMEHLRModule uyumu."""
        return self.get_project_stats(project, days=data.get("days", 30))
