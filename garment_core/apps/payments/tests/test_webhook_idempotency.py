import json

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.payments.models import WebhookEvent


class WebhookIdempotencyTests(TestCase):
    def setUp(self):
        self.client = Client()

    @override_settings(
        IYZICO_WEBHOOK_VERIFY_SIGNATURE=False,
        IYZICO_SECRET_KEY="",
    )
    def test_duplicate_iyzi_reference_returns_idempotent(self):
        payload = {
            "iyziEventType": "SUBSCRIPTION_CANCELED",
            "iyziReferenceCode": "test-ref-idem-001",
            "subscriptionReferenceCode": "sub-does-not-exist",
        }
        url = reverse("payments:iyzico_webhook")
        body = json.dumps(payload)
        r1 = self.client.post(
            url,
            data=body,
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)

        r2 = self.client.post(
            url,
            data=body,
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertTrue(data.get("idempotent"))
        self.assertEqual(WebhookEvent.objects.count(), 1)
