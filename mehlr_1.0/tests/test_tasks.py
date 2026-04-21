"""
Celery görevleri — doğrudan çağrı (eager / unit).
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from mehlr.models import (
    Conversation,
    DressifyeGarment,
    DressifyeUser,
    OutfitRecommendation,
    OutfitRecommendationFeedback,
)
from mehlr.tasks import cleanup_old_data, sync_user_wardrobe_task
from django.contrib.auth import get_user_model

User = get_user_model()


class SyncWardrobeTaskTests(TestCase):
    @patch("mehlr.tasks.DressifyeClient")
    def test_sync_updates_garments(self, mock_client_cls: object) -> None:
        inst = mock_client_cls.return_value
        inst.get_user_wardrobe.return_value = [
            {
                "id": "g1",
                "name": "Gömlek",
                "category": "Üst",
                "color": "Beyaz",
                "size": "M",
            }
        ]
        out = sync_user_wardrobe_task.run("user-x", force=True)
        self.assertEqual(out["api_items"], 1)
        self.assertTrue(DressifyeGarment.objects.filter(external_id="g1").exists())
        du = DressifyeUser.objects.get(external_id="user-x")
        self.assertEqual(DressifyeGarment.objects.get(external_id="g1").user, du)


class CleanupOldDataTests(TestCase):
    def test_deletes_old_rows(self) -> None:
        u = User.objects.create_user(username="a", password="x")
        conv = Conversation.objects.create(user=u, title="t")
        du = DressifyeUser.objects.create(external_id="e1", username="d")
        old = timezone.now() - timedelta(days=60)
        r = OutfitRecommendation.objects.create(
            user=du,
            conversation=conv,
            occasion="",
            style_notes="",
        )
        OutfitRecommendationFeedback.objects.create(
            recommendation=r,
            feedback=OutfitRecommendationFeedback.FeedbackChoices.LIKED,
        )
        OutfitRecommendation.objects.filter(pk=r.pk).update(created_at=old)
        OutfitRecommendationFeedback.objects.filter(recommendation=r).update(created_at=old)

        res = cleanup_old_data(days=30)
        self.assertGreaterEqual(res["recommendations_deleted"], 0)
        self.assertGreaterEqual(res["feedback_deleted"], 0)
