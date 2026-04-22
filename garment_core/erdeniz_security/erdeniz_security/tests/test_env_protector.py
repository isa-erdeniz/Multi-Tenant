from erdeniz_security.env_protector import EnvProtector, _is_sensitive_key


def test_is_sensitive_key():
    assert _is_sensitive_key("DATABASE_PASSWORD") is True
    assert _is_sensitive_key("SECRET_KEY") is True
    assert _is_sensitive_key("DEBUG") is False


def test_encrypt_decrypt_env(tmp_path):
    (tmp_path / ".env").write_text("SECRET_KEY=mysecret\nDEBUG=False\n")
    p = EnvProtector("master123")
    p.encrypt_env(tmp_path / ".env", tmp_path / ".env.encrypted")
    content = (tmp_path / ".env.encrypted").read_text()
    assert "SECRET_KEY=ENC:v1:" in content
    p.decrypt_env(tmp_path / ".env.encrypted", tmp_path / ".env.dec")
    assert "SECRET_KEY=mysecret" in (tmp_path / ".env.dec").read_text()


def test_integrity_checker_no_violation():
    from erdeniz_security.env_protector import IntegrityChecker
    checker = IntegrityChecker(watch_keys=["PATH"])
    checker.take_snapshot()
    violations = checker.check_integrity()
    assert violations == []


def test_integrity_checker_modified():
    import os
    from erdeniz_security.env_protector import IntegrityChecker
    checker = IntegrityChecker(watch_keys=["_TEST_ERDENIZ_VAR"])
    os.environ["_TEST_ERDENIZ_VAR"] = "original"
    checker.take_snapshot()
    os.environ["_TEST_ERDENIZ_VAR"] = "modified"
    violations = checker.check_integrity()
    assert any(v["key"] == "_TEST_ERDENIZ_VAR" and v["status"] == "modified" for v in violations)
    del os.environ["_TEST_ERDENIZ_VAR"]


def test_secure_settings_set_get():
    import os
    os.environ.setdefault("ERDENIZ_ENCRYPTION_KEY", __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode())
    from erdeniz_security.env_protector import SecureSettings
    ss = SecureSettings()
    ss.set("MY_SECRET", "ultra_secret_value")
    assert ss.get("MY_SECRET") == "ultra_secret_value"
    assert ss.get("NON_EXISTENT", "default") == "default"


def test_secure_settings_encrypted_at_rest():
    import os
    os.environ.setdefault("ERDENIZ_ENCRYPTION_KEY", __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode())
    from erdeniz_security.env_protector import SecureSettings
    ss = SecureSettings()
    ss.set("API_KEY", "sk_live_12345")
    assert ss._store["API_KEY"] != "sk_live_12345"
