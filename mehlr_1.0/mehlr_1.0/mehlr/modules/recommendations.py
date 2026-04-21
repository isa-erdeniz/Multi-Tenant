"""
Öneri motoru modülü — veriye dayalı aksiyon önerileri.
"""
from mehlr.modules.base_module import BaseMEHLRModule


class RecommendationModule(BaseMEHLRModule):
    module_name = "recommendations"
    version = "1.0"
    description = "Veriye dayalı aksiyon önerileri, önceliklendirme"
    supported_projects = [
        "looopone", "worktrackere", "garment_core",
        "hairinfinitye", "edulingoe", "stylecoree", "drivetrackere",
    ]

    def analyze(self, data: dict, project: str) -> dict:
        """Öneri için gerekli veriyi hazırlar."""
        return {
            "project": project,
            "data": data,
            "suggestions": [],
        }

    def recommend(self, analysis_result: dict) -> list:
        """Öncelik sıralı (acil / normal / düşük) öneri listesi."""
        suggestions = analysis_result.get("suggestions", [])
        if not suggestions and analysis_result.get("data"):
            return [
                {"priority": "normal", "message": "Veri entegrasyonu tamamlandığında somut öneriler üretilecek."}
            ]
        return [
            {
                "priority": s.get("priority", "normal"),
                "message": s.get("message", str(s)),
            }
            for s in suggestions
        ]

    def report(self, analysis_result: dict, format: str = "markdown") -> str:
        recs = self.recommend(analysis_result)
        lines = ["# Öneri Raporu", ""]
        for r in recs:
            p = r.get("priority", "normal")
            badge = "🔴" if p == "high" else "🟡" if p == "normal" else "🟢"
            lines.append(f"- {badge} {r.get('message', '')}")
        return "\n".join(lines)
