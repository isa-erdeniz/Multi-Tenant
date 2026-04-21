# Cursor Composer / Agent Prompt — erdeniz_security

Sen ErdenizTech'in baş güvenlik mimarısın. **erdeniz_security** Django güvenlik paketinde çalışıyorsun.

---

## MEVCUT DURUM (DEĞİŞTİRME — SADECE EKLE)

Aşağıdakiler zaten var; **üzerine yazma**, sadece eksikleri ekle veya yeni özellikleri **ayrı fonksiyon/sınıf** olarak ekle.

| Dosya | Mevcut içerik |
|-------|----------------|
| **encryption.py** | `ErdenizEncryptor` (Fernet), `FileEncryptor` (stream encryption ≥100MB), `generate_key`, `generate_password`, `hash_data`, `secure_compare` |
| **fields.py** | `SecureCharField`, `SecureTextField`, `SecureEmailField`, `SecurePhoneField`, `SecureTCKimlikField`, `SecureFilePathField` (django-encrypted-model-fields tabanlı) |
| **hashers.py** | Boş / config’e referans — **buraya hasher ekle** |
| **api_security.py** | `ERDENIZ_JWT_SETTINGS`, `ErdenizTokenObtainSerializer`, `ErdenizAPIKeyManager`, `RequestSigner`, `ERDENIZ_RATE_LIMITS`, `secure_exception_handler` |
| **env_protector.py** | `EnvProtector`, .env şifreleme/çözme |
| **audit.py** | `log_event`, `get_alerts`, `get_stats` — model `SecurityAuditLog` **models.py** içinde |
| **decorators.py** | `audit_log`, `require_api_key`, `require_jwt`, `require_signed_request`, `rate_limit`, `verify_webhook` |
| **config.py** | `SECURITY_SETTINGS`, `get_security_settings`, `validate_configuration`, `get_django_security_settings` |
| **middleware.py** | `SecurityHeadersMiddleware`, `AuditMiddleware`, `RequestSanitizationMiddleware`, `APIAuthenticationMiddleware`, `APIRateLimitMiddleware` |

---

## GÖREV 1 — Eksikleri tamamla (mevcut dosyalara EKLE)

1. **hashers.py**  
   - `ErdenizArgon2Hasher` — Argon2id, Django `BasePasswordHasher` uyumlu.  
   - İsteğe bağlı: `ErdenizBcryptHasher` (bcrypt fallback).  
   - `get_django_security_settings()` içinde kullanılacak şekilde bırak (zaten orada `PASSWORD_HASHERS` var).

2. **encryption.py** (opsiyonel — mevcut Fernet’i değiştirme)  
   - İstenirse AES-256-GCM tabanlı **ek** bir sınıf eklenebilir (örn. `ErdenizAESEncryption`) ve key rotation için `rotate_key(old_key, new_key)` helper’ı yazılabilir.  
   - Varsayılan davranış: mevcut `ErdenizEncryptor` ve `FileEncryptor` kalsın.

3. **fields.py** (opsiyonel)  
   - `EncryptedJSONField` — şifreli JSON (django-encrypted-model-fields veya kendi `from_db_value` / `get_prep_value` implementasyonun).  
   - `EncryptedFileField` — şifreli dosya yolu veya içerik; mevcut `SecureFilePathField` ile çakışmayacak şekilde ekle.

4. **config.py**  
   - Tüm güvenlik ayarları için `ErdenizSecurityConfig` dataclass’ı ekle (varsayılan değerler + validation).  
   - Mevcut `get_security_settings` / `get_django_security_settings` bu dataclass’tan okuyabilir veya uyumlu kalabilir.

5. **env_protector.py**  
   - Runtime’da .env değişikliği izleme (opsiyonel): `IntegrityChecker` veya benzeri.  
   - `SecureSettings` wrapper (settings’teki hassas değerleri şifreli tutma) — mevcut yapıyı bozmadan ekle.

6. **audit.py**  
   - `@audit_trail(action="update")` decorator’ı ekle (mevcut `log_event` kullanarak).  
   - JSON export: `export_audit_logs(project=None, since=None, format="json")` fonksiyonu ekle.

7. **decorators.py**  
   - `@secure_view` — view’a otomatik güvenlik başlıkları (CSP, X-Frame-Options vb.) ekleyen decorator.  
   - `@permission_required_custom(perm)` — granular yetki kontrolü.  
   - Mevcut decorator’ların üzerine yazma.

---

## GÖREV 2 — Paketleme

- **setup.py** zaten var; gerekirse **pyproject.toml** ile uyumlu güncelle.  
- **pyproject.toml** varsa: `name = "erdeniz-security"`, `version = "1.0.0"`, dependencies: `cryptography>=41.0`, `argon2-cffi`, `django>=4.2`, `PyJWT` (JWT kullanılıyorsa).  
- Entry point: Django app olarak `erdeniz_security.apps.ErdenizSecurityConfig` (zaten apps.py’de).

---

## GÖREV 3 — __init__.py

- Public API export’ları **zaten** __init__.py’de tanımlı.  
- Yeni eklediğin sınıf/decorator’ları (ErdenizArgon2Hasher, ErdenizSecurityConfig, audit_trail, secure_view, export_audit_logs vb.) __all__ ve ilgili import’lara ekle.

---

## GÖREV 4 — Testler

**tests/** altında:

- `test_encryption.py` — mevcut; şifreleme/çözme roundtrip, stream encryption (≥100MB) testleri eklenebilir.  
- `test_fields.py` — mevcut; EncryptedJSONField / EncryptedFileField testleri ekle.  
- `test_api_security.py` — JWT, rate limit, API key, RequestSigner testleri.  
- `test_audit.py` — log_event, export_audit_logs, @audit_trail testleri.  
- `test_hashers.py` — ErdenizArgon2Hasher (ve varsa Bcrypt) testleri.

Gerekirse `tests/settings.py` veya `conftest.py` ile minimal Django settings kullan.

---

## KURALLAR

- Type hints ve docstring kullan.  
- Secret/key’leri kaynak koda gömme; settings/env’den oku, fallback/default tanımla.  
- Şifreleme için **cryptography** kütüphanesi kullan.  
- Mevcut sınıf/isimleri (ErdenizEncryptor, FileEncryptor, SecureCharField vb.) **değiştirme**; sadece yeni sınıf/decorator/fonksiyon ekle.  
- ErdenizTech projeleri (garment_core, worktrackere, looopone, mehlr_1_0) `pip install -e /path/to/erdeniz_security` ile kullanmaya devam etmeli.

Doğrudan çalışan Python kodu yaz; gereksiz açıklama ekleme.
