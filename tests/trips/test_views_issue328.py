import pytest

from tests.test import TestCase
from tests.trips.factories import ExperienceFactory, MealFactory, TripFactory
from trips.utils import get_trip_stages, group_unpaired_events_by_stage

pytestmark = pytest.mark.django_db


def make_unpaired_experience(trip, city=""):
    """Create an Experience not assigned to any day."""
    event = ExperienceFactory(trip=trip)
    event.day = None
    event.city = city
    event.save()
    return event


def make_unpaired_meal(trip, city=""):
    """Create a Meal not assigned to any day."""
    event = MealFactory(trip=trip)
    event.day = None
    event.city = city
    event.save()
    return event


class TestEventUnpairSetsCity(TestCase):
    """event_unpair auto-sets event.city from day.destination."""

    def test_unpair_sets_city_from_day_destination(self):
        user = self.make_user("u1")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        event = ExperienceFactory(trip=trip, day=day)

        with self.login(user):
            response = self.client.put(f"/events/{event.pk}/unpair")

        self.response_204(response)
        event.refresh_from_db()
        assert event.day is None
        assert event.city == "Firenze"

    def test_unpair_falls_back_to_trip_destination_when_day_destination_blank(self):
        user = self.make_user("u2")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = ""
        day.save()
        event = ExperienceFactory(trip=trip, day=day)

        with self.login(user):
            response = self.client.put(f"/events/{event.pk}/unpair")

        self.response_204(response)
        event.refresh_from_db()
        assert event.city == "Roma"


class TestAddEventToTripStagesContext(TestCase):
    """add_experience_to_trip / add_meal_to_trip pass stages to context."""

    def test_experience_context_has_stages(self):
        user = self.make_user("u3")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.client.get(f"/trips/{trip.pk}/experiences/create")

        assert "stages" in response.context

    def test_meal_context_has_stages(self):
        user = self.make_user("u4")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.client.get(f"/trips/{trip.pk}/meals/create")

        assert "stages" in response.context

    def test_single_stage_trip_has_only_main_stage(self):
        user = self.make_user("u5")
        trip = TripFactory(author=user, destination="Roma")

        with self.login(user):
            response = self.client.get(f"/trips/{trip.pk}/experiences/create")

        stages = response.context["stages"]
        assert all(s["is_main"] for s in stages)

    def test_multi_stage_trip_includes_custom_stage(self):
        user = self.make_user("u6")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()

        with self.login(user):
            response = self.client.get(f"/trips/{trip.pk}/experiences/create")

        stages = response.context["stages"]
        destinations = [s["destination"] for s in stages]
        assert "Firenze" in destinations
        assert len(stages) > 1


class TestGroupUnpairedEventsByStage(TestCase):
    """group_unpaired_events_by_stage utility function."""

    def test_events_grouped_by_matching_stage(self):
        user = self.make_user("u7")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        e1 = make_unpaired_experience(trip, city="Firenze")
        e2 = make_unpaired_experience(trip, city="Roma")

        stages = get_trip_stages(trip)
        groups = group_unpaired_events_by_stage(stages, [e1, e2])

        destinations = {g["destination"] for g in groups}
        assert "Firenze" in destinations
        assert "Roma" in destinations

    def test_events_without_matching_city_go_to_no_stage_group(self):
        user = self.make_user("u8")
        trip = TripFactory(author=user, destination="Roma")
        event = make_unpaired_experience(trip, city="")

        stages = get_trip_stages(trip)
        groups = group_unpaired_events_by_stage(stages, [event])

        no_stage = [g for g in groups if g["destination"] is None]
        assert len(no_stage) == 1
        assert event in no_stage[0]["events"]

    def test_empty_stage_groups_not_included(self):
        user = self.make_user("u9")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        event = make_unpaired_experience(trip, city="Roma")

        stages = get_trip_stages(trip)
        groups = group_unpaired_events_by_stage(stages, [event])

        destinations = [g["destination"] for g in groups]
        assert "Firenze" not in destinations


class TestEventPairChoiceFiltersByStage(TestCase):
    """event_pair_choice filters days by event.city stage."""

    def test_all_days_shown_when_event_has_no_city(self):
        user = self.make_user("u10")
        trip = TripFactory(author=user, destination="Roma")
        day = trip.days.first()
        day.destination = "Firenze"
        day.save()
        event = make_unpaired_experience(trip, city="")

        with self.login(user):
            response = self.client.get(f"/events/{event.pk}/pair-choice")

        days = list(response.context["days"])
        assert len(days) == trip.days.count()

    def test_only_custom_stage_days_shown_when_event_city_matches(self):
        user = self.make_user("u11")
        trip = TripFactory(author=user, destination="Roma")
        days = list(trip.days.order_by("number"))
        days[0].destination = "Firenze"
        days[0].save()
        event = make_unpaired_experience(trip, city="Firenze")

        with self.login(user):
            response = self.client.get(f"/events/{event.pk}/pair-choice")

        returned_days = list(response.context["days"])
        assert all(d.destination == "Firenze" for d in returned_days)
        assert len(returned_days) == 1

    def test_main_stage_days_include_blank_destination_days(self):
        user = self.make_user("u12")
        trip = TripFactory(author=user, destination="Roma")
        days = list(trip.days.order_by("number"))
        days[0].destination = ""
        days[0].save()
        if len(days) > 1:
            days[1].destination = "Roma"
            days[1].save()
        event = make_unpaired_experience(trip, city="Roma")

        with self.login(user):
            response = self.client.get(f"/events/{event.pk}/pair-choice")

        returned_pks = {d.pk for d in response.context["days"]}
        assert days[0].pk in returned_pks

    def test_meal_event_pair_choice_filters_correctly(self):
        user = self.make_user("u13")
        trip = TripFactory(author=user, destination="Roma")
        days = list(trip.days.order_by("number"))
        days[0].destination = "Napoli"
        days[0].save()
        meal = make_unpaired_meal(trip, city="Napoli")

        with self.login(user):
            response = self.client.get(f"/events/{meal.pk}/pair-choice")

        returned_days = list(response.context["days"])
        assert all(d.destination == "Napoli" for d in returned_days)
