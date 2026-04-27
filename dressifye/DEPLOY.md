# Dressifye Cloudflare Worker — Deploy Notları

## Cloudflare Dashboard Variables

Workers & Pages → dressifye → Settings → Variables:

| Değişken | Değer |
|---|---|
| `GARMENT_CORE_API_URL` | `https://<dressifye-saas-django>.railway.app` |
| `GARMENT_CORE_TS_URL` | `https://<dressifye-saas-ts>.railway.app` |
| `GARMENT_CORE_TS_API_KEY` | `npm run db:create-api-key` çıktısı |

> `wrangler.toml` içindeki `[vars]` değerleri boş bırakılmıştır — gerçek URL'leri
> **Cloudflare panelinde** environment variable olarak set edin (secrets için `wrangler secret put`).

## D1 Setup

```bash
wrangler d1 execute dressifye-db --file=./d1/pricing_plans.sql
wrangler d1 execute dressifye-db --file=./d1/migrate_add_description_en.sql
wrangler d1 execute dressifye-db --file=./d1/migrate_add_tier_slug.sql
wrangler d1 execute dressifye-db --file=./d1/migrate_four_tier_plans.sql
```

## Deploy

```bash
cd dressifye && wrangler deploy
```

## Endpoint Özeti

| Endpoint | Yöntem | Açıklama |
|---|---|---|
| `GET /health` | GET | Sağlık kontrolü |
| `GET /api/pricing` | GET | D1'den fiyat planları |
| `GET /api/garments` | GET | TS API'den garment listesi (`tenant_slug`, `limit`, `cursor` query params) |
| `POST /api/v1/auth/token` | POST | Django JWT auth → `GARMENT_CORE_API_URL` proxy |
| `POST /odeme/abonelik-baslat` | POST | Abonelik başlatma → Django `/api/v1/payments/dressifye/subscription/init/` |
| `POST /odeme/abonelik-callback` | POST | iyzico callback → Django `/api/v1/payments/dressifye/subscription/callback/` |

## Dokunma — Değiştirme

- `dressifye/d1/` SQL dosyaları — **dokunma**
- `dressifye/index.html` (ana landing page) içeriği — **dokunma**
- `dressifye_saas/` Django tarafı — **dokunma**
- `packages/dressifye_saas/` TS tarafı — **dokunma**

## Özet Kontrol Listesi

- [x] git commit snapshot alındı
- [x] `wrangler.toml` → `GARMENT_CORE_TS_URL` + `GARMENT_CORE_TS_API_KEY` eklendi, `GARMENT_CORE_API_URL` boşaltıldı
- [x] `fiyatlandirma/index.html` → `<meta name="dressifye-saas-api" content="">` yapıldı
- [x] `fiyatlandirma/index.html` → form alanı `name="tier"` → `name="plan_slug"` olarak güncellendi
- [x] `index.js` → `/odeme/abonelik-baslat` POST + OPTIONS eklendi
- [x] `index.js` → `/api/garments` GET eklendi
- [x] `index.js` → `/api/v1/auth/token` POST proxy eklendi (login formu için)
- [x] `js/pricing.js` → `apiBase()` ve meta tag okuma kaldırıldı
- [x] `js/pricing.js` → login formu `/api/v1/auth/token` Worker proxy'sine yönlendirildi
- [x] `js/pricing.js` → checkout formu `/odeme/abonelik-baslat` Worker endpoint'ine yönlendirildi
- [x] Tüm `dressifye/` HTML/JS dosyaları localhost referansı tarandı → temiz
- [x] `dressifye/DEPLOY.md` oluşturuldu
