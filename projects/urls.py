from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/<int:project_id>", views.project_detail, name="project-detail"),
    path("projects/create", views.project_create, name="project-create"),
]

htmx_urlpatterns = [
    path("projects/create", views.project_create, name="project_create"),
    path(
        "projects/<int:project_id>/delete", views.project_delete, name="project-delete"
    ),
    path("projects/list", views.project_list, name="project-list"),
]

urlpatterns += htmx_urlpatterns
