from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.home, name="home"),
    path("toggle-guide/", views.toggle_guide, name="toggle-guide"),
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
    path(
        "experiences/<int:day_id>/create", views.add_experience, name="add-experience"
    ),
    path("meals/<int:day_id>/create", views.add_meal, name="add-meal"),
    path("stays/<int:day_id>/create", views.add_stay, name="add-stay"),
    path(
        "trips/<int:trip_pk>/experiences/create",
        views.add_experience_to_trip,
        name="add-experience-to-trip",
    ),
    path(
        "trips/<int:trip_pk>/meals/create",
        views.add_meal_to_trip,
        name="add-meal-to-trip",
    ),
    path(
        "trips/<int:trip_pk>/stays/create",
        views.add_stay_for_trip,
        name="add-stay-for-trip",
    ),
    path("stays/<int:pk>/modify", views.stay_modify, name="stay-modify"),
    path("stays/<int:pk>/delete", views.stay_delete, name="stay-delete"),
    path("stays/<int:stay_id>/enrich/", views.enrich_stay, name="enrich-stay"),
    # STAY TRANSFERS
    path(
        "stay-transfers/<int:from_day_id>/create",
        views.create_stay_transfer,
        name="create-stay-transfer",
    ),
    path(
        "stay-transfers/<int:pk>/edit",
        views.edit_stay_transfer,
        name="edit-stay-transfer",
    ),
    path(
        "stay-transfers/<int:pk>/delete",
        views.delete_stay_transfer,
        name="delete-stay-transfer",
    ),
    # MAIN TRANSFERS
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
        "main-transfers/<int:pk>/train-status",
        views.train_status_redirect,
        name="train-status-redirect",
    ),
    path(
        "main-transfers/<int:pk>/flight-status",
        views.flight_status_redirect,
        name="flight-status-redirect",
    ),
    path(
        "trips/<int:trip_id>/main-transfers-section",
        views.main_transfers_section,
        name="main-transfers-section",
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
        "days/<int:day_id>/reorder-events/",
        views.reorder_events,
        name="reorder-events",
    ),
    path(
        "events/<int:event_id>/swap-order/",
        views.swap_event_order,
        name="swap-event-order",
    ),
    path(
        "events/<int:event_id>/swap-order/modal/",
        views.swap_event_order_modal,
        name="swap-event-order-modal",
    ),
    # MAIN TRANSFER CONNECTIONS
    path(
        "main-transfer-connections/<int:main_transfer_pk>/modal",
        views.main_transfer_connection_modal,
        name="main-transfer-connection-modal",
    ),
    path(
        "main-transfer-connections/<int:main_transfer_pk>/create/<str:destination_type>",
        views.create_main_transfer_connection,
        name="create-main-transfer-connection",
    ),
    path(
        "main-transfer-connections/<int:pk>/edit",
        views.edit_main_transfer_connection,
        name="edit-main-transfer-connection",
    ),
    path(
        "main-transfer-connections/<int:pk>/delete",
        views.delete_main_transfer_connection,
        name="delete-main-transfer-connection",
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
    path("search-airports/", views.search_airports_view, name="search-airports"),
    path("search-stations/", views.search_stations, name="search-stations"),
    # MAIN TRANSFER MODAL
    path(
        "trips/<int:trip_id>/arrival-transfer/modal",
        views.arrival_transfer_modal,
        name="arrival-transfer-modal",
    ),
    path(
        "trips/<int:trip_id>/departure-transfer/modal",
        views.departure_transfer_modal,
        name="departure-transfer-modal",
    ),
    path(
        "trips/<int:trip_id>/main-transfer/step",
        views.main_transfer_step,
        name="main-transfer-step",
    ),
    path(
        "trips/<int:trip_id>/main-transfer/save",
        views.save_main_transfer,
        name="save-main-transfer",
    ),
    # IMAGE MANAGEMENT
    path("images/search/", views.search_trip_images, name="search-images"),
    # COLLABORATION
    path(
        "trips/<int:trip_id>/collaborators/",
        views.collaborators_modal,
        name="collaborators-modal",
    ),
    path(
        "trips/<int:trip_id>/collaborators/inline/",
        views.collab_inline,
        name="collab-inline",
    ),
    path(
        "trips/<int:trip_id>/collaborators/search/",
        views.search_user_by_email,
        name="search-user-by-email",
    ),
    path(
        "trips/<int:trip_id>/collaborators/add/",
        views.add_collaborator,
        name="add-collaborator",
    ),
    path(
        "trips/<int:trip_id>/collaborators/<int:collaboration_id>/remove/",
        views.remove_collaborator,
        name="remove-collaborator",
    ),
    path(
        "trips/<int:trip_id>/collaborators/<int:collaboration_id>/toggle-role/",
        views.toggle_participant_role,
        name="toggle-participant-role",
    ),
    path(
        "trips/<int:trip_id>/collaborators/add-viewer/",
        views.add_viewer_by_email,
        name="add-viewer-by-email",
    ),
    path(
        "trips/<int:trip_id>/collaborators/add-named/",
        views.add_named_participant,
        name="add-named-participant",
    ),
    path(
        "trips/<int:trip_id>/collaborators/invite/",
        views.invite_collaborator,
        name="invite-collaborator",
    ),
    path(
        "invitations/<uuid:token>/accept/",
        views.accept_invitation,
        name="accept-invitation",
    ),
    # SHARING
    path(
        "trips/<int:trip_id>/share/create/",
        views.share_link_create,
        name="share-link-create",
    ),
    path("trips/<int:trip_id>/share/", views.share_link_list, name="share-link-list"),
    path(
        "share-link/<uuid:link_id>/revoke/",
        views.share_link_revoke,
        name="share-link-revoke",
    ),
]

urlpatterns += htmx_urlpatterns
urlpatterns += [
    path("share/<uuid:token>/", views.shared_trip_detail, name="shared-trip"),
    # Unified trip map
    path("trips/<int:pk>/map/", views.trip_map, name="trip-map"),
    path("trips/<int:pk>/map/search/", views.map_search, name="map-search"),
    path(
        "trips/<int:pk>/map/add/experience/",
        views.map_add_experience,
        name="map-add-experience",
    ),
    path("trips/<int:pk>/map/add/meal/", views.map_add_meal, name="map-add-meal"),
    path("trips/<int:pk>/map/add/stay/", views.map_add_stay, name="map-add-stay"),
    # Embedded events map (trip-detail toggle)
    path("trips/<int:pk>/events-map/", views.trip_events_map, name="trip-events-map"),
    path(
        "trips/<int:pk>/events-list/", views.trip_events_list, name="trip-events-list"
    ),
    path(
        "trips/<int:pk>/select-day/<str:category>/",
        views.select_day_for_event,
        name="select-day-for-event",
    ),
    path(
        "trips/<int:trip_pk>/destinations/",
        views.trip_destinations,
        name="trip-destinations",
    ),
    path(
        "trips/<int:trip_pk>/days/<int:day_pk>/destination/",
        views.update_day_destination,
        name="update-day-destination",
    ),
]
