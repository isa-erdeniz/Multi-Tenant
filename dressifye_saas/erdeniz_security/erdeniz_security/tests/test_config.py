"""
erdeniz_security/tests/test_config.py — ErdenizSecurityConfig ve config fonksiyonları testleri.
"""
import os
os.environ["ERDENIZ_ENCRYPTION_KEY"] = os.environ.get("ERDENIZ_ENCRYPTION_KEY") or __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()
os.environ["FIELD_ENCRYPTION_KEY"] = os.environ.get("FIELD_ENCRYPTION_KEY") or os.environ["ERDENIZ_ENCRYPTION_KEY"]

from erdeniz_security.config import ErdenizSecurityConfig, get_django_security_settings, validate_configuration


def test_erdeniz_security_config_defaults():
    cfg = ErdenizSecurityConfig(project_name="test")
    assert cfg.project_name == "test"
    assert cfg.min_password_length == 12
    assert cfg.key_rotation_days == 90


def test_erdeniz_security_config_validate_ok():
    cfg = ErdenizSecurityConfig.from_env("test")
    errors = cfg.validate()
    assert "encryption_key (ERDENIZ_ENCRYPTION_KEY) tanımlı olmalı" not in errors


def test_erdeniz_security_config_validate_fail():
    cfg = ErdenizSecurityConfig(project_name="test", encryption_key="", field_encryption_key="")
    errors = cfg.validate()
    assert len(errors) >= 2


def test_from_env():
    cfg = ErdenizSecurityConfig.from_env("dressifye_saas")
    assert cfg.project_name == "dressifye_saas"


def test_get_django_security_settings():
    s = get_django_security_settings()
    assert "PASSWORD_HASHERS" in s
    assert "SESSION_COOKIE_SECURE" in s


def test_validate_configuration():
    errors = validate_configuration()
    assert isinstance(errors, list)
