"""
Harici AI sağlayıcı soyutlaması, fabrika ve kota yönetimi.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import httpx
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.ai_integrations.exceptions import (
    AIProviderError,
    InvalidInputError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    QuotaExceededError,
)
from apps.ai_integrations.http_utils import raise_for_ai_http_status
from apps.ai_integrations.models import AIProvider, AIProcessingTask, AIQuotaLog
from apps.ai_integrations.validators import validate_ai_input, validate_safe_https_url
from apps.subscriptions.models import UserSubscription

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def attach_failure_context(task: AIProcessingTask, exc: BaseException) -> None:
    """
    İstisnayı ``task.record_failure`` ile ``output_data`` üzerine yazar (kaydetme çağıran yapar).

    Args:
        task: Güncellenecek görev örneği.
        exc: Yakalanan hata.
    """
    ctx: dict[str, Any] = {
        "ai_task_id": task.pk,
        "ai_provider": task.provider.name if task.provider_id else None,
    }
    if isinstance(exc, AIProviderError) and getattr(exc, "context", None):
        ctx.update(exc.context)
    sc = getattr(exc, "status_code", None)
    if sc is not None:
        ctx["status_code"] = sc
    raw: str | None = None
    if isinstance(exc, ProviderUnavailableError) and exc.response_body:
        raw = exc.response_body
    task.record_failure(
        type(exc).__name__,
        str(exc),
        context=ctx,
        raw_response=raw,
    )


def _run_async(coro: Any) -> Any:
    """Celery/sync bağlamında async sağlayıcı metodlarını çalıştırır."""
    return asyncio.run(coro)


def enforce_provider_rate_limit(provider_row: AIProvider) -> None:
    """
    Dakikalık pencerede sayaç artırır; limit aşılırsa hata fırlatır.

    Args:
        provider_row: Veritabanı sağlayıcı satırı.

    Raises:
        ProviderUnavailableError: Limit aşıldıysa.
    """
    window = int(time.time()) // 60
    key = f"ai_rl:{provider_row.pk}:{window}"
    try:
        n = cache.incr(key, delta=1)
    except ValueError:
        cache.add(key, 1, timeout=120)
        n = 1
    if n > provider_row.rate_limit_per_minute:
        logger.warning(
            "AI provider rate limit exceeded",
            extra={"ai_event": "rate_limit", "ai_provider_id": provider_row.pk},
        )
        raise ProviderRateLimitError(
            _("Sağlayıcı istek limiti aşıldı; kısa süre sonra tekrar deneyin."),
            retry_after=60,
        )


class BaseAIProvider(ABC):
    """Harici AI API'si için ortak arayüz (async httpx)."""

    def __init__(self, provider_row: AIProvider) -> None:
        self._row = provider_row
        self._base_url = (provider_row.base_url or "").rstrip("/")
        self._config: dict[str, Any] = provider_row.config or {}

    def _api_key(self) -> str:
        raw = (self._row.api_key_encrypted or "").strip()
        if raw:
            return raw
        env_map = {
            AIProvider.NAME_WEARVIEW: getattr(settings, "WEARVIEW_API_KEY", ""),
            AIProvider.NAME_ZMO: getattr(settings, "ZMO_API_KEY", ""),
            AIProvider.NAME_STYLE3D: getattr(settings, "STYLE3D_API_KEY", ""),
        }
        return str(env_map.get(self._row.name, "") or "").strip()

    def _env_base_url(self) -> str:
        env_map = {
            AIProvider.NAME_WEARVIEW: getattr(settings, "WEARVIEW_BASE_URL", ""),
            AIProvider.NAME_ZMO: getattr(settings, "ZMO_BASE_URL", ""),
            AIProvider.NAME_STYLE3D: getattr(settings, "STYLE3D_BASE_URL", ""),
        }
        return str(env_map.get(self._row.name, "") or "").strip().rstrip("/")

    def effective_base_url(self) -> str:
        """DB'deki base_url boşsa ortam değişkeninden tamamlar."""
        if self._base_url:
            return self._base_url
        return self._env_base_url()

    def _log_event(self, event: str, **data: Any) -> None:
        """
        Standart ``logging`` ile yapılandırılmış günlük.

        ``extra`` anahtarları: ai_event, ai_provider ve çağıranın ilettiği ai_* alanları.
        """
        extra: dict[str, Any] = {"ai_event": event, "ai_provider": self._row.name}
        for k, v in data.items():
            key = k if str(k).startswith("ai_") else f"ai_{k}"
            extra[key] = v
        logger.info("ai_integrations.%s", event, extra=extra)

    def _handle_http_error(self, resp: httpx.Response, task_id: int) -> None:
        """Başarısız HTTP yanıtını günlükler; başarılıysa sessizce döner."""
        if resp.is_success:
            return
        preview = (resp.text or "")[:1000]
        try:
            req_url = str(resp.request.url)
        except Exception:
            req_url = ""
        self._log_event(
            "api_http_error",
            task_id=task_id,
            url=req_url,
            status_code=resp.status_code,
            body_preview=preview,
        )
        raise_for_ai_http_status(resp)

    @abstractmethod
    def validate_input(self, task: AIProcessingTask) -> bool:
        """Girdi şemasını doğrular; hata halinde InvalidInputError fırlatır."""

    @abstractmethod
    def estimate_credits(self, task: AIProcessingTask) -> int:
        """Bu iş için tahmini kredi maliyeti."""

    @abstractmethod
    async def process(self, task: AIProcessingTask) -> dict[str, Any]:
        """Harici işi başlatır; dönüşte en azından external_task_id içermelidir."""

    @abstractmethod
    async def check_status(self, external_task_id: str) -> str:
        """Uzak sistemdeki durumu ham string olarak döner (queued/processing/completed/failed)."""

    @abstractmethod
    async def cancel_task(self, external_task_id: str) -> bool:
        """İptal başarılıysa True."""


