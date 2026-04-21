"""
garment-core → Mehlr AI bağlam kaynağı testleri.
Gerçek HTTP yapılmaz; fetch_garments_from_core mock'lanır.
"""
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings

from mehlr.integrations.garment_core_context_source import (
    _map_to_dressifye_shape,
    fetch_garments_from_core,
)

GC_SETTINGS = dict(
    GARMENT_CORE_API_URL="http://localhost:8080",
    GARMENT_CORE_API_KEY="test-api-key",
    GARMENT_CORE_TENANT_SLUGS=["dressifye", "stylecoree"],
)

_SAMPLE_GARMENT = {
    "id": "gc-uuid-1",
    "externalRef": "ext-ref-1",
    "title": "Pamuklu Blazer",
    "normalizedCategory": "Üst Giyim",
    "productKind": "garment",
    "mehlrAttributes": {
        "fabricType": "Pamuk",
        "styleEra": "Retro",
        "colorPalette": ["Siyah", "Beyaz"],
    },
    "universalPayload": {"source_domain": "stylecoree"},
}


class MapToDressifyeShapeTests(TestCase):
    def test_maps_title_to_name(self) -> None:
        result = _map_to_dressifye_shape(_SAMPLE_GARMENT)
        self.assertEqual(result["name"], "Pamuklu Blazer")

    def test_maps_external_ref_to_id(self) -> None:
        result = _map_to_dressifye_shape(_SAMPLE_GARMENT)
        self.assertEqual(result["id"], "ext-ref-1")

    def test_mehlr_attributes_in_metadata(self) -> None:
        result = _map_to_dressifye_shape(_SAMPLE_GARMENT)
        self.assertEqual(result["metadata"]["fabricType"], "Pamuk")
        self.assertEqual(result["metadata"]["styleEra"], "Retro")

    def test_source_domain_in_metadata(self) -> None:
        result = _map_to_dressifye_shape(_SAMPLE_GARMENT)
        self.assertEqual(result["metadata"]["source"], "stylecoree")

    def test_first_color_palette_item_as_color(self) -> None:
        result = _map_to_dressifye_shape(_SAMPLE_GARMENT)
        self.assertEqual(result["color"], "Siyah")


@override_settings(**GC_SETTINGS)
class FetchGarmentsFromCoreTests(TestCase):
    @patch("mehlr.integrations.garment_core_context_source.urllib.request.urlopen")
    def test_returns_mapped_items(self, mock_urlopen) -> None:
        import io, json
        mock_resp = mock_urlopen.return_value.__enter__.return_value
        mock_resp.read.return_value = json.dumps({"items": [_SAMPLE_GARMENT]}).encode()
        mock_resp.status = 200

        result = fetch_garments_from_core("stylecoree")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Pamuklu Blazer")

    @patch("mehlr.integrations.garment_core_context_source.urllib.request.urlopen")
    def test_returns_empty_on_http_error(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None, fp=None  # type: ignore[arg-type]
        )
        result = fetch_garments_from_core("stylecoree")
        self.assertEqual(result, [])

    @override_settings(GARMENT_CORE_API_URL="", GARMENT_CORE_API_KEY="")
    def test_returns_empty_when_no_config(self) -> None:
        result = fetch_garments_from_core("stylecoree")
        self.assertEqual(result, [])


@override_settings(**GC_SETTINGS)
class GetDressifyeContextWithGarmentCoreTests(TestCase):
    @patch("mehlr.integrations.garment_core_context_source.fetch_garments_from_core")
    @patch("mehlr.services.context_manager.DressifyeClient")
    def test_falls_back_to_garment_core_when_dressifye_empty(
        self, mock_client_cls, mock_fetch
    ) -> None:
        from mehlr.services.context_manager import get_dressifye_context

        mock_client_cls.return_value.get_user_wardrobe.return_value = []
        mock_client_cls.return_value.get_user_profile.return_value = {}
        mock_fetch.return_value = [
            {
                "id": "gc-1",
                "name": "Pamuklu Blazer",
                "category": "Üst Giyim",
                "color": "Siyah",
                "size": "",
                "image_url": "",
                "metadata": {"fabricType": "Pamuk", "source": "garment_core"},
            }
        ]
        ctx = get_dressifye_context("user-gc-1")
        self.assertIn("Pamuklu Blazer", ctx["wardrobe_text"])
        self.assertGreaterEqual(ctx["stats"]["total_items"], 1)

    @patch("mehlr.integrations.garment_core_context_source.fetch_garments_from_core")
    @patch("mehlr.services.context_manager.DressifyeClient")
    def test_dressifye_takes_priority_over_garment_core(
        self, mock_client_cls, mock_fetch
    ) -> None:
        from mehlr.services.context_manager import get_dressifye_context

        mock_client_cls.return_value.get_user_wardrobe.return_value = [
            {"id": "d1", "name": "Dressifye Gömlek", "category": "Üst", "color": "Beyaz"}
        ]
        mock_client_cls.return_value.get_user_profile.return_value = {}
        ctx = get_dressifye_context("user-dressifye-1")
        self.assertIn("Dressifye Gömlek", ctx["wardrobe_text"])
        mock_fetch.assert_not_called()
