"""
MEHLR yardımcı fonksiyonlar.
"""
import re
import markdown
from django.utils.html import escape


def sanitize_user_input(text):
    """Kullanıcı girdisini AI'a göndermeden önce temizler (XSS / injection)."""
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    # Aşırı uzun boşlukları tek boşluğa indir
    text = re.sub(r'\s+', ' ', text)
    return text[:4000]


def markdown_to_html(md_text):
    """Markdown metnini HTML'e çevirir."""
    if not md_text:
        return ""
    return markdown.markdown(
        md_text,
        extensions=['nl2br', 'sane_lists'],
        safe_mode=False,
    )


def get_client_ip(request):
    """İstekten istemci IP'sini alır (rate limit vb. için)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
