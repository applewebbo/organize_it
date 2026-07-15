from django.urls import path

from suggestions import views

app_name = "suggestions"

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
    path("trip/<int:pk>/generate/", views.generate, name="generate"),
    path("trip/<int:pk>/cached/", views.cached, name="cached"),
    path("trip/<int:pk>/details/", views.details, name="details"),
    path("trip/<int:pk>/modal/", views.suggestion_modal, name="modal"),
    path(
        "trip/<int:pk>/day/<int:day_id>/plan/",
        views.plan_day_modal,
        name="plan-day-modal",
    ),
    path(
        "trip/<int:pk>/day/<int:day_id>/generate/",
        views.generate_day,
        name="generate-day",
    ),
    path(
        "trip/<int:pk>/day/<int:day_id>/accept/",
        views.accept_day,
        name="accept-day",
    ),
    path(
        "trip/<int:pk>/accept/experience/",
        views.accept_experience,
        name="accept-experience",
    ),
    path("trip/<int:pk>/accept/meal/", views.accept_meal, name="accept-meal"),
    path("trip/<int:pk>/accept/stay/", views.accept_stay, name="accept-stay"),
    path(
        "trip/<int:pk>/dismiss-shared-key-notice/",
        views.dismiss_shared_key_notice,
        name="dismiss-shared-key-notice",
    ),
]
