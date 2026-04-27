"""
erdeniz_security/hashers.py — Argon2id ve bcrypt tabanlı Django password hasher'ları.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

try:
    from django.contrib.auth.hashers import BasePasswordHasher
except ImportError:
    BasePasswordHasher = None  # type: ignore[misc, assignment]

if BasePasswordHasher is not None:

    class ErdenizArgon2Hasher(BasePasswordHasher):
        """Argon2id tabanlı hasher. OWASP 2023 parametreleri."""

        algorithm = "erdeniz_argon2"
        time_cost = 3
        memory_cost = 65536
        parallelism = 4

        def salt(self) -> str:
            """Yeni tuz üret."""
            return os.urandom(16).hex()

        def encode(self, password: str, salt: str) -> str:
            """Şifreyi Argon2id ile hashle."""
            try:
                import argon2
                ph = argon2.PasswordHasher(
                    time_cost=self.time_cost,
                    memory_cost=self.memory_cost,
                    parallelism=self.parallelism,
                    type=argon2.Type.ID,
                )
                h = ph.hash(password)
                return f"{self.algorithm}${h}"
            except ImportError as e:
                raise RuntimeError("argon2-cffi kurulu değil") from e

        def verify(self, password: str, encoded: str) -> bool:
            """Hash ile şifreyi doğrula."""
            try:
                import argon2
                from argon2.exceptions import VerifyMismatchError
                if not encoded.startswith(f"{self.algorithm}$"):
                    return False
                h = encoded[len(self.algorithm) + 1 :]
                ph = argon2.PasswordHasher()
                ph.verify(h, password)
                return True
            except VerifyMismatchError:
                return False
            except ImportError as e:
                raise RuntimeError("argon2-cffi kurulu değil") from e
            except Exception:
                return False

        def safe_summary(self, encoded: str) -> dict[str, Any]:
            """Hash'in güvenli özeti."""
            return {
                "algorithm": self.algorithm,
                "hash": encoded[:20] + "...",
            }

        def must_update(self, encoded: str) -> bool:
            """Hash yeniden hesaplanmalı mı (parametre değişikliği)."""
            try:
                import argon2
                ph = argon2.PasswordHasher(
                    time_cost=self.time_cost,
                    memory_cost=self.memory_cost,
                    parallelism=self.parallelism,
                    type=argon2.Type.ID,
                )
                if not encoded.startswith(f"{self.algorithm}$"):
                    return True
                h = encoded[len(self.algorithm) + 1 :]
                return ph.check_needs_rehash(h)
            except Exception:
                return True

        def harden_runtime(self, password: str, encoded: str) -> None:
            """Zamanlama saldırılarını zorlaştır (no-op veya verify)."""
            self.verify(password, encoded)

    class ErdenizBcryptHasher(BasePasswordHasher):
        """bcrypt fallback. 72 byte sınırı için SHA-256 önişleme."""

        algorithm = "erdeniz_bcrypt"
        rounds = 13

        def salt(self) -> str:
            """bcrypt salt üret."""
            try:
                import bcrypt
                return bcrypt.gensalt(rounds=self.rounds).decode("ascii")
            except ImportError as e:
                raise RuntimeError("bcrypt kurulu değil") from e

        def _preprocess_password(self, password: str) -> str:
            """72 byte üzeri şifreleri SHA-256 ile önişle."""
            raw = password.encode("utf-8")
            if len(raw) > 72:
                return hashlib.sha256(raw).hexdigest()
            return password

        def encode(self, password: str, salt: str) -> str:
            """Şifreyi bcrypt ile hashle."""
            try:
                import bcrypt
                pre = self._preprocess_password(password)
                h = bcrypt.hashpw(pre.encode("utf-8"), salt.encode("ascii"))
                return f"{self.algorithm}${self.rounds}${h.decode('ascii')}"
            except ImportError as e:
                raise RuntimeError("bcrypt kurulu değil") from e

        def verify(self, password: str, encoded: str) -> bool:
            """Hash ile şifreyi doğrula."""
            try:
                import bcrypt
                if not encoded.startswith(f"{self.algorithm}$"):
                    return False
                parts = encoded.split("$", 2)
                if len(parts) != 3:
                    return False
                pre = self._preprocess_password(password)
                return bcrypt.checkpw(pre.encode("utf-8"), parts[2].encode("ascii"))
            except ImportError as e:
                raise RuntimeError("bcrypt kurulu değil") from e
            except Exception:
                return False

        def safe_summary(self, encoded: str) -> dict[str, Any]:
            """Hash'in güvenli özeti."""
            return {
                "algorithm": self.algorithm,
                "rounds": self.rounds,
                "hash": encoded[:30] + "...",
            }

        def must_update(self, encoded: str) -> bool:
            """Round sayısı değiştiyse True."""
            if not encoded.startswith(f"{self.algorithm}$"):
                return True
            parts = encoded.split("$", 2)
            if len(parts) != 3:
                return True
            try:
                return int(parts[1]) != self.rounds
            except ValueError:
                return True

        def harden_runtime(self, password: str, encoded: str) -> None:
            """Zamanlama saldırılarını zorlaştır."""
            self.verify(password, encoded)

else:
    ErdenizArgon2Hasher = None  # type: ignore[misc, assignment]
    ErdenizBcryptHasher = None  # type: ignore[misc, assignment]

# PASSWORD_HASHERS = [
#     "erdeniz_security.hashers.ErdenizArgon2Hasher",
#     "erdeniz_security.hashers.ErdenizBcryptHasher",
#     "django.contrib.auth.hashers.Argon2PasswordHasher",
#     "django.contrib.auth.hashers.PBKDF2PasswordHasher",
# ]
