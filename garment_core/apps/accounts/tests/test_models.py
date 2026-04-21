"""
Garment Core — accounts modelleri testleri.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_user_create_with_email():
    """E-posta ile kullanıcı oluşturulabilmeli."""
    user = User.objects.create_user(
        username="test@example.com",
        email="test@example.com",
        password="TestPass123!",
    )
    assert user.email == "test@example.com"
    assert user.check_password("TestPass123!")
    assert user.is_active
    assert not user.is_staff
    user.refresh_from_db()
    assert user.tenant_id is not None
    assert user.subscription.tenant_id == user.tenant_id


@pytest.mark.django_db
def test_user_email_unique():
    """E-posta benzersiz olmalı."""
    User.objects.create_user(
        username="unique@example.com",
        email="unique@example.com",
        password="pass",
    )
    with pytest.raises(Exception):
        User.objects.create_user(
            username="unique@example.com",
            email="unique@example.com",
            password="pass2",
        )


@pytest.mark.django_db
def test_superuser_create():
    """Superuser oluşturulabilmeli."""
    admin = User.objects.create_superuser(
        username="admin@garmentcore.com",
        email="admin@garmentcore.com",
        password="Admin123!",
    )
    assert admin.is_staff
    assert admin.is_superuser
    admin.refresh_from_db()
    assert admin.tenant_id is not None
