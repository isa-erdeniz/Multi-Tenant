"""
erdeniz_security/env_protector.py — .env şifreleme/çözme.
Master password → key derivation → Fernet. ENCRYPTED_PREFIX = "ENC:v1:"
"""
from __future__ import annotations

import base64
import os
import re
import secrets
from hashlib import sha256
from pathlib import Path

from cryptography.fernet import Fernet

from .encryption import DecryptionError

ENCRYPTED_PREFIX = "ENC:v1:"
HEADER_SALT = "# Salt:"
SENSITIVE_PATTERNS = [
    r".*PASSWORD.*",
    r".*SECRET.*",
    r".*KEY.*",
    r".*TOKEN.*",
    r".*API.*",
    r".*DATABASE_URL.*",
    r".*DSN.*",
    r".*CREDENTIALS.*",
    r".*PRIVATE.*",
]


def _compile_patterns() -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in SENSITIVE_PATTERNS]


def _is_sensitive_key(key: str) -> bool:
    return any(p.search(key) for p in _compile_patterns())


def _derive_key(master_password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    salt = salt or secrets.token_bytes(16)
    raw = master_password.encode("utf-8") + salt
    key_b64 = base64.urlsafe_b64encode(sha256(raw).digest())
    return key_b64, salt


class EnvProtector:
    """Master password ile .env şifreleme/çözme."""

    def __init__(self, master_password: str, salt: bytes | None = None) -> None:
        if not master_password or not master_password.strip():
            raise ValueError("Master password boş olamaz")
        self._master_password = master_password
        self._key_b64, self._salt = _derive_key(master_password, salt)
        self._fernet = Fernet(self._key_b64)

    def encrypt_env(self, input_path: str | Path, output_path: str | Path | None = None) -> str:
        """.env → .env.encrypted"""
        inp = Path(input_path)
        out = Path(output_path) if output_path else inp.with_name(inp.name + ".encrypted")
        if not inp.exists():
            raise FileNotFoundError(str(inp))
        lines = inp.read_text(encoding="utf-8", errors="replace").splitlines()
        out_lines = [
            "# ErdenizVault Encrypted Environment",
            f"# Project: {inp.parent.name}",
            f"# Encrypted: {__import__('datetime').datetime.utcnow().isoformat()}Z",
            "# Algorithm: Fernet (AES-128-CBC + HMAC-SHA256)",
            f"{HEADER_SALT} {self._salt.hex()}",
            "",
        ]
        for line in lines:
            s = line.rstrip()
            if not s.strip() or s.strip().startswith("#"):
                out_lines.append(line)
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                key, value = k.strip(), v.strip().strip("'\"")
                if _is_sensitive_key(key) and value and not value.startswith(ENCRYPTED_PREFIX):
                    enc = self._fernet.encrypt(value.encode("utf-8")).decode("ascii")
                    out_lines.append(f"{key}=ENC:v1:{enc}")
                else:
                    out_lines.append(line)
            else:
                out_lines.append(line)
        out.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        return str(out)

    def decrypt_env(self, input_path: str | Path, output_path: str | Path | None = None) -> str:
        """.env.encrypted → .env. Salt header'dan okunur."""
        inp = Path(input_path)
        out = Path(output_path) if output_path else inp.with_name(inp.name.replace(".encrypted", "").replace(".env.encrypted", ".env"))
        if not inp.exists():
            raise FileNotFoundError(str(inp))
        content = inp.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        salt_hex = None
        for line in lines:
            if line.strip().startswith(HEADER_SALT):
                salt_hex = line.split(HEADER_SALT, 1)[-1].strip()
                break
        decryptor = self
        if salt_hex:
            try:
                decryptor = EnvProtector(self._master_password, bytes.fromhex(salt_hex))
            except Exception:
                pass
        out_lines = []
        for line in lines:
            if line.strip().startswith("#") or not line.strip():
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                key, value = k.strip(), v.strip().strip("'\"")
                if value.startswith(ENCRYPTED_PREFIX):
                    try:
                        dec = decryptor._fernet.decrypt(value[len(ENCRYPTED_PREFIX):].encode("ascii")).decode("utf-8")
                        out_lines.append(f"{key}={dec}")
                    except Exception:
                        raise DecryptionError(f"Değer çözülemedi: {key}")
                else:
                    out_lines.append(line)
            else:
                out_lines.append(line)
        out.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        return str(out)

    def get_value(self, encrypted_env_path: str | Path, key: str) -> str:
        """Şifreli .env'den tek değer çöz."""
        inp = Path(encrypted_env_path)
        if not inp.exists():
            raise FileNotFoundError(str(inp))
        for line in inp.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, _, v = line.partition("=")
            if k.strip() != key:
                continue
            value = v.strip().strip("'\"")
            if self.is_encrypted(value):
                return self._fernet.decrypt(value[len(ENCRYPTED_PREFIX):].encode("ascii")).decode("utf-8")
            return value
        raise KeyError(key)

    @staticmethod
    def is_encrypted(value: str) -> bool:
        return value.strip().startswith(ENCRYPTED_PREFIX)

    def rotate_encryption(self, env_path: str | Path, new_password: str) -> None:
        """Eski şifreyi çöz, yeni şifreyle tekrar şifrele."""
        dec_path = Path(env_path).with_suffix(".env.tmp")
        self.decrypt_env(env_path, dec_path)
        EnvProtector(new_password).encrypt_env(dec_path, env_path)
        dec_path.unlink(missing_ok=True)


class IntegrityChecker:
    """Runtime'da env değişkenlerinin manipülasyonunu tespit eder."""

    def __init__(self, watch_keys: list[str] | None = None) -> None:
        self.watch_keys = watch_keys
        self._snapshot: dict[str, str] = {}
        self._violations: list[dict] = []

    def take_snapshot(self) -> None:
        import hashlib
        keys = self.watch_keys or list(os.environ.keys())
        self._snapshot = {k: hashlib.sha256(os.environ.get(k, "").encode()).hexdigest() for k in keys}

    def check_integrity(self) -> list[dict]:
        import hashlib
        violations: list[dict] = []
        current_keys = set(os.environ.keys())
        snapshot_keys = set(self._snapshot.keys())
        for k in snapshot_keys:
            current_hash = hashlib.sha256(os.environ.get(k, "").encode()).hexdigest()
            if k not in current_keys:
                violations.append({"key": k, "status": "deleted"})
            elif current_hash != self._snapshot[k]:
                violations.append({"key": k, "status": "modified"})
        if self.watch_keys is None:
            for k in current_keys - snapshot_keys:
                violations.append({"key": k, "status": "added"})
        if violations:
            try:
                from .audit import log_event
                log_event("SECURITY_ALERT", "env_integrity", "erdeniz_security", success=False, details={"violations": violations})
            except Exception:
                pass
        self._violations.extend(violations)
        return violations

    def get_violations(self) -> list[dict]:
        return list(self._violations)


class SecureSettings:
    """Hassas değerleri runtime'da şifreli tutar."""

    def __init__(self, encryption_key: str | None = None) -> None:
        from .encryption import ErdenizEncryptor
        self._encryptor = ErdenizEncryptor(encryption_key)
        self._store: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self._store[key] = self._encryptor.encrypt(value)

    def get(self, key: str, default: str = "") -> str:
        if key not in self._store:
            return default
        try:
            return self._encryptor.decrypt(self._store[key])
        except Exception:
            return default

    def load_from_env(self, keys: list[str]) -> None:
        for k in keys:
            v = os.environ.get(k, "")
            if v:
                self.set(k, v)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self) -> list[str]:
        return list(self._store.keys())
