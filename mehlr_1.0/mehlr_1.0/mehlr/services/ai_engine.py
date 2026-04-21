"""
MEHLR AI Motor Servisi — Google Gemini API iletişimi.
"""
import time
from django.conf import settings
from django.core.cache import cache

from mehlr.models import Conversation, Message
from mehlr.prompts.base_prompt import BASE_SYSTEM_PROMPT
from mehlr.services.context_manager import get_project_context


# Rate limit: kullanıcı başına dakikada istek (dekoratör için kullanılacak)
def _rate_limit_key(user_id):
    return f"mehlr_rate_{user_id}"


def _check_rate_limit(user_id):
    """Dakikada MEHLR_RATE_LIMIT_PER_MINUTE'dan fazla istek varsa True döner (limit aşıldı)."""
    config = getattr(settings, 'MEHLR_CONFIG', {})
    limit = config.get('RATE_LIMIT_PER_MINUTE', 15)
    key = _rate_limit_key(user_id)
    count = cache.get(key, 0)
    return count >= limit


def _incr_rate_limit(user_id):
    """İstek sayacını artırır; ilk istekte 1 dakika TTL verir."""
    config = getattr(settings, 'MEHLR_CONFIG', {})
    ttl = config.get('CACHE_TTL', 300)
    key = _rate_limit_key(user_id)
    count = cache.get(key, 0) + 1
    cache.set(key, count, 60)  # 1 dakika pencere
    return count


def _cache_key(user_message, project_slug, history_hash):
    """Benzer sorguları önbelleklemek için anahtar."""
    return f"mehlr_resp:{hash(user_message[:200])}:{project_slug}:{history_hash}"


def _build_system_prompt(project_slug=None):
    """Proje bazlı system prompt metnini oluşturur."""
    context = get_project_context(project_slug)
    return BASE_SYSTEM_PROMPT.format(project_context=context)


def _build_conversation_history(conversation, max_messages=20):
    """Son N mesajı Gemini chat formatına çevirir."""
    config = getattr(settings, 'MEHLR_CONFIG', {})
    max_n = config.get('MAX_CONVERSATION_HISTORY', max_messages)
    messages = list(
        conversation.messages.order_by('-created_at')[:max_n]
    )
    messages.reverse()
    return [{'role': m.role, 'parts': [m.content]} for m in messages]


def _parse_response(raw_response):
    """Gemini yanıt nesnesinden metin ve (varsa) token bilgisini çıkarır."""
    text = ""
    token_count = 0
    if hasattr(raw_response, 'text'):
        text = raw_response.text or ""
    if hasattr(raw_response, 'usage_metadata') and raw_response.usage_metadata:
        token_count = getattr(raw_response.usage_metadata, 'total_token_count', 0) or 0
    return text.strip(), token_count


def generate_response(user_message, conversation, project_slug=None):
    """
    Kullanıcı mesajına göre MEHLR yanıtı üretir.
    conversation: Conversation örneği (user bilgisi için)
    project_slug: seçili proje (None ise genel)
    Döner: (response_text, tokens_used, processing_time, error_message)
    error_message doluysa response_text boş olabilir.
    """
    user_id = conversation.user_id
    if _check_rate_limit(user_id):
        return "", 0, 0.0, "Dakikada izin verilen sorgu sayısına ulaştınız. Lütfen biraz bekleyin."

    cache_ttl = getattr(settings, 'MEHLR_CONFIG', {}).get('CACHE_TTL', 300)
    history = _build_conversation_history(conversation)
    history_hash = hash(tuple((m.get('role'), m.get('parts', [''])[0][:50]) for m in history))
    ckey = _cache_key(user_message, project_slug or 'general', history_hash)
    cached = cache.get(ckey)
    if cached:
        return cached['text'], cached.get('tokens', 0), 0.0, None

    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        return "", 0, 0.0, "Gemini API anahtarı yapılandırılmamış. Lütfen GEMINI_API_KEY ayarlayın."

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        system_prompt = _build_system_prompt(project_slug)
        start = time.time()

        # Gemini 1.5: system instruction + chat history ile generate_content
        chat = model.start_chat(history=[])
        response = chat.send_message(
            f"{system_prompt}\n\n---\nKullanıcı mesajı:\n{user_message}",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=getattr(settings, 'MEHLR_CONFIG', {}).get('MAX_TOKENS', 4096),
                temperature=getattr(settings, 'MEHLR_CONFIG', {}).get('TEMPERATURE', 0.7),
            ),
        )
        elapsed = time.time() - start
        text, tokens = _parse_response(response)
        _incr_rate_limit(user_id)
        cache.set(ckey, {'text': text, 'tokens': tokens}, cache_ttl)
        return text, tokens, elapsed, None
    except Exception as e:
        return "", 0, 0.0, f"AI yanıtı alınamadı: {str(e)}"
