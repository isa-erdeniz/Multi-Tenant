"""Dressifye API URL'leri — /mehlr/api/dressifye/..."""
from django.urls import path

from mehlr.api import dressifye

app_name = "dressifye_api"

urlpatterns = [
    path("recommend/", dressifye.OutfitRecommendationView.as_view(), name="recommend"),
    path("analyze/", dressifye.WardrobeAnalysisView.as_view(), name="analyze"),
    path("feedback/", dressifye.OutfitFeedbackView.as_view(), name="feedback"),
    path("webhook/", dressifye.DressifyeWebhookView.as_view(), name="webhook"),
    path("health/", dressifye.HealthCheckView.as_view(), name="health"),
]
