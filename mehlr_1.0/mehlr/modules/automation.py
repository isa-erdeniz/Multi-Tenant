"""
MEHLR 1.0 — Automation Module
Kural tabanlı otomasyon tetikleyicileri.
Celery hazır olduğunda task'larla entegre edilecek.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from mehlr.modules.base_module import BaseMEHLRModule
from mehlr.models import Project, Conversation, AnalysisReport

logger = logging.getLogger("mehlr")


class AutomationModule(BaseMEHLRModule):

    module_name = "automation"
    version = "1.0"

    # Otomasyon kuralları: {rule_id: {condition_fn, action_fn, description}}
    _rules: dict = {}

    def register_rule(self, rule_id: str, condition_fn, action_fn, description: str = ""):
        """
        Dinamik kural kaydı.
        condition_fn(context) → bool
        action_fn(context) → dict
        """
        self._rules[rule_id] = {
            "condition": condition_fn,
            "action": action_fn,
            "description": description,
            "enabled": True,
        }
        logger.info(f"AutomationModule: rule registered — {rule_id}")

    def evaluate_rules(self, context: dict) -> list:
        """
        Tüm kayıtlı kuralları değerlendir, tetiklenen aksiyonları döner.
        Döner: [{"rule_id": str, "action_result": dict}]
        """
        triggered = []
        for rule_id, rule in self._rules.items():
            if not rule["enabled"]:
                continue
            try:
                if rule["condition"](context):
                    result = rule["action"](context)
                    triggered.append({"rule_id": rule_id, "action_result": result})
                    logger.info(f"AutomationModule: rule triggered — {rule_id}")
            except Exception as e:
                logger.error(f"AutomationModule: rule error — {rule_id}: {e}")
        return triggered

    # ─────────────────────────────────────────
    # HAZIR KURALAR
    # ─────────────────────────────────────────
    def check_idle_conversations(self, hours: int = 24) -> list:
        """
        N saatten uzun süredir mesaj alınmayan konuşmaları döner.
        Celery ile otomatik bildirim için kullanılacak.
        """
        cutoff = timezone.now() - timedelta(hours=hours)
        idle = Conversation.objects.filter(
            updated_at__lt=cutoff,
            messages__isnull=False,
        ).distinct().values("id", "title", "project__slug", "updated_at")
        result = list(idle[:50])
        logger.debug(f"AutomationModule: {len(result)} idle conversations (>{hours}h)")
        return result

    def check_report_due(self, project_slug: str, days: int = 7) -> bool:
        """
        Son N günde rapor üretilmemişse True döner.
        Periyodik rapor otomasyonu için.
        """
        since = timezone.now() - timedelta(days=days)
        recent = AnalysisReport.objects.filter(
            project__slug=project_slug,
            created_at__gte=since,
        ).exists()
        return not recent

    def get_pending_automations(self, project_slug: str) -> list:
        """
        Proje için bekleyen otomasyon aksiyonlarını döner.
        Dashboard'da gösterim için.
        """
        pending = []

        if self.check_report_due(project_slug, days=7):
            pending.append({
                "type": "report_due",
                "message": f"{project_slug} için haftalık rapor henüz oluşturulmadı.",
                "priority": "medium",
                "action_url": f"/mehlr/reports/create/?project={project_slug}&type=summary",
            })

        idle = self.check_idle_conversations(hours=48)
        project_idle = [c for c in idle if c.get("project__slug") == project_slug]
        if project_idle:
            pending.append({
                "type": "idle_conversations",
                "message": f"{len(project_idle)} konuşma 48 saattir aktif değil.",
                "priority": "low",
                "count": len(project_idle),
            })

        return pending

    def trigger_post_report(self, report_id: int) -> dict:
        """
        Rapor oluşturulduktan sonra tetiklenecek aksiyonlar.
        Şimdilik log + metadata dönüyor.
        Celery hazır olduğunda: send_notification.delay(report_id)
        """
        try:
            report = AnalysisReport.objects.get(id=report_id)
            logger.info(f"AutomationModule: post-report trigger — report #{report_id}")
            return {
                "triggered": True,
                "report_id": report_id,
                "project":   report.project.slug if report.project else None,
                "next_actions": ["notify_user", "update_dashboard"],
            }
        except AnalysisReport.DoesNotExist:
            logger.warning(f"AutomationModule: report not found — #{report_id}")
            return {"triggered": False, "error": "Report not found"}

    def analyze(self, data: dict, project: str) -> dict:
        """BaseMEHLRModule uyumu."""
        return {"pending": self.get_pending_automations(project)}
