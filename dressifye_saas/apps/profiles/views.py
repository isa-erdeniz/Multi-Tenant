from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import UserProfile
from .forms import OnboardingStep1Form, OnboardingStep2Form, OnboardingStep3Form


def _get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@login_required
def onboarding_view(request, step=1):
    """
    3 adımlı onboarding.
    URL: /profil/onboarding/adim/<step>/
    """
    profile = _get_or_create_profile(request.user)

    # Onboarding zaten tamamlandıysa dashboard'a gönder
    if profile.onboarding_completed:
        return redirect("core:dashboard")

    # Adım 1
    if step == 1:
        form = OnboardingStep1Form(request.POST or None, instance=profile)
        if request.method == "POST" and form.is_valid():
            form.save()
            profile.onboarding_step = 2
            profile.save(update_fields=["onboarding_step"])
            return redirect("profiles:onboarding_step", step=2)

        return render(
            request,
            "profiles/onboarding.html",
            {
                "form": form,
                "step": 1,
                "step_title": "Sizi tanıyalım",
                "step_desc": "Adınızı girerek başlayalım.",
                "total_steps": 3,
            },
        )

    # Adım 2
    elif step == 2:
        form = OnboardingStep2Form(request.POST or None, instance=profile)
        if request.method == "POST":
            if form.is_valid():
                form.save()
                profile.onboarding_step = 3
                profile.save(update_fields=["onboarding_step"])
                return redirect("profiles:onboarding_step", step=3)
            if "skip" in request.POST:
                return redirect("profiles:onboarding_step", step=3)

        return render(
            request,
            "profiles/onboarding.html",
            {
                "form": form,
                "step": 2,
                "step_title": "Vücut ölçüleriniz",
                "step_desc": "AI önerilerinin daha iyi olması için bilgi verin. İsterseniz atlayabilirsiniz.",
                "total_steps": 3,
                "skippable": True,
            },
        )

    # Adım 3
    elif step == 3:
        form = OnboardingStep3Form(
            request.POST or None,
            initial={"styles": profile.preferred_styles},
        )
        if request.method == "POST":
            if form.is_valid():
                profile.preferred_styles = form.cleaned_data["styles"]
                profile.onboarding_completed = True
                profile.onboarding_step = 3
                profile.save(
                    update_fields=[
                        "preferred_styles",
                        "onboarding_completed",
                        "onboarding_step",
                    ]
                )
                messages.success(
                    request, f"Hoş geldin, {profile.get_display_name()}! Profilin hazır."
                )
                return redirect("core:dashboard")
            if "skip" in request.POST:
                profile.onboarding_completed = True
                profile.save(update_fields=["onboarding_completed"])
                return redirect("core:dashboard")

        return render(
            request,
            "profiles/onboarding.html",
            {
                "form": form,
                "step": 3,
                "step_title": "Stil tercihleriniz",
                "step_desc": "Hangi tarzı seviyorsunuz?",
                "total_steps": 3,
                "skippable": True,
            },
        )

    # Geçersiz adım
    return redirect("profiles:onboarding_step", step=1)


@login_required
def profile_view(request):
    profile = _get_or_create_profile(request.user)
    return render(request, "profiles/profile.html", {"profile": profile})


@login_required
def profile_edit_view(request):
    profile = _get_or_create_profile(request.user)

    if request.method == "POST":
        form = OnboardingStep2Form(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil güncellendi.")
            return redirect("profiles:profile")
    else:
        form = OnboardingStep2Form(instance=profile)

    return render(request, "profiles/edit.html", {"form": form})
