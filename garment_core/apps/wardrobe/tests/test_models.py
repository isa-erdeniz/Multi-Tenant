"""
Wardrobe model testleri.

GarmentCategory: TimeStampedModel — tenant alanı YOK.
Garment: TenantModel — tenant FK zorunlu; all_objects ile kapsamsız sorgulama.
"""
import pytest
from django.contrib.auth import get_user_model

from apps.core.tenant_context import use_tenant
from apps.tenants.models import Tenant
from apps.wardrobe.models import Garment, GarmentCategory

User = get_user_model()


@pytest.fixture
def user_and_tenant(db):
    # post_save sinyali kullanıcı için otomatik Tenant oluşturur.
    user = User.objects.create_user(
        username="wardrobeuser", email="wardrobe@test.com", password="pass"
    )
    user.refresh_from_db()
    tenant = user.tenant  # signal tarafından oluşturuldu
    return user, tenant


@pytest.fixture
def category(db):
    # GarmentCategory, TimeStampedModel'dir — tenant alanı yoktur.
    return GarmentCategory.objects.create(name="Üst Giyim", slug="ust-giyim")


@pytest.mark.django_db
def test_garment_category_create(category):
    assert category.pk is not None
    assert str(category) == "Üst Giyim"


@pytest.mark.django_db
def test_garment_create(user_and_tenant, category):
    user, tenant = user_and_tenant
    garment = Garment.all_objects.create(
        user=user,
        tenant=tenant,
        name="Beyaz Gömlek",
        category=category,
        color="beyaz",
    )
    assert garment.pk is not None
    assert "Beyaz Gömlek" in str(garment)
    assert garment.is_active is True
    assert garment.slug  # auto-slug oluşturuldu


@pytest.mark.django_db
def test_garment_str_contains_name(user_and_tenant, category):
    user, tenant = user_and_tenant
    garment = Garment.all_objects.create(
        user=user, tenant=tenant, name="Mavi Kot", category=category
    )
    assert "Mavi Kot" in str(garment)


@pytest.mark.django_db
def test_garment_soft_delete(user_and_tenant, category):
    """is_active=False olan garment aktif sorgusunda çıkmamalı."""
    user, tenant = user_and_tenant
    garment = Garment.all_objects.create(
        user=user, tenant=tenant, name="Silinecek", category=category
    )
    garment.is_active = False
    garment.save(update_fields=["is_active"])

    # all_objects kullanarak kapsamsız sorgulama yapılır
    active_ids = set(
        Garment.all_objects.filter(user=user, is_active=True).values_list("pk", flat=True)
    )
    assert garment.pk not in active_ids


@pytest.mark.django_db
def test_garment_scoped_manager_empty_without_context(user_and_tenant, category):
    """TenantScopedManager: tenant bağlamı yokken objects.all() boş döner."""
    user, tenant = user_and_tenant
    Garment.all_objects.create(user=user, tenant=tenant, name="Test", category=category)
    # Bağlam olmadan objects = boş
    assert Garment.objects.count() == 0


@pytest.mark.django_db
def test_garment_scoped_manager_with_context(user_and_tenant, category):
    """use_tenant context manager ile objects.all() sonuç döner."""
    user, tenant = user_and_tenant
    Garment.all_objects.create(user=user, tenant=tenant, name="Bağlamlı", category=category)
    with use_tenant(tenant):
        assert Garment.objects.count() == 1


@pytest.mark.django_db
def test_garment_tags_default_empty_list(user_and_tenant):
    user, tenant = user_and_tenant
    garment = Garment.all_objects.create(user=user, tenant=tenant, name="Tag Test")
    assert garment.tags == []
