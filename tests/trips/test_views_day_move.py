from datetime import date, timedelta

import pytest

from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.models import Event

pytestmark = pytest.mark.django_db


def _make_trip_with_two_days(user):
    return TripFactory(
        author=user,
        destination="Roma",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
    )


def _create_event(trip, day, name="Test Event"):
    return Event.objects.create(
        trip=trip,
        day=day,
        name=name,
        address="Via Roma 1",
        category=Event.Category.EXPERIENCE,
        order=0,
    )


class TestMoveEventToDayView(TestCase):
    def test_owner_can_move_event_to_another_day(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        days = list(trip.days.order_by("number"))
        event = _create_event(trip, days[0])
        with self.login(user):
            response = self.post(
                "trips:move-event-to-day",
                event_id=event.pk,
                day_id=days[1].pk,
            )
        self.response_204(response)
        event.refresh_from_db()
        assert event.day == days[1]

    def test_move_triggers_both_day_modified_events(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        days = list(trip.days.order_by("number"))
        event = _create_event(trip, days[0])
        with self.login(user):
            response = self.post(
                "trips:move-event-to-day",
                event_id=event.pk,
                day_id=days[1].pk,
            )
        trigger = response.headers.get("HX-Trigger", "")
        assert str(days[0].pk) in trigger
        assert str(days[1].pk) in trigger

    def test_move_to_same_day_returns_204_no_change(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        day = trip.days.first()
        event = _create_event(trip, day)
        with self.login(user):
            response = self.post(
                "trips:move-event-to-day",
                event_id=event.pk,
                day_id=day.pk,
            )
        self.response_204(response)
        event.refresh_from_db()
        assert event.day == day

    def test_other_user_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = _make_trip_with_two_days(owner)
        days = list(trip.days.order_by("number"))
        event = _create_event(trip, days[0])
        with self.login(other):
            response = self.post(
                "trips:move-event-to-day",
                event_id=event.pk,
                day_id=days[1].pk,
            )
        self.response_404(response)
        event.refresh_from_db()
        assert event.day == days[0]

    def test_unauthenticated_redirects(self):
        trip = TripFactory()
        days = list(trip.days.order_by("number"))
        event = _create_event(trip, days[0])
        response = self.post(
            "trips:move-event-to-day",
            event_id=event.pk,
            day_id=days[1].pk,
        )
        self.response_302(response)

    def test_unpaired_event_gets_404(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        event = Event.objects.create(
            trip=trip,
            day=None,
            name="Unpaired",
            address="Via Roma",
            category=Event.Category.EXPERIENCE,
        )
        day = trip.days.first()
        with self.login(user):
            response = self.post(
                "trips:move-event-to-day",
                event_id=event.pk,
                day_id=day.pk,
            )
        self.response_404(response)

    def test_move_appends_event_at_end_of_target_day(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        days = list(trip.days.order_by("number"))
        existing = _create_event(trip, days[1], name="Existing")
        existing.order = 0
        existing.save()
        event = _create_event(trip, days[0], name="Moving")
        with self.login(user):
            self.post(
                "trips:move-event-to-day",
                event_id=event.pk,
                day_id=days[1].pk,
            )
        event.refresh_from_db()
        assert event.order >= 1

    def test_get_not_allowed(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        days = list(trip.days.order_by("number"))
        event = _create_event(trip, days[0])
        with self.login(user):
            response = self.get(
                "trips:move-event-to-day",
                event_id=event.pk,
                day_id=days[1].pk,
            )
        self.response_405(response)


class TestMoveEventDayModalView(TestCase):
    def test_owner_gets_day_list(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        days = list(trip.days.order_by("number"))
        event = _create_event(trip, days[0])
        with self.login(user):
            response = self.get(
                "trips:move-event-day-modal",
                event_id=event.pk,
            )
        self.response_200(response)
        assert response.context["event"] == event
        # days list excludes the current day
        assert days[0] not in response.context["days"]
        assert days[1] in response.context["days"]

    def test_other_user_gets_404(self):
        owner = self.make_user("owner@example.com")
        other = self.make_user("other@example.com")
        trip = _make_trip_with_two_days(owner)
        day = trip.days.first()
        event = _create_event(trip, day)
        with self.login(other):
            response = self.get(
                "trips:move-event-day-modal",
                event_id=event.pk,
            )
        self.response_404(response)

    def test_unauthenticated_redirects(self):
        trip = TripFactory()
        day = trip.days.first()
        event = _create_event(trip, day)
        response = self.get("trips:move-event-day-modal", event_id=event.pk)
        self.response_302(response)

    def test_unpaired_event_gets_404(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        event = Event.objects.create(
            trip=trip,
            day=None,
            name="Unpaired",
            address="Via Roma",
            category=Event.Category.EXPERIENCE,
        )
        with self.login(user):
            response = self.get(
                "trips:move-event-day-modal",
                event_id=event.pk,
            )
        self.response_404(response)

    def test_post_not_allowed(self):
        user = self.make_user("owner@example.com")
        trip = _make_trip_with_two_days(user)
        day = trip.days.first()
        event = _create_event(trip, day)
        with self.login(user):
            response = self.post("trips:move-event-day-modal", event_id=event.pk)
        self.response_405(response)
