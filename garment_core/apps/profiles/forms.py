from django import forms

from .models import UserProfile


STYLE_CHOICES = [
    ("casual", "Günlük"),
    ("elegant", "Şık / Elegant"),
    ("sport", "Spor"),
    ("bohemian", "Bohem"),
    ("minimalist", "Minimalist"),
    ("classic", "Klasik"),
    ("streetwear", "Sokak Stili"),
    ("romantic", "Romantik"),
]


class OnboardingStep1Form(forms.ModelForm):
    """Adım 1: İsim"""

    class Meta:
        model = UserProfile
        fields = ["first_name"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "Adınız",
                    "class": "input-field",
                    "autofocus": True,
                }
            ),
        }
        labels = {
            "first_name": "Adınız",
        }


class OnboardingStep2Form(forms.ModelForm):
    """Adım 2: Vücut ölçüleri + şehir (opsiyonel)"""

    class Meta:
        model = UserProfile
        fields = ["city", "height", "weight", "bust", "waist", "hips", "body_shape", "skin_tone"]
        widgets = {
            "city": forms.TextInput(
                attrs={"placeholder": "örn. İstanbul, İzmir", "class": "input-field"}
            ),
            "height": forms.NumberInput(
                attrs={"placeholder": "örn. 165", "class": "input-field"}
            ),
            "weight": forms.NumberInput(
                attrs={"placeholder": "örn. 60", "class": "input-field"}
            ),
            "bust": forms.NumberInput(
                attrs={"placeholder": "örn. 90", "class": "input-field"}
            ),
            "waist": forms.NumberInput(
                attrs={"placeholder": "örn. 70", "class": "input-field"}
            ),
            "hips": forms.NumberInput(
                attrs={"placeholder": "örn. 95", "class": "input-field"}
            ),
            "body_shape": forms.Select(attrs={"class": "input-field"}),
            "skin_tone": forms.Select(attrs={"class": "input-field"}),
        }
        labels = {
            "city": "Şehir (hava durumu için)",
            "height": "Boy (cm)",
            "weight": "Kilo (kg)",
            "bust": "Göğüs çevresi (cm)",
            "waist": "Bel çevresi (cm)",
            "hips": "Kalça çevresi (cm)",
            "body_shape": "Vücut tipi",
            "skin_tone": "Ten rengi",
        }


class OnboardingStep3Form(forms.Form):
    """Adım 3: Stil tercihleri"""

    styles = forms.MultipleChoiceField(
        choices=STYLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tercih ettiğiniz stiller",
        help_text="İstediğiniz kadar seçebilirsiniz.",
    )
