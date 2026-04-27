"""
API v1 endpoints.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.ai_integrations import views as ai_views

from apps.intake.views import MultiSourceIntakeView

from . import views
from . import payment_views

urlpatterns = [
    path(
        "auth/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "payments/dressifye/subscription/init/",
        payment_views.DressifyeSubscriptionInitView.as_view(),
        name="dressifye-subscription-init",
    ),
    path(
        "payments/dressifye/subscription/callback/",
        payment_views.DressifyeSubscriptionCallbackView.as_view(),
        name="dressifye-subscription-callback",
    ),
    path("intake/", MultiSourceIntakeView.as_view(), name="ecosystem-intake"),
    path("tryon/", views.TryOnViewSet.as_view()),
    path("wardrobe/", views.WardrobeViewSet.as_view()),
    path("account/", views.AccountView.as_view()),
    path("ai/process/", ai_views.AIProcessView.as_view(), name="ai-process"),
    path("ai/quota/", ai_views.AIQuotaView.as_view(), name="ai-quota"),
    path("ai/tasks/<int:pk>/", ai_views.AITaskDetailView.as_view(), name="ai-task-detail"),
    path(
        "ai/tasks/<int:pk>/cancel/",
        ai_views.AITaskCancelView.as_view(),
        name="ai-task-cancel",
    ),
]
