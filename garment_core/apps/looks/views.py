"""FAZ 11: Hazır Görünüm Paketleri.

Kullanıcı tarafından look oluşturma akışı yok; yalnızca LookPackage listesi.
look_create için FeatureUsage (look_create) bu modülde kullanılmıyor.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import LookPackage


@login_required
def looks_index_view(request):
    """Görünüm galerisi."""
    looks = LookPackage.objects.all()[:24]
    return render(request, "looks/index.html", {"looks": looks})
