"""
Dressifye REST API — auth, recommend (mock), health.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient


@override_settings(
    DRESSIFYE_API_KEY="test-dressifye-secret",
    REST_FRAMEWORK={
        "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
        "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
        "DEFAULT_THROTTLE_RATES": {"dressifye": "10000/minute"},
    },
)
class DressifyeAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def _headers(self) -> dict[str, str]:
        return {
            "HTTP_X_API_KEY": "test-dressifye-secret",
            "HTTP_X_SERVICE_NAME": "dressifye",
        }

    def test_health_public(self) -> None:
        r = self.client.get("/mehlr/api/dressifye/health/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json().get("service"), "mehlr")

    def test_recommend_unauthorized(self) -> None:
        r = self.client.post(
            "/mehlr/api/dressifye/recommend/",
            {"user_id": "u1", "query": "test"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_recommend_validation(self) -> None:
        r = self.client.post(
            "/mehlr/api/dressifye/recommend/",
            {},
            format="json",
            **self._headers(),
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("mehlr.api.dressifye.query_dressifye_ai", new_callable=AsyncMock)
    def test_recommend_ok(self, mock_ai: AsyncMock) -> None:
        mock_ai.return_value = {
            "outfit_recommendation": {
                "garment_ids": [1],
                "description": "Test",
                "style_notes": "s",
                "color_palette": ["#000"],
                "occasion": "iş",
            },
            "missing_items": [],
            "confidence": 0.8,
            "raw_response": "{}",
            "recommendation_id": 0,
        }
        r = self.client.post(
            "/mehlr/api/dressifye/recommend/",
            {"user_id": "ext-u", "query": "Ne giyeyim?"},
            format="json",
            **self._headers(),
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = r.json()
        self.assertEqual(data["confidence"], 0.8)
        self.assertIn("outfit", data)
        mock_ai.assert_awaited_once()
