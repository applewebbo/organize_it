from datetime import date

import pytest
from pydantic import ValidationError

from suggestions.schemas import (
    NOTES_MAX_LENGTH,
    DayItinerary,
    DayPlan,
    ItineraryStop,
    Suggestion,
    SuggestionKind,
    SuggestionPrefs,
    TripItinerary,
    TripStage,
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


class TestDayPlanSchema:
    def test_holds_date_destination_and_stops(self):
        plan = DayPlan(
            date=date(2026, 6, 2),
            destination="Firenze",
            stops=[ItineraryStop(kind="experience", name="Uffizi")],
        )
        assert plan.date == date(2026, 6, 2)
        assert plan.destination == "Firenze"
        assert [s.name for s in plan.stops] == ["Uffizi"]

    def test_defaults(self):
        plan = DayPlan(date=date(2026, 6, 2))
        assert plan.destination == ""
        assert plan.stops == []

    def test_date_is_required(self):
        with pytest.raises(ValidationError):
            DayPlan(destination="Roma")


class TestTripItinerarySchema:
    def test_holds_ordered_days(self):
        itinerary = TripItinerary(
            days=[
                DayPlan(date=date(2026, 6, 1), destination="Roma"),
                DayPlan(date=date(2026, 6, 2), destination="Firenze"),
            ]
        )
        assert [d.destination for d in itinerary.days] == ["Roma", "Firenze"]

    def test_defaults_to_empty(self):
        assert TripItinerary().days == []


class TestTripStageSchema:
    def test_holds_destination_dates_and_coords(self):
        stage = TripStage(
            destination="Roma",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 3),
            latitude=41.9,
            longitude=12.5,
        )
        assert stage.destination == "Roma"
        assert stage.start_date == date(2026, 6, 1)
        assert stage.latitude == 41.9

    def test_coords_default_to_none(self):
        stage = TripStage(
            destination="Roma",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 3),
        )
        assert stage.latitude is None
        assert stage.longitude is None


class TestSuggestionPrefsNotes:
    def test_notes_within_cap_are_kept(self):
        prefs = SuggestionPrefs(notes="with kids")
        assert prefs.notes == "with kids"

    def test_notes_are_truncated_to_the_cap(self):
        prefs = SuggestionPrefs(notes="x" * (NOTES_MAX_LENGTH + 50))
        assert len(prefs.notes) == NOTES_MAX_LENGTH
