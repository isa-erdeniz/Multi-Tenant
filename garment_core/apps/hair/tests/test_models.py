"""
Hair model testleri — HairStyle, HairColor, HairSession.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.hair.models import HairColor, HairSession, HairStyle

User = get_user_model()


@pytest.mark.django_db
def test_hair_style_create():
    style = HairStyle.objects.create(name="Bob Kesim", category="bob")
    assert style.pk is not None
    assert style.is_premium is False


@pytest.mark.django_db
def test_hair_color_create():
    color = HairColor.objects.create(name="Siyah", hex_code="#000000", category="doğal")
    assert color.pk is not None
    assert color.hex_code == "#000000"


@pytest.mark.django_db
def test_hair_session_create_minimal():
    user = User.objects.create_user(
        username="hairuser", email="hair@test.com", password="pass"
    )
    session = HairSession.objects.create(user=user)
    assert session.pk is not None
    assert session.status == "pending"
    assert session.output_data == {}
    assert session.applied_style is None
    assert session.applied_color is None


@pytest.mark.django_db
def test_hair_session_with_style_and_color():
    user = User.objects.create_user(
        username="hairuser2", email="hair2@test.com", password="pass"
    )
    style = HairStyle.objects.create(name="Pixie", category="pixie")
    color = HairColor.objects.create(name="Kızıl", hex_code="#CC4400", category="fantezi")
    session = HairSession.objects.create(
        user=user, applied_style=style, applied_color=color
    )
    assert session.applied_style == style
    assert session.applied_color == color


@pytest.mark.django_db
def test_hair_session_status_transitions():
    user = User.objects.create_user(
        username="hairuser3", email="hair3@test.com", password="pass"
    )
    for status in ("pending", "processing", "completed", "failed"):
        s = HairSession.objects.create(user=user, status=status)
        assert s.status == status
