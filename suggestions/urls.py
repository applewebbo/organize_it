from django.urls import path

from suggestions import views

app_name = "suggestions"

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
    path("trip/<int:pk>/generate/", views.generate, name="generate"),
    path("trip/<int:pk>/details/", views.details, name="details"),
    path("trip/<int:pk>/modal/", views.suggestion_modal, name="modal"),
    path(
        "trip/<int:pk>/accept/experience/",
        views.accept_experience,
        name="accept-experience",
    ),
    path("trip/<int:pk>/accept/meal/", views.accept_meal, name="accept-meal"),
    path("trip/<int:pk>/accept/stay/", views.accept_stay, name="accept-stay"),
]
