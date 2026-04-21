"""
mehlr_1.0 URL yapılandırması.
"""
from django.urls import include, path
from mehlr import views

app_name = "mehlr"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("chat/", views.chat, name="chat"),
    path("chat/<slug:project_slug>/", views.chat, name="chat_project"),
    path("chat/conversation/<int:conversation_id>/", views.chat_detail, name="chat_detail"),
    path("send/", views.send_message, name="send_message"),
    path("reports/", views.report_list, name="reports"),
    path("reports/<int:report_id>/", views.report_detail, name="report_detail"),
    path("reports/create/", views.create_report, name="create_report"),
    path("api/project/<slug:project_slug>/", views.project_context_api, name="project_context_api"),
    path("api/analyze/", views.api_analyze, name="api_analyze"),
    # Eski API
    path("api/chat/send/", views.api_chat_send, name="api_chat_send"),
    path("api/chat/new/", views.api_chat_new, name="api_chat_new"),
    path("api/projects/", views.api_projects, name="api_projects"),
    path("api/report/generate/", views.api_report_generate, name="api_report_generate"),
    path("api/stats/", views.api_stats, name="api_stats"),
    path("api/dressifye/", include("mehlr.api.urls")),
]
