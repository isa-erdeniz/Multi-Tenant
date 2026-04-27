from django import forms
from django.contrib.auth.forms import UserCreationForm
from allauth.account.forms import SignupForm

from .models import DressifyeUser


class AllauthSignupForm(SignupForm):
    """django-allauth kayıt formu: username=email, trial signal tetiklenir."""

    def save(self, request):
        user = super().save(request)
        user.username = user.email
        user.save(update_fields=["username"])
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "E-posta adresiniz",
                "class": "input-field",
                "autofocus": True,
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Şifreniz",
                "class": "input-field",
            }
        )
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "E-posta adresiniz",
                "class": "input-field",
            }
        )
    )
    password1 = forms.CharField(
        label="Şifre",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Şifre oluşturun",
                "class": "input-field",
            }
        ),
    )
    password2 = forms.CharField(
        label="Şifre tekrar",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Şifreyi tekrar girin",
                "class": "input-field",
            }
        ),
    )

    class Meta:
        model = DressifyeUser
        fields = ("email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email  # username = email
        if commit:
            user.save()
        return user
