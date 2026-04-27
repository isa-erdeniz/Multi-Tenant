"""
DressifyeSaasTSClient unit testleri — HTTP çağrısı mock'lanır.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


@override_settings(
    GARMENT_CORE_TS_ENABLED=True,
    GARMENT_CORE_TS_URL="https://ts.example.com",
    GARMENT_CORE_WEBHOOK_SECRET="test-secret",
    GARMENT_CORE_TS_API_KEY="test-api-key",
)
class DressifyeSaasTSClientTests(TestCase):

    def _get_client(self):
        from apps.core.clients.dressifye_saas_ts_client import DressifyeSaasTSClient
        return DressifyeSaasTSClient()

    # ------------------------------------------------------------------
    # push_garment
    # ------------------------------------------------------------------

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.post")
    def test_push_garment_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "id": "abc123", "verdict": "allowed"}
        mock_post.return_value = mock_resp

        client = self._get_client()
        result = client.push_garment(
            tenant_slug="stylecoree",
            garment_data={"name": "Test", "category": "üst"},
            external_ref="django-42",
        )
        self.assertTrue(result["success"])
        mock_post.assert_called_once()

        # HMAC imzası gönderildi mi?
        call_kwargs = mock_post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        self.assertIn("X-Hub-Signature-256", headers)
        self.assertTrue(headers["X-Hub-Signature-256"].startswith("sha256="))

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.post")
    def test_push_garment_security_rejected_422(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.json.return_value = {"ok": False, "verdict": "quarantined"}
        mock_post.return_value = mock_resp

        client = self._get_client()
        result = client.push_garment("dressifye", {"name": "X"})
        self.assertFalse(result["success"])
        self.assertEqual(result.get("verdict"), "quarantined")

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.post")
    def test_push_garment_auth_failure_401(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        client = self._get_client()
        result = client.push_garment("dressifye", {"name": "X"})
        self.assertFalse(result["success"])

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.post")
    def test_push_garment_timeout(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.Timeout()

        client = self._get_client()
        result = client.push_garment("dressifye", {"name": "X"})
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.post")
    def test_push_garment_connection_error(self, mock_post):
        import requests as req_lib
        mock_post.side_effect = req_lib.ConnectionError()

        client = self._get_client()
        result = client.push_garment("dressifye", {"name": "X"})
        self.assertFalse(result["success"])

    # ------------------------------------------------------------------
    # list_garments
    # ------------------------------------------------------------------

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.get")
    def test_list_garments_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "garments": [{"id": "1", "title": "Elbise"}],
            "next_cursor": "",
        }
        mock_get.return_value = mock_resp

        client = self._get_client()
        result = client.list_garments("dressifye")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["garments"]), 1)

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.get")
    def test_list_garments_calls_correct_url(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"garments": [], "next_cursor": ""}
        mock_get.return_value = mock_resp

        client = self._get_client()
        client.list_garments("stylecoree", limit=10, cursor="abc")

        called_url = mock_get.call_args[0][0]
        self.assertIn("/v1/garments", called_url)
        self.assertNotIn("/api/v1/garments", called_url)  # URL düzeltmesi doğrulama

    # ------------------------------------------------------------------
    # disabled / config missing
    # ------------------------------------------------------------------

    def test_disabled_client_returns_reason(self):
        with self.settings(GARMENT_CORE_TS_ENABLED=False):
            client = self._get_client()
            result = client.push_garment("dressifye", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "disabled")

    def test_missing_url_returns_config_missing(self):
        with self.settings(GARMENT_CORE_TS_URL=""):
            client = self._get_client()
            result = client.push_garment("dressifye", {})
        self.assertFalse(result["success"])
        self.assertEqual(result.get("reason"), "config_missing")

    # ------------------------------------------------------------------
    # health_check
    # ------------------------------------------------------------------

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.get")
    def test_health_check_true(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        client = self._get_client()
        self.assertTrue(client.health_check())

    @patch("apps.core.clients.dressifye_saas_ts_client.requests.get")
    def test_health_check_false_on_error(self, mock_get):
        import requests as req_lib
        mock_get.side_effect = req_lib.ConnectionError()

        client = self._get_client()
        self.assertFalse(client.health_check())

    def test_health_check_false_when_disabled(self):
        with self.settings(GARMENT_CORE_TS_ENABLED=False):
            client = self._get_client()
        self.assertFalse(client.health_check())
