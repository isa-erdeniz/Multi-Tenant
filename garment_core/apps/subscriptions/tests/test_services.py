"""
Subscriptions servis katmanı testleri.

NOT: DressifyeUser.post_save sinyali her yeni kullanıcı için otomatik olarak
  - Kişisel Tenant oluşturur ve user.tenant_id'yi günceller
  - UserSubscription (status="trial", plan=None) oluşturur
Helper bu davranışı bilerek update kullanır.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.subscriptions.models import FeatureUsage, Plan, UserSubscription
from apps.subscriptions.services import (
    can_use_feature,
    get_effective_plan,
    get_remaining,
    increment_usage,
)

User = get_user_model()


def make_user_with_plan(limit: int, feature: str = FeatureUsage.FEATURE_TRYON, suffix: str = "u"):
    """
    Kullanıcı oluşturur (signal Tenant + trial sub yaratır), ardından
    sub planını test planıyla değiştirir.
    """
    user = User.objects.create_user(
        username=f"user-{suffix}",
        email=f"user-{suffix}@test.com",
        password="pass",
    )
    # Signal user.tenant_id'yi ve subscription'ı set etmiş olabilir;
    # DB'den güncel değerleri alalım.
    user.refresh_from_db()

    plan = Plan.objects.create(
        name="Test Plan",
        slug=f"plan-{suffix}",
        tryon_limit=limit if feature == FeatureUsage.FEATURE_TRYON else 0,
        makeup_limit=limit if feature == FeatureUsage.FEATURE_MAKEUP else 0,
        hair_limit=limit if feature == FeatureUsage.FEATURE_HAIR else 0,
        avatar_limit=limit if feature == FeatureUsage.FEATURE_AVATAR else 0,
        look_apply_limit=limit if feature == FeatureUsage.FEATURE_LOOK_APPLY else 0,
    )
    # Auto-created subscription'ı istenen planla güncelle.
    UserSubscription.objects.filter(user=user).update(plan=plan, status="active")
    # Subscription cache'ini temizle.
    if hasattr(user, "_subscription_cache"):
        del user._subscription_cache
    try:
        del user.__dict__["subscription"]
    except KeyError:
        pass
    return user


# ---------------------------------------------------------------------------
# can_use_feature
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCanUseFeature:
    def test_no_plan_uses_default_limit(self):
        """Kullanıcının aboneliği plan=None ise default limit kullanılır (3 tryon)."""
        # create_user sinyali plan=None ile subscription açar (test DB'de "ucretsiz" yok).
        user = User.objects.create_user(
            username="noplan", email="noplan@test.com", password="pass"
        )
        user.refresh_from_db()
        # plan=None → _limit_for_feature(None, tryon) = 3 → remaining=3 → True
        assert can_use_feature(user, FeatureUsage.FEATURE_TRYON) is True

    def test_unlimited_plan_always_true(self):
        """limit=0 → sınırsız → 20 kullanım sonra da True."""
        user = make_user_with_plan(0, feature=FeatureUsage.FEATURE_TRYON, suffix="unlim")
        for _ in range(20):
            increment_usage(user, FeatureUsage.FEATURE_TRYON)
        assert can_use_feature(user, FeatureUsage.FEATURE_TRYON) is True

    def test_limit_reached_returns_false(self):
        """Limit dolunca False."""
        user = make_user_with_plan(2, feature=FeatureUsage.FEATURE_TRYON, suffix="lim2")
        increment_usage(user, FeatureUsage.FEATURE_TRYON)
        increment_usage(user, FeatureUsage.FEATURE_TRYON)
        assert can_use_feature(user, FeatureUsage.FEATURE_TRYON) is False

    def test_unauthenticated_user_returns_false(self):
        """Anonim kullanıcı → False."""
        from django.contrib.auth.models import AnonymousUser

        assert can_use_feature(AnonymousUser(), FeatureUsage.FEATURE_TRYON) is False

    @pytest.mark.parametrize(
        "feature,suffix",
        [
            (FeatureUsage.FEATURE_MAKEUP, "mk"),
            (FeatureUsage.FEATURE_HAIR, "hr"),
            (FeatureUsage.FEATURE_AVATAR, "av"),
            (FeatureUsage.FEATURE_LOOK_APPLY, "la"),
        ],
    )
    def test_new_feature_types_work(self, feature: str, suffix: str):
        """Yeni feature type'ları: limit=1 → True, 1 increment sonrası False."""
        user = make_user_with_plan(1, feature=feature, suffix=suffix)
        assert can_use_feature(user, feature) is True
        increment_usage(user, feature)
        assert can_use_feature(user, feature) is False


# ---------------------------------------------------------------------------
# get_remaining
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetRemaining:
    def test_remaining_decreases(self):
        user = make_user_with_plan(3, feature=FeatureUsage.FEATURE_TRYON, suffix="rem")
        assert get_remaining(user, FeatureUsage.FEATURE_TRYON) == 3
        increment_usage(user, FeatureUsage.FEATURE_TRYON)
        assert get_remaining(user, FeatureUsage.FEATURE_TRYON) == 2

    def test_unlimited_returns_none(self):
        """limit=0 plan → get_remaining → None (sınırsız)."""
        user = make_user_with_plan(0, feature=FeatureUsage.FEATURE_TRYON, suffix="ulim")
        assert get_remaining(user, FeatureUsage.FEATURE_TRYON) is None

    def test_remaining_never_negative(self):
        """Sayaç limiti geçse bile remaining 0 döner, negatif olmaz."""
        user = make_user_with_plan(1, feature=FeatureUsage.FEATURE_TRYON, suffix="neg")
        increment_usage(user, FeatureUsage.FEATURE_TRYON)
        increment_usage(user, FeatureUsage.FEATURE_TRYON)  # limit aşıldı
        assert get_remaining(user, FeatureUsage.FEATURE_TRYON) == 0


# ---------------------------------------------------------------------------
# get_effective_plan
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_effective_plan_with_subscription():
    """Aktif abonelik varsa o plan döner."""
    user = make_user_with_plan(3, suffix="ep")
    plan = get_effective_plan(user)
    assert plan is not None
    assert plan.slug == "plan-ep"


@pytest.mark.django_db
def test_get_effective_plan_no_subscription():
    """Abonelik silinirse ve "ucretsiz" plan da yoksa None döner."""
    user = User.objects.create_user(
        username="nosub", email="nosub@test.com", password="pass"
    )
    # Signal'in oluşturduğu subscription'ı sil.
    UserSubscription.objects.filter(user=user).delete()
    assert get_effective_plan(user) is None
