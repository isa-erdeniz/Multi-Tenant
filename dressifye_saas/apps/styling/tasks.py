import json
import logging
import re
import time

from django.conf import settings

logger = logging.getLogger(__name__)


def _build_placeholder_outfit(garment_list: list, prompt: str) -> dict:
    """
    MEHLR yokken basit bir öneri üretir.
    """
    tops = [
        g
        for g in garment_list
        if "üst" in g["category"].lower() or "elbise" in g["category"].lower()
    ]
    bottoms = [g for g in garment_list if "alt" in g["category"].lower()]
    shoes = [g for g in garment_list if "ayakkabı" in g["category"].lower()]

    outfit_items = []
    if tops:
        outfit_items.append(
            {"garment_id": tops[0]["id"], "role": "üst", "note": tops[0]["name"]}
        )
    if bottoms:
        outfit_items.append(
            {"garment_id": bottoms[0]["id"], "role": "alt", "note": bottoms[0]["name"]}
        )
    if shoes:
        outfit_items.append(
            {
                "garment_id": shoes[0]["id"],
                "role": "ayakkabı",
                "note": shoes[0]["name"],
            }
        )

    text = "Gardırobunuzdan uygun parçalar seçildi. "
    text += "MEHLR AI motoru aktif olduğunda daha kişiselleştirilmiş öneriler alacaksınız."

    return {
        "text": text,
        "data": {
            "outfit": outfit_items,
            "style_notes": text,
            "occasion_fit": "Orta",
            "is_placeholder": True,
        },
    }


def _process_style_session_sync(session_id: int):
    """Senkron işlem (Celery yoksa)."""
    from apps.core.tenant_context import use_tenant
    from apps.styling.models import StyleSession
    from apps.wardrobe.models import Garment
    from apps.core.clients.mehlr_client import MEHLRClient

    try:
        session = StyleSession.all_objects.select_related("user").get(id=session_id)
    except StyleSession.DoesNotExist:
        logger.error(f"StyleSession bulunamadı: {session_id}")
        return

    tenant = getattr(session.user, "tenant", None)
    with use_tenant(tenant):
        session.status = "processing"
        session.save(update_fields=["status"])

        start = time.time()

        garments = Garment.objects.filter(
            user=session.user, is_active=True
        ).select_related("category")

        garment_list = [
            {
                "id": g.id,
                "name": g.name,
                "category": g.category.name if g.category else "Diğer",
                "color": g.color,
                "brand": g.brand,
                "season": g.get_season_display(),
                "tags": g.tags,
            }
            for g in garments
        ]

        client = MEHLRClient()
        result = client.analyze(
            project=settings.MEHLR_PROJECT,
            prompt=session.user_prompt,
            context={
                "user_context": session.context,
                "wardrobe": garment_list,
                "garment_count": len(garment_list),
                "task": "outfit_suggestion",
            },
        )

        session.processing_time = time.time() - start

        if result.get("success"):
            data = result.get("data") or {}
            raw_response = data.get("response", data.get("style_notes", ""))
            session.ai_response = raw_response

            outfit_data = None
            try:
                outfit_data = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError):
                pass

            if not outfit_data:
                json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
                if json_match:
                    try:
                        outfit_data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass

            if outfit_data:
                outfit_block = outfit_data.get("outfit", outfit_data)
                session.suggested_outfit = outfit_block

                if "response" in outfit_data:
                    session.ai_response = outfit_data["response"]

                outfit_items = (
                    outfit_block.get("outfit", [])
                    if isinstance(outfit_block, dict)
                    else []
                )
                garment_ids = [
                    item["garment_id"]
                    for item in outfit_items
                    if isinstance(item, dict) and "garment_id" in item
                ]
                if garment_ids:
                    suggested = Garment.objects.filter(
                        id__in=garment_ids, user=session.user
                    )
                    session.garments_suggested.set(suggested)

            if not session.title:
                occasion = session.context.get("occasion", "")
                session.title = f"{occasion} kombini" if occasion else "Stil önerisi"

            session.status = "completed"
        else:
            logger.warning(
                f"MEHLR yanıt vermedi, placeholder kullanılıyor: {result.get('error')}"
            )
            placeholder_outfit = _build_placeholder_outfit(
                garment_list, session.user_prompt
            )
            session.ai_response = placeholder_outfit["text"]
            session.suggested_outfit = placeholder_outfit["data"]
            session.status = "completed"

        session.save()
        logger.info(
            f"StyleSession {session_id} tamamlandı ({session.processing_time:.1f}s)"
        )


try:
    from celery import shared_task

    @shared_task(bind=True, max_retries=3, default_retry_delay=10)
    def process_style_session(self, session_id: int):
        try:
            _process_style_session_sync(session_id)
        except Exception as exc:
            raise self.retry(exc=exc)

except ImportError:
    def process_style_session(session_id: int):
        _process_style_session_sync(session_id)
