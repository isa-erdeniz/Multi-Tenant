# garment_core — HTTP API

Kimlik doğrulama: `Authorization: Bearer <api_key>` veya `X-Api-Key: <api_key>`.

## Sağlık

| Yöntem | Yol | Açıklama |
|--------|-----|----------|
| GET | `/health` | Servis + `database` bayrağı |
| GET | `/version` | Sürüm |

## v1 (API anahtarı gerekir)

| Yöntem | Yol | Açıklama |
|--------|-----|----------|
| GET | `/v1/tenants` | Anahtarın erişebildiği kiracılar (`platform_tenant_access`) |
| GET | `/v1/garments?tenant_slug=&limit=&cursor=` | Kiracı kapsamlı liste (sayfalama) |
| GET | `/v1/garments/:id` | Tek kayıt (yalnızca izin verilen kiracılar) |
| POST | `/v1/garments/ingest` | Evrensel ingest (güvenlik + normalizer + upsert) |

### Ingest gövdesi

```json
{
  "tenant_slug": "stylecoree",
  "external_ref": "opsiyonel-yoksa-raw.id",
  "source_domain": "opsiyonel",
  "raw": { "title": "...", "fabric": "Pamuk" }
}
```

Yazma için ilgili kiracıda `read_write` erişimi gerekir.
