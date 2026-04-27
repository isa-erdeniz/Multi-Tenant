from django.urls import path

from . import views

app_name = "social"

urlpatterns = [
    path("", views.feed_view, name="feed"),
    path("yeni/", views.post_compose_view, name="compose"),
    path("gonderi/<int:pk>/", views.post_detail_view, name="post_detail"),
    path("gonderi/olustur/", views.post_create_view, name="post_create"),
    path("gonderi/<int:pk>/begen/", views.post_like_toggle_view, name="post_like"),
    path("gonderi/<int:pk>/yorum/", views.post_comment_view, name="post_comment"),
    path(
        "kullanici/<int:user_id>/takip/",
        views.user_follow_toggle_view,
        name="user_follow",
    ),
    path("yarismalar/", views.challenge_list_view, name="challenges"),
]
