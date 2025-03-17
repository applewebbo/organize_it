from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/<int:pk>", views.trip_detail, name="trip-detail"),
    path("trips/list", views.trip_list, name="trip-list"),
    path("stays/<int:pk>", views.stay_detail, name="stay-detail"),
]

htmx_urlpatterns = [
    path("trips/create", views.trip_create, name="trip-create"),
    path("trips/<int:pk>/delete", views.trip_delete, name="trip-delete"),
    path("trips/<int:pk>/update", views.trip_update, name="trip-update"),
    path("trips/<int:pk>/archive", views.trip_archive, name="trip-archive"),
    path("trips/<int:pk>/dates", views.trip_dates_update, name="trip-dates"),
    path("transports/<int:day_id>/create", views.add_transport, name="add-transport"),
    path(
        "experiences/<int:day_id>/create", views.add_experience, name="add-experience"
    ),
    path("meals/<int:day_id>/create", views.add_meal, name="add-meal"),
    path("stays/<int:day_id>/create", views.add_stay, name="add-stay"),
    path("stays/<int:pk>/modify", views.stay_modify, name="stay-modify"),
    path("stays/<int:pk>/delete", views.stay_delete, name="stay-delete"),
    path("events/<int:pk>/delete", views.event_delete, name="event-delete"),
    path("events/<int:pk>/modify", views.event_modify, name="event-modify"),
    path(
        "days/<int:day_id>/check-overlap/",
        views.check_event_overlap,
        name="check-event-overlap",
    ),
]

urlpatterns += htmx_urlpatterns
