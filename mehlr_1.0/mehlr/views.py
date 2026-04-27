"""
mehlr_1.0 — Views
Yeni AI engine entegrasyonu: preprocess_query, validate_response, get_enriched_context, PROJECT_PROMPTS.
"""
import json
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from mehlr.auth import api_key_or_login_required
from mehlr.models import Project, Conversation, Message, AnalysisReport
from mehlr.services.ai_engine import generate_response, query_ai
from mehlr.services.context_manager import get_enriched_context, get_project_context
from mehlr.services.query_processor import preprocess_query, validate_response
from mehlr.services.report_generator import generate as generate_report_legacy, save_report
from mehlr.prompts.project_prompts import PROJECT_PROMPTS
from mehlr.utils import sanitize_user_input, markdown_to_html


def _project_meta(slug):
    """PROJECT_PROMPTS'tan meta döner; dressifye_saas / dressifye-saas uyumlu."""
    if not slug:
        return {}
    return PROJECT_PROMPTS.get(slug) or PROJECT_PROMPTS.get(slug.replace("_", "-")) or {}


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@login_required
def dashboard(request):
    projects = Project.objects.filter(is_active=True).order_by("name")
    recent_conversations = (
        Conversation.objects.filter(user=request.user, is_active=True)
        .select_related("project")
        .order_by("-updated_at")[:10]
    )
    recent_reports = (
        AnalysisReport.objects.filter(is_active=True)
        .select_related("project")
        .order_by("-created_at")[:5]
    )

    projects_with_meta = []
    for p in projects:
        meta = _project_meta(p.slug)
        projects_with_meta.append({
            "project": p,
            "capabilities": meta.get("capabilities", []),
            "domain": meta.get("domain", ""),
            "display_name": meta.get("display_name", p.name),
        })

    total_conversations = Conversation.objects.filter(user=request.user).count()
    total_messages = Message.objects.filter(conversation__user=request.user).count()

    return render(request, "mehlr/dashboard.html", {
        "projects_with_meta": projects_with_meta,
        "projects": projects,
        "recent_conversations": recent_conversations,
        "recent_reports": recent_reports,
        "total_projects": projects.count(),
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_reports": AnalysisReport.objects.filter(is_active=True).count(),
        "page_title": "mehlr_1.0 Dashboard",
    })


# ─────────────────────────────────────────────
# CHAT — Ana görünüm
# ─────────────────────────────────────────────
@login_required
def chat(request, project_slug=None):
    projects = Project.objects.filter(is_active=True).order_by("name")
    active_project = None
    conversation = None

    if project_slug:
        active_project = get_object_or_404(Project, slug=project_slug, is_active=True)
        conversation_id = request.GET.get("conversation_id")
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                pk=conversation_id,
                user=request.user,
            )

    project_meta = _project_meta(project_slug) if project_slug else {}

    selector_active = (project_slug or "") or (conversation.project.slug if conversation and getattr(conversation, "project", None) and conversation.project else "")

    return render(request, "mehlr/chat.html", {
        "projects": projects,
        "active_project": active_project,
        "conversation": conversation,
        "project_meta": project_meta,
        "selector_active_slug": selector_active,
        "page_title": f"Sohbet — {project_meta.get('display_name', 'mehlr_1.0')}",
    })


