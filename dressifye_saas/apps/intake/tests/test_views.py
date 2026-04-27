"""
Intake endpoint testleri — POST /api/v1/intake/
"""
import json

from django.test import Client, TestCase, override_settings


@override_settings(INTAKE_BEARER_TOKEN="test-intake-token")
class IntakeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/api/v1/intake/"

    def _post(self, data, token="test-intake-token", tenant="styleforhuman"):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        if tenant:
            headers["HTTP_X_TENANT_ID"] = tenant
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
            **headers,
        )

    def test_valid_intake_creates_record(self):
        resp = self._post({"event_type": "page_view", "payload": {"page": "/"}})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["tenant_slug"], "styleforhuman")

    def test_missing_token_returns_401(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
            HTTP_X_TENANT_ID="styleforhuman",
        )
        self.assertEqual(resp.status_code, 401)

    def test_wrong_token_returns_401(self):
        resp = self._post({"event_type": "test"}, token="wrong-token")
        self.assertEqual(resp.status_code, 401)

    def test_missing_tenant_returns_400(self):
        resp = self.client.post(
            self.url,
            data=json.dumps({"event_type": "test"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-intake-token",
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_returns_400(self):
        resp = self.client.post(
            self.url,
            data="not-json",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-intake-token",
            HTTP_X_TENANT_ID="styleforhuman",
        )
        self.assertEqual(resp.status_code, 400)

    def test_unconfigured_token_returns_503(self):
        with self.settings(INTAKE_BEARER_TOKEN=""):
            resp = self._post({"event_type": "test"})
            self.assertEqual(resp.status_code, 503)

    def test_tenant_slug_from_body_when_no_header(self):
        """tenant_slug JSON body'den de alınabilir."""
        resp = self.client.post(
            self.url,
            data=json.dumps({"event_type": "click", "tenant_slug": "dressifye"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-intake-token",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["tenant_slug"], "dressifye")

    def test_response_contains_record_id(self):
        resp = self._post({"event_type": "signup", "payload": {"source": "web"}})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn("id", data)
        self.assertIsNotNone(data["id"])
