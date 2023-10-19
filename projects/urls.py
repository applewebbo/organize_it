from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/<int:pk>", views.project_detail, name="project-detail"),
]

htmx_urlpatterns = [
    path("projects/create", views.project_create, name="project-create"),
    path("projects/<int:pk>/delete", views.project_delete, name="project-delete"),
    path("projects/<int:pk>/update", views.project_update, name="project-update"),
    path("projects/list", views.project_list, name="project-list"),
    path("projects/<int:pk>/add-link", views.project_add_link, name="project-add-link"),
    path("links/<int:pk>/delete", views.link_delete, name="link-delete"),
    path("links/<int:pk>/", views.link_update, name="link-update"),
    path("links/<int:project_id>/list", views.link_list, name="link-list"),
    path(
        "places/<int:project_id>/create", views.place_create, name="project-add-place"
    ),
]

urlpatterns += htmx_urlpatterns
