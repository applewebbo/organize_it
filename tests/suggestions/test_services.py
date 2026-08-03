from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.test import override_settings

from suggestions.ai.base import AISuggestionError
from suggestions.schemas import (
    DayItinerary,
    DayPlan,
    ItineraryStop,
    Suggestion,
    SuggestionPrefs,
    TripContext,
    TripItinerary,
)
from suggestions.services import (
    _CACHE_TTL,
    _LAST_TTL,
    DAY_STRATEGY_ADD,
    DAY_STRATEGY_DELETE,
    DAY_STRATEGY_UNPAIR,
    GroundedDay,
    GroundedStop,
    GroundedSuggestion,
    _last_key,
    _trip_stages,
    build_day_context,
    build_trip_context,
    generate_day_itinerary,
    generate_suggestions,
    generate_trip_itinerary,
    get_cached_suggestions,
    merge_preferences,
    resolve_credentials,
    should_show_shared_key_notice,
)
from tests.accounts.factories import UserFactory
from tests.suggestions.factories import (
    AICredentialsFactory,
    SharedKeyNoticeDismissalFactory,
    SuggestionPreferencesFactory,
)
from tests.trips.factories import ExperienceFactory, StayFactory, TripFactory
from trips.models import TripCollaboration
from trips.services import GooglePlacesError, PlaceResult
from trips.utils import apply_stage


def _add_collaborator(trip, user):
    TripCollaboration.objects.create(
        trip=trip, user=user, color="blue", added_by=trip.author
    )


pytestmark = pytest.mark.django_db

PLACE = PlaceResult(
    place_id="ChIJ_grounded",
    name="Trattoria",
    address="Via Roma 1, Roma, Italy",
    lat=41.9,
    lng=12.5,
)


class TestBuildTripContext:
    def test_maps_trip_fields(self):
        trip = TripFactory(destination="Roma")
        context = build_trip_context(trip, language="it")
        assert isinstance(context, TripContext)
        assert context.destination == "Roma"
        assert context.start_date == trip.start_date
        assert context.language == "it"

    def test_collects_existing_events_and_stays(self):
        trip = TripFactory(destination="Roma")
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day, name="Colosseo", city="Roma")
        StayFactory(name="Hotel Rex", city="Roma", day=day)

        context = build_trip_context(trip)

        assert "Colosseo (Roma)" in context.existing_places
        assert "Hotel Rex (Roma)" in context.existing_places

    def test_existing_place_without_city_uses_bare_name(self):
        trip = TripFactory(destination="Roma")
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day, name="Passeggiata", city="")

        context = build_trip_context(trip)

        assert "Passeggiata" in context.existing_places

    def test_collects_weather_for_days_with_data(self):
        trip = TripFactory(destination="Roma")
        day = trip.days.first()
        day.weather_data = {
            "weather_label": "Clear sky",
            "temperature_min": 15.4,
            "temperature_max": 28.1,
            "precipitation_sum": 0.0,
        }
        day.save(update_fields=["weather_data"])

        context = build_trip_context(trip)

        assert len(context.weather) == 1
        assert "Clear sky" in context.weather[0]
        assert "15" in context.weather[0]
        assert "28" in context.weather[0]

    def test_no_weather_when_data_missing(self):
        trip = TripFactory(destination="Roma")
        context = build_trip_context(trip)
        assert context.weather == []

    def test_stage_scopes_existing_places_and_weather(self):
        trip = TripFactory(destination="Roma")
        days = list(trip.days.all())
        florence_day, rome_day = days[0], days[1]
        florence_day.destination = "Firenze"
        florence_day.weather_data = {
            "weather_label": "Rain",
            "temperature_min": 10.0,
            "temperature_max": 16.0,
            "precipitation_sum": 12.0,
        }
        florence_day.save(update_fields=["destination", "weather_data"])
        rome_day.destination = "Roma"
        rome_day.weather_data = {
            "weather_label": "Clear sky",
            "temperature_min": 18.0,
            "temperature_max": 30.0,
            "precipitation_sum": 0.0,
        }
        rome_day.save(update_fields=["destination", "weather_data"])
        ExperienceFactory(trip=trip, day=florence_day, name="Uffizi", city="Firenze")
        ExperienceFactory(trip=trip, day=rome_day, name="Colosseo", city="Roma")

        context = build_trip_context(trip, stage="Firenze")

        assert "Uffizi (Firenze)" in context.existing_places
        assert "Colosseo (Roma)" not in context.existing_places
        assert len(context.weather) == 1
        assert "Rain" in context.weather[0]


