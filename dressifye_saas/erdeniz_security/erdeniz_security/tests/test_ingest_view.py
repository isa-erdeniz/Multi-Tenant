"""
SecurityIngestView testleri — bağımsız çalıştırma.
Dressifye Django ortamına bağlıdır (DJANGO_SETTINGS_MODULE).
Çalıştırma:
    cd Multi-Tenant/dressifye_saas
    pytest ../erdeniz_security/erdeniz_security/tests/ --tb=short -q
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
                "payload": {"name": "Test Kıyafet"},
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "allowed")

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
