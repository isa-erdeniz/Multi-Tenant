from django.contrib import admin
from .models import Post, Comment, Like, Follow, Challenge, ChallengeEntry


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["user", "outfit", "likes_count", "created_at"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["post", "user", "content"]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ["post", "user"]


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "following"]


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ["title", "start_date", "end_date"]


@admin.register(ChallengeEntry)
class ChallengeEntryAdmin(admin.ModelAdmin):
    list_display = ["challenge", "user", "votes_count"]
