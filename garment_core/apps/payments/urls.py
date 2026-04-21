from django.urls import path

from . import views
from . import webhooks

app_name = "payments"

urlpatterns = [
    path("webhook/iyzico/", webhooks.iyzico_webhook, name="iyzico_webhook"),
    path("yukselt/", views.upgrade_view, name="upgrade"),
    path("odeme/<slug:plan_slug>/", views.checkout_view, name="checkout"),
    path("callback/", views.callback_view, name="callback"),
    path("basarili/", views.success_view, name="success"),
]
