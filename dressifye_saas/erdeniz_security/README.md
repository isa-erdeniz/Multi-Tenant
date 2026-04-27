# ErdenizTech Security — Tek Katman

Tek paket: **erdeniz_security**. Ayrı modül/katman/klasör yok. Hem iş projeleri hem kişisel dosyalar aynı araçlarla korunur.

## Yapı (sabit)

- `config.py` — SECURITY_SETTINGS, get_security_settings(), validate_configuration(), get_django_security_settings()
- `encryption.py` — ErdenizEncryptor, FileEncryptor, generate_key(), generate_field_encryption_key(), generate_password(), hash_data(), secure_compare()
- `env_protector.py` — .env şifreleme/çözme
- `fields.py` — SecureCharField, SecureTextField, SecureEmailField, SecurePhoneField, SecureTCKimlikField, SecureFilePathField
- `middleware.py` — SecurityHeadersMiddleware, AuditMiddleware, RequestSanitizationMiddleware
- `audit.py`, `validators.py`, `decorators.py`, `hashers.py`, `models.py`, `apps.py`
- `management/commands/` — encrypt_env, decrypt_env, rotate_field_key, security_check, encrypt_existing, encrypt_files, generate_password, generate_key

## Kurulum

```bash
pip install -e /path/to/erdeniz_security
pip install -r requirements.txt
```

**GitHub yüklemek için:** Gitingiroe kurulu olmalıdır. Gitingiroe olmadan GitHub’a yükleme yapılamaz.

Reponun kökünde **.gitignore** bulunur; `.env`, `*.evault`, sanal ortamlar ve hassas dosyalar takip dışındadır. `security_check` komutu `.env` dosyasının `.gitignore` içinde olmasını kontrol eder.

## Projede kullanım

1. INSTALLED_APPS: `"erdeniz_security"`, `"axes"`
2. MIDDLEWARE: SecurityHeadersMiddleware, RequestSanitizationMiddleware, AuditMiddleware, AxesMiddleware (sıra önemli)
3. Settings: `.env` yükledikten sonra `from erdeniz_security.config import get_django_security_settings; locals().update(get_django_security_settings())`
4. Anahtarlar: `python manage.py generate_key --type fernet` → ERDENIZ_ENCRYPTION_KEY, `--type field` → FIELD_ENCRYPTION_KEY

## Komutlar

- `encrypt_env` / `decrypt_env` — .env şifrele/çöz
- `encrypt_files --path <dosya|klasör>` — .evault (proje veya kişisel)
- `encrypt_files --decrypt --path <dosya.evault>`
- `encrypt_files --path <dosya> --shred` — şifrele ve orijinali güvenli sil
- `generate_password` — güçlü şifre (iş/kişisel aynı)
- `security_check` — güvenlik raporu
- `encrypt_existing` — mevcut veriyi şifreli alanlara taşı

## Toplu kurulum

```bash
chmod +x setup_security.sh
./setup_security.sh
```

ERDENIZTECH_ROOT ile kök dizini değiştirilebilir.
# erdeniz_security
