from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from suggestions.ai.base import AISuggestionError
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext
from suggestions.services import (
    _CACHE_TTL,
    _LAST_TTL,
    GroundedSuggestion,
    _last_key,
    build_trip_context,
    generate_suggestions,
    get_cached_suggestions,
    merge_preferences,
)
from tests.suggestions.factories import (
    AICredentialsFactory,
    SuggestionPreferencesFactory,
)
from tests.trips.factories import ExperienceFactory, StayFactory, TripFactory
from trips.services import GooglePlacesError, PlaceResult

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
