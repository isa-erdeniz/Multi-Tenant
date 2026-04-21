from erdeniz_security.encryption import (
    ErdenizEncryptor,
    FileEncryptor,
    generate_key,
    generate_field_encryption_key,
    generate_password,
    hash_data,
    secure_compare,
    DecryptionError,
)


def test_generate_key():
    k = generate_key()
    assert k and len(k) > 40


def test_generate_field_key():
    k = generate_field_encryption_key()
    assert k and len(k) > 20


def test_generate_password():
    p = generate_password(24, symbols=True)
    assert len(p) == 24
    p2 = generate_password(16, symbols=False)
    assert len(p2) == 16


def test_encrypt_decrypt():
    key = generate_key()
    enc = ErdenizEncryptor(key)
    assert enc.decrypt(enc.encrypt("secret")) == "secret"


def test_decrypt_invalid():
    import pytest
    enc = ErdenizEncryptor(generate_key())
    with pytest.raises(DecryptionError):
        enc.decrypt("invalid")


def test_hash_data():
    assert len(hash_data("x")) == 64
    assert hash_data("x", "sha256") == hash_data("x", "sha256")


def test_secure_compare():
    assert secure_compare("a", "a") is True
    assert secure_compare("a", "b") is False
