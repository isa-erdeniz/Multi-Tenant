from django import forms


OCCASION_CHOICES = [
    ("", "Seçin (opsiyonel)"),
    ("gunluk", "Günlük"),
    ("is", "İş / Toplantı"),
    ("aksam", "Akşam yemeği"),
    ("parti", "Parti / Davet"),
    ("spor", "Spor / Egzersiz"),
    ("seyahat", "Seyahat"),
    ("ozel", "Özel gün"),
    ("hafta_sonu", "Hafta sonu"),
]

WEATHER_CHOICES = [
    ("", "Seçin (opsiyonel)"),
    ("sicak", "☀️ Sıcak"),
    ("ilik", "🌤️ Ilık"),
    ("serin", "🌥️ Serin"),
    ("soguk", "🥶 Soğuk"),
    ("yagmur", "🌧️ Yağmurlu"),
]

MOOD_CHOICES = [
    ("", "Seçin (opsiyonel)"),
    ("enerjik", "⚡ Enerjik"),
    ("sakin", "😌 Sakin"),
    ("eglenceli", "😄 Eğlenceli"),
    ("ciddi", "💼 Ciddi"),
    ("romantik", "💕 Romantik"),
    ("rahat", "😎 Rahat"),
]


class StyleRequestForm(forms.Form):
    user_prompt = forms.CharField(
        label="Ne arıyorsunuz?",
        widget=forms.Textarea(
            attrs={
                "placeholder": "Örn: Yarın iş toplantım var, şık ama rahat bir kombin öner...",
                "class": "input-field",
                "rows": 3,
                "autofocus": True,
            }
        ),
        max_length=500,
    )

    occasion = forms.ChoiceField(
        choices=OCCASION_CHOICES,
        required=False,
        label="Etkinlik",
        widget=forms.Select(attrs={"class": "input-field"}),
    )

    weather = forms.ChoiceField(
        choices=WEATHER_CHOICES,
        required=False,
        label="Hava durumu",
        widget=forms.Select(attrs={"class": "input-field"}),
    )

    mood = forms.ChoiceField(
        choices=MOOD_CHOICES,
        required=False,
        label="Ruh hali",
        widget=forms.Select(attrs={"class": "input-field"}),
    )
