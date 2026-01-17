from unittest.mock import patch

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
from trips.forms import ExperienceForm, MealForm

pytestmark = pytest.mark.django_db


class AddExperienceView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Walking Tour",
            "type": 1,
            "address": "Starting Point",
            "start_time": "14:00",
            "duration": "120",
            "website": "https://example.com",
        }

        with self.login(user):
            response = self.post("trips:add-experience", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Experience added successfully"
        assert day.events.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Visit Museum",
        }

        with self.login(user):
            response = self.post("trips:add-experience", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/experience-create.html")
        assert day.events.count() == 0


class AddMealView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "La Pergola",
            "type": 1,  # LUNCH
            "address": "Via Alberto Cadlolo, 101, Rome",
            "start_time": "13:00",
            "duration": "60",  # 1 hour
            "website": "https://example.com",
        }

        with self.login(user):
            response = self.post("trips:add-meal", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Meal added successfully"
        assert day.events.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Lunch",
        }

        with self.login(user):
            response = self.post("trips:add-meal", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/meal-create.html")
        assert day.events.count() == 0


class EventDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.delete("trips:event-delete", pk=event.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event deleted successfully"
        assert event.day.events.count() == 0


class EventUnpairView(TestCase):
    def test_unpair(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.put("trips:event-unpair", pk=event.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event unpaired successfully"
        event.refresh_from_db()
        assert event.day is None


class EventPairView(TestCase):
    def test_pair(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)
        event.day = None  # Unpair the event first
        event.save()

        with self.login(user):
            response = self.put("trips:event-pair", pk=event.pk, day_id=day.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Event paired successfully"
        event.refresh_from_db()
        assert event.day == day


class EventPairChoiceView(TestCase):
    """Test cases for event pair choice view"""

    def test_get_pair_choice(self):
        """Test successful retrieval of event pair choice page"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        event = EventFactory(trip=trip)
        event.day = None  # Ensure event is unpaired
        event.save()

        with self.login(user):
            response = self.get("trips:event-pair-choice", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-pair-choice.html")
        assert response.context["event"] == event
        assert list(response.context["days"]) == list(trip.days.all())

    def test_get_pair_choice_already_paired(self):
        """Test pair choice view with already paired event"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)  # Event is already paired

        with self.login(user):
            response = self.get("trips:event-pair-choice", pk=event.pk)

        self.response_200(response)
        assert list(response.context["days"]) == list(trip.days.all())


class EventModalView(TestCase):
    """Test cases for event modal view"""

    def test_get_modal(self):
        """Test successful retrieval of event modal"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-modal", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-modal.html")
        assert response.context["event"] == event


class EventModifyView(TestCase):
    def test_get_experience(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(day=day)  # Experience

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_200(response)
        assert isinstance(response.context["form"], ExperienceForm)

    def test_get_meal(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = MealFactory(day=day)  # Meal

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_200(response)
        assert isinstance(response.context["form"], MealForm)

    def test_get_invalid_category(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        event = EventFactory(trip=trip, category=99)  # Invalid category

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_404(response)

    def test_get_invalid_category_for_coverage(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, category=4)  # Invalid category

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_404(response)