class WearViewProvider(BaseAIProvider):
    """WearView sanal deneme / model üretimi (yapılandırılabilir uç yollar)."""

    def validate_input(self, task: AIProcessingTask) -> bool:
        validate_ai_input(task.input_data or {}, task.task_type)
        return True

    def estimate_credits(self, task: AIProcessingTask) -> int:
        overrides = self._config.get("credit_costs") or {}
        key = task.task_type
        if isinstance(overrides, dict) and key in overrides:
            return int(overrides[key])
        defaults = {
            AIProcessingTask.TASK_TRYON: 5,
            AIProcessingTask.TASK_MODEL_GENERATION: 10,
            AIProcessingTask.TASK_TEXTURE: 8,
            AIProcessingTask.TASK_BACKGROUND_REMOVAL: 3,
            AIProcessingTask.TASK_POSE_TRANSFER: 6,
            AIProcessingTask.TASK_GARMENT_3D: 15,
            AIProcessingTask.TASK_PATTERN_GENERATION: 12,
            AIProcessingTask.TASK_FABRIC_SIMULATION: 14,
        }
        return int(defaults.get(task.task_type, 5))

    async def process(self, task: AIProcessingTask) -> dict[str, Any]:
        api_key = self._api_key()
        base = self.effective_base_url()
        if not base:
            raise ProviderUnavailableError(_("WearView base_url tanımlı değil."))
        if not api_key and not settings.DEBUG:
            raise ProviderUnavailableError(_("WearView API anahtarı eksik."))

        path = self._config.get("tryon_path", "/virtual-try-on/jobs")
        if task.task_type != AIProcessingTask.TASK_TRYON:
            path = self._config.get("generic_job_path", "/jobs")

        url = f"{base}{path}"
        payload: dict[str, Any] = {
            "task_type": task.task_type,
            "input": task.input_data or {},
            "client_task_ref": str(task.pk),
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if settings.DEBUG and not api_key:
            self._log_event("stub_response", task_id=task.pk, url=url)
            return {
                "external_task_id": f"stub-wearview-{task.pk}",
                "raw": {"stub": True},
            }

        od = dict(task.output_data or {})
        od["submit"] = {
            "url": url,
            "method": "POST",
            "task_type": task.task_type,
            "payload_keys": list(payload.keys()),
        }
        task.output_data = od
        task.save(update_fields=["output_data", "updated_at"])

        self._log_event("api_request", task_id=task.pk, url=url, method="POST")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(str(exc)) from exc

        self._log_event(
            "api_response",
            task_id=task.pk,
            url=url,
            status_code=resp.status_code,
            body_preview=(resp.text or "")[:2000],
        )
        self._handle_http_error(resp, task.pk)

        try:
            data = resp.json()
        except ValueError as exc:
            raise InvalidInputError(
                _("Geçersiz JSON yanıtı."),
                context={"raw_response": (resp.text or "")[:8000]},
            ) from exc

        ext = (
            data.get("id")
            or data.get("job_id")
            or data.get("task_id")
            or data.get("external_id")
        )
        if not ext:
            raise ProviderUnavailableError(_("Yanıtta external task id yok."))
        self._log_event("api_success", task_id=task.pk, url=url, status_code=resp.status_code)
        return {"external_task_id": str(ext), "raw": data}

    async def check_status(self, external_task_id: str) -> str:
        api_key = self._api_key()
        base = self.effective_base_url()
        status_path = self._config.get("status_path", "/jobs/{id}/status").replace("{id}", external_task_id)
        url = f"{base}{status_path}"
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if settings.DEBUG and not api_key:
            return "completed"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                resp = await client.get(url, headers=headers)
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(str(exc)) from exc

        if resp.status_code >= 400:
            return "failed"
        try:
            body = resp.json()
        except ValueError:
            return "processing"
        state = str(body.get("status") or body.get("state") or "processing").lower()
        return state

    async def cancel_task(self, external_task_id: str) -> bool:
        api_key = self._api_key()
        base = self.effective_base_url()
        cancel_path = self._config.get("cancel_path", "/jobs/{id}/cancel").replace("{id}", external_task_id)
        url = f"{base}{cancel_path}"
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if settings.DEBUG and not api_key:
            return True

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                resp = await client.post(url, headers=headers)
        except httpx.RequestError:
            return False
        return resp.status_code < 400


class ZmoProvider(BaseAIProvider):
    """Zmo.ai — yapılandırılabilir genel iş gönderimi."""

    def validate_input(self, task: AIProcessingTask) -> bool:
        validate_ai_input(task.input_data or {}, task.task_type)
        return True

    def estimate_credits(self, task: AIProcessingTask) -> int:
        return int((self._config.get("credit_costs") or {}).get(task.task_type, 4))

    async def process(self, task: AIProcessingTask) -> dict[str, Any]:
        api_key = self._api_key()
        base = self.effective_base_url()
        if not base:
            raise ProviderUnavailableError(_("Zmo base_url tanımlı değil."))
        path = self._config.get("job_path", "/fashion/jobs")
        url = f"{base}{path}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if settings.DEBUG and not api_key:
            self._log_event("stub_response", task_id=task.pk, url=url)
            return {"external_task_id": f"stub-zmo-{task.pk}", "raw": {"stub": True}}

        self._log_event("api_request", task_id=task.pk, url=url, method="POST")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                resp = await client.post(
                    url,
                    json={"type": task.task_type, "input": task.input_data or {}},
                    headers=headers,
                )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        self._log_event(
            "api_response",
            task_id=task.pk,
            url=url,
            status_code=resp.status_code,
            body_preview=(resp.text or "")[:2000],
        )
        self._handle_http_error(resp, task.pk)
        try:
            data = resp.json()
        except ValueError as exc:
            raise InvalidInputError(
                _("Geçersiz JSON yanıtı."),
                context={"raw_response": (resp.text or "")[:8000]},
            ) from exc
        ext = data.get("id") or data.get("job_id")
        if not ext:
            raise ProviderUnavailableError(_("Zmo yanıtında id yok."))
        self._log_event("api_success", task_id=task.pk, url=url, status_code=resp.status_code)
        return {"external_task_id": str(ext), "raw": data}

    async def check_status(self, external_task_id: str) -> str:
        return await WearViewProvider(self._row).check_status(external_task_id)

    async def cancel_task(self, external_task_id: str) -> bool:
        return await WearViewProvider(self._row).cancel_task(external_task_id)


class Style3DProvider(BaseAIProvider):
    """Style3D — dijital numune / desen işleri."""

    def validate_input(self, task: AIProcessingTask) -> bool:
        validate_ai_input(task.input_data or {}, task.task_type)
        return True

    def estimate_credits(self, task: AIProcessingTask) -> int:
        return int((self._config.get("credit_costs") or {}).get(task.task_type, 12))

    async def process(self, task: AIProcessingTask) -> dict[str, Any]:
        api_key = self._api_key()
        base = self.effective_base_url()
        if not base:
            raise ProviderUnavailableError(_("Style3D base_url tanımlı değil."))
        path = self._config.get("job_path", "/sampling/jobs")
        url = f"{base}{path}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if settings.DEBUG and not api_key:
            self._log_event("stub_response", task_id=task.pk, url=url)
            return {"external_task_id": f"stub-style3d-{task.pk}", "raw": {"stub": True}}

        self._log_event("api_request", task_id=task.pk, url=url, method="POST")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                resp = await client.post(
                    url,
                    json={"task_type": task.task_type, "payload": task.input_data or {}},
                    headers=headers,
                )
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        self._log_event(
            "api_response",
            task_id=task.pk,
            url=url,
            status_code=resp.status_code,
            body_preview=(resp.text or "")[:2000],
        )
        self._handle_http_error(resp, task.pk)
        try:
            data = resp.json()
        except ValueError as exc:
            raise InvalidInputError(
                _("Geçersiz JSON yanıtı."),
                context={"raw_response": (resp.text or "")[:8000]},
            ) from exc
        ext = data.get("id") or data.get("job_id")
        if not ext:
            raise ProviderUnavailableError(_("Style3D yanıtında id yok."))
        self._log_event("api_success", task_id=task.pk, url=url, status_code=resp.status_code)
        return {"external_task_id": str(ext), "raw": data}

    async def check_status(self, external_task_id: str) -> str:
        return await WearViewProvider(self._row).check_status(external_task_id)

    async def cancel_task(self, external_task_id: str) -> bool:
        return await WearViewProvider(self._row).cancel_task(external_task_id)


_REGISTRY: dict[str, type[BaseAIProvider]] = {
    AIProvider.NAME_WEARVIEW: WearViewProvider,
    AIProvider.NAME_ZMO: ZmoProvider,
    AIProvider.NAME_STYLE3D: Style3DProvider,
}


class ProviderFactory:
    """Sağlayıcı adına göre somut sınıf örneği üretir."""

    @staticmethod
    def get_provider(provider_name: str) -> BaseAIProvider:
        """
        Args:
            provider_name: wearview | zmo | style3d

        Returns:
            Yapılandırılmış sağlayıcı örneği.

        Raises:
            ProviderUnavailableError: Kayıt veya aktif yapılandırma yoksa.
            InvalidInputError: Bilinmeyen isim.
        """
        key = (provider_name or "").strip().lower()
        if key not in _REGISTRY:
            raise InvalidInputError(_("Bilinmeyen sağlayıcı."))
        row = AIProvider.objects.filter(name=key, is_active=True).first()
        if row is None:
            raise ProviderUnavailableError(_("Bu sağlayıcı için aktif yapılandırma yok."))
        cls = _REGISTRY[key]
        return cls(row)


class QuotaManager:
    """Plan üzerinden harici AI kredisi ve abonelik satırı yönetimi."""

    @staticmethod
    def _next_calendar_month_start(dt: datetime) -> datetime:
        """Verilen zaman damgasını takip eden ayın ilk anını döner (TZ korunur)."""
        if dt.month == 12:
            return dt.replace(
                year=dt.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        return dt.replace(
            month=dt.month + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    @staticmethod
    def get_upcoming_reset_date_for_tenant(tenant: Tenant) -> datetime | None:
        """
        Kiracıdaki herhangi bir kullanıcının aboneliğine göre en erken sıfırlama zamanı (salt okunur).

        Çoklu abonelik varsa ilk bulunanı kullanır; yoksa None.
        """
        sub = (
            UserSubscription.objects.filter(tenant=tenant)
            .select_related("plan")
            .order_by("pk")
            .first()
        )
        if sub is None or sub.user_id is None:
            return None
        return QuotaManager.get_upcoming_reset_date(sub.user, tenant.pk)

    @staticmethod
    def get_upcoming_reset_date(user: AbstractBaseUser, tenant_id: int) -> datetime | None:
        """
        Aboneliğin bir sonraki harici AI kredi sıfırlama zamanını döner (salt okunur).

        Veritabanını değiştirmez; `ai_credits_reset_date` gelecekteyse onu kullanır,
        aksi halde takvim ayı sonrasını hesaplar.
        """
        sub = UserSubscription.objects.filter(user=user, tenant_id=tenant_id).first()
        if sub is None:
            return None
        now = timezone.now()
        if sub.ai_credits_reset_date and sub.ai_credits_reset_date > now:
            return sub.ai_credits_reset_date
        return QuotaManager._next_calendar_month_start(now)

    @staticmethod
    def _ensure_ai_period(sub: UserSubscription) -> None:
        """Takvim ayı sınırında kullanılan krediyi sıfırlar."""
        now = timezone.now()
        if sub.ai_credits_reset_date and now < sub.ai_credits_reset_date:
            return
        sub.ai_credits_used = 0
        sub.ai_credits_reset_date = QuotaManager._next_calendar_month_start(now)
        sub.save(update_fields=["ai_credits_used", "ai_credits_reset_date", "updated_at"])

    @staticmethod
    def check_quota(
        tenant_id: int,
        user: AbstractBaseUser,
        estimated_credits: int,
        *,
        lock_subscription: bool = False,
    ) -> None:
        """
        Yeterli harici AI kredisi var mı kontrol eder.

        Args:
            lock_subscription: True ise ``select_for_update`` (çağıran ``atomic()`` içinde olmalı).

        Raises:
            QuotaExceededError: Plan uygun değil veya kota yetersiz.
        """
        if estimated_credits <= 0:
            raise InvalidInputError(_("Tahmini kredi pozitif olmalıdır."))
        qs = UserSubscription.objects.filter(user=user, tenant_id=tenant_id).select_related(
            "plan"
        )
        if lock_subscription:
            qs = qs.select_for_update()
        sub = qs.first()
        if sub is None or sub.plan is None:
            raise QuotaExceededError(
                _("Aktif abonelik bulunamadı."),
                required=estimated_credits,
                available=0,
            )
        if not sub.plan.external_ai_enabled:
            raise QuotaExceededError(
                _("Planınız harici AI kullanımını içermiyor."),
                required=estimated_credits,
                available=0,
            )
        limit = sub.plan.ai_credits_monthly
        if limit == 0:
            raise QuotaExceededError(
                _("Harici AI kredisi tanımlı değil."),
                required=estimated_credits,
                available=0,
            )
        QuotaManager._ensure_ai_period(sub)
        sub.refresh_from_db(fields=["ai_credits_used", "ai_credits_reset_date"])
        available = max(0, limit - sub.ai_credits_used)
        if sub.ai_credits_used + estimated_credits > limit:
            raise QuotaExceededError(
                _("Yetersiz harici AI kredisi."),
                required=estimated_credits,
                available=available,
            )

    @staticmethod
    @transaction.atomic
    def deduct_credits(
        tenant_id: int,
        user: AbstractBaseUser,
        credits: int,
        task: AIProcessingTask,
    ) -> None:
        """Krediyi düşer ve denetim günlüğü yazar."""
        if credits <= 0:
            return
        sub = (
            UserSubscription.objects.select_for_update()
            .filter(user=user, tenant_id=tenant_id)
            .first()
        )
        if sub is None:
            raise QuotaExceededError(_("Abonelik bulunamadı."), required=credits, available=0)
        QuotaManager._ensure_ai_period(sub)
        sub.refresh_from_db(fields=["ai_credits_used", "ai_credits_reset_date", "plan_id"])
        limit = sub.plan.ai_credits_monthly if sub.plan else 0
        if sub.plan is None or not sub.plan.external_ai_enabled:
            raise QuotaExceededError(_("Plan harici AI içermiyor."), required=credits, available=0)
        if sub.ai_credits_used + credits > limit:
            raise QuotaExceededError(
                _("Yetersiz harici AI kredisi."),
                required=credits,
                available=max(0, limit - sub.ai_credits_used),
            )
        balance_before = sub.ai_credits_used
        sub.ai_credits_used += credits
        balance_after = sub.ai_credits_used
        sub.save(update_fields=["ai_credits_used", "updated_at"])
        AIQuotaLog.objects.create(
            tenant_id=tenant_id,
            user=user,
            task=task,
            credits_used=credits,
            note="deduct",
            transaction_type=AIQuotaLog.TX_USAGE,
            credits_amount=-credits,
            balance_before=balance_before,
            balance_after=balance_after,
            description=_("Harici AI görevi — kredi düşümü"),
        )

    @staticmethod
    @transaction.atomic
    def refund_credits(task: AIProcessingTask, *, reason: str = "") -> None:
        """Başarısız veya iptal edilen işlem için krediyi geri yükler."""
        credits = int(task.credits_used or 0)
        if credits <= 0 or not task.user_id:
            return
        sub = (
            UserSubscription.objects.select_for_update()
            .filter(user_id=task.user_id, tenant_id=task.tenant_id)
            .first()
        )
        if sub is None:
            return
        balance_before = sub.ai_credits_used
        sub.ai_credits_used = max(0, int(sub.ai_credits_used) - credits)
        balance_after = sub.ai_credits_used
        sub.save(update_fields=["ai_credits_used", "updated_at"])
        AIQuotaLog.objects.create(
            tenant_id=task.tenant_id,
            user_id=task.user_id,
            task=task,
            credits_used=credits,
            note="refund",
            transaction_type=AIQuotaLog.TX_REFUND,
            credits_amount=credits,
            balance_before=balance_before,
            balance_after=balance_after,
            description=reason or _("Harici AI görevi — iade"),
        )

    @staticmethod
    @transaction.atomic
    def adjust_credits(
        tenant_id: int,
        user: AbstractBaseUser,
        bonus_credits: int,
        *,
        task: AIProcessingTask | None = None,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AIQuotaLog | None:
        """
        Yönetimsel düzeltme: kullanıcıya ek kredi tanır (kullanılan sayacı düşürür).

        Args:
            tenant_id: Kiracı PK.
            user: Abonelik kullanıcısı.
            bonus_credits: Pozitif: kullanıcıya ek kota (ai_credits_used azalır).
            task: İsteğe bağlı ilişkili görev (denetim günlüğü için).
            description: Günlük açıklaması.

        Returns:
            Oluşturulan günlük veya bonus_credits <= 0 ise None.
        """
        if bonus_credits <= 0:
            return None
        sub = (
            UserSubscription.objects.select_for_update()
            .filter(user=user, tenant_id=tenant_id)
            .first()
        )
        if sub is None:
            return None
        balance_before = sub.ai_credits_used
        sub.ai_credits_used = max(0, int(sub.ai_credits_used) - bonus_credits)
        balance_after = sub.ai_credits_used
        sub.save(update_fields=["ai_credits_used", "updated_at"])
        return AIQuotaLog.objects.create(
            tenant_id=tenant_id,
            user=user,
            task=task,
            credits_used=0,
            note="adjustment",
            transaction_type=AIQuotaLog.TX_ADJUSTMENT,
            credits_amount=bonus_credits,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description or _("Yönetimsel kota düzeltmesi"),
            metadata=metadata or {},
        )


def run_provider_validate_and_estimate(task: AIProcessingTask) -> tuple[BaseAIProvider, int]:
    """Fabrika + doğrulama + tahmini kredi (senkron)."""
    provider = ProviderFactory.get_provider(task.provider.name)
    provider.validate_input(task)
    est = provider.estimate_credits(task)
    return provider, est


def run_provider_process(provider: BaseAIProvider, task: AIProcessingTask) -> dict[str, Any]:
    """Async process çağrısını senkron çalıştırır."""
    return _run_async(provider.process(task))


def run_provider_process_with_fallback(
    primary: BaseAIProvider,
    task: AIProcessingTask,
) -> tuple[dict[str, Any], str]:
    """
    Önce birincil sağlayıcıyı dener; yalnızca ProviderUnavailableError sonrası yedeğe geçer.

    Başarılı yedek kullanımda ``task.provider`` güncellenir ve ``output_data`` içine iz bırakılır.

    Returns:
        (sağlayıcı yanıt sözlüğü, kullanılan sağlayıcı adı).
    """
    primary_name = primary._row.name
    try:
        return run_provider_process(primary, task), primary_name
    except ProviderUnavailableError:
        fb_row = primary._row.fallback_provider
        if fb_row is None or not fb_row.is_active:
            raise
        fb_cls = _REGISTRY.get(fb_row.name)
        if fb_cls is None:
            raise
        fallback = fb_cls(fb_row)
        logger.warning(
            "ai_integrations.provider_fallback",
            extra={
                "ai_event": "provider_fallback",
                "ai_task_id": task.pk,
                "ai_from": primary_name,
                "ai_to": fb_row.name,
            },
        )
        result = run_provider_process(fallback, task)
        task.provider_id = fb_row.pk
        out = task.output_data or {}
        trail = list(out.get("api_trail") or [])
        trail.append({"from": primary_name, "to": fb_row.name, "event": "fallback"})
        out["api_trail"] = trail
        task.output_data = out
        task.save(update_fields=["provider", "output_data", "updated_at"])
        return result, fb_row.name


def run_provider_check_status(provider: BaseAIProvider, external_task_id: str) -> str:
    """Uzak durum sorgusu."""
    return _run_async(provider.check_status(external_task_id))


def run_provider_cancel(provider: BaseAIProvider, external_task_id: str) -> bool:
    """Uzak iptal."""
    return _run_async(provider.cancel_task(external_task_id))
