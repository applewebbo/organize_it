from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("update-theme/", views.update_theme, name="update_theme"),
    path(
        "autocomplete-home-address/",
        views.autocomplete_home_address,
        name="autocomplete-home-address",
    ),
]
