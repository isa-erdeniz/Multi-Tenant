"""
MEHLR URL yapılandırması.
"""
from django.urls import path
from mehlr import views

app_name = 'mehlr'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('chat/<int:conversation_id>/', views.ChatView.as_view(), name='chat_detail'),
    path('reports/', views.ReportListView.as_view(), name='reports'),
    path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),

    path('api/chat/send/', views.api_chat_send, name='api_chat_send'),
    path('api/chat/new/', views.api_chat_new, name='api_chat_new'),
    path('api/projects/', views.api_projects, name='api_projects'),
    path('api/report/generate/', views.api_report_generate, name='api_report_generate'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
