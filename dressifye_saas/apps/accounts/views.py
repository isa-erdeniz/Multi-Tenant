from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import LoginForm, RegisterForm
from .models import DressifyeUser


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                next_url = request.GET.get("next", "core:dashboard")
                return redirect(next_url)
            else:
                messages.error(request, "E-posta veya şifre hatalı.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("core:landing")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Signal (create_user_subscription) otomatik trial oluşturur

            login(request, user)
            messages.success(request, "Hoş geldiniz! 7 günlük ücretsiz denemeniz başladı.")
            return redirect("profiles:onboarding_step", step=1)
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_settings_view(request):
    return render(request, "accounts/settings.html")
