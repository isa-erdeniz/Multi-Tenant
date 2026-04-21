"""FAZ 9: Sanal Saç Değiştirme."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import HairStyle, HairColor


@login_required
def hair_index_view(request):
    """Saç değiştirme ana sayfası."""
    styles = HairStyle.objects.all()[:20]
    colors = HairColor.objects.all()[:20]
    return render(request, "hair/index.html", {"styles": styles, "colors": colors})
