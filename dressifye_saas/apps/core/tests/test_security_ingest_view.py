"""
SecurityIngestView testleri — POST /erdeniz-security/ingest/

Route, erdeniz_security kuruluysa dressifye_saas config/urls.py içinde aktif olur.
"""
import json

from django.test import Client, TestCase


class SecurityIngestViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/erdeniz-security/ingest/"

    def _post(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_valid_garment_ingest_returns_allowed(self):
        resp = self._post(
            {
                "tenantId": "abc-123",
                "tenantSlug": "stylecoree",
                "resourceType": "garment_ingest",
                "payload": {"name": "Test Kıyafet", "category": "üst"},
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "allowed")
        self.assertIn("trace", data)

    def test_unknown_resource_type_quarantined(self):
        resp = self._post(
            {
                "tenantId": "abc-123",
                "tenantSlug": "stylecoree",
                "resourceType": "unknown_type",
                "payload": {"name": "X"},
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["verdict"], "quarantined")

    def test_empty_payload_quarantined(self):
        resp = self._post(
            {
                "tenantId": "abc-123",
                "tenantSlug": "stylecoree",
                "resourceType": "garment_ingest",
                "payload": {},
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["verdict"], "quarantined")

    def test_invalid_json_returns_400(self):
        resp = self.client.post(
            self.url,
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_garment_resource_type_allowed(self):
        resp = self._post(
            {
                "tenantId": "abc-123",
                "tenantSlug": "stylecoree",
                "resourceType": "garment",
                "payload": {"id": "g-1"},
            }
        )
        self.assertEqual(resp.json()["verdict"], "allowed")

    def test_user_action_resource_type_allowed(self):
        resp = self._post(
            {
                "tenantId": "abc-123",
                "tenantSlug": "stylecoree",
                "resourceType": "user_action",
                "payload": {"action": "login"},
            }
        )
        self.assertEqual(resp.json()["verdict"], "allowed")

    def test_trace_contains_tenant_info(self):
        resp = self._post(
            {
                "tenantId": "t-999",
                "tenantSlug": "dressifye",
                "resourceType": "garment_ingest",
                "payload": {"name": "Elbise"},
            }
        )
        trace = resp.json()["trace"]
        self.assertEqual(trace["tenant_id"], "t-999")
        self.assertEqual(trace["tenant_slug"], "dressifye")

    def test_options_returns_204(self):
        resp = self.client.options(self.url)
        self.assertEqual(resp.status_code, 204)

    def _is_erdeniz_security_installed(self):
        from django.conf import settings
        return "erdeniz_security" in settings.INSTALLED_APPS

    def test_erdeniz_security_route_registered(self):
        """erdeniz_security kuruluysa URL 404 dönmemeli."""
        if not self._is_erdeniz_security_installed():
            self.skipTest("erdeniz_security kurulu değil")
        resp = self._post({
            "tenantId": "x", "tenantSlug": "x",
            "resourceType": "garment_ingest", "payload": {"x": 1}
        })
        self.assertNotEqual(resp.status_code, 404)
