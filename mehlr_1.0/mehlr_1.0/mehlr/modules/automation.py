"""
Otomasyon modülü — tetikleme kuralları, n8n webhook (ileride).
"""
from mehlr.modules.base_module import BaseMEHLRModule


class AutomationModule(BaseMEHLRModule):
    module_name = "automation"
    version = "1.0"
    description = "Tetikleme kuralları, bildirim altyapısı"
    supported_projects = [
        "looopone", "worktrackere", "dressifye_saas",
        "hairinfinitye", "edulingoe", "stylecoree", "drivetrackere",
    ]

    def analyze(self, data: dict, project: str) -> dict:
        """Tetikleme koşullarını değerlendirir."""
        return {
            "project": project,
            "triggers": data.get("triggers", []),
            "actions_suggested": [],
        }

    def recommend(self, analysis_result: dict) -> list:
        """Tetiklenmesi önerilen aksiyonlar."""
        return [
            {"priority": "normal", "message": msg}
            for msg in analysis_result.get("actions_suggested", [])
        ]

    def report(self, analysis_result: dict, format: str = "markdown") -> str:
        lines = ["# Otomasyon Özeti", ""]
        for t in analysis_result.get("triggers", []):
            lines.append(f"- Tetikleyici: {t}")
        for a in analysis_result.get("actions_suggested", []):
            lines.append(f"- Önerilen aksiyon: {a}")
        return "\n".join(lines) if lines else "Henüz tetikleyici tanımlanmadı."
