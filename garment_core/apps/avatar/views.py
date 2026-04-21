"""FAZ 10: AI Avatar Oluşturma."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import AvatarStyle, BackgroundTemplate


@login_required
def avatar_index_view(request):
    """Avatar oluşturma ana sayfası."""
    styles = AvatarStyle.objects.all()[:12]
    backgrounds = BackgroundTemplate.objects.all()[:8]
    return render(request, "avatar/index.html", {"styles": styles, "backgrounds": backgrounds})
