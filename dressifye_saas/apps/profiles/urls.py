from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("onboarding/", views.onboarding_view, {"step": 1}, name="onboarding"),
    path(
        "onboarding/adim/<int:step>/",
        views.onboarding_view,
        name="onboarding_step",
    ),
    path("", views.profile_view, name="profile"),
    path("duzenle/", views.profile_edit_view, name="edit"),
]