# ─────────────────────────────────────────────
# CHAT — Mesaj gönderme (HTMX veya JSON)
# ─────────────────────────────────────────────
@api_key_or_login_required
@require_http_methods(["POST"])
def send_message(request):
    """
    POST: project_slug, message, conversation_id (opsiyonel)
    HTMX: chat_message.html partial döner.
    JSON: content, conversation_id, project_slug.
    """
    try:
        data = json.loads(request.body) if request.content_type == "application/json" else request.POST
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    user_message = (data.get("message") or data.get("content") or "").strip()
    user_message = sanitize_user_input(user_message)
    project_slug = (data.get("project_slug") or data.get("project") or "").strip() or None
    conversation_id = data.get("conversation_id")

    if not user_message:
        if request.headers.get("HX-Request"):
            return HttpResponseBadRequest("Mesaj boş olamaz.")
        return JsonResponse({"status": "error", "message": "Mesaj boş olamaz."}, status=400)

    processed = preprocess_query(user_message)
    if not processed["query"]:
        if request.headers.get("HX-Request"):
            return HttpResponseBadRequest("Geçersiz sorgu.")
        return JsonResponse({"status": "error", "message": "Geçersiz sorgu."}, status=400)

    project = None
    if project_slug:
        project = Project.objects.filter(slug=project_slug, is_active=True).first()

    if conversation_id:
        conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
    else:
        conversation = Conversation.objects.create(
            user=request.user,
            project=project,
            title=processed["query"][:80],
            is_active=True,
        )

    Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=processed["query"],
    )

    start = time.time()
    response_text, tokens_used, elapsed, error = generate_response(
        processed["query"],
        conversation,
        project_slug or "general",
    )
    elapsed = round(time.time() - start, 2)

    quality = validate_response(response_text) if response_text else {"score": 0, "issues": []}

    if error:
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=f"[Hata] {error}",
            tokens_used=0,
            processing_time=elapsed,
        )
        if request.headers.get("HX-Request"):
            return render(request, "mehlr/components/chat_message.html", {
                "message": conversation.messages.order_by("-created_at").first(),
                "error": error,
                "hx_swap": True,
            })
        return JsonResponse({"status": "error", "message": error}, status=500)

    assistant_msg = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=response_text,
        tokens_used=tokens_used,
        processing_time=elapsed,
    )

    if not conversation.title or conversation.title == processed["query"][:80]:
        conversation.title = processed["query"][:80]
        conversation.save(update_fields=["title", "updated_at"])

    if request.headers.get("HX-Request"):
        return render(request, "mehlr/components/chat_message.html", {
            "message": assistant_msg,
            "conversation": conversation,
            "quality_score": quality.get("score"),
            "is_analysis": processed.get("is_analysis", False),
            "warnings": processed.get("warnings", []),
            "elapsed": elapsed,
            "tokens_used": tokens_used,
            "error": None,
            "hx_swap": True,
            "rendered_content": markdown_to_html(response_text),
        })

    content_html = markdown_to_html(response_text)
    return JsonResponse({
        "status": "success",
        "conversation_id": conversation.pk,
        "message_id": assistant_msg.pk,
        "content": response_text,
        "content_html": content_html,
        "tokens_used": tokens_used,
        "processing_time": elapsed,
        "quality_score": quality.get("score"),
    })


# ─────────────────────────────────────────────
# RAPOR LİSTESİ
# ─────────────────────────────────────────────
@login_required
def report_list(request):
    project_slug = request.GET.get("project", "")
    reports = (
        AnalysisReport.objects.filter(is_active=True)
        .select_related("project")
        .order_by("-created_at")
    )
    if project_slug:
        reports = reports.filter(project__slug=project_slug)
    projects = Project.objects.filter(is_active=True).order_by("name")

    return render(request, "mehlr/report_list.html", {
        "reports": reports,
        "projects": projects,
        "active_project_slug": project_slug,
        "page_title": "Raporlar",
    })


# ─────────────────────────────────────────────
# RAPOR DETAY
# ─────────────────────────────────────────────
@login_required
def report_detail(request, report_id):
    report = get_object_or_404(AnalysisReport, pk=report_id, is_active=True)
    project_meta = _project_meta(report.project.slug if report.project else "")

    return render(request, "mehlr/report_detail.html", {
        "report": report,
        "project_meta": project_meta,
        "page_title": f"Rapor — {report.title}",
    })


# ─────────────────────────────────────────────
# RAPOR OLUŞTUR — POST endpoint
# ─────────────────────────────────────────────
@login_required
@require_POST
def create_report(request):
    from mehlr.services.report_generator import generate_report

    project_slug = (request.POST.get("project_slug") or request.POST.get("project") or "").strip()
    report_type = (request.POST.get("report_type") or "summary").strip()
    custom_query = (request.POST.get("query") or "").strip()

    if not project_slug:
        if request.headers.get("HX-Request"):
            return HttpResponseBadRequest("Proje gerekli.")
        return JsonResponse({"status": "error", "message": "Proje gerekli."}, status=400)

    project = get_object_or_404(Project, slug=project_slug, is_active=True)

    try:
        report = generate_report(
            project=project,
            report_type=report_type,
            custom_query=custom_query,
            user=request.user,
        )
    except Exception as e:
        if request.headers.get("HX-Request"):
            return HttpResponseBadRequest(str(e))
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    if request.headers.get("HX-Request"):
        return render(request, "mehlr/components/report_card.html", {
            "report": report,
            "just_created": True,
        })

    return redirect("mehlr:report_detail", report_id=report.pk)


# ─────────────────────────────────────────────
# API — Proje bağlamı (HTMX project selector)
# ─────────────────────────────────────────────
@login_required
def project_context_api(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug, is_active=True)
    meta = _project_meta(project_slug)

    return JsonResponse({
        "slug": project_slug,
        "display_name": meta.get("display_name", project.name),
        "domain": meta.get("domain", ""),
        "capabilities": meta.get("capabilities", []),
        "report_types": meta.get("analytics_config", {}).get("report_types", []),
        "description": meta.get("description", ""),
    })


