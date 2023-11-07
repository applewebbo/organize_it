from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/<int:pk>", views.project_detail, name="project-detail"),
    path("projects/list", views.project_list, name="project-list"),
]

htmx_urlpatterns = [
    path("projects/create", views.project_create, name="project-create"),
    path("projects/<int:pk>/delete", views.project_delete, name="project-delete"),
    path("projects/<int:pk>/update", views.project_update, name="project-update"),
    path("projects/<int:pk>/archive", views.project_archive, name="project-archive"),
    path("projects/<int:pk>/add-link", views.project_add_link, name="project-add-link"),
    path("projects/<int:pk>/dates", views.project_dates_update, name="project-dates"),
    path("links/<int:pk>/delete", views.link_delete, name="link-delete"),
    path("links/<int:pk>/update", views.link_update, name="link-update"),
    path("links/<int:pk>/list", views.link_list, name="link-list"),
    path("places/<int:pk>/add", views.project_add_place, name="project-add-place"),
    path("places/<int:pk>/list", views.place_list, name="place-list"),
    path("places/<int:pk>/delete", views.place_delete, name="place-delete"),
    path("places/<int:pk>/update", views.place_update, name="place-update"),
    path("notes/<int:pk>/add", views.project_add_note, name="project-add-note"),
    path("notes/<int:pk>/list", views.note_list, name="note-list"),
    path("notes/<int:pk>/update", views.note_update, name="note-update"),
    path("notes/<int:pk>/delete", views.note_delete, name="note-delete"),
]

urlpatterns += htmx_urlpatterns
