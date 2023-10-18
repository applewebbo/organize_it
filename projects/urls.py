from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/<int:pk>", views.project_detail, name="project-detail"),
    path("projects/create", views.project_create, name="project-create"),
]

htmx_urlpatterns = [
    path("projects/create", views.project_create, name="project_create"),
    path("projects/<int:pk>/delete", views.project_delete, name="project-delete"),
    path("projects/<int:pk>/update", views.project_update, name="project-update"),
    path("projects/list", views.project_list, name="project-list"),
    path("projects/<int:pk>/add-link", views.project_add_link, name="project-add-link"),
]

urlpatterns += htmx_urlpatterns
