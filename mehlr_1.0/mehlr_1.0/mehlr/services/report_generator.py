"""
Rapor üretim servisi — MEHLR analiz raporları oluşturur ve kaydeder.
"""
from mehlr.models import Project, AnalysisReport, Conversation
from mehlr.services.context_manager import get_project_context


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
