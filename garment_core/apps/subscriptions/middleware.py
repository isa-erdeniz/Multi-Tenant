"""
İstek başına abonelik özeti (şablon / view'larda kullanım için).
Yönlendirme TrialMiddleware'de yapılır; burada yalnızca request'e alan eklenir.
"""


class SubscriptionCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            sub = getattr(request.user, "subscription", None)
            request.subscription = sub
            request.subscription_is_active = (
                sub.is_active() if sub else False
            )
            request.subscription_trial_expired = (
                sub.is_trial_expired() if sub else False
            )
        else:
            request.subscription = None
            request.subscription_is_active = False
            request.subscription_trial_expired = False

        return self.get_response(request)
