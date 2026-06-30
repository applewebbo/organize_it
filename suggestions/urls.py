from django.urls import path

from suggestions import views

app_name = "suggestions"

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
]
