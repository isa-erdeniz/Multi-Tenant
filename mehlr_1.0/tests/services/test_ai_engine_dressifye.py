"""
ai_engine — Dressifye JSON ayrıştırma ve query_dressifye_ai (mock) testleri.
"""
from __future__ import annotations

from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from mehlr.models import Conversation, OutfitRecommendation
from mehlr.services.ai_engine import _parse_dressifye_response, query_dressifye_ai

User = get_user_model()

_SAMPLE_JSON = """
```json
{
  "response": "Akşam için şık bir kombin.",
  "outfit": {
    "outfit": [
      {"garment_id": 101, "role": "üst", "note": "Blazer"},
      {"garment_id": 202, "role": "alt", "note": "Pantolon"}
    ],
    "style_notes": "Monokrom",
    "color_palette": ["#000000", "#ffffff"],
    "occasion_fit": "Yüksek",
    "tips": ["Kemer ekleyin"]
  }
}
```
"""


class ParseDressifyeResponseTests(TestCase):
    def test_parse_markdown_json(self) -> None:
        out = _parse_dressifye_response(_SAMPLE_JSON)
        self.assertEqual(out["outfit_recommendation"]["garment_ids"], [101, 202])
        self.assertIn("Akşam", out["outfit_recommendation"]["description"])
        self.assertEqual(out["outfit_recommendation"]["style_notes"], "Monokrom")
        self.assertEqual(len(out["outfit_recommendation"]["color_palette"]), 2)
        self.assertGreaterEqual(out["confidence"], 0.8)
        self.assertTrue(out["missing_items"])

    def test_parse_invalid_returns_fallback(self) -> None:
        out = _parse_dressifye_response("not json {{{")
        self.assertEqual(out["outfit_recommendation"]["garment_ids"], [])
        self.assertEqual(out["confidence"], 0.0)


@override_settings(
    GEMINI_API_KEY="test-key-for-mock",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "dressifye-ai-tests",
        }
    },
)
class QueryDressifyeAiTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="tuser", password="x")
        self.conv = Conversation.objects.create(user=self.user, title="d")

    def test_query_dressifye_ai_happy_path(self) -> None:
        def _fake_ctx(*args: object, **kwargs: object) -> dict:
            return {
                "wardrobe_text": "test",
                "wardrobe_items": [{"id": "1"}],
                "metadata": {"wardrobe_source": "api"},
                "stats": {},
            }

        async def run() -> dict:
            with (
                patch(
                    "mehlr.services.ai_engine._generate_dressifye_content",
                    return_value=(_SAMPLE_JSON.strip(), 100, None),
                ),
                patch(
                    "mehlr.services.context_manager.get_dressifye_context",
                    _fake_ctx,
                ),
            ):
                return await query_dressifye_ai(
                    user_id="ext-1",
                    user_query="Ne giyeyim?",
                    conversation_id=str(self.conv.pk),
                    occasion="iş",
                )

        out = async_to_sync(run)()
        self.assertIn("outfit_recommendation", out)
        self.assertEqual(out["outfit_recommendation"]["garment_ids"], [101, 202])
        self.assertEqual(out["outfit_recommendation"]["occasion"], "iş")
        rid = out.get("recommendation_id", 0)
        self.assertGreater(rid, 0)
        self.assertTrue(
            OutfitRecommendation.objects.filter(pk=rid, occasion="iş").exists()
        )

    def test_query_dressifye_ai_gemini_error(self) -> None:
        def _fake_ctx(*args: object, **kwargs: object) -> dict:
            return {
                "wardrobe_text": "x",
                "wardrobe_items": [],
                "metadata": {"wardrobe_source": "mock"},
                "stats": {},
            }

        async def run() -> dict:
            with (
                patch(
                    "mehlr.services.ai_engine._generate_dressifye_content",
                    return_value=("", 0, "timeout"),
                ),
                patch(
                    "mehlr.services.context_manager.get_dressifye_context",
                    _fake_ctx,
                ),
            ):
                return await query_dressifye_ai(
                    user_id="ext-2",
                    user_query="Test",
                    conversation_id=str(self.conv.pk),
                )

        out = async_to_sync(run)()
        self.assertEqual(out["confidence"], 0.0)
        self.assertIn("description", out["outfit_recommendation"])
