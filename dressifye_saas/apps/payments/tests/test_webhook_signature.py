import hashlib
import hmac
import json

from django.test import RequestFactory, override_settings
from django.test import TestCase

from apps.payments.webhook_signature import verify_iyzico_webhook_signature


def _hpp_sig(secret: str, payload: dict) -> str:
    et = str(payload.get("iyziEventType") or "")
    msg = (
        secret
        + et
        + str(payload.get("iyziPaymentId"))
        + str(payload.get("token"))
        + str(payload.get("paymentConversationId"))
        + str(payload.get("status") or "")
    )
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


class WebhookSignatureTests(TestCase):
    def test_hpp_format_accepts_valid_header(self):
        secret = "test-secret-key"
        payload = {
            "iyziEventType": "CHECKOUT_FORM_AUTH",
            "iyziPaymentId": "999",
            "token": "tok-abc",
            "paymentConversationId": "conv-1",
            "status": "SUCCESS",
        }
        sig = _hpp_sig(secret, payload)
        rf = RequestFactory()
        req = rf.post(
            "/odemeler/webhook/iyzico/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_IYZ_SIGNATURE_V3=sig,
        )
        with override_settings(
            IYZICO_SECRET_KEY=secret,
            IYZICO_WEBHOOK_VERIFY_SIGNATURE=True,
            IYZICO_WEBHOOK_ALLOW_UNSIGNED=False,
        ):
            self.assertTrue(verify_iyzico_webhook_signature(req, payload))

    def test_rejects_bad_signature(self):
        secret = "test-secret-key"
        payload = {
            "iyziEventType": "CHECKOUT_FORM_AUTH",
            "iyziPaymentId": "999",
            "token": "tok-abc",
            "paymentConversationId": "conv-1",
            "status": "SUCCESS",
        }
        rf = RequestFactory()
        req = rf.post(
            "/odemeler/webhook/iyzico/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_IYZ_SIGNATURE_V3="deadbeef",
        )
        with override_settings(
            IYZICO_SECRET_KEY=secret,
            IYZICO_WEBHOOK_VERIFY_SIGNATURE=True,
            IYZICO_WEBHOOK_ALLOW_UNSIGNED=False,
        ):
            self.assertFalse(verify_iyzico_webhook_signature(req, payload))
