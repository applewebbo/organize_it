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
    path("events/<int:pk>/modal", views.event_modal, name="event-modal"),
    path("events/<int:pk>/delete", views.event_delete, name="event-delete"),
    path("events/<int:pk>/unpair", views.event_unpair, name="event-unpair"),
    path(
        "events/<int:pk>/pair-choice", views.event_pair_choice, name="event-pair-choice"
    ),
    path("events/<int:pk>/<int:day_id>/pair", views.event_pair, name="event-pair"),
    path("events/<int:pk>/detail", views.event_detail, name="event-detail"),
    path("events/<int:pk>/modify", views.event_modify, name="event-modify"),
    path(
        "days/<int:day_id>/check-overlap/",
        views.check_event_overlap,
        name="check-event-overlap",
    ),
    path("events/<int:pk1>/swap/<int:pk2>/", views.event_swap, name="event-swap"),
    path(
        "events/<int:pk>/swap-choices", views.event_swap_modal, name="event-swap-modal"
    ),
    path("days/<int:pk>/detail", views.day_detail, name="day-detail"),
]

urlpatterns += htmx_urlpatterns