# ─────────────────────────────────────────────
# API Analyze — Stateless analiz (Dressifye, EvidenceHome vb.)
# ─────────────────────────────────────────────
@api_key_or_login_required
@csrf_exempt
@require_POST
@require_http_methods(["POST"])
def api_analyze(request):
    """
    Stateless analiz endpoint.
    Body: {"project": "dressifye", "prompt": "...", "context": {...}}
    X-API-Key: INTER_SERVICE_API_KEY ile yetkilendirme.
    """
    try:
        data = json.loads(request.body) if request.content_type == "application/json" else {}
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"status": "error", "message": "Geçersiz JSON"}, status=400)

    project = (data.get("project") or "").strip() or "general"
    prompt = (data.get("prompt") or "").strip()
    context = data.get("context") or {}

    if not prompt:
        return JsonResponse({"status": "error", "message": "prompt gerekli"}, status=400)

    # Bağlamı prompt'a ekle
    if context:
        context_str = json.dumps(context, ensure_ascii=False)
        user_message = f"Bağlam:\n{context_str}\n\nİstek:\n{prompt}"
    else:
        user_message = prompt

    result = query_ai(
        project_key=project,
        user_message=user_message,
        conversation_history=[],
    )

    if result.get("error"):
        return JsonResponse(
            {"status": "error", "message": result["error"]},
            status=500,
        )

    return JsonResponse({
        "status": "success",
        "response": result["response"],
        "tokens_used": result.get("tokens_used", 0),
    })


# ─────────────────────────────────────────────
# Eski API endpoint'leri (geriye dönük uyumluluk)
# ─────────────────────────────────────────────
@csrf_exempt
@require_POST
def api_chat_send(request):
    # Inter-service API key kontrolü
    if not request.user.is_authenticated:
        api_key = request.headers.get("X-API-Key", "")
        inter_service_secret = getattr(settings, "INTER_SERVICE_API_KEY", "")
        if not inter_service_secret or api_key != inter_service_secret:
            return JsonResponse({"error": "Unauthorized"}, status=401)

    return send_message(request)


@login_required
@require_http_methods(["POST"])
def api_chat_new(request):
    project_slug = request.POST.get("project") or request.GET.get("project")
    project = Project.objects.filter(slug=project_slug, is_active=True).first() if project_slug else None
    conv = Conversation.objects.create(
        user=request.user,
        project=project,
        title="",
        is_active=True,
    )
    return JsonResponse({
        "status": "success",
        "conversation_id": conv.pk,
        "redirect": f"/mehlr/chat/{conv.pk}/" if conv.pk else "/mehlr/chat/",
    })


@login_required
@require_http_methods(["GET"])
def api_projects(request):
    projects = list(
        Project.objects.filter(is_active=True).values("id", "name", "slug", "description", "project_type")
    )
    return JsonResponse({"status": "success", "projects": projects})


@login_required
@require_http_methods(["POST"])
def api_report_generate(request):
    project_slug = request.POST.get("project")
    report_type = request.POST.get("report_type", "weekly")
    conversation_id = request.POST.get("conversation_id")
    if not project_slug:
        return JsonResponse({"status": "error", "message": "Proje gerekli."}, status=400)
    project = get_object_or_404(Project, slug=project_slug, is_active=True)
    conv = None
    if conversation_id:
        conv = Conversation.objects.filter(pk=conversation_id, user=request.user).first()
    report_data = generate_report_legacy(project, report_type, conversation=conv)
    if not report_data:
        return JsonResponse({"status": "error", "message": "Rapor üretilemedi."}, status=500)
    report = save_report(report_data)
    return JsonResponse({
        "status": "success",
        "report_id": report.pk,
        "title": report.title,
        "redirect": f"/mehlr/reports/{report.pk}/",
    })


@login_required
@require_http_methods(["GET"])
def api_stats(request):
    user = request.user
    return JsonResponse({
        "status": "success",
        "total_conversations": Conversation.objects.filter(user=user).count(),
        "total_messages": Message.objects.filter(conversation__user=user).count(),
        "total_reports": AnalysisReport.objects.filter(is_active=True).count(),
        "active_projects": Project.objects.filter(is_active=True).count(),
    })


# ─────────────────────────────────────────────
# Chat by conversation_id (mevcut URL uyumu)
# ─────────────────────────────────────────────
@login_required
def chat_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
    projects = Project.objects.filter(is_active=True).order_by("name")
    project_meta = _project_meta(conversation.project.slug if conversation.project else "")

    return render(request, "mehlr/chat.html", {
        "projects": projects,
        "active_project": conversation.project,
        "conversation": conversation,
        "project_meta": project_meta,
        "selector_active_slug": conversation.project.slug if conversation.project else "",
        "page_title": "Sohbet",
    })
