from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    path("planlar/", views.PlanListView.as_view(), name="plan_list"),
    path(
        "plan/<slug:plan_slug>/checkout/",
        views.SubscriptionCheckoutView.as_view(),
        name="checkout",
    ),
    path(
        "basarili/",
        views.SubscriptionSuccessView.as_view(),
        name="success",
    ),
    path("iptal/", views.SubscriptionCancelView.as_view(), name="cancel"),
    path("detay/", views.SubscriptionDetailView.as_view(), name="detail"),
]
