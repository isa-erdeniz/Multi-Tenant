"""FAZ 8: AR Makyaj Deneme Motoru."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import MakeupLook


@login_required
def beauty_index_view(request):
    """Makyaj deneme ana sayfası."""
    looks = MakeupLook.objects.all()[:24]
    return render(request, "beauty/index.html", {"looks": looks})
