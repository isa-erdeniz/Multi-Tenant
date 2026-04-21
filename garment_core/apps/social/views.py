"""Topluluk — gönderi, beğeni, yorum, takip."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.wardrobe.models import Outfit

from .models import Challenge, Comment, Follow, Like, Post

User = get_user_model()


def feed_view(request):
    """Herkese açık gönderi akışı."""
    posts = (
        Post.objects.filter(visibility="public")
        .select_related("user", "outfit")
        .prefetch_related("likes")[:30]
    )
    return render(request, "social/feed.html", {"posts": posts})


@login_required
def post_detail_view(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("user", "outfit"), pk=pk
    )
    comments = post.comments.filter(parent__isnull=True).select_related("user")[:50]
    liked = Like.objects.filter(post=post, user=request.user).exists()
    return render(
        request,
        "social/post_detail.html",
        {"post": post, "comments": comments, "liked": liked},
    )


@login_required
@require_POST
def post_create_view(request):
    """Kombin paylaşımı (Outfit gerekli)."""
    outfit_id = request.POST.get("outfit_id")
    caption = (request.POST.get("caption") or "").strip()[:2000]
    if not outfit_id:
        messages.error(request, "Kombin seçin.")
        return redirect("social:feed")
    outfit = get_object_or_404(
        Outfit, pk=outfit_id, user=request.user
    )
    Post.objects.create(
        user=request.user,
        outfit=outfit,
        caption=caption,
    )
    messages.success(request, "Gönderiniz paylaşıldı.")
    return redirect("social:feed")


@login_required
@require_POST
def post_like_toggle_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    with transaction.atomic():
        like = Like.objects.filter(post=post, user=request.user).first()
        if like:
            like.delete()
            Post.objects.filter(pk=post.pk).update(
                likes_count=F("likes_count") - 1
            )
        else:
            Like.objects.create(post=post, user=request.user)
            Post.objects.filter(pk=post.pk).update(
                likes_count=F("likes_count") + 1
            )
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    return redirect(next_url or "social:feed")


@login_required
@require_POST
def post_comment_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    content = (request.POST.get("content") or "").strip()
    if not content:
        messages.error(request, "Yorum boş olamaz.")
        return redirect("social:post_detail", pk=pk)
    Comment.objects.create(post=post, user=request.user, content=content[:2000])
    # likes_count benzeri yorum sayısı için alan yok; şimdilik sadece kayıt
    return redirect("social:post_detail", pk=pk)


@login_required
@require_POST
def user_follow_toggle_view(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.id == request.user.id:
        messages.error(request, "Kendinizi takip edemezsiniz.")
        return redirect("social:feed")
    rel = Follow.objects.filter(
        follower=request.user, following=target
    ).first()
    if rel:
        rel.delete()
        messages.info(request, "Takipten çıktınız.")
    else:
        Follow.objects.create(follower=request.user, following=target)
        messages.success(request, "Takip ediliyor.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    return redirect(next_url or "social:feed")


def challenge_list_view(request):
    from django.utils import timezone

    today = timezone.now().date()
    challenges = Challenge.objects.filter(end_date__gte=today).order_by(
        "-start_date"
    )[:20]
    return render(
        request,
        "social/challenges.html",
        {"challenges": challenges},
    )


@login_required
def post_compose_view(request):
    """Kombin seçerek paylaşım formu."""
    outfits = Outfit.objects.filter(user=request.user).order_by("-created_at")[:50]
    return render(
        request,
        "social/compose.html",
        {"outfits": outfits},
    )
