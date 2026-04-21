"""
context_manager — Dressifye gardırop ve prompt formatı testleri.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from mehlr.services.context_manager import (
    filter_wardrobe_for_prompt,
    format_wardrobe_for_prompt,
    get_dressifye_context,
)


class FormatWardrobeTests(SimpleTestCase):
    def test_format_wardrobe_for_prompt_structure(self) -> None:
        garments = [
            {
                "id": "123",
                "name": "Siyah Blazer",
                "category": "Üst Giyim",
                "color": "Siyah",
                "size": "M",
            },
            {
                "external_id": "124",
                "name": "Beyaz Gömlek",
                "category": "Üst Giyim",
                "color": "Beyaz",
                "size": "L",
            },
        ]
        text = format_wardrobe_for_prompt(garments)
        self.assertIn("Kullanıcının mevcut gardırobundaki ürünler:", text)
        self.assertIn("ID: 123", text)
        self.assertIn("Siyah Blazer", text)
        self.assertIn("ID: 124", text)
        self.assertIn("Bu ürünlerin ID'lerini kullanarak kombin öner.", text)

    def test_format_includes_subsample_notice_when_truncated(self) -> None:
        garments = [{"id": str(i), "name": f"X{i}", "category": "Üst Giyim", "color": "Siyah", "size": "M"} for i in range(5)]
        text = format_wardrobe_for_prompt(garments, total_source_count=50)
        self.assertIn("tüm gardırobunu değil", text)
        self.assertIn("en alakalı 5 parçayı", text)
        self.assertIn("toplam 50 parça", text)
        self.assertIn("varsayma", text)


class FilterWardrobeTests(SimpleTestCase):
    def test_filter_caps_at_max_items(self) -> None:
        garments = [
            {
                "id": str(i),
                "name": f"Item {i}",
                "category": "Üst Giyim" if i % 2 == 0 else "Alt Giyim",
                "color": "Siyah",
                "size": "M",
            }
            for i in range(60)
        ]
        out = filter_wardrobe_for_prompt(garments, max_items=30)
        self.assertEqual(len(out), 30)

    def test_filter_empty(self) -> None:
        self.assertEqual(filter_wardrobe_for_prompt([]), [])


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "dressifye-context-tests",
        }
    }
)
class GetDressifyeContextTests(TestCase):
    def setUp(self) -> None:
        cache.clear()

    @patch("mehlr.services.context_manager.DressifyeClient")
    def test_get_dressifye_context_structure(self, mock_cls: MagicMock) -> None:
        instance = mock_cls.return_value
        instance.get_user_wardrobe.return_value = []
        instance.get_user_profile.return_value = {"display_name": "Test"}

        ctx = get_dressifye_context("user-1", occasion=None, include_profile=True)

        self.assertIn("wardrobe_text", ctx)
        self.assertIn("wardrobe_items", ctx)
        self.assertIn("user_profile", ctx)
        self.assertIn("stats", ctx)
        self.assertIn("total_items", ctx["stats"])
        self.assertIn("included_items", ctx["stats"])
        self.assertIn("categories", ctx["stats"])
        self.assertIn("estimated_tokens", ctx["stats"])
        self.assertIn("mock-ext-1", ctx["wardrobe_text"])
        self.assertIn("core_context", ctx)
        self.assertIn("hair_form", ctx)
        self.assertIn("integration_text", ctx)

    @patch("mehlr.services.context_manager.DressifyeClient")
    def test_cache_second_call(self, mock_cls: MagicMock) -> None:
        instance = mock_cls.return_value
        instance.get_user_wardrobe.return_value = [
            {"id": "a1", "name": "X", "category": "Üst Giyim", "color": "Siyah", "size": "M"},
        ]
        instance.get_user_profile.return_value = {}

        get_dressifye_context("user-cache", client=instance)
        get_dressifye_context("user-cache", client=instance)

        self.assertEqual(instance.get_user_wardrobe.call_count, 1)
