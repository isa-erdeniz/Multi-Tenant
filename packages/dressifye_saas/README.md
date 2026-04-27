# dressifye_saas

`dressifye` altında değil; monorepo içinde **ürün** olarak `packages/dressifye_saas` konumunda tutulur. Diğer projeler bu servise **HTTP API** ile bağlanmalıdır.

## Gereksinimler

- Node.js 20+ (yerel geliştirme için)
- Docker + Docker Compose (dağıtım için)

## Yerel çalıştırma

```bash
cd packages/dressifye_saas
cp .env.example .env
npm install
npm run build
npm run db:migrate
npm run db:seed
npm run start
```

Geliştirme (TypeScript doğrudan): `npm run dev`

- Sağlık: `GET http://localhost:8080/health`
- Sürüm: `GET http://localhost:8080/version`
- API özeti: `docs/API.md`

### Yedek

- Yalnızca veritabanı: `DATABASE_URL=... npm run backup:db` (çıktı `backups/`)
- Veritabanı + Drizzle migrasyonları + şema kaynakları: `npm run backup:all`
- Geri yükleme: `DATABASE_URL=... bash scripts/restore-postgres.sh backups/dressifye_saas_db_....sql.gz`

### GitHub (üst depo `erdeniztech`)

Üç işletim sisteminde arşiv artifact’i, zaman damgalı tag ve `dressifye-saas` çoklu platform derlemesi: üst dizinde `.github/workflows/` ve `.github/BACKUP.md`.

### Ek anahtar üretimi

`npm run db:create-api-key` — ortam değişkenleri için `.env.example` içindeki `GARMENT_CORE_*` notlarına bakın.

## Docker

```bash
cd packages/dressifye_saas
cp .env.example .env
docker compose up --build
```

## Sürüm

- `VERSION` dosyası ile semver tutun; yayın öncesi `package.json` içindeki `version` ile eşleştirin.

## Django dressifye_saas ↔ packages/dressifye_saas Köprüsü

### Bu servis → Django

Bu TypeScript servisi, her garment ingest'inde `ERDENIZ_SECURITY_INGEST_URL`'e POST yapar.
Django tarafında `erdeniz_security` paketi bu isteği `/erdeniz-security/ingest/` endpoint'inde karşılar.

`.env` içinde:
```
ERDENIZ_SECURITY_INGEST_URL=https://<dressifye-saas-django>.railway.app/erdeniz-security/ingest/
ERDENIZ_SECURITY_MODE=audit   # off | audit | enforce
GARMENT_CORE_WEBHOOK_SECRET=<Django-ile-paylasilan-secret>
```

### Django → Bu servis (push)

Django `wardrobe/tasks.py` içinde MEHLR analizi tamamlandıktan sonra `DressifyeSaasTSClient`
aracılığıyla bu servisteki `/webhook/mehlr` endpoint'ine HMAC-imzalı POST gönderir.

**Django Railway Variables panelinde şu değerlerin set edilmesi gerekir:**
```
GARMENT_CORE_TS_ENABLED=True
GARMENT_CORE_TS_URL=https://<dressifye-saas-ts>.railway.app
GARMENT_CORE_WEBHOOK_SECRET=<TS ile paylaşılan secret — .env içindeki ile aynı>
GARMENT_CORE_TS_API_KEY=<bu servisten üretilen platform API key>
```

API key üretmek için: `npm run db:create-api-key`

## Mevcut kodunuzu taşıma

Giriş noktası `src/index.ts` (derleme çıktısı `dist/index.js`). Drizzle şeması `src/db/schema/` altındadır.
