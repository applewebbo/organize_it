from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/<int:pk>", views.trip_detail, name="trip-detail"),
    path("trips/list", views.trip_list, name="trip-list"),
]

htmx_urlpatterns = [
    path("trips/create", views.trip_create, name="trip-create"),
    path("trips/<int:pk>/delete", views.trip_delete, name="trip-delete"),
    path("trips/<int:pk>/update", views.trip_update, name="trip-update"),
    path("trips/<int:pk>/archive", views.trip_archive, name="trip-archive"),
    path("trips/<int:pk>/add-link", views.trip_add_link, name="trip-add-link"),
    path("trips/<int:pk>/dates", views.trip_dates_update, name="trip-dates"),
    path("links/<int:pk>/delete", views.link_delete, name="link-delete"),
    path("links/<int:pk>/update", views.link_update, name="link-update"),
    path("links/<int:pk>/list", views.link_list, name="link-list"),
    path("places/<int:pk>/add", views.trip_add_place, name="trip-add-place"),
    path("places/<int:pk>/list", views.place_list, name="place-list"),
    path("places/<int:pk>/delete", views.place_delete, name="place-delete"),
    path("places/<int:pk>/update", views.place_update, name="place-update"),
    path("places/<int:pk>/assign", views.place_assign, name="place-assign"),
    path("notes/<int:pk>/add", views.trip_add_note, name="trip-add-note"),
    path("notes/<int:pk>/list", views.note_list, name="note-list"),
    path("notes/<int:pk>/update", views.note_update, name="note-update"),
    path("notes/<int:pk>/delete", views.note_delete, name="note-delete"),
    path("notes/<int:pk>/check", views.note_check_or_uncheck, name="note-check"),
    path("trips/<int:pk>/map", views.map, name="map"),
    path("trips/<int:pk>/<int:day>/map", views.map, name="map"),
    path("transports/<int:day_id>/create", views.add_transport, name="add-transport"),
]

urlpatterns += htmx_urlpatterns
