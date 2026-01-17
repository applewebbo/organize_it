import datetime

import pytest
from django.contrib.messages import get_messages
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    MealFactory,
    TripFactory,
)

pytestmark = pytest.mark.django_db


class TestEventOverlapCheck(TestCase):
    def test_overlap_warning(self):
        """Test that overlap warning is shown when times overlap"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Create existing event
        EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(12, 0)
        )

        # Check overlap
        with self.login(user):
            response = self.get(
                "trips:check-event-overlap",
                day_id=day.pk,
                data={"start_time": "11:00", "end_time": "13:00"},
            )

        self.response_200(response)
        assertTemplateUsed(response, "trips/overlap-warning.html")
        assert "This event overlaps with another event" in str(response.content)

    def test_no_overlap_warning(self):
        """Test that no warning is shown when times don't overlap"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Create existing event
        EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(12, 0)
        )

        # Check non-overlapping time
        with self.login(user):
            response = self.get(
                "trips:check-event-overlap",
                day_id=day.pk,
                data={"start_time": "13:00", "end_time": "14:00"},
            )

        self.response_200(response)
        assert response.content.decode() == ""

    def test_missing_time_parameters(self):
        """Test that empty response is returned when time parameters are missing"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        test_cases = [
            {},  # No parameters
            {"start_time": "10:00"},  # Only start_time
            {"end_time": "11:00"},  # Only end_time
            {"start_time": "", "end_time": ""},  # Empty parameters
        ]

        with self.login(user):
            for params in test_cases:
                response = self.get(
                    "trips:check-event-overlap", day_id=day.pk, data=params
                )
                self.response_200(response)
                assert response.content.decode() == ""


class TestEventSwap(TestCase):
    """Test cases for event swapping functionality"""

    def test_event_swap_success(self):
        """Test successful swapping of two events times"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        event1 = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )
        event2 = EventFactory(
            day=day, start_time=datetime.time(14, 0), end_time=datetime.time(15, 0)
        )

        with self.login(user):
            response = self.post("trips:event-swap", pk1=event1.pk, pk2=event2.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Events swapped successfully"

        # Verify events were swapped
        event1.refresh_from_db()
        event2.refresh_from_db()
        assert event1.start_time == datetime.time(14, 0)
        assert event1.end_time == datetime.time(15, 0)
        assert event2.start_time == datetime.time(10, 0)
        assert event2.end_time == datetime.time(11, 0)

    def test_event_swap_different_days(self):
        """Test swapping events from different days"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day1 = trip.days.first()
        day2 = trip.days.last()
        event1 = EventFactory(day=day1)
        event2 = EventFactory(day=day2)

        with self.login(user):
            response = self.post("trips:event-swap", pk1=event1.pk, pk2=event2.pk)

        self.response_400(response)


class TestEventSwapModal(TestCase):
    """Test cases for event swap modal view"""

    def test_get_swap_modal(self):
        """Test successful retrieval of swap modal"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        selected_event = EventFactory(day=day)
        swappable_event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-swap-modal", pk=selected_event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-swap.html")
        assert response.context["selected_event"] == selected_event
        assert swappable_event in response.context["swappable_events"]

    def test_get_swap_modal_no_other_events(self):
        """Test swap modal when no other events exist"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-swap-modal", pk=event.pk)

        self.response_200(response)
        assert len(response.context["swappable_events"]) == 0


class TestEventDetail(TestCase):
    """Test cases for event detail view"""

    def test_get_experience_detail(self):
        """Test successful retrieval of experience event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        experience = ExperienceFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=experience.pk)

        self.response_200(response)
        assert response.context["event"] == experience

    def test_get_meal_detail(self):
        """Test successful retrieval of meal event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        meal = MealFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=meal.pk)

        self.response_200(response)
        assert response.context["event"] == meal

    def test_get_detail_unauthorized(self):
        """Test unauthorized access to event detail"""
        other_user = self.make_user("other")
        trip = TripFactory(author=other_user)
        day = trip.days.first()
        event = EventFactory(day=day)

        user = self.make_user("user")
        with self.login(user):
            response = self.get("trips:event-detail", pk=event.pk)

        self.response_404(response)

    def test_get_detail_invalid_category(self):
        """Test event detail with invalid category"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, category=99)  # Invalid category

        with self.login(user):
            response = self.get("trips:event-detail", pk=event.pk)

        self.response_404(response)


class TestEventChangeTimes(TestCase):
    """Test cases for event time changes"""

    def test_get_change_times(self):
        """Test successful retrieval of change times form"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )

        with self.login(user):
            response = self.get("trips:event-change-times", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-change-times.html")
        assert "form" in response.context
        assert response.context["event"] == event

    def test_post_change_times_success(self):
        """Test successful time update"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )

        data = {
            "start_time": "14:00",
            "end_time": "15:00",
        }

        with self.login(user):
            response = self.post("trips:event-change-times", pk=event.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event times updated successfully"

        event.refresh_from_db()
        assert event.start_time == datetime.time(14, 0)
        assert event.end_time == datetime.time(15, 0)

    def test_post_change_times_invalid(self):
        """Test time update with invalid data"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(
            day=day, start_time=datetime.time(10, 0), end_time=datetime.time(11, 0)
        )

        data = {
            "start_time": "",  # Invalid: required field
            "end_time": "15:00",
        }

        with self.login(user):
            response = self.post("trips:event-change-times", pk=event.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-change-times.html")
        assert "form" in response.context
        assert response.context["form"].errors

        event.refresh_from_db()
        assert event.start_time == datetime.time(10, 0)  # Time shouldn't change

    def test_get_change_times_unauthorized(self):
        """Test unauthorized access to change times"""
        other_user = self.make_user("other")
        trip = TripFactory(author=other_user)
        day = trip.days.first()
        event = EventFactory(day=day)

        user = self.make_user("user")
        with self.login(user):
            response = self.get("trips:event-change-times", pk=event.pk)

        self.response_404(response)
