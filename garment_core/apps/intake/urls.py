from django.urls import path
from apps.intake.views import MultiSourceIntakeView

app_name = "intake"

urlpatterns = [
    path("", MultiSourceIntakeView.as_view(), name="receive"),
]
