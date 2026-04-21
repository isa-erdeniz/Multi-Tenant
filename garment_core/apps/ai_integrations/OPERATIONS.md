# AI Integrations — operasyon özeti

## Celery Beat

| Anahtar | Görev | Sıklık |
|---------|--------|--------|
| `ai-check-pending-tasks` | `apps.ai_integrations.tasks.check_pending_tasks` | Her 2 dakika (`crontab(minute="*/2")`) |
| `ai-reset-monthly-credits` | `apps.ai_integrations.tasks.reset_monthly_credits` | Günlük 04:00 |
| `ai-cleanup-old-tasks` | `apps.ai_integrations.tasks.cleanup_old_tasks` | Günlük 02:15 |

## Celery görevleri (manuel / zincir)

- `process_ai_task` — Kuyruktaki harici AI işini işler; failover ve kota düşümü burada.
- `check_pending_tasks` — Uzun süredir `processing` kalan ve webhook gelmeyen kayıtları uzaktan sorgular.
- `cleanup_old_tasks` — 90 günden eski terminal görevleri siler; dönüş `{"deleted": n}`.
- `reset_monthly_credits` — Aboneliklerde dönemsel harici AI kredi sıfırlaması (`_ensure_ai_period`).
- `notify_task_completion` — Tamamlanma logu (ileride bildirim genişletilebilir).

## Management komutları

- `python manage.py ai_integrations_health` — Aktif `AIProvider`, Celery `ping()` ve API anahtarlarının ortamda tanımlı olup olmadığının JSON özeti. Üretimde ` --strict` ile worker veya sağlayıcı yoksa çıkış kodu 1.

## Abonelik / kota

- Kota düşümü ve yarış güvenliği `QuotaManager.deduct_credits` içinde `select_for_update` ile yapılır.
- `POST /api/v1/ai/process/` kota ve sağlayıcı rate limit kontrolünü iş oluşturduktan sonra, Celery’ye göndermeden önce yapar.
