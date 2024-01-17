from datetime import date, timedelta

import factory
import pytest

from trips.forms import (
    LinkForm,
    NoteForm,
    PlaceAssignForm,
    PlaceForm,
    TripDateUpdateForm,
    TripForm,
)

pytestmark = pytest.mark.django_db


class TestTripForm:
    def test_form(self):
        data = {
            "title": "Test Trip",
            "description": "Test Description",
            "start_date": date.today() + timedelta(days=10),
            "end_date": date.today() + timedelta(days=12),
        }
        form = TripForm(data=data)

        assert form.is_valid()

    def test_end_date_before_start_date(self):
        data = {
            "title": "Test Trip",
            "description": "Test Description",
            "start_date": date.today() + timedelta(days=12),
            "end_date": date.today() + timedelta(days=10),
        }
        form = TripForm(data=data)

        assert not form.is_valid()
        assert "End date must be after start date" in form.non_field_errors()

    def test_start_date_before_today(self):
        data = {
            "title": "Test Trip",
            "description": "Test Description",
            "start_date": date.today() - timedelta(days=7),
            "end_date": date.today() + timedelta(days=10),
        }
        form = TripForm(data=data)

        assert not form.is_valid()
        assert "Start date must be after today" in form.errors["start_date"]


class TestTripDateUpdateForm:
    def test_form(self):
        data = {
            "start_date": date.today() + timedelta(days=10),
            "end_date": date.today() + timedelta(days=12),
        }
        form = TripDateUpdateForm(data=data)

        assert form.is_valid()

    def test_end_date_before_start_date(self):
        data = {
            "start_date": date.today() + timedelta(days=12),
            "end_date": date.today() + timedelta(days=10),
        }
        form = TripDateUpdateForm(data=data)

        assert not form.is_valid()
        assert "End date must be after start date" in form.non_field_errors()


class TestLinkForm:
    def test_form(self):
        data = {
            "url": "https://www.google.com",
            "description": "Test Description",
        }
        form = LinkForm(data=data)

        assert form.is_valid()


class TestPlaceForm:
    def test_form(self, user_factory, trip_factory):
        """Test that the form saves a place"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        day = trip.days.first()
        data = {
            "name": "Test Place",
            "address": factory.Faker("street_address"),
            "day": day,
        }
        form = PlaceForm(parent=trip, data=data)
        if form.is_valid():
            place = form.save(commit=False)
            place.trip = trip
            place.save()

        assert form.is_valid()
        assert place == trip.places.first()

    def test_update(self, user_factory, trip_factory, place_factory):
        """Test that the form updates the place"""
        user = user_factory()
        trip = trip_factory(author=user)
        place = place_factory(trip=trip)
        data = {
            "name": "Test Place",
            "address": factory.Faker("street_address"),
            "day": trip.days.first(),
        }
        form = PlaceForm(data=data, instance=place)
        if form.is_valid():
            place = form.save(commit=False)
            place.trip = trip
            place.save()

        assert form.is_valid()
        assert place == trip.places.first()


class TestPlaceAssignForm:
    def test_form(self, user_factory, trip_factory, place_factory):
        """Test that the form only shows the days of the trip it's assigned to"""
        user = user_factory()
        user2 = user_factory()
        trip = trip_factory(author=user)
        trip2 = trip_factory(author=user2)  # noqa: F841
        place = place_factory(trip=trip)
        form = PlaceAssignForm(instance=place)

        assert len(form.fields["day"].choices) == trip.days.count()


class TestNoteForm:
    def test_form(self, user_factory, trip_factory):
        """Test that the form saves a note"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        data = {
            "content": "Test content",
        }
        form = NoteForm(trip=trip, data=data)

        assert form.is_valid()

    def test_queryset(self, user_factory, trip_factory, place_factory, link_factory):
        """Test that the form display the correct places and links to be assigned to the newly created note"""
        user = user_factory()
        trip = trip_factory(author=user)
        place = place_factory(trip=trip)
        link = link_factory(author=user)
        trip.links.add(link)
        trip.save()

        form = NoteForm(trip=trip)

        assert place in form.fields["place"].queryset
        assert link in form.fields["link"].queryset