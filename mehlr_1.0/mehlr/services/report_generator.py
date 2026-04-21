"""
Rapor üretim servisi — MEHLR analiz raporları oluşturur ve kaydeder.
Analiz raporu üretimi: Gemini AI + proje bağlamı (generate_report).
"""
import time
from mehlr.models import Project, AnalysisReport, Conversation
from mehlr.services.context_manager import get_project_context


# Rapor tipi → Gemini'ye gönderilecek soru şablonları
REPORT_TEMPLATES = {
    "summary": (
        "{project_name} projesi için genel durum özeti raporu hazırla. "
        "Temel metrikler, son gelişmeler ve öneriler içersin."
    ),
    "trend_report": (
        "{project_name} için trend analizi yap. "
        "Son dönem verileri, yönelimler ve gelecek tahminlerini içersin."
    ),
    "audit_report": (
        "{project_name} için denetim raporu oluştur. "
        "Uyumluluk durumu, riskler ve aksiyon önerileri içersin."
    ),
    "performance": (
        "{project_name} için performans raporu hazırla. "
        "KPI'lar, başarı oranları ve iyileştirme alanlarını içersin."
    ),
    "custom": "{custom_query}",
}


def generate_report(
    project: Project,
    report_type: str = "summary",
    custom_query: str = "",
    user=None,
) -> AnalysisReport:
    """
    Gemini ile rapor üret ve AnalysisReport modeline kaydet.
    Mevcut model alanları kullanılır; ek bilgi data_snapshot'ta.
    Döner: AnalysisReport instance
    """
    from mehlr.services.ai_engine import query_ai
    from mehlr.prompts.project_prompts import PROJECT_PROMPTS

    project_meta = PROJECT_PROMPTS.get(project.slug) or PROJECT_PROMPTS.get(project.slug.replace("_", "-")) or {}
    display_name = project_meta.get("display_name", project.name)

    template = REPORT_TEMPLATES.get(report_type, REPORT_TEMPLATES["summary"])
    if report_type == "custom" and custom_query:
        query = custom_query
    else:
        query = template.format(
            project_name=display_name,
            custom_query=custom_query,
        )

    start = time.time()
    result = query_ai(
        project_key=project.slug,
        user_message=query,
        conversation_history=[],
        is_analysis=True,
    )
    elapsed = round(time.time() - start, 2)

    report_content = result.get("response", "Rapor üretilemedi.")
    confidence = result.get("confidence", "BELİRTİLMEDİ")
    tokens_used = result.get("tokens_used", 0)
    error = result.get("error")

    report_type_label = _report_type_label(report_type)
    title = f"{display_name} — {report_type_label}"

    report = AnalysisReport.objects.create(
        project=project,
        title=title,
        report_type="custom",
        content=report_content,
        data_snapshot={
            "query": query,
            "response": report_content,
            "confidence_score": confidence,
            "tokens_used": tokens_used,
            "generation_time": elapsed,
            "has_error": bool(error),
            "error_message": error or "",
            "report_type_label": report_type_label,
            "project_display_name": display_name,
            "model_used": "gemini-2.5-flash",
        },
        generated_by=None,
        is_active=True,
    )
    return report


def _report_type_label(report_type: str) -> str:
    labels = {
        "summary": "Genel Özet",
        "trend_report": "Trend Analizi",
        "audit_report": "Denetim Raporu",
        "performance": "Performans Raporu",
        "custom": "Özel Rapor",
    }
    return labels.get(report_type, "Rapor")


def format_as_markdown(data):
    """
    Sözlük/liste verisini Markdown formatında metne çevirir.
    """
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"**{k}**")
                lines.append(format_as_markdown(v))
            else:
                lines.append(f"- **{k}**: {v}")
        return '\n'.join(lines)
    if isinstance(data, list):
        return '\n'.join(f"- {format_as_markdown(item)}" for item in data)
    return str(data)


def generate(project, report_type, date_range=None, conversation=None):
    """
    Belirtilen proje ve tip için rapor içeriği üretir.
    Gerçek veri çekme ileride proje API'leri ile yapılacak; şimdilik şablon döner.
    """
    if isinstance(project, str):
        try:
            project = Project.objects.get(slug=project, is_active=True)
        except Project.DoesNotExist:
            return None
    context = get_project_context(project.slug if hasattr(project, 'slug') else project)
    title = f"{project.name} — {dict(AnalysisReport.ReportType.choices).get(report_type, report_type)} Rapor"
    data_snapshot = {
        'report_type': report_type,
        'date_range': date_range,
        'project_slug': getattr(project, 'slug', str(project)),
    }
    content = f"# {title}\n\n"
    content += f"**Proje:** {project.name}\n\n"
    content += f"**Rapor tipi:** {report_type}\n\n"
    if date_range:
        content += f"**Tarih aralığı:** {date_range}\n\n"
    content += "Bu rapor MEHLR tarafından üretilmiştir. Detaylı veri entegrasyonu proje API'leri eklendiğinde doldurulacaktır.\n\n"
    content += "---\n*ErdenizTech mehlr_1.0*"
    return {
        'project': project,
        'report_type': report_type,
        'title': title,
        'content': content,
        'data_snapshot': data_snapshot,
        'conversation': conversation,
    }


def save_report(report_data):
    """
    Üretilen rapor verisini AnalysisReport modeline kaydeder.
    """
    if not report_data:
        return None
    report = AnalysisReport.objects.create(
        project=report_data['project'],
        report_type=report_data['report_type'],
        title=report_data['title'],
        content=report_data['content'],
        data_snapshot=report_data.get('data_snapshot', {}),
        generated_by=report_data.get('conversation'),
        is_active=True,
    )
    return report
