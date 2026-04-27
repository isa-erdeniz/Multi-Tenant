"""
Avatar model testleri — AvatarStyle, AvatarSession.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.avatar.models import AvatarSession, AvatarStyle

User = get_user_model()


@pytest.mark.django_db
def test_avatar_style_create():
    style = AvatarStyle.objects.create(name="Gerçekçi", category="realistic")
    assert style.pk is not None
    assert style.is_premium is False
    assert style.example_images == []


@pytest.mark.django_db
def test_avatar_session_create_minimal():
    user = User.objects.create_user(
        username="avataruser", email="avatar@test.com", password="pass"
    )
    session = AvatarSession.objects.create(user=user)
    assert session.pk is not None
    assert session.status == "pending"
    assert session.output_data == {}
    assert session.result_images == []
    assert session.input_selfie.name is None or session.input_selfie.name == ""


@pytest.mark.django_db
def test_avatar_session_with_style():
    user = User.objects.create_user(
        username="avataruser2", email="avatar2@test.com", password="pass"
    )
    style = AvatarStyle.objects.create(name="Anime", category="anime")
    session = AvatarSession.objects.create(user=user, style=style)
    assert session.style == style


@pytest.mark.django_db
def test_avatar_session_result_images_default_list():
    """result_images varsayılan boş liste olmalı (dict değil)."""
    user = User.objects.create_user(
        username="avataruser3", email="avatar3@test.com", password="pass"
    )
    session = AvatarSession.objects.create(user=user)
    assert isinstance(session.result_images, list)
    assert session.result_images == []


@pytest.mark.django_db
def test_avatar_session_completed_with_images():
    user = User.objects.create_user(
        username="avataruser4", email="avatar4@test.com", password="pass"
    )
    images = ["https://cdn.example.com/av1.jpg", "https://cdn.example.com/av2.jpg"]
    session = AvatarSession.objects.create(
        user=user, status="completed", result_images=images
    )
    assert session.status == "completed"
    assert len(session.result_images) == 2


@pytest.mark.django_db
def test_avatar_session_all_statuses():
    user = User.objects.create_user(
        username="avataruser5", email="avatar5@test.com", password="pass"
    )
    for status in ("pending", "processing", "completed", "failed"):
        s = AvatarSession.objects.create(user=user, status=status)
        assert s.status == status
