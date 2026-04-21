from django.conf import settings


def subscription_context(request):
    """Navbar ve şablonlarda güvenli abonelik erişimi."""
    cur = getattr(settings, "IYZICO_CURRENCY", "TRY")
    sym = "$" if cur == "USD" else "₺"
    base = {
        "payment_currency": cur,
        "payment_currency_symbol": sym,
    }
    if request.user.is_authenticated:
        try:
            base["user_subscription"] = request.user.subscription
        except Exception:
            base["user_subscription"] = None
        return base
    base["user_subscription"] = None
    return base
