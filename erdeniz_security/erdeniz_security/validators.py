"""Güvenlik doğrulayıcıları (TC Kimlik, telefon)."""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_tc_kimlik(value: str) -> None:
    if not value or len(str(value).strip()) != 11 or not str(value).isdigit():
        raise ValidationError(_("TC Kimlik Numarası 11 haneli olmalıdır."))
    s = str(value).strip()
    if s[0] == "0":
        raise ValidationError(_("TC Kimlik Numarası 0 ile başlamaz."))
    digits = [int(x) for x in s]
    if (sum(digits[0:9:2]) * 7 - sum(digits[1:8:2])) % 10 != digits[9]:
        raise ValidationError(_("Geçersiz TC Kimlik Numarası."))
    if sum(digits[:10]) % 10 != digits[10]:
        raise ValidationError(_("Geçersiz TC Kimlik Numarası."))


def validate_phone_tr(value: str) -> None:
    import re
    if not value:
        return
    cleaned = re.sub(r"[\s\-\(\)]", "", str(value))
    if not re.match(r"^(\+90)?0?5\d{9}$", cleaned):
        raise ValidationError(_("Geçerli bir Türkiye telefon numarası girin."))
