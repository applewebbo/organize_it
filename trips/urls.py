from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.home, name="home"),
    path("trips/<int:pk>", views.trip_detail, name="trip-detail"),
    path("trips/list", views.trip_list, name="trip-list"),
    path("stays/<int:pk>", views.stay_detail, name="stay-detail"),
    path("log/<str:filename>", views.view_log_file, name="log"),
]

htmx_urlpatterns = [
    path("trips/create", views.trip_create, name="trip-create"),
    path("trips/<int:pk>/delete", views.trip_delete, name="trip-delete"),
    path("trips/<int:pk>/update", views.trip_update, name="trip-update"),
    path("trips/<int:pk>/archive", views.trip_archive, name="trip-archive"),
    path("trips/<int:pk>/unarchive", views.trip_unarchive, name="trip-unarchive"),
    path("trips/<int:pk>/dates", views.trip_dates_update, name="trip-dates"),
    path("transports/<int:day_id>/create", views.add_transport, name="add-transport"),
    path(
        "experiences/<int:day_id>/create", views.add_experience, name="add-experience"
    ),
    path("meals/<int:day_id>/create", views.add_meal, name="add-meal"),
    path("stays/<int:day_id>/create", views.add_stay, name="add-stay"),
    path("stays/<int:pk>/modify", views.stay_modify, name="stay-modify"),
    path("stays/<int:pk>/delete", views.stay_delete, name="stay-delete"),
    path("stays/<int:stay_id>/enrich/", views.enrich_stay, name="enrich-stay"),
    # MAIN TRANSFERS
    path(
        "trips/<int:trip_id>/main-transfer/create",
        views.add_main_transfer,
        name="add-main-transfer",
    ),
    path(
        "main-transfers/<int:pk>/edit",
        views.edit_main_transfer,
        name="edit-main-transfer",
    ),
    path(
        "main-transfers/<int:pk>/delete",
        views.delete_main_transfer,
        name="delete-main-transfer",
    ),
    path(
        "transport-type-fields/",
        views.get_transport_type_fields,
        name="transport-type-fields",
    ),
    path(
        "stays/<int:stay_id>/enrich/confirm/",
        views.confirm_enrich_stay,
        name="confirm-enrich-stay",
    ),
    # EVENTS
    path("events/<int:pk>/modal", views.event_modal, name="event-modal"),
    path("events/<int:pk>/delete", views.event_delete, name="event-delete"),
    path("events/<int:pk>/unpair", views.event_unpair, name="event-unpair"),
    path(
        "events/<int:pk>/pair-choice", views.event_pair_choice, name="event-pair-choice"
    ),
    path("events/<int:pk>/<int:day_id>/pair", views.event_pair, name="event-pair"),
    path("events/<int:pk>/detail", views.event_detail, name="event-detail"),
    path("events/<int:pk>/modify", views.event_modify, name="event-modify"),
    path("events/single/<int:pk>/", views.single_event, name="single-event"),
    path("events/<int:event_id>/enrich/", views.enrich_event, name="enrich-event"),
    path(
        "events/<int:event_id>/enrich/confirm/",
        views.confirm_enrich_event,
        name="confirm-enrich-event",
    ),
    path(
        "events/<int:pk>/change-times",
        views.event_change_times,
        name="event-change-times",
    ),
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
    path("validate/dates/", views.validate_dates, name="validate-dates"),
    # NOTES
    path("notes/<int:event_id>/", views.event_notes, name="event-notes"),
    path("notes/<int:event_id>/create", views.note_create, name="note-create"),
    path("notes/<int:event_id>/delete", views.note_delete, name="note-delete"),
    path("notes/<int:event_id>/modify", views.note_modify, name="note-modify"),
    path("stay-notes/<int:stay_id>/", views.stay_notes, name="stay-notes"),
    path(
        "stay-notes/<int:stay_id>/create",
        views.stay_note_create,
        name="stay-note-create",
    ),
    path(
        "stay-notes/<int:stay_id>/modify",
        views.stay_note_modify,
        name="stay-note-modify",
    ),
    path(
        "stay-notes/<int:stay_id>/delete",
        views.stay_note_delete,
        name="stay-note-delete",
    ),
    path("geocode-address/", views.geocode_address, name="geocode-address"),
    path("get-trip-addresses/", views.get_trip_addresses, name="get-trip-addresses"),
    path("days/<int:day_id>/map/", views.DayMapView.as_view(), name="day-map"),
    # IMAGE MANAGEMENT
    path("images/search/", views.search_trip_images, name="search-images"),
]

urlpatterns += htmx_urlpatterns