class TestMergePreferences:
    def test_defaults_when_nothing_provided(self):
        prefs = merge_preferences(None, None)
        assert prefs == SuggestionPrefs()

    def test_uses_user_defaults(self):
        defaults = SuggestionPreferencesFactory.build(
            favored_experience_types=[1, 2],
            dietary="vegan",
            budget="high",
            travel_party="family",
            travel_style="offbeat",
            interests=["history"],
            cuisine="local",
            search_radius="city",
            notes="no crowds",
        )
        prefs = merge_preferences(defaults, None)
        assert prefs.dietary == "vegan"
        assert prefs.favored_experience_types == [1, 2]
        assert prefs.travel_party == "family"
        assert prefs.travel_style == "offbeat"
        assert prefs.interests == ["history"]
        assert prefs.cuisine == "local"
        assert prefs.search_radius == "city"
        assert prefs.notes == "no crowds"

    def test_overrides_win_field_by_field(self):
        defaults = SuggestionPreferencesFactory.build(dietary="vegan", budget="low")
        prefs = merge_preferences(defaults, {"budget": "high"})
        assert prefs.dietary == "vegan"
        assert prefs.budget == "high"

    def test_notes_are_concatenated(self):
        defaults = SuggestionPreferencesFactory.build(notes="no crowds")
        prefs = merge_preferences(defaults, {"notes": "with kids"})
        assert prefs.notes == "no crowds\nwith kids"

    def test_extra_notes_without_defaults(self):
        prefs = merge_preferences(None, {"notes": "with kids"})
        assert prefs.notes == "with kids"

    def test_uses_user_result_count(self):
        defaults = SuggestionPreferencesFactory.build(result_count=12)
        prefs = merge_preferences(defaults, None)
        assert prefs.result_count == 12

    def test_kinds_override(self):
        prefs = merge_preferences(None, {"kinds": ["meal", "stay"]})
        assert prefs.kinds == ["meal", "stay"]


class TestResolveCredentials:
    def test_returns_own_key(self):
        creds = AICredentialsFactory()
        trip = TripFactory(author=creds.user)
        assert resolve_credentials(creds.user, trip) == creds

    def test_own_key_takes_precedence_over_shared(self):
        author = AICredentialsFactory(share_with_collaborators=True)
        trip = TripFactory(author=author.user)
        collab_creds = AICredentialsFactory()
        _add_collaborator(trip, collab_creds.user)
        assert resolve_credentials(collab_creds.user, trip) == collab_creds

    def test_falls_back_to_author_shared_key(self):
        author = AICredentialsFactory(share_with_collaborators=True)
        trip = TripFactory(author=author.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)
        assert resolve_credentials(collaborator, trip) == author

    def test_no_fallback_when_author_not_sharing(self):
        author = AICredentialsFactory(share_with_collaborators=False)
        trip = TripFactory(author=author.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)
        assert resolve_credentials(collaborator, trip) is None

    def test_no_fallback_when_shared_key_empty(self):
        author = AICredentialsFactory(
            share_with_collaborators=True, api_key_encrypted=""
        )
        trip = TripFactory(author=author.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)
        assert resolve_credentials(collaborator, trip) is None

    def test_returns_none_without_any_key(self):
        trip = TripFactory()
        assert resolve_credentials(trip.author, trip) is None

    def test_own_empty_key_does_not_borrow_when_author(self):
        creds = AICredentialsFactory(api_key_encrypted="")
        trip = TripFactory(author=creds.user)
        assert resolve_credentials(creds.user, trip) is None


class TestShouldShowSharedKeyNotice:
    def test_hidden_for_author(self):
        author = AICredentialsFactory(share_with_collaborators=True)
        trip = TripFactory(author=author.user)
        assert should_show_shared_key_notice(author.user, trip) is False

    def test_shown_for_collaborator_when_author_shares(self):
        author = AICredentialsFactory(share_with_collaborators=True)
        trip = TripFactory(author=author.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)
        assert should_show_shared_key_notice(collaborator, trip) is True

    def test_hidden_when_author_not_sharing(self):
        author = AICredentialsFactory(share_with_collaborators=False)
        trip = TripFactory(author=author.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)
        assert should_show_shared_key_notice(collaborator, trip) is False

    def test_hidden_when_shared_key_empty(self):
        author = AICredentialsFactory(
            share_with_collaborators=True, api_key_encrypted=""
        )
        trip = TripFactory(author=author.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)
        assert should_show_shared_key_notice(collaborator, trip) is False

    def test_hidden_after_dismissal(self):
        author = AICredentialsFactory(share_with_collaborators=True)
        trip = TripFactory(author=author.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)
        SharedKeyNoticeDismissalFactory(user=collaborator, trip=trip)
        assert should_show_shared_key_notice(collaborator, trip) is False


