# test_models.py
from datetime import date, timedelta

import factory
import pytest

pytestmark = pytest.mark.django_db


class TestTripModel:
    def test_trip_model_factory(self, user_factory, trip_factory):
        """Test trip model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")

        assert trip.__str__() == "Test Trip"
        assert trip.author == user

    @pytest.mark.parametrize(
        "start_date, end_date, status",
        [
            (date.today() + timedelta(days=10), date.today() + timedelta(days=12), 1),
            (date.today() + timedelta(days=4), date.today() + timedelta(days=6), 2),
            (date.today() - timedelta(days=1), date.today() + timedelta(days=1), 3),
            (date.today() - timedelta(days=10), date.today() - timedelta(days=8), 4),
        ],
    )
    def test_trip_status(
        self, user_factory, trip_factory, start_date, end_date, status
    ):
        user = user_factory()

        trip = trip_factory(
            author=user, title="Test Trip", start_date=start_date, end_date=end_date
        )

        print(start_date, end_date, status)

        assert trip.status == status


class TestDayModel:
    def test_day_model_factory(self, user_factory, trip_factory):
        """Test day automatically created matches requirements"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )

        assert trip.days.all().first().__str__() == "Day 1"
        assert trip.days.all().first().number == 1
        assert trip.days.all().first().date == trip.start_date
        assert trip.days.all().count() == 3


class TestPlaceModel:
    @factory.Faker.override_default_locale("it_IT")
    def test_place_model_factory(self, user_factory, trip_factory, place_factory):
        """Test place model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        place = place_factory(name="Test Place", trip=trip)

        assert place.__str__() == "Test Place"
        assert place.trip == trip
        assert place.latitude is not None
        assert place.longitude is not None

    @factory.Faker.override_default_locale("it_IT")
    def test_place_assign_to_day(self, user_factory, trip_factory, place_factory):
        """Test place assign to day"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        place = place_factory(name="Test Place", trip=trip)

        place.day = trip.days.all().first()
        place.save()

        assert place.day == trip.days.all().first()

    @factory.Faker.override_default_locale("it_IT")
    def test_place_unassign_on_trip_dates_update(
        self, user_factory, trip_factory, place_factory
    ):
        """Test place unassign on trip dates update"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            title="Test Trip",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        place = place_factory(name="Test Place", trip=trip)

        place.day = trip.days.first()
        place.save()

        trip.start_date = date.today() + timedelta(days=7)
        trip.end_date = date.today() + timedelta(days=11)
        trip.save()

        assert trip.places.first().day is None
