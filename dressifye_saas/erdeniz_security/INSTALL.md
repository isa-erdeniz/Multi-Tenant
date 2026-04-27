# ErdenizTech Security — Kurulum Rehberi

## Linux / macOS (Önerilen)

```bash
git clone https://github.com/isa-erdeniz/erdeniz_security.git
cd erdeniz_security
pip install -e .
python manage.py generate_key --type fernet
python manage.py generate_key --type field
```

## Windows

### Yöntem 1 — PowerShell (Önerilen)
```powershell
git clone https://github.com/isa-erdeniz/erdeniz_security.git
cd erdeniz_security
pip install --only-binary :all: cryptography argon2-cffi
pip install -e .
python manage.py generate_key --type fernet
```

### Yöntem 2 — WSL2 (En iyi Windows deneyimi)
```bash
# WSL2 içinde Linux kurulumu uygula
wsl
pip install -e /path/to/erdeniz_security
```

### Yöntem 3 — setup_security.bat
```
setup_security.bat dosyasını çift tıkla veya:
cmd /c setup_security.bat
```

## Android (Termux)

```bash
pkg update && pkg install python git
pip install cryptography argon2-cffi django python-decouple
git clone https://github.com/isa-erdeniz/erdeniz_security.git
pip install -e ./erdeniz_security --no-deps
```

## Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY erdeniz_security/ ./erdeniz_security/
RUN pip install --no-cache-dir -e ./erdeniz_security
```

## Ortam Değişkenleri

| Platform | Komut |
|----------|-------|
| Linux/macOS | `export ERDENIZ_ENCRYPTION_KEY=<key>` |
| Windows CMD | `set ERDENIZ_ENCRYPTION_KEY=<key>` |
| Windows PS | `$env:ERDENIZ_ENCRYPTION_KEY='<key>'` |
| Android | `export ERDENIZ_ENCRYPTION_KEY=<key>` |
| Docker | `ENV ERDENIZ_ENCRYPTION_KEY=<key>` |
| .env dosyası | `ERDENIZ_ENCRYPTION_KEY=<key>` |

## Hızlı Test

```python
from erdeniz_security.encryption import ErdenizEncryptor, generate_key
key = generate_key()
enc = ErdenizEncryptor(key)
assert enc.decrypt(enc.encrypt("test")) == "test"
print("ErdenizSecurity çalışıyor!")
```

### Son Kontrol (Terminal)

```bash
# 1. Sürüm
python -c "import erdeniz_security; print(erdeniz_security.__version__)"

# 2. Şifreleme
python -c "from erdeniz_security.encryption import generate_key, ErdenizEncryptor; k=generate_key(); e=ErdenizEncryptor(k); print('Encryption OK:', e.decrypt(e.encrypt('test'))=='test')"

# 3. Hasher (Django kurulu ortam gerekir: pip install django)
python -c "from erdeniz_security.hashers import ErdenizArgon2Hasher; h=ErdenizArgon2Hasher(); enc=h.encode('test',h.salt()); print('Hasher OK:', h.verify('test',enc))"
```

## Sorun Giderme

**Windows — cryptography build hatası:**
```
pip install cryptography --only-binary :all:
```

**Android — C extension hatası:**
```
pip install cryptography --prefer-binary
```

**ImportError: No module named 'erdeniz_security':**
```
pip install -e /path/to/erdeniz_security
```
