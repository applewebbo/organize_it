import pytest
from pydantic import ValidationError

from suggestions.schemas import (
    DayItinerary,
    ItineraryStop,
    Suggestion,
    SuggestionKind,
)


class TestSuggestionSchema:
    def test_valid_experience(self):
        s = Suggestion(kind="experience", name="Louvre", type=1)
        assert s.kind is SuggestionKind.EXPERIENCE
        assert s.type == 1

    def test_invalid_experience_type_coerced_to_none(self):
        s = Suggestion(kind="experience", name="X", type=99)
        assert s.type is None

    def test_experience_without_type_stays_none(self):
        s = Suggestion(kind="experience", name="X")
        assert s.type is None

    def test_valid_meal(self):
        s = Suggestion(kind="meal", name="Trattoria", type=3)
        assert s.type == 3

    def test_invalid_meal_type_coerced_to_none(self):
        s = Suggestion(kind="meal", name="X", type=99)
        assert s.type is None

    def test_stay_type_is_forced_to_none(self):
        s = Suggestion(kind="stay", name="Hotel", type=4)
        assert s.type is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            Suggestion(kind="stay", name="")


class TestItineraryStopSchema:
    def test_valid_experience_stop_with_duration(self):
        stop = ItineraryStop(
            kind="experience", name="Louvre", type=1, estimated_duration_minutes=120
        )
        assert stop.kind is SuggestionKind.EXPERIENCE
        assert stop.type == 1
        assert stop.estimated_duration_minutes == 120

    def test_invalid_type_coerced_to_none(self):
        stop = ItineraryStop(kind="experience", name="X", type=99)
        assert stop.type is None

    def test_meal_stop_keeps_valid_type(self):
        stop = ItineraryStop(kind="meal", name="Trattoria", type=3)
        assert stop.type == 3

    def test_duration_defaults_to_none(self):
        stop = ItineraryStop(kind="meal", name="Trattoria")
        assert stop.estimated_duration_minutes is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ItineraryStop(kind="experience", name="")


class TestDayItinerarySchema:
    def test_holds_ordered_stops(self):
        itinerary = DayItinerary(
            stops=[
                ItineraryStop(kind="meal", name="Breakfast"),
                ItineraryStop(kind="experience", name="Museum"),
            ]
        )
        assert [s.name for s in itinerary.stops] == ["Breakfast", "Museum"]

    def test_defaults_to_empty(self):
        assert DayItinerary().stops == []
