"""
Veri analizi modülü — KPI, trend, anomali tespiti.
"""
from mehlr.modules.base_module import BaseMEHLRModule


class AnalyticsModule(BaseMEHLRModule):
    module_name = "analytics"
    version = "1.0"
    description = "KPI hesaplama, trend analizi, anomali tespiti"
    supported_projects = [
        "looopone", "worktrackere", "garment_core",
        "hairinfinitye", "edulingoe", "stylecoree", "drivetrackere",
    ]

    def analyze(self, data: dict, project: str) -> dict:
        """
        Ham veriyi analiz eder. Gerçek proje API'leri bağlandığında doldurulacak.
        """
        result = {
            "project": project,
            "summary": "",
            "kpis": {},
            "trends": [],
            "anomalies": [],
        }
        if not data:
            result["summary"] = "Veri bulunamadı. Proje entegrasyonu sonrası KPI ve trendler hesaplanacak."
            return result
        result["summary"] = f"{project} için {len(data)} kayıt incelendi."
        result["kpis"] = data.get("kpis", {})
        result["trends"] = data.get("trends", [])
        result["anomalies"] = data.get("anomalies", [])
        return result

    def recommend(self, analysis_result: dict) -> list:
        """Anomali veya düşük KPI'lara göre öneri üretir."""
        recs = []
        for a in analysis_result.get("anomalies", []):
            recs.append({"priority": "high", "message": f"Anomali: {a}"})
        return recs

    def report(self, analysis_result: dict, format: str = "markdown") -> str:
        lines = [f"# {analysis_result.get('project', 'Proje')} Analiz Özeti", ""]
        lines.append(analysis_result.get("summary", ""))
        if analysis_result.get("kpis"):
            lines.append("\n## KPI'lar")
            for k, v in analysis_result["kpis"].items():
                lines.append(f"- **{k}**: {v}")
        if analysis_result.get("trends"):
            lines.append("\n## Trendler")
            for t in analysis_result["trends"]:
                lines.append(f"- {t}")
        if analysis_result.get("anomalies"):
            lines.append("\n## Anomaliler")
            for a in analysis_result["anomalies"]:
                lines.append(f"- ⚠️ {a}")
        return "\n".join(lines)
