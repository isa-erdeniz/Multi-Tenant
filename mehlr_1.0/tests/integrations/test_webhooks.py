"""
Dressifye webhook — cache invalidation ve Celery delay (mock).
"""
from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from mehlr.integrations.webhooks import process_dressifye_webhook
from mehlr.models import DressifyeGarment, DressifyeUser


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "webhook-tests",
        }
    },
    DRESSIFYE_API_KEY="x",
)
class DressifyeWebhookTests(TestCase):
    def setUp(self) -> None:
        cache.clear()

    @patch("mehlr.tasks.sync_user_wardrobe_task")
    def test_wardrobe_updated_triggers_sync_delay(self, mock_task: MagicMock) -> None:
        ok = process_dressifye_webhook({"event": "wardrobe.updated", "user_id": "u-99"})
        self.assertTrue(ok)
        mock_task.delay.assert_called_once_with("u-99", force=True)

    def test_item_deleted_removes_garment(self) -> None:
        du = DressifyeUser.objects.create(external_id="u1", username="a")
        DressifyeGarment.objects.create(
            external_id="g-ext-1",
            user=du,
            name="T",
            category="",
            color="",
            size="",
        )
        ok = process_dressifye_webhook(
            {"event": "item.deleted", "external_id": "g-ext-1", "user_id": "u1"}
        )
        self.assertTrue(ok)
        self.assertFalse(DressifyeGarment.objects.filter(external_id="g-ext-1").exists())
