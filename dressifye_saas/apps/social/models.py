"""
FAZ 15: Sosyal Özellikler & Topluluk
"""
from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models import TimeStampedModel
from apps.wardrobe.models import Outfit

User = get_user_model()


class Post(TimeStampedModel):
    """Kombin paylaşımı (Instagram benzeri)."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posts"
    )
    outfit = models.ForeignKey(
        Outfit, on_delete=models.CASCADE, related_name="posts"
    )
    caption = models.TextField(blank=True)
    hashtags = models.JSONField(default=list)
    visibility = models.CharField(max_length=20, default="public")
    likes_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Gönderi"
        verbose_name_plural = "Gönderiler"
        ordering = ["-created_at"]


class Comment(TimeStampedModel):
    """Yorum."""
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField()
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )

    class Meta:
        verbose_name = "Yorum"
        verbose_name_plural = "Yorumlar"
        ordering = ["created_at"]


class Like(TimeStampedModel):
    """Beğeni."""
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="likes"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="likes"
    )

    class Meta:
        verbose_name = "Beğeni"
        verbose_name_plural = "Beğeniler"
        unique_together = ["post", "user"]


class Follow(TimeStampedModel):
    """Takip ilişkisi."""
    follower = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="following"
    )
    following = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="followers"
    )

    class Meta:
        verbose_name = "Takip"
        verbose_name_plural = "Takipçiler"
        unique_together = ["follower", "following"]


class Challenge(TimeStampedModel):
    """Stil yarışması."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    rules = models.TextField(blank=True)

    class Meta:
        verbose_name = "Yarışma"
        verbose_name_plural = "Yarışmalar"
        ordering = ["-start_date"]


class ChallengeEntry(TimeStampedModel):
    """Yarışma katılımı."""
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name="entries"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="challenge_entries"
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="challenge_entries"
    )
    votes_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Yarışma Katılımı"
        verbose_name_plural = "Yarışma Katılımları"
        unique_together = ["challenge", "user"]
