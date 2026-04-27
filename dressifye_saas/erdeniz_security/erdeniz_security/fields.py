"""
erdeniz_security/fields.py — django-encrypted-model-fields tabanlı secure alanlar.
SecureCharField, SecureTextField, SecureEmailField, SecurePhoneField,
SecureTCKimlikField, SecureFilePathField. Audit logging + validasyon.
"""
from __future__ import annotations

import re

try:
    from encrypted_model_fields.fields import (
        EncryptedCharField as BaseEncryptedCharField,
        EncryptedTextField as BaseEncryptedTextField,
        EncryptedEmailField as BaseEncryptedEmailField,
    )
except ImportError:
    BaseEncryptedCharField = BaseEncryptedTextField = BaseEncryptedEmailField = None  # type: ignore


def _log_field_access(model_name: str, field_name: str, action: str) -> None:
    try:
        from .audit import log_event
        log_event(
            "DECRYPT" if action == "decrypt" else "ENCRYPT",
            f"{model_name}.{field_name}",
            "erdeniz_security",
            success=True,
        )
    except Exception:
        pass


def _tc_kimlik_valid(value: str) -> bool:
    if not value or len(str(value).strip()) != 11 or not str(value).isdigit():
        return False
    s = str(value).strip()
    if s[0] == "0":
        return False
    digits = [int(x) for x in s]
    if (sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10 != digits[9]:
        return False
    return sum(digits[:10]) % 10 == digits[10]


def _phone_tr_valid(value: str) -> bool:
    cleaned = re.sub(r"[\s\-\(\)]", "", str(value or ""))
    return bool(re.match(r"^(\+90)?0?5\d{9}$", cleaned))


if BaseEncryptedCharField is not None:

    class _SecureMixin:
        def _audit_encrypt(self, value):
            if value is not None and value != "":
                _log_field_access(
                    getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "",
                    getattr(self, "name", ""),
                    "encrypt",
                )
            return value

        def _audit_decrypt(self, value):
            if value is not None and value != "":
                _log_field_access(
                    getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "",
                    getattr(self, "name", ""),
                    "decrypt",
                )
            return value

    class SecureCharField(_SecureMixin, BaseEncryptedCharField):
        def get_prep_value(self, value):
            self._audit_encrypt(value)
            return super().get_prep_value(value)

        def from_db_value(self, value, expression, connection):
            v = super().from_db_value(value, expression, connection)
            self._audit_decrypt(v)
            return v

    class SecureTextField(_SecureMixin, BaseEncryptedTextField):
        def get_prep_value(self, value):
            self._audit_encrypt(value)
            return super().get_prep_value(value)

        def from_db_value(self, value, expression, connection):
            v = super().from_db_value(value, expression, connection)
            self._audit_decrypt(v)
            return v

    class SecureEmailField(_SecureMixin, BaseEncryptedEmailField):
        def get_prep_value(self, value):
            self._audit_encrypt(value)
            return super().get_prep_value(value)

        def from_db_value(self, value, expression, connection):
            v = super().from_db_value(value, expression, connection)
            self._audit_decrypt(v)
            return v

    class SecurePhoneField(BaseEncryptedCharField):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("max_length", 255)
            super().__init__(*args, **kwargs)

        def validate(self, value, model_instance):
            super().validate(value, model_instance)
            if value and not _phone_tr_valid(str(value)):
                from django.core.exceptions import ValidationError
                raise ValidationError("Geçerli bir Türkiye telefon numarası girin.")

        def get_prep_value(self, value):
            if value is not None and value != "":
                _log_field_access(getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "", getattr(self, "name", ""), "encrypt")
            return super().get_prep_value(value)

        def from_db_value(self, value, expression, connection):
            v = super().from_db_value(value, expression, connection)
            if v is not None and v != "":
                _log_field_access(getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "", getattr(self, "name", ""), "decrypt")
            return v

    class SecureTCKimlikField(BaseEncryptedCharField):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("max_length", 255)
            super().__init__(*args, **kwargs)

        def validate(self, value, model_instance):
            super().validate(value, model_instance)
            if value and not _tc_kimlik_valid(str(value)):
                from django.core.exceptions import ValidationError
                raise ValidationError("Geçerli bir TC Kimlik Numarası girin (11 hane).")

        def get_prep_value(self, value):
            if value is not None and value != "":
                _log_field_access(getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "", getattr(self, "name", ""), "encrypt")
            return super().get_prep_value(value)

        def from_db_value(self, value, expression, connection):
            v = super().from_db_value(value, expression, connection)
            if v is not None and v != "":
                _log_field_access(getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "", getattr(self, "name", ""), "decrypt")
            return v

    class SecureFilePathField(BaseEncryptedCharField):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("max_length", 1024)
            super().__init__(*args, **kwargs)

        def validate(self, value, model_instance):
            super().validate(value, model_instance)
            if value and ".." in str(value):
                from django.core.exceptions import ValidationError
                raise ValidationError("Geçersiz dosya yolu (path traversal).")

        def get_prep_value(self, value):
            if value is not None and value != "":
                _log_field_access(getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "", getattr(self, "name", ""), "encrypt")
            return super().get_prep_value(value)

        def from_db_value(self, value, expression, connection):
            v = super().from_db_value(value, expression, connection)
            if v is not None and v != "":
                _log_field_access(getattr(self, "model", type(self)).__name__ if hasattr(self, "model") else "", getattr(self, "name", ""), "decrypt")
            return v

else:
    from django.db import models
    SecureCharField = models.CharField  # type: ignore
    SecureTextField = models.TextField  # type: ignore
    SecureEmailField = models.EmailField  # type: ignore
    SecurePhoneField = models.CharField  # type: ignore
    SecureTCKimlikField = models.CharField  # type: ignore
    SecureFilePathField = models.CharField  # type: ignore
