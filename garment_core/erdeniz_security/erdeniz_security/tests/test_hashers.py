"""
erdeniz_security/tests/test_hashers.py — ErdenizArgon2Hasher ve ErdenizBcryptHasher testleri.
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erdeniz_security.tests.settings")
os.environ["ERDENIZ_ENCRYPTION_KEY"] = __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()

import django
django.setup()

import pytest
from erdeniz_security.hashers import ErdenizArgon2Hasher, ErdenizBcryptHasher


def test_argon2_encode_verify():
    h = ErdenizArgon2Hasher()
    salt = h.salt()
    encoded = h.encode("test_password_123", salt)
    assert encoded.startswith("erdeniz_argon2$")
    assert h.verify("test_password_123", encoded) is True
    assert h.verify("wrong_password", encoded) is False


def test_argon2_must_update():
    h = ErdenizArgon2Hasher()
    encoded = h.encode("test", h.salt())
    assert isinstance(h.must_update(encoded), bool)


def test_argon2_safe_summary():
    h = ErdenizArgon2Hasher()
    summary = h.safe_summary(h.encode("test", h.salt()))
    assert summary["algorithm"] == "erdeniz_argon2"


def test_bcrypt_encode_verify():
    h = ErdenizBcryptHasher()
    salt = h.salt()
    encoded = h.encode("test_password_123", salt)
    assert encoded.startswith("erdeniz_bcrypt$")
    assert h.verify("test_password_123", encoded) is True
    assert h.verify("wrong_password", encoded) is False


def test_bcrypt_long_password():
    h = ErdenizBcryptHasher()
    long_pwd = "x" * 200
    encoded = h.encode(long_pwd, h.salt())
    assert h.verify(long_pwd, encoded) is True