class TestGenerateSuggestions:
    def _provider_returning(self, suggestions):
        provider = MagicMock()
        provider.generate.return_value = suggestions
        return provider

    def test_raises_without_credentials(self):
        user = TripFactory().author
        trip = TripFactory(author=user)
        with pytest.raises(AISuggestionError):
            generate_suggestions(user, trip)

    def test_raises_with_empty_key(self):
        creds = AICredentialsFactory(api_key_encrypted="")
        trip = TripFactory(author=creds.user)
        with pytest.raises(AISuggestionError):
            generate_suggestions(creds.user, trip)

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_happy_path_grounds_with_location_bias(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        # bypass save() so the auto-geocoding does not overwrite coordinates
        TripFactory._meta.model.objects.filter(pk=trip.pk).update(
            destination_latitude=41.9, destination_longitude=12.5
        )
        trip.refresh_from_db()
        suggestion = Suggestion(kind="meal", name="Trattoria", type=3, city="Roma")
        mock_get_provider.return_value = self._provider_returning([suggestion])
        mock_client.return_value.search_text.return_value = [PLACE]

        results = generate_suggestions(creds.user, trip, language="it")

        assert len(results) == 1
        grounded = results[0]
        assert isinstance(grounded, GroundedSuggestion)
        assert grounded.place_id == "ChIJ_grounded"
        assert grounded.latitude == 41.9
        # location bias passed because the trip has coordinates
        _, kwargs = mock_client.return_value.search_text.call_args
        assert kwargs["location_bias"] == (41.9, 12.5, 50000)

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_search_radius_preference_sets_bias_radius(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        SuggestionPreferencesFactory(user=creds.user, search_radius="city")
        trip = TripFactory(author=creds.user)
        TripFactory._meta.model.objects.filter(pk=trip.pk).update(
            destination_latitude=41.9, destination_longitude=12.5
        )
        trip.refresh_from_db()
        suggestion = Suggestion(kind="meal", name="Trattoria", type=3, city="Roma")
        mock_get_provider.return_value = self._provider_returning([suggestion])
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip)

        _, kwargs = mock_client.return_value.search_text.call_args
        assert kwargs["location_bias"] == (41.9, 12.5, 8000)

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_day_trips_radius_is_clamped_for_google_bias(
        self, mock_get_provider, mock_client
    ):
        # Google Places rejects a locationBias circle radius above 50km, so the
        # bias must be clamped even though the acceptance radius is wider.
        creds = AICredentialsFactory(user=TripFactory().author)
        SuggestionPreferencesFactory(user=creds.user, search_radius="day_trips")
        trip = TripFactory(author=creds.user)
        TripFactory._meta.model.objects.filter(pk=trip.pk).update(
            destination_latitude=43.77, destination_longitude=11.25
        )
        trip.refresh_from_db()
        suggestion = Suggestion(kind="experience", name="Cinque Terre", type=1)
        mock_get_provider.return_value = self._provider_returning([suggestion])
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip)

        _, kwargs = mock_client.return_value.search_text.call_args
        assert kwargs["location_bias"] == (43.77, 11.25, 50000)

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_day_trips_radius_accepts_places_beyond_50km(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        SuggestionPreferencesFactory(user=creds.user, search_radius="day_trips")
        trip = TripFactory(author=creds.user)
        TripFactory._meta.model.objects.filter(pk=trip.pk).update(
            destination_latitude=43.77, destination_longitude=11.25
        )
        trip.refresh_from_db()
        suggestion = Suggestion(kind="experience", name="Bologna", type=1)
        mock_get_provider.return_value = self._provider_returning([suggestion])
        # ~100km north of Florence: rejected under "nearby" (50km) but within
        # the "day_trips" acceptance radius (150km).
        near_day_trip = PlaceResult(
            place_id="ChIJ_bologna",
            name="Bologna",
            address="Piazza Maggiore, Bologna BO",
            lat=44.67,
            lng=11.25,
        )
        mock_client.return_value.search_text.return_value = [near_day_trip]

        assert len(generate_suggestions(creds.user, trip)) == 1

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_without_coordinates_no_location_bias(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        TripFactory._meta.model.objects.filter(pk=trip.pk).update(
            destination_latitude=None, destination_longitude=None
        )
        trip.refresh_from_db()
        suggestion = Suggestion(kind="experience", name="Colosseo", type=1)
        mock_get_provider.return_value = self._provider_returning([suggestion])
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip)

        _, kwargs = mock_client.return_value.search_text.call_args
        assert kwargs["location_bias"] is None

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_ungrounded_suggestion_is_skipped(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        suggestion = Suggestion(kind="stay", name="Unknown Hotel")
        mock_get_provider.return_value = self._provider_returning([suggestion])
        mock_client.return_value.search_text.return_value = []

        assert generate_suggestions(creds.user, trip) == []

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_grounded_result_outside_radius_is_skipped(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        # bias centred on Florence, but Places returns a place in Palermo (~400km)
        TripFactory._meta.model.objects.filter(pk=trip.pk).update(
            destination_latitude=43.77, destination_longitude=11.25
        )
        trip.refresh_from_db()
        suggestion = Suggestion(kind="meal", name="La Raccolta", type=3)
        mock_get_provider.return_value = self._provider_returning([suggestion])
        far_place = PlaceResult(
            place_id="ChIJ_palermo",
            name="La Raccolta",
            address="Via Antonio de Saliba, 6, 90145 Palermo PA",
            lat=38.15,
            lng=13.33,
        )
        mock_client.return_value.search_text.return_value = [far_place]

        assert generate_suggestions(creds.user, trip) == []

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_places_error_skips_suggestion(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        suggestion = Suggestion(kind="experience", name="Park", type=2)
        mock_get_provider.return_value = self._provider_returning([suggestion])
        mock_client.return_value.search_text.side_effect = GooglePlacesError("boom")

        assert generate_suggestions(creds.user, trip) == []

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_second_call_uses_cache(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = self._provider_returning(
            [Suggestion(kind="experience", name="X", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip)
        generate_suggestions(creds.user, trip)

        assert provider.generate.call_count == 1

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_force_refresh_bypasses_cache(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = self._provider_returning(
            [Suggestion(kind="experience", name="X", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip)
        generate_suggestions(creds.user, trip, force_refresh=True)

        assert provider.generate.call_count == 2

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_caps_grounding_to_result_count(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        SuggestionPreferencesFactory(user=creds.user, result_count=2)
        trip = TripFactory(author=creds.user)
        provider = self._provider_returning(
            [Suggestion(kind="experience", name=f"X{i}", type=1) for i in range(5)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        results = generate_suggestions(creds.user, trip)

        # grounding stops as soon as result_count results are collected
        assert mock_client.return_value.search_text.call_count == 2
        assert len(results) == 2

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_overfetch_compensates_grounding_failures(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        SuggestionPreferencesFactory(user=creds.user, result_count=2)
        trip = TripFactory(author=creds.user)
        provider = self._provider_returning(
            [Suggestion(kind="experience", name=f"X{i}", type=1) for i in range(4)]
        )
        mock_get_provider.return_value = provider
        # first two candidates fail to ground, the next two succeed
        mock_client.return_value.search_text.side_effect = [[], [], [PLACE], [PLACE]]

        results = generate_suggestions(creds.user, trip)

        # we keep grounding past the failures until result_count is reached
        assert len(results) == 2

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_kinds_filter_discards_other_kinds(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = self._provider_returning(
            [
                Suggestion(kind="experience", name="Exp", type=1),
                Suggestion(kind="meal", name="Meal", type=3),
                Suggestion(kind="stay", name="Hotel"),
            ]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        results = generate_suggestions(creds.user, trip, overrides={"kinds": ["meal"]})

        # only the meal suggestion survives, so a single Places call is made
        assert mock_client.return_value.search_text.call_count == 1
        assert [r.suggestion.kind.value for r in results] == ["meal"]

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_stage_scopes_destination_and_bias(self, mock_get_provider, mock_client):
        from trips.models import Day

        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        Day.objects.filter(trip=trip).update(
            destination="Firenze",
            destination_latitude=43.77,
            destination_longitude=11.25,
        )
        provider = self._provider_returning(
            [Suggestion(kind="experience", name="Uffizi", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip, stage="Firenze")

        context = provider.generate.call_args.args[0]
        assert context.destination == "Firenze"
        assert context.latitude == 43.77
        _, kwargs = mock_client.return_value.search_text.call_args
        assert kwargs["location_bias"] == (43.77, 11.25, 50000)

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_stage_uses_separate_cache_key(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = self._provider_returning(
            [Suggestion(kind="experience", name="X", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip)
        generate_suggestions(creds.user, trip, stage="Firenze")

        # a stage-scoped request is cached under a different key
        assert provider.generate.call_count == 2


class TestBuildDayContext:
    def test_uses_day_destination_and_coordinates(self):
        trip = TripFactory(destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.destination_latitude = 43.77
        day.destination_longitude = 11.25
        day.save(
            update_fields=[
                "destination",
                "destination_latitude",
                "destination_longitude",
            ]
        )

        context = build_day_context(trip, day, language="it")

        assert context.destination == "Firenze"
        assert context.latitude == 43.77
        assert context.language == "it"

    def test_falls_back_to_trip_destination_and_coordinates(self):
        trip = TripFactory(destination="Roma")
        TripFactory._meta.model.objects.filter(pk=trip.pk).update(
            destination_latitude=41.9, destination_longitude=12.5
        )
        trip.refresh_from_db()
        day = trip.days.first()

        context = build_day_context(trip, day)

        assert context.destination == "Roma"
        assert context.latitude == 41.9

    def test_excludes_target_day_events_from_existing_places(self):
        trip = TripFactory(destination="Roma")
        days = list(trip.days.all())
        target, other = days[0], days[1]
        ExperienceFactory(trip=trip, day=target, name="Colosseo", city="Roma")
        ExperienceFactory(trip=trip, day=other, name="Duomo", city="Roma")

        context = build_day_context(trip, target)

        assert "Duomo (Roma)" in context.existing_places
        assert "Colosseo (Roma)" not in context.existing_places

    def test_exclude_names_drops_homonyms_from_avoid_list(self):
        # A same-named event on another day must not land in the "do NOT propose"
        # list when that name is fed as a must-include stop (the "add" strategy).
        trip = TripFactory(destination="Roma")
        days = list(trip.days.all())
        target, other = days[0], days[1]
        ExperienceFactory(trip=trip, day=target, name="Colosseo", city="Roma")
        ExperienceFactory(trip=trip, day=other, name="Colosseo", city="Roma")
        ExperienceFactory(trip=trip, day=other, name="Pantheon", city="Roma")

        context = build_day_context(trip, target, exclude_names=["Colosseo"])

        assert "Colosseo (Roma)" not in context.existing_places
        assert "Pantheon (Roma)" in context.existing_places

    def test_weather_scoped_to_the_day(self):
        trip = TripFactory(destination="Roma")
        day = trip.days.first()
        day.weather_data = {
            "weather_label": "Clear sky",
            "temperature_min": 15.0,
            "temperature_max": 28.0,
            "precipitation_sum": 0.0,
        }
        day.save(update_fields=["weather_data"])

        context = build_day_context(trip, day)

        assert len(context.weather) == 1
        assert "Clear sky" in context.weather[0]

    def test_no_weather_without_data(self):
        trip = TripFactory(destination="Roma")
        context = build_day_context(trip, trip.days.first())
        assert context.weather == []


class TestGenerateDayItinerary:
    def _provider_returning(self, stops):
        provider = MagicMock()
        provider.generate_day.return_value = DayItinerary(stops=stops)
        return provider

    def test_raises_without_credentials(self):
        trip = TripFactory()
        with pytest.raises(AISuggestionError):
            generate_day_itinerary(trip.author, trip, trip.days.first())

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_grounds_new_stops_with_duration(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        day = trip.days.first()
        stop = ItineraryStop(
            kind="meal", name="Trattoria", type=3, estimated_duration_minutes=90
        )
        mock_get_provider.return_value = self._provider_returning([stop])
        mock_client.return_value.search_text.return_value = [PLACE]

        results = generate_day_itinerary(creds.user, trip, day)

        assert len(results) == 1
        assert isinstance(results[0], GroundedStop)
        assert results[0].place_id == "ChIJ_grounded"
        assert results[0].stop.estimated_duration_minutes == 90
        assert results[0].existing_event_id is None

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_add_strategy_reuses_existing_event(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        day = trip.days.first()
        existing = ExperienceFactory(
            trip=trip, day=day, name="Colosseo", city="Roma", address="Piazza"
        )
        stops = [
            ItineraryStop(kind="experience", name="Colosseo", type=1),
            ItineraryStop(kind="meal", name="New Trattoria", type=3),
        ]
        provider = self._provider_returning(stops)
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        results = generate_day_itinerary(
            creds.user, trip, day, strategy=DAY_STRATEGY_ADD
        )

        # existing event fed to the prompt and reused without a Places call
        assert provider.generate_day.call_args.args[3] == ["Colosseo"]
        # the fed event is not also in the "do NOT propose" avoid-list
        context = provider.generate_day.call_args.args[0]
        assert "Colosseo (Roma)" not in context.existing_places
        assert results[0].existing_event_id == existing.pk
        assert results[0].address == "Piazza"
        assert results[1].existing_event_id is None
        assert mock_client.return_value.search_text.call_count == 1

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_unpair_strategy_ignores_existing_events(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day, name="Colosseo", city="Roma")
        provider = self._provider_returning(
            [ItineraryStop(kind="experience", name="Forum", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_day_itinerary(creds.user, trip, day, strategy=DAY_STRATEGY_UNPAIR)

        # no must-include stops are fed to the model for a clean day
        assert provider.generate_day.call_args.args[3] is None

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_delete_strategy_ignores_existing_events(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day, name="Colosseo", city="Roma")
        provider = self._provider_returning(
            [ItineraryStop(kind="experience", name="Forum", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_day_itinerary(creds.user, trip, day, strategy=DAY_STRATEGY_DELETE)

        assert provider.generate_day.call_args.args[3] is None

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_stays_are_dropped(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        stops = [
            ItineraryStop(kind="stay", name="Hotel"),
            ItineraryStop(kind="experience", name="Forum", type=1),
        ]
        mock_get_provider.return_value = self._provider_returning(stops)
        mock_client.return_value.search_text.return_value = [PLACE]

        results = generate_day_itinerary(creds.user, trip, trip.days.first())

        assert [r.stop.name for r in results] == ["Forum"]

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_ungrounded_stop_is_dropped(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        stops = [
            ItineraryStop(kind="experience", name="Nowhere", type=1),
            ItineraryStop(kind="meal", name="Trattoria", type=3),
        ]
        mock_get_provider.return_value = self._provider_returning(stops)
        # first stop fails to ground, second succeeds
        mock_client.return_value.search_text.side_effect = [[], [PLACE]]

        results = generate_day_itinerary(creds.user, trip, trip.days.first())

        assert [r.stop.name for r in results] == ["Trattoria"]

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_second_call_uses_cache(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        day = trip.days.first()
        provider = self._provider_returning(
            [ItineraryStop(kind="experience", name="Forum", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_day_itinerary(creds.user, trip, day)
        generate_day_itinerary(creds.user, trip, day)

        assert provider.generate_day.call_count == 1

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_force_refresh_bypasses_cache(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        day = trip.days.first()
        provider = self._provider_returning(
            [ItineraryStop(kind="experience", name="Forum", type=1)]
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_day_itinerary(creds.user, trip, day)
        generate_day_itinerary(creds.user, trip, day, force_refresh=True)

        assert provider.generate_day.call_count == 2

    @override_settings(
        AI_GENERATION_DAILY_CAP_PER_USER=0, AI_GENERATION_DAILY_CAP_PER_TRIP=100
    )
    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_quota_blocks_before_provider(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = self._provider_returning(
            [ItineraryStop(kind="experience", name="Forum", type=1)]
        )
        mock_get_provider.return_value = provider

        with pytest.raises(AISuggestionError) as exc:
            generate_day_itinerary(creds.user, trip, trip.days.first())

        assert exc.value.kind == AISuggestionError.RATE_LIMIT
        provider.generate_day.assert_not_called()


class TestGetCachedSuggestions:
    def test_returns_none_when_nothing_cached(self):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        assert get_cached_suggestions(creds.user, trip) is None

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_returns_cached_without_calling_provider(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = MagicMock()
        provider.generate.return_value = [
            Suggestion(kind="experience", name="X", type=1)
        ]
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_suggestions(creds.user, trip)
        cached = get_cached_suggestions(creds.user, trip)

        assert cached is not None
        assert len(cached) == 1
        # peeking the cache does not spend quota
        assert provider.generate.call_count == 1

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_returns_last_results_regardless_of_prefs(
        self, mock_get_provider, mock_client
    ):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = MagicMock()
        provider.generate.return_value = [
            Suggestion(kind="meal", name="Trattoria", type=3)
        ]
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        # generated with per-request kinds/notes overrides
        generate_suggestions(
            creds.user,
            trip,
            overrides={"kinds": ["meal"], "notes": "with kids"},
        )

        # reopening the panel/modal peeks without knowing those overrides
        cached = get_cached_suggestions(creds.user, trip)
        assert cached is not None
        assert len(cached) == 1


class TestCacheTTLs:
    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_last_pointer_outlives_prefs_cache(self, mock_get_provider, mock_client):
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)
        provider = MagicMock()
        provider.generate.return_value = [
            Suggestion(kind="experience", name="X", type=1)
        ]
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        last_key = _last_key(creds.user, trip)
        with patch("suggestions.services.cache.set", wraps=cache.set) as spy:
            generate_suggestions(creds.user, trip)

        ttls_by_key = {c.args[0]: c.args[2] for c in spy.call_args_list}
        # the last-results pointer lives longer (48h) than the prefs cache (24h)
        assert ttls_by_key[last_key] == _LAST_TTL == 48 * 3600
        prefs_ttls = [t for k, t in ttls_by_key.items() if k != last_key]
        assert prefs_ttls and all(t == _CACHE_TTL == 24 * 3600 for t in prefs_ttls)


class TestGenerationQuota:
    """Daily caps prevent shared-key abuse: a real provider call (cache miss or
    Regenerate) is counted per executing user and per trip; cache hits are free.
    """

    def _setup(self, mock_get_provider, mock_client):
        provider = MagicMock()
        provider.generate.return_value = [
            Suggestion(kind="experience", name="X", type=1)
        ]
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]
        return provider

    @override_settings(
        AI_GENERATION_DAILY_CAP_PER_USER=1, AI_GENERATION_DAILY_CAP_PER_TRIP=100
    )
    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_per_user_cap_blocks_further_generations(
        self, mock_get_provider, mock_client
    ):
        provider = self._setup(mock_get_provider, mock_client)
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)

        generate_suggestions(creds.user, trip)  # consumes the single allowance
        with pytest.raises(AISuggestionError) as exc:
            generate_suggestions(creds.user, trip, force_refresh=True)

        assert exc.value.kind == AISuggestionError.RATE_LIMIT
        # blocked before spending the provider quota
        assert provider.generate.call_count == 1

    @override_settings(
        AI_GENERATION_DAILY_CAP_PER_USER=100, AI_GENERATION_DAILY_CAP_PER_TRIP=1
    )
    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_per_trip_cap_is_shared_across_collaborators(
        self, mock_get_provider, mock_client
    ):
        self._setup(mock_get_provider, mock_client)
        author_creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=author_creds.user)
        collaborator = UserFactory()
        AICredentialsFactory(user=collaborator)
        _add_collaborator(trip, collaborator)

        generate_suggestions(author_creds.user, trip)  # trip allowance spent
        with pytest.raises(AISuggestionError) as exc:
            generate_suggestions(collaborator, trip, force_refresh=True)

        assert exc.value.kind == AISuggestionError.RATE_LIMIT

    @override_settings(
        AI_GENERATION_DAILY_CAP_PER_USER=1, AI_GENERATION_DAILY_CAP_PER_TRIP=100
    )
    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_cache_hits_do_not_consume_quota(self, mock_get_provider, mock_client):
        provider = self._setup(mock_get_provider, mock_client)
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)

        # one real call followed by two cache hits, all under a cap of 1
        generate_suggestions(creds.user, trip)
        generate_suggestions(creds.user, trip)
        generate_suggestions(creds.user, trip)

        assert provider.generate.call_count == 1

    @override_settings(
        AI_GENERATION_DAILY_CAP_PER_USER=1, AI_GENERATION_DAILY_CAP_PER_TRIP=100
    )
    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_shared_key_counts_against_executing_collaborator(
        self, mock_get_provider, mock_client
    ):
        provider = self._setup(mock_get_provider, mock_client)
        author_creds = AICredentialsFactory(
            share_with_collaborators=True, user=TripFactory().author
        )
        trip = TripFactory(author=author_creds.user)
        collaborator = UserFactory()
        _add_collaborator(trip, collaborator)

        # collaborator generates on the author's shared key, hitting their own cap
        generate_suggestions(collaborator, trip)
        with pytest.raises(AISuggestionError) as exc:
            generate_suggestions(collaborator, trip, force_refresh=True)
        assert exc.value.kind == AISuggestionError.RATE_LIMIT

        # the author's own per-user quota is untouched, so they can still generate
        generate_suggestions(author_creds.user, TripFactory(author=author_creds.user))
        assert provider.generate.call_count == 2

    @override_settings(
        AI_GENERATION_DAILY_CAP_PER_USER=0, AI_GENERATION_DAILY_CAP_PER_TRIP=100
    )
    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_zero_cap_blocks_before_calling_provider(
        self, mock_get_provider, mock_client
    ):
        provider = self._setup(mock_get_provider, mock_client)
        creds = AICredentialsFactory(user=TripFactory().author)
        trip = TripFactory(author=creds.user)

        with pytest.raises(AISuggestionError) as exc:
            generate_suggestions(creds.user, trip)

        assert exc.value.kind == AISuggestionError.RATE_LIMIT
        provider.generate.assert_not_called()


class TestTripStages:
    def test_groups_consecutive_days_and_averages_coords(self):
        trip = TripFactory(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 5), destination="Roma"
        )
        days = list(trip.days.order_by("number"))
        apply_stage(
            trip, [d.pk for d in days[3:]], "Firenze", latitude=43.77, longitude=11.25
        )

        stages = _trip_stages(trip)

        assert [s.destination for s in stages] == ["Roma", "Firenze"]
        assert stages[0].start_date == date(2026, 6, 1)
        assert stages[0].end_date == date(2026, 6, 3)
        assert stages[1].start_date == date(2026, 6, 4)
        assert stages[1].end_date == date(2026, 6, 5)
        assert stages[1].latitude == 43.77
        assert stages[1].longitude == 11.25

    def test_blank_day_destination_falls_back_to_trip(self):
        trip = TripFactory(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 2), destination="Roma"
        )
        day = trip.days.first()
        day.destination = ""
        day.save(update_fields=["destination"])

        stages = _trip_stages(trip)

        assert stages[0].destination == "Roma"


class TestGenerateTripItinerary:
    def _provider_returning(self, itinerary):
        provider = MagicMock()
        provider.generate_trip.return_value = itinerary
        return provider

    def _trip_with_creds(self, **kwargs):
        creds = AICredentialsFactory(user=TripFactory().author)
        kwargs.setdefault("start_date", date(2026, 6, 1))
        kwargs.setdefault("end_date", date(2026, 6, 2))
        kwargs.setdefault("destination", "Roma")
        trip = TripFactory(author=creds.user, **kwargs)
        return creds, trip

    def test_raises_without_credentials(self):
        trip = TripFactory()
        with pytest.raises(AISuggestionError):
            generate_trip_itinerary(trip.author, trip)

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_grounds_each_day_and_drops_stays(self, mock_get_provider, mock_client):
        creds, trip = self._trip_with_creds()
        days = list(trip.days.order_by("number"))
        itinerary = TripItinerary(
            days=[
                DayPlan(
                    date=days[0].date,
                    destination="Roma",
                    stops=[
                        ItineraryStop(
                            kind="meal",
                            name="Trattoria",
                            type=3,
                            estimated_duration_minutes=90,
                        )
                    ],
                ),
                DayPlan(
                    date=days[1].date,
                    destination="Roma",
                    stops=[ItineraryStop(kind="stay", name="Hotel")],
                ),
            ]
        )
        mock_get_provider.return_value = self._provider_returning(itinerary)
        mock_client.return_value.search_text.return_value = [PLACE]

        result = generate_trip_itinerary(creds.user, trip)

        assert len(result) == 2
        assert isinstance(result[0], GroundedDay)
        assert result[0].date == days[0].date
        assert result[0].stops[0].place_id == "ChIJ_grounded"
        assert result[0].stops[0].stop.estimated_duration_minutes == 90
        # stays are dropped during grounding
        assert result[1].stops == []

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_blank_destination_uses_trip_coords(self, mock_get_provider, mock_client):
        creds, trip = self._trip_with_creds()
        day = trip.days.first()
        itinerary = TripItinerary(
            days=[
                DayPlan(
                    date=day.date,
                    destination="",
                    stops=[ItineraryStop(kind="experience", name="Forum", type=1)],
                )
            ]
        )
        mock_get_provider.return_value = self._provider_returning(itinerary)
        mock_client.return_value.search_text.return_value = [PLACE]

        result = generate_trip_itinerary(creds.user, trip)

        assert result[0].destination == ""
        assert result[0].stops[0].place_id == "ChIJ_grounded"

    @patch("suggestions.services.GooglePlacesClient")
    @patch("suggestions.services.get_provider")
    def test_caches_and_force_refresh(self, mock_get_provider, mock_client):
        creds, trip = self._trip_with_creds()
        day = trip.days.first()
        provider = self._provider_returning(
            TripItinerary(
                days=[
                    DayPlan(
                        date=day.date,
                        destination="Roma",
                        stops=[ItineraryStop(kind="meal", name="X", type=3)],
                    )
                ]
            )
        )
        mock_get_provider.return_value = provider
        mock_client.return_value.search_text.return_value = [PLACE]

        generate_trip_itinerary(creds.user, trip)
        generate_trip_itinerary(creds.user, trip)
        assert provider.generate_trip.call_count == 1

        generate_trip_itinerary(creds.user, trip, force_refresh=True)
        assert provider.generate_trip.call_count == 2
