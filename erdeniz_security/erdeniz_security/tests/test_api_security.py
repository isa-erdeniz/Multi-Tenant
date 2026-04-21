"""
erdeniz_security/tests/test_api_security.py — JWT, rate limit, RequestSigner testleri.
"""
import os
os.environ["ERDENIZ_ENCRYPTION_KEY"] = __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()

from datetime import timedelta
from erdeniz_security.api_security import RequestSigner, ERDENIZ_JWT_SETTINGS, ERDENIZ_RATE_LIMITS


def test_jwt_settings_structure():
    assert "ACCESS_TOKEN_LIFETIME" in ERDENIZ_JWT_SETTINGS
    assert "ALGORITHM" in ERDENIZ_JWT_SETTINGS
    assert ERDENIZ_JWT_SETTINGS["ACCESS_TOKEN_LIFETIME"] <= timedelta(minutes=15)


def test_rate_limits_structure():
    assert "default" in ERDENIZ_RATE_LIMITS
    assert "auth" in ERDENIZ_RATE_LIMITS
    assert "sensitive" in ERDENIZ_RATE_LIMITS


def test_request_signer_roundtrip():
    signer = RequestSigner("test_secret_key_for_signing")
    headers = signer.sign_request("POST", "https://api.erdeniztech.com/test/", '{"data": 1}')
    assert "X-Erdeniz-Signature" in headers
    assert "X-Erdeniz-Timestamp" in headers
    assert "X-Erdeniz-Nonce" in headers


def test_request_signer_different_keys():
    s1 = RequestSigner("secret1")
    s2 = RequestSigner("secret2")
    headers = s1.sign_request("GET", "https://api.erdeniztech.com/", "")
    assert headers["X-Erdeniz-Signature"] != s2.sign_request("GET", "https://api.erdeniztech.com/", "")["X-Erdeniz-Signature"]
