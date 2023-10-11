from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/<int:project_id>", views.project_detail, name="project_detail"),
]
