# test_models.py
from datetime import date, timedelta
from unittest.mock import Mock, patch

import factory
import pytest

from trips.models import Place

pytestmark = pytest.mark.django_db


class TestTripModel:
    def test_factory(self, user_factory, trip_factory):
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
    def test_status(self, user_factory, trip_factory, start_date, end_date, status):
        user = user_factory()
        trip = trip_factory(
            author=user, title="Test Trip", start_date=start_date, end_date=end_date
        )

        assert trip.status == status

    def test_status_without_dates_given(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(
            author=user, title="Test Trip", start_date=None, end_date=None
        )

        assert trip.status == 1

    def test_archived_trip_bypass_dates_checks(self, user_factory, trip_factory):
        user = user_factory()
        trip = trip_factory(
            author=user,
            title="Test Trip",
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=8),
            status=5,
        )

        assert trip.status == 5


class TestDayModel:
    def test_factory(self, user_factory, trip_factory):
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

    def test_days_deleted_when_trip_dates_updated(self, user_factory, trip_factory):
        """Test correct days are deleted when trip dates updated"""
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
        )

        assert trip.days.all().first().date == date.today()

        trip.start_date = date.today() + timedelta(days=1)
        trip.save()

        assert trip.days.all().first().date == date.today() + timedelta(days=1)


mock_geocoder_response = Mock(latlng=(10.0, 20.0))


@pytest.fixture
def mocked_geocoder():
    with patch(
        "trips.models.geocoder.mapbox", return_value=mock_geocoder_response
    ) as mocked_geocoder:
        yield mocked_geocoder


class TestPlaceModel:
    @pytest.mark.mapbox
    @factory.Faker.override_default_locale("it_IT")
    def test_factory(self, user_factory, trip_factory, place_factory, mocked_geocoder):
        """Test place model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        place = place_factory(name="Test Place", trip=trip)

        assert place.__str__() == "Test Place"
        assert place.trip == trip
        assert place.latitude is not None
        assert place.longitude is not None

    @pytest.mark.mapbox
    @factory.Faker.override_default_locale("it_IT")
    def test_assign_to_day(
        self, user_factory, trip_factory, place_factory, mocked_geocoder
    ):
        """Test place assign to day"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        place = place_factory(name="Test Place", trip=trip)

        place.day = trip.days.all().first()
        place.save()

        assert place.day == trip.days.all().first()

    @pytest.mark.mapbox
    @factory.Faker.override_default_locale("it_IT")
    def test_place_unassign_on_trip_dates_update(
        self, user_factory, trip_factory, place_factory, mocked_geocoder
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

    @pytest.mark.mapbox
    def test_unassigned_manager(
        self, user_factory, trip_factory, place_factory, mocked_geocoder
    ):
        """Test place unassigned manager"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        place = place_factory(name="Test Place", trip=trip)

        place.day = trip.days.first()
        place.save()

        assert trip.places.count() == 1
        assert trip.places.first().day is not None
        assert trip.places.first().day == trip.days.first()

        assert Place.na_objects.filter(trip=trip).count() == 0

        trip.start_date = date.today() + timedelta(days=7)
        trip.end_date = date.today() + timedelta(days=11)
        trip.save()

        assert Place.na_objects.filter(trip=trip).count() == 1


class TestLinkModel:
    def test_factory(self, user_factory, trip_factory, link_factory):
        """Test link model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        link = link_factory()

        trip.links.add(link)
        trip.save()

        assert link.__str__() == link.url
        assert trip.links.first() == link


class TestNoteModel:
    def test_factory(self, user_factory, trip_factory, note_factory):
        """Test note model factory"""
        user = user_factory()
        trip = trip_factory(author=user, title="Test Trip")
        note = note_factory()

        trip.notes.add(note)
        trip.save()

        assert note.__str__() == f"{note.content[:35]} ..."
        assert trip.notes.first() == note
        assert note.checked is False
