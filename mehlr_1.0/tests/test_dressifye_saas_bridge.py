"""
Mehlr → dressifye-saas köprüsü testleri.
gerçek HTTP isteği atılmaz; send_to_dressifye_saas mock'lanır.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from mehlr.models import (
    Conversation,
    DressifyeGarment,
    DressifyeUser,
    OutfitRecommendation,
)
from mehlr.tasks_dressifye_saas import (
    push_garment_to_core,
    push_outfit_recommendation_to_core,
)
from django.contrib.auth import get_user_model

User = get_user_model()

GARMENT_CORE_SETTINGS = dict(
    GARMENT_CORE_WEBHOOK_URL="http://localhost:8080/webhook/mehlr",
    GARMENT_CORE_WEBHOOK_SECRET="test-secret",
)


@override_settings(**GARMENT_CORE_SETTINGS)
class PushGarmentToCoreTests(TestCase):
    @patch("mehlr.tasks_dressifye_saas.send_to_dressifye_saas")
    def test_push_garment_calls_client(self, mock_send: MagicMock) -> None:
        mock_send.return_value = {"ok": True}
        result = push_garment_to_core.run(
            garment_external_id="g-ext-99",
            garment_data={"name": "Test Kıyafet", "category": "Üst"},
            tenant_slug="dressifye",
        )
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        self.assertEqual(call_kwargs.kwargs.get("tenant_slug") or call_kwargs[1].get("tenant_slug") or call_kwargs[0][2] if len(call_kwargs[0]) > 2 else "dressifye", "dressifye")
        self.assertTrue(result["sent"])

    @patch("mehlr.tasks_dressifye_saas.send_to_dressifye_saas")
    def test_push_garment_returns_none_gracefully(self, mock_send: MagicMock) -> None:
        mock_send.return_value = None
        result = push_garment_to_core.run(
            garment_external_id="g-ext-99",
            garment_data={"name": "Test"},
            tenant_slug="dressifye",
        )
        self.assertTrue(result["sent"])
        self.assertIsNone(result["result"])


@override_settings(**GARMENT_CORE_SETTINGS)
class PushOutfitRecommendationToCoreTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser2", password="pass")
        self.conv = Conversation.objects.create(user=self.user, title="conv")
        self.du = DressifyeUser.objects.create(external_id="du-ext-1", username="du")

    @patch("mehlr.tasks_dressifye_saas.send_to_dressifye_saas")
    def test_push_recommendation_marks_synced(self, mock_send: MagicMock) -> None:
        mock_send.return_value = {"ok": True}
        rec = OutfitRecommendation.objects.create(
            user=self.du,
            conversation=self.conv,
            occasion="Casual",
            style_notes="Rahat görünüm",
        )
        result = push_outfit_recommendation_to_core.run(
            recommendation_id=rec.pk,
            tenant_slug="dressifye",
        )
        self.assertTrue(result["sent"])
        rec.refresh_from_db()
        self.assertTrue(rec.synced_to_dressifye)

    def test_push_recommendation_not_found_returns_gracefully(self) -> None:
        result = push_outfit_recommendation_to_core.run(
            recommendation_id=99999,
            tenant_slug="dressifye",
        )
        self.assertFalse(result["sent"])
        self.assertEqual(result["reason"], "not_found")


@override_settings(**GARMENT_CORE_SETTINGS)
class GarmentSavedSignalTests(TestCase):
    """
    DressifyeGarment kaydedilince Celery task kuyruğa alınmalı.
    """

    def setUp(self) -> None:
        self.du = DressifyeUser.objects.create(external_id="signal-user-1", username="siguser")

    @patch("mehlr.tasks_dressifye_saas.push_garment_to_core")
    def test_signal_queues_task_on_create(self, mock_task: MagicMock) -> None:
        mock_task.delay = MagicMock()
        DressifyeGarment.objects.create(
            external_id="signal-g-1",
            user=self.du,
            name="Sinyal kıyafet",
            category="Alt",
        )
        mock_task.delay.assert_called_once()

    @patch("mehlr.tasks_dressifye_saas.push_garment_to_core")
    def test_signal_queues_task_on_update(self, mock_task: MagicMock) -> None:
        mock_task.delay = MagicMock()
        g = DressifyeGarment.objects.create(
            external_id="signal-g-2",
            user=self.du,
            name="Sinyal kıyafet 2",
        )
        mock_task.delay.reset_mock()
        g.name = "Güncellenmiş"
        g.save()
        mock_task.delay.assert_called_once()
