"""
MEHLR 1.0 — Recommendations Module
Geçmiş konuşma ve analitik veriye dayalı öneri üretimi.
"""
import logging
from django.db.models import Count
from mehlr.modules.base_module import BaseMEHLRModule
from mehlr.models import Project, Conversation, Message, AnalysisReport
from mehlr.prompts.project_prompts import PROJECT_PROMPTS

logger = logging.getLogger("mehlr")


class RecommendationsModule(BaseMEHLRModule):

    module_name = "recommendations"
    version = "1.0"

    # Sorgu niyeti → capability eşleştirmesi
    INTENT_CAPABILITY_MAP = {
        "analiz":        ["analytics", "evidence_analysis", "sensor_data_analysis"],
        "rapor":         ["transparency_reporting", "municipal_reporting", "performance_reporting"],
        "öneri":         ["outfit_recommendation", "care_routine", "product_suggestion"],
        "tahmin":        ["failure_prediction", "fill_level_prediction", "trend_forecasting"],
        "optimizasyon":  ["route_optimization", "workload_balancing", "fuel_efficiency"],
        "sınıflandır":   ["garment_classification", "document_classification"],
    }

    def suggest_capabilities(self, project_slug: str, user_query: str) -> list:
        """
        Kullanıcı sorgusuna göre ilgili capability listesi önerir.
        Döner: [{"capability": str, "reason": str}]
        """
        meta = PROJECT_PROMPTS.get(project_slug, {})
        available = meta.get("capabilities", [])
        query_lower = user_query.lower()
        suggestions = []

        for keyword, caps in self.INTENT_CAPABILITY_MAP.items():
            if keyword in query_lower:
                matched = [c for c in caps if c in available]
                for cap in matched:
                    suggestions.append({
                        "capability": cap,
                        "reason": f"'{keyword}' anahtar kelimesi tespit edildi",
                    })

        # Tekrar kaldır
        seen = set()
        unique = []
        for s in suggestions:
            if s["capability"] not in seen:
                seen.add(s["capability"])
                unique.append(s)

        logger.debug(f"RecommendationsModule: {len(unique)} suggestion — {project_slug}")
        return unique

    def suggest_report_type(self, user_query: str, project_slug: str) -> str:
        """
        Kullanıcı sorgusundan en uygun rapor tipini tahmin eder.
        Döner: 'summary' | 'trend_report' | 'audit_report' | 'performance' | 'custom'
        """
        q = user_query.lower()
        if any(k in q for k in ["trend", "yönelim", "gelecek", "tahmin"]):
            return "trend_report"
        if any(k in q for k in ["denetim", "audit", "uyumluluk", "risk"]):
            return "audit_report"
        if any(k in q for k in ["performans", "kpi", "başarı", "verimlilik"]):
            return "performance"
        if any(k in q for k in ["özet", "genel", "durum", "summary"]):
            return "summary"
        return "custom"

    def suggest_follow_up_questions(self, project_slug: str, last_message: str) -> list:
        """
        Son AI mesajına göre takip sorusu önerileri üretir.
        Döner: [str, str, str]
        """
        meta = PROJECT_PROMPTS.get(project_slug, {})
        caps = meta.get("capabilities", [])

        templates = {
            "sensor_data_analysis":   "Son 24 saatteki sensör verilerini analiz edebilir misin?",
            "route_optimization":     "Mevcut rota için optimizasyon önerileri neler?",
            "outfit_recommendation":  "Bu kombinle uyumlu başka parçalar önerir misin?",
            "evidence_analysis":      "Bu belgenin güvenilirlik skorunu hesaplar mısın?",
            "maintenance_scheduling": "Yaklaşan bakım tarihlerini listeler misin?",
            "lesson_planning":        "Bu konuyla ilgili alıştırma önerir misin?",
            "trend_forecasting":      "Önümüzdeki ay için trend tahmini yapabilir misin?",
            "anomaly_detection":      "Son dönemde tespit edilen anomaliler var mı?",
        }

        suggestions = []
        for cap in caps:
            if cap in templates:
                suggestions.append(templates[cap])
            if len(suggestions) >= 3:
                break

        # Yeterliyse 3 tane, değilse genel sorular ekle
        general = [
            "Bu konuda daha detaylı rapor oluşturabilir misin?",
            "Özet bilgiyi tablo formatında verir misin?",
            "Bu analizi geçen ay ile karşılaştırır mısın?",
        ]
        while len(suggestions) < 3:
            suggestions.append(general[len(suggestions) % len(general)])

        return suggestions[:3]

    def get_similar_conversations(self, project_slug: str, limit: int = 3) -> list:
        """
        Aynı projedeki son konuşmaları döner.
        Takip önerisi veya bağlam için kullanılır.
        """
        convs = (
            Conversation.objects.filter(
                project__slug=project_slug
            )
            .order_by("-updated_at")[:limit]
            .values("id", "title", "updated_at")
        )
        return list(convs)

    def analyze(self, data: dict, project: str) -> dict:
        """BaseMEHLRModule uyumu."""
        return {"suggestions": self.suggest_capabilities(project, data.get("query", ""))}
