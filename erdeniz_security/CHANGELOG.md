# Changelog — erdeniz_security

## [1.0.0] — 2025

### Added
- ErdenizEncryptor: Fernet tabanlı metin şifreleme, dict şifreleme
- FileEncryptor: Büyük dosyalar için stream şifreleme (chunk-based, SHA-256 bütünlük)
- ErdenizArgon2Hasher: Argon2id (OWASP 2023 parametreleri)
- ErdenizBcryptHasher: bcrypt fallback, sha256 önişleme ile 72-byte koruması
- ErdenizSecurityConfig: Dataclass tabanlı tip-güvenli konfigürasyon
- SecureCharField, SecureEmailField, SecurePhoneField, SecureTCKimlikField, SecureFilePathField
- SecurityAuditLog modeli: tüm güvenlik olayları için merkezi log
- @audit_trail: view ve servis fonksiyonları için otomatik audit loglama
- export_audit_logs: JSON ve CSV formatında log dışa aktarma
- ErdenizAPIKeyManager: Argon2 hash'li API key yönetimi (oluştur/doğrula/iptal/döndür)
- RequestSigner: HMAC-SHA256 tabanlı projeler arası istek imzalama
- EnvProtector: Master password ile .env şifreleme/çözme
- IntegrityChecker: Runtime env manipülasyonu tespiti
- SecureSettings: Hassas ayarları bellek içinde şifreli tutma
- SecurityHeadersMiddleware, AuditMiddleware, RequestSanitizationMiddleware
- APIAuthenticationMiddleware, APIRateLimitMiddleware
- @secure_view, @permission_required_custom, @audit_log, @require_api_key,
  @require_jwt, @require_signed_request, @rate_limit, @verify_webhook
- Management commands: encrypt_env, decrypt_env, encrypt_files, generate_key,
  generate_password, rotate_field_key, security_check, encrypt_existing, generate_api_key
- WebhookVerifier: HMAC + Stripe webhook doğrulama
- IPGuard, SSLHelper, get_cors_settings
