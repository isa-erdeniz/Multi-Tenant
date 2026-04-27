"""
Harici AI entegrasyonu: kota, failover, webhook imzası ve eşzamanlı kota.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import threading
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from apps.ai_integrations.exceptions import ProviderUnavailableError, QuotaExceededError
from apps.ai_integrations.models import AIProcessingTask, AIProvider
from apps.ai_integrations.services import QuotaManager, WearViewProvider, run_provider_process_with_fallback
from apps.subscriptions.models import Plan

User = get_user_model()


def _ensure_plan(user):
    """post_save sinyali plan=None ile subscription oluşturabilir; bu helper test planını garantiler."""
    sub = user.subscription
    if sub.plan is None:
        plan, _ = Plan.objects.get_or_create(
            slug="ai-test-plan",
            defaults={
                "name": "AI Test Plan",
                "external_ai_enabled": False,
                "ai_credits_monthly": 0,
            },
        )
        sub.plan = plan
        sub.save(update_fields=["plan"])
    return sub.plan


def _tryon_payload() -> dict:
    return {
        "provider": "wearview",
        "task_type": "tryon",
        "input_data": {
            "garment_image_url": "https://example.com/g.jpg",
            "model_image_url": "https://example.com/m.jpg",
        },
    }


class AIProcessQuotaTests(TestCase):
    @override_settings(DEBUG=True)
    def test_process_view_quota_exceeded_does_not_enqueue(self):
        user = User.objects.create_user(
            username="quota0@example.com",
            email="quota0@example.com",
            password="x",
        )
        # Signal tenant_id'yi DB'de günceller ama in-memory instance'ı değil;
        # TenantContextMiddleware user.tenant'ı okur — refresh şart.
        user.refresh_from_db()
        sub = user.subscription
        plan = _ensure_plan(user)
        plan.external_ai_enabled = True
        plan.ai_credits_monthly = 5
        plan.save()
        # ai_credits_reset_date None olunca _ensure_ai_period kullanımı sıfırlar;
        # gelecek tarih vererek sıfırlamayı engelliyoruz.
        from django.utils import timezone as tz
        sub.ai_credits_used = 5
        sub.ai_credits_reset_date = tz.now() + datetime.timedelta(days=30)
        sub.save(update_fields=["ai_credits_used", "ai_credits_reset_date"])

        client = APIClient()
        client.force_authenticate(user=user)
        # TenantContextMiddleware Django request.user'ından okur (DRF wrapping öncesi);
        # header ile tenant'ı doğrudan geçmek daha güvenilir.
        with patch("apps.ai_integrations.views.process_ai_task.delay") as delay_mock:
            r = client.post(
                "/api/v1/ai/process/",
                _tryon_payload(),
                format="json",
                HTTP_X_GARMENT_CORE_TENANT_SLUG=user.tenant.slug,
            )
        self.assertEqual(r.status_code, 402)
        delay_mock.assert_not_called()


class FallbackProviderTests(TestCase):
    def test_fallback_after_provider_unavailable(self):
        wear = AIProvider.objects.get(name=AIProvider.NAME_WEARVIEW)
        zmo = AIProvider.objects.get(name=AIProvider.NAME_ZMO)
        wear.fallback_provider = zmo
        wear.save(update_fields=["fallback_provider"])

        user = User.objects.create_user(
            username="fb@example.com",
            email="fb@example.com",
            password="x",
        )
        task = AIProcessingTask.all_objects.create(
            tenant_id=user.tenant_id,
            user=user,
            provider=wear,
            task_type=AIProcessingTask.TASK_TRYON,
            status=AIProcessingTask.STATUS_QUEUED,
            input_data=_tryon_payload()["input_data"],
        )

        primary = WearViewProvider(wear)

        def _fake_run(provider, t):
            if provider._row.name == AIProvider.NAME_WEARVIEW:
                raise ProviderUnavailableError("simulated down")
            return {"external_task_id": "ext-fb-1", "raw": {"ok": True}}

        with patch("apps.ai_integrations.services.run_provider_process", side_effect=_fake_run):
            result, used = run_provider_process_with_fallback(primary, task)
        task.refresh_from_db()
        self.assertEqual(used, AIProvider.NAME_ZMO)
        self.assertEqual(result.get("external_task_id"), "ext-fb-1")
        self.assertEqual(task.provider_id, zmo.pk)


class WebhookSignatureTests(TestCase):
    @override_settings(DEBUG=False, AI_WEBHOOK_ALLOW_UNSIGNED=False)
    def test_wearview_webhook_signature_valid_and_invalid(self):
        user = User.objects.create_user(
            username="wh@example.com",
            email="wh@example.com",
            password="x",
        )
        wear = AIProvider.objects.get(name=AIProvider.NAME_WEARVIEW)
        wear.webhook_secret_encrypted = "wh-secret"
        wear.save(update_fields=["webhook_secret_encrypted"])

        AIProcessingTask.all_objects.create(
            tenant_id=user.tenant_id,
            user=user,
            provider=wear,
            task_type=AIProcessingTask.TASK_TRYON,
            status=AIProcessingTask.STATUS_PROCESSING,
            input_data={},
            external_task_id="ext-wh-1",
        )

        body_dict = {"external_task_id": "ext-wh-1", "status": "completed"}
        body = json.dumps(body_dict).encode("utf-8")
        good_sig = hmac.new(b"wh-secret", body, hashlib.sha256).hexdigest()

        c = Client()
        r_ok = c.post(
            "/webhooks/ai/wearview/",
            data=body,
            content_type="application/json",
            HTTP_X_WEARVIEW_SIGNATURE=good_sig,
        )
        self.assertEqual(r_ok.status_code, 200)

        r_bad = c.post(
            "/webhooks/ai/wearview/",
            data=body,
            content_type="application/json",
            HTTP_X_WEARVIEW_SIGNATURE="deadbeef",
        )
        self.assertEqual(r_bad.status_code, 403)


class ConcurrentQuotaTests(TransactionTestCase):
    def test_concurrent_deduct_does_not_exceed_limit(self):
        from django.db import connection as _conn

        if _conn.vendor == "sqlite":
            self.skipTest(
                "SQLite eşzamanlı satır kilitlemeyi desteklemiyor; PostgreSQL gerekir."
            )

        user = User.objects.create_user(
            username="race@example.com",
            email="race@example.com",
            password="x",
        )
        # Signal DB'yi günceller, in-memory değil; FK okuma için refresh şart.
        user.refresh_from_db()
        sub = user.subscription
        plan = _ensure_plan(user)
        plan.external_ai_enabled = True
        plan.ai_credits_monthly = 5
        plan.save()
        sub.ai_credits_used = 0
        sub.save()

        wear = AIProvider.objects.get(name=AIProvider.NAME_WEARVIEW)
        errors: list[int] = []
        lock = threading.Lock()
        barrier = threading.Barrier(8)

        def worker() -> None:
            connection.close()
            barrier.wait()
            task = AIProcessingTask.all_objects.create(
                tenant_id=user.tenant_id,
                user=user,
                provider=wear,
                task_type=AIProcessingTask.TASK_TRYON,
                status=AIProcessingTask.STATUS_QUEUED,
                input_data={},
            )
            try:
                with transaction.atomic():
                    QuotaManager.deduct_credits(user.tenant_id, user, 1, task)
            except QuotaExceededError:
                with lock:
                    errors.append(1)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        sub.refresh_from_db()
        self.assertEqual(sub.ai_credits_used, 5)
        self.assertEqual(len(errors), 3)
