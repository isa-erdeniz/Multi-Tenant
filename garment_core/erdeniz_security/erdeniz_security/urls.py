from django.urls import path

from .views import SecurityIngestView

app_name = "erdeniz_security"

urlpatterns = [
    path("ingest/", SecurityIngestView.as_view(), name="ingest"),
]
