"""
MEHLR view'ları — sayfa ve API endpoint'leri.
"""
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

from mehlr.models import Project, Conversation, Message, AnalysisReport
from mehlr.services.ai_engine import generate_response
from mehlr.services.report_generator import generate as generate_report, save_report
from mehlr.utils import sanitize_user_input, markdown_to_html


# ---------- Sayfa view'ları ----------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'mehlr/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['projects'] = Project.objects.filter(is_active=True)
        ctx['recent_conversations'] = (
            Conversation.objects.filter(user=self.request.user, is_active=True)
            .select_related('project')[:10]
        )
        ctx['total_conversations'] = Conversation.objects.filter(user=self.request.user).count()
        ctx['total_messages'] = Message.objects.filter(
            conversation__user=self.request.user
        ).count()
        ctx['total_reports'] = AnalysisReport.objects.filter(is_active=True).count()
        return ctx


class ChatView(LoginRequiredMixin, TemplateView):
    template_name = 'mehlr/chat.html'

    def get(self, request, *args, **kwargs):
        conversation_id = kwargs.get('conversation_id')
        if conversation_id:
            conv = get_object_or_404(
                Conversation,
                pk=conversation_id,
                user=request.user,
            )
            return self.render_to_response(self.get_context_data(conversation=conv))
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['projects'] = Project.objects.filter(is_active=True)
        ctx['conversation'] = kwargs.get('conversation')
        return ctx


class ReportListView(LoginRequiredMixin, ListView):
    model = AnalysisReport
    template_name = 'mehlr/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        return AnalysisReport.objects.filter(is_active=True).select_related('project').order_by('-created_at')


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = AnalysisReport
    template_name = 'mehlr/report_detail.html'
    context_object_name = 'report'


# ---------- API view'ları ----------

@login_required
@require_http_methods(["POST"])
def api_chat_send(request):
    """Mesaj gönder, AI yanıtı al. JSON veya HTMX fragment döner."""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except (json.JSONDecodeError, ValueError):
        data = request.POST
    content = data.get('content', '').strip()
    conversation_id = data.get('conversation_id')
    project_slug = data.get('project_slug') or None

    content = sanitize_user_input(content)
    if not content:
        return JsonResponse({'status': 'error', 'message': 'Mesaj boş olamaz.'}, status=400)

    if conversation_id:
        conv = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
    else:
        conv = Conversation.objects.create(
            user=request.user,
            project=Project.objects.filter(slug=project_slug).first() if project_slug else None,
            title=content[:80],
            is_active=True,
        )

    # Kullanıcı mesajını kaydet
    Message.objects.create(
        conversation=conv,
        role=Message.Role.USER,
        content=content,
    )

    # AI yanıtı üret
    project_slug = project_slug or (conv.project.slug if conv.project else None)
    response_text, tokens, elapsed, err = generate_response(content, conv, project_slug)

    if err:
        Message.objects.create(
            conversation=conv,
            role=Message.Role.ASSISTANT,
            content=f"[Hata] {err}",
            tokens_used=0,
            processing_time=elapsed,
        )
        return JsonResponse({
            'status': 'error',
            'message': err,
            'conversation_id': conv.pk,
        }, status=500)

    # MEHLR yanıtını kaydet
    assistant_msg = Message.objects.create(
        conversation=conv,
        role=Message.Role.ASSISTANT,
        content=response_text,
        tokens_used=tokens,
        processing_time=elapsed,
    )

    # Sohbet başlığını ilk mesajdan güncelle (boşsa)
    if not conv.title or conv.title == content[:80]:
        conv.title = content[:80]
        conv.save(update_fields=['title', 'updated_at'])

    from django.template.loader import render_to_string
    content_html = render_to_string('mehlr/components/chat_message.html', {
        'message': assistant_msg,
        'rendered_content': markdown_to_html(response_text),
    })
    if request.headers.get('HX-Request'):
        return JsonResponse({
            'status': 'success',
            'conversation_id': conv.pk,
            'message_id': assistant_msg.pk,
            'content': response_text,
            'content_html': content_html,
            'tokens_used': tokens,
        })
    return JsonResponse({
        'status': 'success',
        'conversation_id': conv.pk,
        'message_id': assistant_msg.pk,
        'content': response_text,
        'content_html': content_html,
        'tokens_used': tokens,
        'processing_time': round(elapsed, 2),
    })


@login_required
@require_http_methods(["POST"])
def api_chat_new(request):
    """Yeni sohbet başlat."""
    project_slug = request.POST.get('project') or request.GET.get('project')
    project = Project.objects.filter(slug=project_slug, is_active=True).first() if project_slug else None
    conv = Conversation.objects.create(
        user=request.user,
        project=project,
        title='',
        is_active=True,
    )
    return JsonResponse({'status': 'success', 'conversation_id': conv.pk, 'redirect': f'/mehlr/chat/{conv.pk}/'})


@login_required
@require_http_methods(["GET"])
def api_projects(request):
    """Proje listesi (JSON)."""
    projects = list(
        Project.objects.filter(is_active=True).values('id', 'name', 'slug', 'description', 'project_type')
    )
    return JsonResponse({'status': 'success', 'projects': projects})


@login_required
@require_http_methods(["POST"])
def api_report_generate(request):
    """Rapor üret ve kaydet."""
    project_slug = request.POST.get('project')
    report_type = request.POST.get('report_type', 'weekly')
    conversation_id = request.POST.get('conversation_id')
    if not project_slug:
        return JsonResponse({'status': 'error', 'message': 'Proje gerekli.'}, status=400)
    project = get_object_or_404(Project, slug=project_slug, is_active=True)
    conv = None
    if conversation_id:
        conv = Conversation.objects.filter(pk=conversation_id, user=request.user).first()
    report_data = generate_report(project, report_type, conversation=conv)
    if not report_data:
        return JsonResponse({'status': 'error', 'message': 'Rapor üretilemedi.'}, status=500)
    report = save_report(report_data)
    return JsonResponse({
        'status': 'success',
        'report_id': report.pk,
        'title': report.title,
        'redirect': f'/mehlr/reports/{report.pk}/',
    })


@login_required
@require_http_methods(["GET"])
def api_stats(request):
    """Dashboard istatistikleri."""
    user = request.user
    return JsonResponse({
        'status': 'success',
        'total_conversations': Conversation.objects.filter(user=user).count(),
        'total_messages': Message.objects.filter(conversation__user=user).count(),
        'total_reports': AnalysisReport.objects.filter(is_active=True).count(),
        'active_projects': Project.objects.filter(is_active=True).count(),
    })
