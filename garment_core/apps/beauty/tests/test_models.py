"""
Beauty model testleri — MakeupLook, MakeupSession.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.beauty.models import MakeupLook, MakeupSession

User = get_user_model()


@pytest.mark.django_db
def test_makeup_look_create():
    look = MakeupLook.objects.create(name="Gündüz Makyajı", category="günlük")
    assert look.pk is not None
    assert look.is_premium is False
    assert look.products_json == []


@pytest.mark.django_db
def test_makeup_session_create():
    user = User.objects.create_user(
        username="beautyuser", email="beauty@test.com", password="pass"
    )
    look = MakeupLook.objects.create(name="Gece Makyajı", category="gece")
    session = MakeupSession.objects.create(user=user, applied_look=look)
    assert session.pk is not None
    assert session.status == "pending"
    assert session.output_data == {}


@pytest.mark.django_db
def test_makeup_session_without_look():
    """applied_look olmadan da session oluşturulabilir (null=True)."""
    user = User.objects.create_user(
        username="beautyuser2", email="beauty2@test.com", password="pass"
    )
    session = MakeupSession.objects.create(user=user)
    assert session.pk is not None
    assert session.applied_look is None


@pytest.mark.django_db
def test_makeup_session_status_choices():
    user = User.objects.create_user(
        username="beautyuser3", email="beauty3@test.com", password="pass"
    )
    session = MakeupSession.objects.create(
        user=user, status="completed", output_data={"result": "ok"}
    )
    assert session.status == "completed"
    assert session.output_data["result"] == "ok"


@pytest.mark.django_db
def test_makeup_session_all_statuses():
    """Tüm geçerli status değerleri kaydedilebilir."""
    user = User.objects.create_user(
        username="beautyuser4", email="beauty4@test.com", password="pass"
    )
    for status in ("pending", "processing", "completed", "failed"):
        s = MakeupSession.objects.create(user=user, status=status)
        assert s.status == status
