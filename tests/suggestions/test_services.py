from unittest.mock import MagicMock, patch

import pytest

from suggestions.ai.base import AISuggestionError
from suggestions.schemas import Suggestion, SuggestionPrefs, TripContext
from suggestions.services import (
    GroundedSuggestion,
    build_trip_context,
    generate_suggestions,
    get_cached_suggestions,
    merge_preferences,
)
from tests.suggestions.factories import (
    AICredentialsFactory,
    SuggestionPreferencesFactory,
)
from tests.trips.factories import TripFactory
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


class TestMergePreferences:
    def test_defaults_when_nothing_provided(self):
        prefs = merge_preferences(None, None)
        assert prefs == SuggestionPrefs()

    def test_uses_user_defaults(self):
        defaults = SuggestionPreferencesFactory.build(
            favored_experience_types=[1, 2],
            dietary="vegan",
            pace="relaxed",
            budget="high",
            notes="no crowds",
        )
        prefs = merge_preferences(defaults, None)
        assert prefs.dietary == "vegan"
        assert prefs.favored_experience_types == [1, 2]
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

        # only result_count suggestions are grounded (one Places call each)
        assert mock_client.return_value.search_text.call_count == 2
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
