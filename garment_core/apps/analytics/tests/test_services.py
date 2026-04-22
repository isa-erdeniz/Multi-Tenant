"""
Analytics servis testleri.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from apps.analytics.models import UsageEvent
from apps.analytics.services import record_usage_event

User = get_user_model()


@pytest.mark.django_db
def test_record_usage_event_creates_record():
    user = User.objects.create_user(
        username="analyticsuser", email="analytics@test.com", password="pass"
    )
    record_usage_event(user, "tryon", metadata={"garment_id": 1})
    assert UsageEvent.objects.filter(user=user, event_type="tryon").count() == 1


@pytest.mark.django_db
def test_record_usage_event_anonymous_user_skipped():
    """Anonim kullanıcı → kayıt oluşturulmamalı."""
    record_usage_event(AnonymousUser(), "tryon")
    assert UsageEvent.objects.count() == 0


@pytest.mark.django_db
def test_record_usage_event_none_user_skipped():
    """None kullanıcı → kayıt oluşturulmamalı."""
    record_usage_event(None, "tryon")
    assert UsageEvent.objects.count() == 0


@pytest.mark.django_db
def test_record_usage_event_metadata_stored():
    user = User.objects.create_user(
        username="analyticsuser2", email="analytics2@test.com", password="pass"
    )
    record_usage_event(user, "wardrobe_add", metadata={"source": "upload"})
    event = UsageEvent.objects.get(user=user)
    assert event.metadata["source"] == "upload"


@pytest.mark.django_db
def test_record_usage_event_empty_metadata():
    """metadata verilmezse {} olarak kaydedilmeli."""
    user = User.objects.create_user(
        username="analyticsuser3", email="analytics3@test.com", password="pass"
    )
    record_usage_event(user, "editor")
    event = UsageEvent.objects.get(user=user)
    assert event.metadata == {}


@pytest.mark.django_db
def test_record_usage_event_multiple_events():
    """Aynı kullanıcı için birden fazla event oluşturulabilir."""
    user = User.objects.create_user(
        username="analyticsuser4", email="analytics4@test.com", password="pass"
    )
    record_usage_event(user, "tryon")
    record_usage_event(user, "makeup")
    record_usage_event(user, "hair")
    assert UsageEvent.objects.filter(user=user).count() == 3


@pytest.mark.django_db
def test_record_usage_event_session_id_stored():
    user = User.objects.create_user(
        username="analyticsuser5", email="analytics5@test.com", password="pass"
    )
    record_usage_event(user, "avatar", session_id="sess-abc-123")
    event = UsageEvent.objects.get(user=user)
    assert event.session_id == "sess-abc-123"
