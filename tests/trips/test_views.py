import datetime
import json
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TransportFactory,
    TripFactory,
)
from trips.forms import ExperienceForm, MealForm, TransportForm
from trips.models import Stay, Trip
from trips.utils import generate_cache_key, geocode_location

pytestmark = pytest.mark.django_db

mock_geocoder_response = Mock(latlng=(10.0, 20.0))
invalid_mock_geocoder_response = Mock(latlng=None)


@pytest.fixture
def mocked_geocoder():
    with patch(
        "trips.models.geocoder.mapbox", return_value=mock_geocoder_response
    ) as mocked_geocoder:
        yield mocked_geocoder


class HomeView(TestCase):
    def test_get(self):
        response = self.get("trips:home")
        self.response_200(response)
        assertTemplateUsed(response, "trips/index.html")

    def test_get_with_authenticated_user(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert (
            response.context["latest_trip"] == trip
            or trip in response.context["other_trips"]
        )

    def test_get_with_latest_trip(self):
        user = self.make_user("user")
        trip1 = TripFactory(
            author=user,
            status=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
        )
        trip2 = TripFactory(
            author=user,
            status=3,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 10),
        )  # IN_PROGRESS

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert response.context["latest_trip"] == trip2
        assert trip1 in response.context["other_trips"]

    def test_get_with_fav_trip(self):
        user = self.make_user("user")
        fav_trip = TripFactory(author=user)
        user.profile.fav_trip = fav_trip
        user.profile.save()

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert response.context["fav_trip"] == fav_trip
        assert response.context["latest_trip"] is None

    def test_get_with_fav_trip_and_days(self):
        user = self.make_user("user")
        fav_trip = TripFactory(
            author=user, start_date=date(2024, 1, 1), end_date=date(2024, 1, 3)
        )
        user.profile.fav_trip = fav_trip
        user.profile.save()

        day = fav_trip.days.first()
        ExperienceFactory(day=day, trip=fav_trip)

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert response.context["fav_trip"] == fav_trip
        assert len(response.context["fav_trip"].days.all()) == 3

    def test_get_with_unpaired_events(self):
        from datetime import time as time_obj

        from trips.models import Experience

        user = self.make_user("user")
        trip = TripFactory(author=user)
        unpaired_event = Experience.objects.create(
            trip=trip,
            day=None,
            name="Test Event",
            start_time=time_obj(10, 0),
            end_time=time_obj(11, 0),
            address="Test Address",
            city=trip.destination,
        )

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert unpaired_event.event_ptr in response.context["unpaired_events"]

    def test_get_excludes_archived_trips(self):
        user = self.make_user("user")
        TripFactory(author=user, status=5)  # ARCHIVED

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert response.context["latest_trip"] is None
        assert len(response.context["other_trips"]) == 0

    def test_get_with_no_profile(self):
        user = self.make_user("user")
        user.profile.delete()

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)


class TripListView(TestCase):
    def test_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-list.html")

    def test_trips(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        archived_trip = TripFactory(author=user, status=5)

        with self.login(user):
            response = self.get("trips:trip-list")

        assert trip in response.context["active_trips"]
        assert archived_trip in response.context["archived_trips"]

    def test_htmx_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-list", extra={"HTTP_HX-Request": "true"})

        self.response_200(response)
        assert "trips/trip-list.html" not in [t.name for t in response.templates]

    def test_trip_list_sorted_by_date_asc_default(self):
        """Test trip list uses date_asc sorting by default"""
        user = self.make_user("user")
        trip1 = TripFactory(author=user, title="Alpha", start_date=date(2026, 3, 1))
        trip2 = TripFactory(author=user, title="Beta", start_date=date(2026, 1, 1))
        trip3 = TripFactory(author=user, title="Gamma", start_date=date(2026, 2, 1))

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        active_trips = list(response.context["active_trips"])
        assert active_trips == [trip2, trip3, trip1]  # sorted by start_date asc

    def test_trip_list_sorted_by_date_asc(self):
        """Test trip list sorting by date ascending"""
        user = self.make_user("user")
        user.profile.trip_sort_preference = "date_asc"
        user.profile.save()

        trip1 = TripFactory(author=user, title="Alpha", start_date=date(2025, 3, 1))
        trip2 = TripFactory(author=user, title="Beta", start_date=date(2025, 1, 1))
        trip3 = TripFactory(author=user, title="Gamma", start_date=date(2025, 2, 1))

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        active_trips = list(response.context["active_trips"])
        assert active_trips == [trip2, trip3, trip1]  # sorted by start_date asc

    def test_trip_list_sorted_by_date_desc(self):
        """Test trip list sorting by date descending"""
        user = self.make_user("user")
        user.profile.trip_sort_preference = "date_desc"
        user.profile.save()

        trip1 = TripFactory(author=user, title="Alpha", start_date=date(2025, 3, 1))
        trip2 = TripFactory(author=user, title="Beta", start_date=date(2025, 1, 1))
        trip3 = TripFactory(author=user, title="Gamma", start_date=date(2025, 2, 1))

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        active_trips = list(response.context["active_trips"])
        assert active_trips == [trip1, trip3, trip2]  # sorted by start_date desc

    def test_trip_list_sorted_by_name_asc(self):
        """Test trip list sorting by name ascending"""
        user = self.make_user("user")
        user.profile.trip_sort_preference = "name_asc"
        user.profile.save()

        trip1 = TripFactory(author=user, title="Gamma Trip")
        trip2 = TripFactory(author=user, title="Alpha Trip")
        trip3 = TripFactory(author=user, title="Beta Trip")

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        active_trips = list(response.context["active_trips"])
        assert active_trips == [trip2, trip3, trip1]  # sorted by title asc

    def test_trip_list_sorted_by_name_desc(self):
        """Test trip list sorting by name descending"""
        user = self.make_user("user")
        user.profile.trip_sort_preference = "name_desc"
        user.profile.save()

        trip1 = TripFactory(author=user, title="Gamma Trip")
        trip2 = TripFactory(author=user, title="Alpha Trip")
        trip3 = TripFactory(author=user, title="Beta Trip")

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        active_trips = list(response.context["active_trips"])
        assert active_trips == [trip1, trip3, trip2]  # sorted by title desc

    def test_trip_list_sorting_applies_to_archived(self):
        """Test that sorting preference applies to archived trips too"""
        user = self.make_user("user")
        user.profile.trip_sort_preference = "name_asc"
        user.profile.save()

        archived1 = TripFactory(author=user, status=5, title="Zulu")
        archived2 = TripFactory(author=user, status=5, title="Alpha")

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        archived_trips = list(response.context["archived_trips"])
        assert archived_trips == [archived2, archived1]  # sorted by title asc

    def test_trip_list_with_none_start_dates(self):
        """Test trip list sorting handles None start_dates gracefully"""
        user = self.make_user("user")
        user.profile.trip_sort_preference = "date_asc"
        user.profile.save()

        TripFactory(author=user, title="Alpha", start_date=None)
        TripFactory(author=user, title="Beta", start_date=date(2025, 1, 1))

        with self.login(user):
            response = self.get("trips:trip-list")

        self.response_200(response)
        # Should not crash, None dates sorted to end or beginning depending on DB
        assert response.status_code == 200


class TripDetailView(TestCase):
    """Test cases for trip detail view"""

    def test_get_trip_detail_success(self):
        """Test successful retrieval of trip detail page"""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-detail.html")
        assert response.context["trip"] == trip

    def test_get_trip_detail_not_found(self):
        """Test 404 response for non-existent trip"""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-detail", pk=99999)

        self.response_404(response)

    def test_get_trip_detail_with_htmx(self):
        """Test that trip detail returns partial template with HTMX request"""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get(
                "trips:trip-detail", pk=trip.pk, extra={"HTTP_HX-Request": "true"}
            )

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/day.html")
        assert response.context["trip"] == trip

    def test_get_trip_detail_without_htmx(self):
        """Test that trip detail returns full template without HTMX request"""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-detail.html")
        assert response.context["trip"] == trip


class TestTripDatesUpdate(TestCase):
    """Test cases for trip dates update view"""

    def test_get_displays_form(self):
        """Test GET request displays date edit form"""
        user = self.make_user("user")
        trip = TripFactory(
            author=user, start_date=date(2025, 6, 1), end_date=date(2025, 6, 5)
        )

        with self.login(user):
            response = self.get("trips:trip-dates", pk=trip.pk)

        self.response_200(response)
        assert "form" in response.context
        assertTemplateUsed(response, "trips/trip-dates-update.html")

    def test_post_valid_updates_dates_and_days(self):
        """Test valid POST updates dates and regenerates days"""
        user = self.make_user("user")
        trip = TripFactory(
            author=user, start_date=date(2025, 6, 1), end_date=date(2025, 6, 5)
        )
        # Trip initially has 5 days (June 1-5)
        assert trip.days.count() == 5

        data = {
            "start_date": "06/01/2025",  # Same start (MM/DD/YYYY)
            "end_date": "06/10/2025",  # Extended by 5 days (MM/DD/YYYY)
        }

        with self.login(user):
            response = self.post("trips:trip-dates", pk=trip.pk, data=data)

        self.assertEqual(response.status_code, 204)
        trip.refresh_from_db()
        assert trip.days.count() == 10  # Signal auto-generated 5 more days
        assert trip.end_date == date(2025, 6, 10)

    def test_post_valid_triggers_htmx_events(self):
        """Test valid POST triggers tripSaved and tripModified events"""
        user = self.make_user("user")
        trip = TripFactory(
            author=user, start_date=date(2025, 6, 1), end_date=date(2025, 6, 5)
        )

        data = {
            "start_date": "06/01/2025",  # MM/DD/YYYY
            "end_date": "06/10/2025",  # MM/DD/YYYY
        }

        with self.login(user):
            response = self.post("trips:trip-dates", pk=trip.pk, data=data)

        self.assertEqual(response.status_code, 204)
        # Check that HX-Trigger header contains both events
        hx_trigger = response.headers.get("HX-Trigger")
        assert hx_trigger is not None
        trigger_data = json.loads(hx_trigger)
        assert "tripSaved" in trigger_data
        assert "tripModified" in trigger_data

    def test_post_invalid_shows_errors(self):
        """Test invalid POST shows validation errors"""
        user = self.make_user("user")
        trip = TripFactory(
            author=user, start_date=date(2025, 6, 1), end_date=date(2025, 6, 5)
        )

        data = {
            "start_date": "06/10/2025",  # MM/DD/YYYY
            "end_date": "06/01/2025",  # End before start - invalid (MM/DD/YYYY)
        }

        with self.login(user):
            response = self.post("trips:trip-dates", pk=trip.pk, data=data)

        self.response_200(response)  # Re-renders form with errors
        assert "form" in response.context
        assert response.context["form"].errors

    def test_unauthorized_user_cannot_access(self):
        """Test only trip author can edit dates"""
        user = self.make_user("user")
        other_user = self.make_user("other")
        trip = TripFactory(
            author=user, start_date=date(2025, 6, 1), end_date=date(2025, 6, 5)
        )

        with self.login(other_user):
            self.get("trips:trip-dates", pk=trip.pk)

        self.response_404()  # get_object_or_404 checks author


class DayDetailView(TestCase):
    """Test cases for day detail view"""

    def test_get_day_detail_success(self):
        """Test successful retrieval of day detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day)

        with self.login(user):
            response = self.get("trips:day-detail", pk=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/day.html")
        assert day.events.first() == event
        assert "day" in response.context
        assert response.context["day"] == day
        assert "show_map" in response.context
        assert response.context["show_map"] is False

    def test_get_day_detail_with_map_preference(self):
        """Test day detail respects user's map view preference"""
        user = self.make_user("user")
        user.profile.default_map_view = "map"
        user.profile.save()
        trip = TripFactory(author=user)
        day = trip.days.first()
        EventFactory(day=day, latitude=45.4773, longitude=9.1815)

        with self.login(user):
            response = self.get("trips:day-detail", pk=day.pk)

        self.response_200(response)
        assert response.context["show_map"] is True
        assert "map" in response.context
        assert "locations" in response.context

    def test_get_day_detail_with_forced_view_parameter(self):
        """Test day detail with ?view=map query parameter overrides user preference"""
        user = self.make_user("user")
        user.profile.default_map_view = "list"
        user.profile.save()
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.get("trips:day-detail", pk=day.pk, data={"view": "map"})

        self.response_200(response)
        assert response.context["show_map"] is True

    def test_get_day_detail_map_with_stay_spanning_days(self):
        """Test day detail map view with stay spanning multiple days"""
        user = self.make_user("user")
        user.profile.default_map_view = "map"
        user.profile.save()
        trip = TripFactory(
            author=user,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
        )
        stay = StayFactory(latitude=45.4773, longitude=9.1815)
        day1 = trip.days.first()
        day2 = trip.days.all()[1]
        day1.stay = stay
        day1.save()
        day2.stay = stay
        day2.save()
        EventFactory(day=day2, trip=trip, latitude=45.4773, longitude=9.1815)

        with self.login(user):
            response = self.get("trips:day-detail", pk=day2.pk)

        self.response_200(response)
        assert response.context["show_map"] is True
        assert "locations" in response.context
        assert "first_day" not in response.context["locations"]

    def test_get_day_detail_map_with_different_stays(self):
        """Test day detail map view with different stays on consecutive days"""
        user = self.make_user("user")
        user.profile.default_map_view = "map"
        user.profile.save()
        trip = TripFactory(
            author=user,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
        )
        stay1 = StayFactory(latitude=45.4773, longitude=9.1815)
        stay2 = StayFactory(latitude=45.5, longitude=9.2)
        day1 = trip.days.first()
        day2 = trip.days.all()[1]
        trip.days.all()[2]
        day1.stay = stay1
        day1.save()
        day2.stay = stay2
        day2.save()
        EventFactory(day=day2, trip=trip, latitude=45.4773, longitude=9.1815)

        with self.login(user):
            response = self.get("trips:day-detail", pk=day2.pk)

        self.response_200(response)
        assert response.context["show_map"] is True
        assert "locations" in response.context
        assert "next_day_stay" in response.context["locations"]
        # day3 has no stay, so next_day_stay should be None
        assert response.context["locations"]["next_day_stay"] is None

    def test_get_day_detail_map_without_next_day_stay(self):
        """Test day detail map view when next day has no stay"""
        user = self.make_user("user")
        user.profile.default_map_view = "map"
        user.profile.save()
        trip = TripFactory(
            author=user,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=1),
        )
        stay = StayFactory(latitude=45.4773, longitude=9.1815)
        day1 = trip.days.first()
        day1.stay = stay
        day1.save()
        EventFactory(day=day1, trip=trip, latitude=45.4773, longitude=9.1815)

        with self.login(user):
            response = self.get("trips:day-detail", pk=day1.pk)

        self.response_200(response)
        assert response.context["show_map"] is True
        assert "locations" in response.context
        assert response.context["locations"]["next_day_stay"] is None

    def test_get_day_detail_map_with_next_day_different_stay(self):
        """Test day detail map view when next day has a different stay"""
        user = self.make_user("user")
        user.profile.default_map_view = "map"
        user.profile.save()
        trip = TripFactory(
            author=user,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
        )
        stay1 = StayFactory(latitude=45.4773, longitude=9.1815)
        stay2 = StayFactory(latitude=45.5, longitude=9.2)
        day1 = trip.days.first()
        day2 = trip.days.all()[1]
        day1.stay = stay1
        day1.save()
        day2.stay = stay2
        day2.save()
        EventFactory(day=day1, trip=trip, latitude=45.4773, longitude=9.1815)

        with self.login(user):
            response = self.get("trips:day-detail", pk=day1.pk)

        self.response_200(response)
        assert response.context["show_map"] is True
        assert "locations" in response.context
        assert response.context["locations"]["next_day_stay"] == stay2


class TripCreateView(TestCase):
    def test_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-create")

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-create.html")

    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "destination": "Novara",
            "description": "A trip to Paris",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.post("trips:trip-create", data=data)

        self.response_204(response)
        trip = Trip.objects.filter(author=user).first()
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> added successfully"
        assert Trip.objects.filter(author=user).count() == 1

    def test_post_with_invalid_start_date(self):
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "description": "A trip to Paris",
            "start_date": datetime.date.today() + datetime.timedelta(days=3),
            "end_date": datetime.date.today(),
        }

        with self.login(user):
            response = self.post("trips:trip-create", data=data)

        self.response_200(response)
        assert Trip.objects.filter(author=user).count() == 0


class TripDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.delete("trips:trip-delete", pk=trip.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> deleted successfully"
        assert Trip.objects.filter(author=user).count() == 0


class TripUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-update", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-create.html")

    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Trip to Paris",
            "destination": "Novara",
            "description": "A trip to Paris",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.post("trips:trip-update", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        trip = Trip.objects.filter(author=user).first()
        assert message == f"<strong>{trip.title}</strong> updated successfully"
        assert trip.title == data["title"]

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Trip to Paris",
        }

        with self.login(user):
            response = self.post("trips:trip-update", pk=trip.pk, data=data)

        self.response_200(response)


class TripArchiveView(TestCase):
    def test_archive(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.post("trips:trip-archive", pk=trip.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> archived successfully"
        assert Trip.objects.filter(author=user).count() == 1
        assert Trip.objects.filter(author=user, status=5).count() == 1

    def test_archive_resets_fav_trip_if_favourite(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        user.profile.fav_trip = trip
        user.profile.save()

        with self.login(user):
            response = self.post("trips:trip-archive", pk=trip.pk)

        self.response_204(response)
        user.profile.refresh_from_db()
        assert user.profile.fav_trip is None
        assert Trip.objects.filter(author=user, status=5).count() == 1

    def test_archive_does_not_reset_fav_trip_if_different(self):
        user = self.make_user("user")
        trip1 = TripFactory(author=user)
        trip2 = TripFactory(author=user)
        user.profile.fav_trip = trip1
        user.profile.save()

        with self.login(user):
            response = self.post("trips:trip-archive", pk=trip2.pk)

        self.response_204(response)
        user.profile.refresh_from_db()
        assert user.profile.fav_trip == trip1
        assert Trip.objects.filter(author=user, status=5).count() == 1


class TripUnarchiveView(TestCase):
    def test_unarchive(self):
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            status=5,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=5),
        )

        with self.login(user):
            response = self.post("trips:trip-unarchive", pk=trip.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> unarchived successfully"
        trip.refresh_from_db()
        assert trip.status == Trip.Status.COMPLETED


class TripDatesUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-dates", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-dates-update.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=3)
        data = {
            "start_date": start_date.strftime("%m/%d/%Y"),  # Format as MM/DD/YYYY
            "end_date": end_date.strftime("%m/%d/%Y"),  # Format as MM/DD/YYYY
        }

        with self.login(user):
            response = self.post("trips:trip-dates", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        trip = Trip.objects.filter(author=user).first()
        assert message == "Dates updated successfully"
        trip.refresh_from_db()
        assert trip.start_date == start_date
        assert trip.end_date == end_date

    def test_day_numbers_are_correct_and_unique_after_date_change(self):
        """
        Ensure that after changing the trip's start_date, all days have correct and unique numbers.
        """
        user = self.make_user("user")
        # Create a trip with 3 days
        start_date = datetime.date(2024, 5, 2)
        end_date = start_date + datetime.timedelta(days=2)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)
        days = list(trip.days.order_by("date"))
        assert [d.number for d in days] == [1, 2, 3]

        # Change start_date to add a day before
        trip.start_date = start_date - datetime.timedelta(days=1)
        trip.save()
        trip.refresh_from_db()
        days = list(trip.days.order_by("date"))

        # Check that numbers are 1, 2, 3, 4 and unique
        numbers = [d.number for d in days]
        assert numbers == [1, 2, 3, 4]
        assert len(numbers) == len(set(numbers)), "Day numbers are not unique"

        # Check that the dates are consecutive and ordered
        expected_dates = [
            trip.start_date + datetime.timedelta(days=i) for i in range(4)
        ]
        assert [d.date for d in days] == expected_dates


class AddTransportView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "type": 1,
            "origin_city": "Milan",
            "origin_address": "Central Station",
            "destination_city": "Rome",
            "destination_address": "Termini",
            "start_time": "10:00",
            "end_time": "12:00",
            "company": "Trenitalia",
            "website": "https://example.com",
        }

        with self.login(user):
            response = self.post("trips:add-transport", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Transport added successfully"
        assert day.events.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "type": 1,
        }

        with self.login(user):
            response = self.post("trips:add-transport", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/transport-create.html")
        assert day.events.count() == 0


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


class AddStayView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        day = days.first()
        data = {
            "name": "Grand Hotel",
            "check_in": "14:00",
            "check_out": "11:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "website": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay added successfully"
        day.refresh_from_db()
        assert day.stay is not None

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        data = {
            "name": "Hotel",
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=day.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-create.html")
        assert day.stay is None

    @patch("geocoder.mapbox")
    def test_post_single_day(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        first_day = days.first()
        data = {
            "name": "Grand Hotel",
            "check_in": "14:00",
            "check_out": "11:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "website": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [first_day.pk],  # Only apply to first day
        }

        with self.login(user):
            response = self.post("trips:add-stay", day_id=first_day.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay added successfully"

        # Refresh days from db and verify
        first_day.refresh_from_db()
        assert first_day.stay is not None

        # Other days should not have the stay
        other_days = days.exclude(pk=first_day.pk)
        for day in other_days:
            day.refresh_from_db()
            assert day.stay is None


class StayDetailView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        # Create stay and set days after creation
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-detail", pk=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-detail.html")
        assert response.context["stay"] == stay
        assert response.context["first_day"] == days.first()
        assert response.context["last_day"] == days.last()

    def test_get_with_previous_day(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.all())
        # Create stay and set only second day onwards
        stay = StayFactory()
        stay.days.set(days[1:])

        with self.login(user):
            response = self.get("trips:stay-detail", pk=stay.pk)

        self.response_200(response)
        assert (
            response.context["first_day"] == days[0]
        )  # Should be the day before first stay day
        assert response.context["last_day"] == days[-1]


class StayModifyView(TestCase):
    @patch("geocoder.mapbox")
    def test_post(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        data = {
            "name": "Updated Hotel",
            "check_in": "15:00",
            "check_out": "10:00",
            "cancellation_date": "2024-12-31",
            "phone_number": "+1234567890",
            "website": "https://example.com",
            "address": "Via Roma 1, Rome",
            "apply_to_days": [day.pk for day in days],
        }

        with self.login(user):
            response = self.post("trips:stay-modify", pk=stay.pk, data=data)

        self.response_200(response)
        assert response.context["modified"]
        stay.refresh_from_db()
        assert stay.name == "Updated Hotel"
        assert stay.check_in == datetime.time(15, 0)
        assert stay.check_out == datetime.time(10, 0)

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        data = {
            "name": "",  # Invalid: name is required
        }

        with self.login(user):
            response = self.post("trips:stay-modify", pk=stay.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-modify.html")


class StayDeleteView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-delete.html")
        assert response.context["stay"] == stay

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        stay.days.set(days)

        with self.login(user):
            response = self.post("trips:stay-delete", pk=stay.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay deleted successfully"
        # Refresh the day from the database to get the updated stay value
        first_day = days.first()
        first_day.refresh_from_db()
        assert not first_day.stay

    def test_get_with_single_other_stay(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stay = StayFactory()
        stay.days.set(days[:2])  # First two days
        other_stay.days.set(days[2:])  # Remaining days

        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay.pk)

        self.response_200(response)
        assert response.context["show_dropdown"] is False
        assert response.context["other_stays"].count() == 1
        assert response.context["other_stays"].first() == other_stay

    def test_get_with_multiple_other_stays(self):
        """Test stay deletion view when there are multiple other stays available"""
        user = self.make_user("user")

        # Create a trip with exactly 6 days
        start_date = datetime.date(2024, 1, 1)  # Use fixed date instead of today
        end_date = start_date + datetime.timedelta(days=5)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)

        # Get all days and ensure we have exactly 6
        days = list(trip.days.all().order_by("date"))
        assert len(days) == 6, f"Expected 6 days, got {len(days)}"

        # Create stays
        stay_to_delete = StayFactory()
        other_stay1 = StayFactory()
        other_stay2 = StayFactory()

        # Assign exactly 2 days to each stay
        stay_to_delete.days.set(days[:2])
        other_stay1.days.set(days[2:4])
        other_stay2.days.set(days[4:6])

        # Force refresh and verify setup
        for stay in [stay_to_delete, other_stay1, other_stay2]:
            stay.refresh_from_db()
            assert stay.days.count() == 2, f"Stay {stay.pk} should have exactly 2 days"

        # Verify trip has exactly 3 stays
        trip_stays = Stay.objects.filter(days__trip=trip).distinct()
        assert trip_stays.count() == 3, f"Expected 3 stays, got {trip_stays.count()}"

        # Get stay deletion page
        with self.login(user):
            response = self.get("trips:stay-delete", pk=stay_to_delete.pk)

        self.response_200(response)

        # Verify response
        other_stays = response.context["other_stays"]
        assert other_stays.count() == 2, (
            f"Expected 2 other stays, got {other_stays.count()}"
        )
        assert set(other_stays) == {other_stay1, other_stay2}, "Wrong stays in context"
        assert response.context["show_dropdown"] is True, "show_dropdown should be True"

    def test_post_with_single_other_stay_auto_reassign(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory()
        other_stay = StayFactory()
        stay.days.set(days[:2])
        other_stay.days.set(days[2:])

        with self.login(user):
            response = self.post("trips:stay-delete", pk=other_stay.pk)

        self.response_204(response)
        # Verify days were reassigned to the selected stay
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == stay

    def test_post_with_manual_stay_selection(self):
        """Test stay deletion when manually selecting a new stay from multiple options"""
        user = self.make_user("user")
        # Create a trip with exactly 6 days
        start_date = datetime.date(2024, 1, 1)  # Use fixed date instead of today
        end_date = start_date + datetime.timedelta(days=5)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)
        days = trip.days.all()

        # Create three stays
        stay_to_delete = StayFactory()
        new_stay = StayFactory()
        other_stay = StayFactory()

        # Assign days to stays
        stay_to_delete.days.set(days[:2])  # First two days
        new_stay.days.set(days[2:4])  # Next two days
        other_stay.days.set(days[4:])  # Remaining days

        # Verify initial setup
        assert Stay.objects.count() == 3

        with self.login(user):
            response = self.post(
                "trips:stay-delete",
                pk=stay_to_delete.pk,
                data={"new_stay": new_stay.pk},
            )

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Stay deleted successfully"

        # Verify stay was deleted
        assert not Stay.objects.filter(pk=stay_to_delete.pk).exists()

        # Verify days were reassigned to the selected stay
        for day in days[:2]:
            day.refresh_from_db()
            assert day.stay == new_stay


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
    def test_get_transport(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = TransportFactory(day=day)  # Transport

        with self.login(user):
            response = self.get("trips:event-modify", pk=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-modify.html")
        assert isinstance(response.context["form"], TransportForm)

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

    @patch("geocoder.mapbox")
    def test_post_transport(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = TransportFactory(day=day)  # Transport
        data = {
            "origin_city": "Milan",
            "origin_address": "Piazza Duomo",
            "destination_city": "Rome",
            "destination_address": "Termini Station",
            "start_time": "10:00",
            "end_time": "12:00",
            "company": "Trenitalia",
            "booking_reference": "TR123",
            "ticket_url": "https://example.com",
            "price": "50.00",
            "website": "https://example.com",
            "type": 1,
        }

        with self.login(user):
            response = self.post("trips:event-modify", pk=event.pk, data=data)

        self.response_200(response)
        event.refresh_from_db()
        assert event.name == "Milan → Rome"
        assert event.origin_city == "Milan"
        assert event.destination_city == "Rome"
        assert event.company == "Trenitalia"
        assert event.booking_reference == "TR123"

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = TransportFactory(day=day)  # Transport
        original_name = event.name
        data = {
            "name": "",  # Invalid: name is required
        }

        with self.login(user):
            response = self.post("trips:event-modify", pk=event.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-modify.html")
        event.refresh_from_db()
        assert event.name == original_name  # Check that name wasn't changed


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

    def test_get_transport_detail(self):
        """Test successful retrieval of transport event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        transport = TransportFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=transport.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-detail.html")
        assert response.context["event"] == transport

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


class TestViewLogFile(TestCase):
    """
    Tests for the view_log_file function-based view.
    """

    def test_view_log_file_success(self):
        """
        Should return the content of the log file if it exists and user is staff.
        """
        log_content = "test log content"
        with tempfile.TemporaryDirectory() as tmpdirname:
            log_file_path = f"{tmpdirname}/test.log"
            with open(log_file_path, "w") as f:
                f.write(log_content)
            url = reverse("trips:log", kwargs={"filename": "test.log"})
            user = self.make_user()
            user.is_staff = True
            user.save()
            with self.login(user), override_settings(BASE_DIR=Path(tmpdirname)):
                response = self.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain"
        assert log_content in response.content.decode()

    def test_view_log_file_not_found(self):
        """
        Should return 404 if the log file does not exist and user is staff.
        """
        with tempfile.TemporaryDirectory() as tmpdirname:
            url = reverse("trips:log", kwargs={"filename": "notfound.log"})
            user = self.make_user()
            user.is_staff = True
            user.save()
            with self.login(user), override_settings(BASE_DIR=Path(tmpdirname)):
                response = self.get(url)

        assert response.status_code == 404

    def test_view_log_file_forbidden_for_non_staff(self):
        """
        Should return 302 redirect to login for non-staff users.
        """
        log_content = "test log content"
        with tempfile.TemporaryDirectory() as tmpdirname:
            log_file_path = f"{tmpdirname}/test.log"
            with open(log_file_path, "w") as f:
                f.write(log_content)
            url = reverse("trips:log", kwargs={"filename": "test.log"})
            user = self.make_user()
            user.is_staff = False
            user.save()
            with self.login(user), override_settings(BASE_DIR=Path(tmpdirname)):
                response = self.get(url)

        assert response.status_code == 302


class ValidateDatesViewTests(TestCase):
    """
    Tests for the validate_dates function-based view.
    """

    def test_valid_dates(self):
        """Should return empty response if dates are valid."""
        today = datetime.date.today()
        data = {
            "start_date": today.isoformat(),
            "end_date": (today + datetime.timedelta(days=1)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_start_date_before_today(self):
        """Should return error if start_date is before today."""
        today = datetime.date.today()
        data = {
            "start_date": (today - datetime.timedelta(days=1)).isoformat(),
            "end_date": today.isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert b"Start date must be after today" in response.content

    def test_start_date_after_end_date(self):
        """Should return error if start_date is after end_date."""
        today = datetime.date.today()
        data = {
            "start_date": (today + datetime.timedelta(days=2)).isoformat(),
            "end_date": (today + datetime.timedelta(days=1)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert b"Start date cannot be after end date" in response.content

    def test_invalid_date_format(self):
        """Should return empty response if date format is invalid."""
        data = {
            "start_date": "not-a-date",
            "end_date": "also-not-a-date",
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_both_errors(self):
        """Should return both errors if start_date is before today and after end_date."""
        today = datetime.date.today()
        data = {
            "start_date": (today - datetime.timedelta(days=1)).isoformat(),
            "end_date": (today - datetime.timedelta(days=2)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert b"Start date must be after today" in response.content
        assert b"Start date cannot be after end date" in response.content

    def test_missing_start_date(self):
        """Should return empty response if start_date is missing."""
        today = datetime.date.today()
        data = {
            "end_date": (today + datetime.timedelta(days=1)).isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_missing_end_date(self):
        """Should return empty response if end_date is missing."""
        today = datetime.date.today()
        data = {
            "start_date": today.isoformat(),
        }
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""

    def test_missing_both_dates(self):
        """Should return empty response if both start_date and end_date are missing."""
        data = {}
        response = self.client.post(reverse("trips:validate-dates"), data)
        assert response.status_code == 200
        assert response.content == b""


class EventNotesView(TestCase):
    def test_event_notes_with_note(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Test note content")

        with self.login(user):
            response = self.get("trips:event-notes", event_id=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-notes.html")
        assert response.context["event"] == event
        assert response.context["form"].instance == event
        assert response.context["form"].initial["notes"] == "Test note content"

    def test_event_notes_without_note(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="")

        with self.login(user):
            response = self.get("trips:event-notes", event_id=event.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/event-notes.html")
        assert response.context["event"] == event
        assert response.context["form"].instance == event
        assert response.context["form"].initial["notes"] == ""


class StayNotesView(TestCase):
    def test_stay_notes_with_note(self):
        """
        Test stay_notes view when the stay has a note.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Test stay note")
        stay.save()  # Ensure stay has a primary key
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-notes", stay_id=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-notes.html")
        assert response.context["stay"] == stay
        assert response.context["form"].instance == stay
        assert response.context["form"].initial["notes"] == "Test stay note"

    def test_stay_notes_without_note(self):
        """
        Test stay_notes view when the stay has no note.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="")
        stay.save()  # Ensure stay has a primary key
        stay.days.set(days)

        with self.login(user):
            response = self.get("trips:stay-notes", stay_id=stay.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/stay-notes.html")
        assert response.context["stay"] == stay
        assert response.context["form"].instance == stay
        assert response.context["form"].initial["notes"] == ""


class NoteCreateView(TestCase):
    def test_note_create_success(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="")
        data = {"notes": "This is a test note."}

        with self.login(user):
            response = self.post("trips:note-create", event_id=event.pk, data=data)

        self.response_204(response)
        event.refresh_from_db()
        assert event.notes == data["notes"]

    def test_note_create_invalid_data(self):
        """
        Test note creation with invalid data: send a value that is too long for the notes field.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="")
        data = {"notes": ""}

        with self.login(user):
            response = self.post("trips:note-create", event_id=event.pk, data=data)

        assert response.status_code == 400
        event.refresh_from_db()
        assert event.notes == ""


class NoteModifyView(TestCase):
    def test_note_modify_success(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Old note")
        data = {"notes": "Updated note content"}

        with self.login(user):
            response = self.post("trips:note-modify", event_id=event.pk, data=data)

        self.response_200(response)
        event.refresh_from_db()
        assert event.notes == data["notes"]

    def test_note_modify_invalid_data(self):
        """
        Test modifying an event's note with invalid data (empty string).
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Some note")
        data = {"notes": ""}  # Notes can be blank

        with self.login(user):
            response = self.post("trips:note-modify", event_id=event.pk, data=data)

        self.response_200(response)
        event.refresh_from_db()
        assert event.notes == "Some note"


class NoteDeleteView(TestCase):
    def test_note_delete_success(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip, notes="Some note")

        with self.login(user):
            response = self.post("trips:note-delete", event_id=event.pk)

        self.response_204(response)
        event.refresh_from_db()
        assert event.notes == ""


class StayNoteCreateView(TestCase):
    def test_stay_note_create_success(self):
        """
        Test successful creation of a note for a stay.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="")
        stay.save()
        stay.days.set(days)
        data = {"notes": "This is a test stay note."}

        with self.login(user):
            response = self.post("trips:stay-note-create", stay_id=stay.pk, data=data)

        self.response_204(response)
        stay.refresh_from_db()
        assert stay.notes == data["notes"]

    def test_stay_note_create_invalid_data(self):
        """
        Test stay note creation with invalid data: send a value that is too long for the notes field.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="")
        stay.save()
        stay.days.set(days)
        # Assuming notes field has max_length=500
        data = {"notes": "a" * 1001}  # Exceeds max_length

        with self.login(user):
            response = self.post("trips:stay-note-create", stay_id=stay.pk, data=data)

        assert response.status_code == 400
        stay.refresh_from_db()
        assert stay.notes == ""


class StayNoteModifyView(TestCase):
    def test_stay_note_modify_success(self):
        """
        Test successful modification of a note for a stay.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Original stay note")
        stay.save()
        stay.days.set(days)
        data = {"notes": "Updated stay note content."}

        with self.login(user):
            response = self.post("trips:stay-note-modify", stay_id=stay.pk, data=data)

        self.response_200(response)
        stay.refresh_from_db()
        assert stay.notes == data["notes"]

    def test_stay_note_modify_invalid_data(self):
        """
        Test modification of a stay note with invalid data: send a value that is too long for the notes field.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Original stay note")
        stay.save()
        stay.days.set(days)
        # Assuming notes field has max_length=500
        data = {"notes": "a" * 1001}  # Exceeds max_length

        with self.login(user):
            response = self.post("trips:stay-note-modify", stay_id=stay.pk, data=data)

        assert response.status_code == 200  # Form should be invalid and re-rendered
        stay.refresh_from_db()
        assert stay.notes == "Original stay note"


class StayNoteDeleteView(TestCase):
    def test_stay_note_delete_success(self):
        """
        Test successful deletion of a note for a stay.
        """
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = trip.days.all()
        stay = StayFactory(notes="Note to delete")
        stay.save()
        stay.days.set(days)

        with self.login(user):
            response = self.post("trips:stay-note-delete", stay_id=stay.pk)

        self.response_204(response)
        stay.refresh_from_db()
        assert stay.notes == ""

    def test_stay_note_delete_not_found(self):
        """
        Test deletion of a note for a non-existent stay returns 404.
        """
        user = self.make_user("user")
        with self.login(user):
            response = self.post("trips:stay-note-delete", stay_id=99999)
        self.response_404(response)


class RateLimitCheckTests(TestCase):
    def test_rate_limit_check_waits_if_called_too_soon(self):
        """Should sleep if called within 1 second of last request."""

        from trips.utils import rate_limit_check

        cache.set("nominatim_last_request_time", time.time(), 60)
        start = time.time()
        rate_limit_check()
        elapsed = time.time() - start
        assert elapsed >= 0.99  # Should wait at least ~1 second

    def test_rate_limit_check_no_wait_if_enough_time_passed(self):
        """Should not sleep if more than 1 second has passed since last request."""

        from trips.utils import rate_limit_check

        cache.set("nominatim_last_request_time", time.time() - 2, 60)
        start = time.time()
        rate_limit_check()
        elapsed = time.time() - start
        assert elapsed < 0.5  # Should not wait


class GenerateCacheKeyTests(TestCase):
    def test_generate_cache_key_basic(self):
        key = generate_cache_key("Hotel Milano", "Milan")
        assert key.startswith("geocode_")
        assert len(key) < 100  # Should not be excessively long

    def test_generate_cache_key_empty(self):
        key = generate_cache_key("", "")
        assert key.startswith("geocode_")
        assert len(key) < 100  # Should not be excessively long


class GeocodeLocationTests(TestCase):
    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_sorted_addresses(self, mock_get):
        from trips.utils import geocode_location

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "address": {"road": "Via Roma", "city": "Rome"},
                "lat": "41.9028",
                "lon": "12.4964",
                "importance": 0.7,
                "place_rank": 30,
                "name": "Hotel Roma",
            },
            {
                "address": {"road": "Via Milano", "city": "Milan"},
                "lat": "45.4642",
                "lon": "9.19",
                "importance": 0.9,
                "place_rank": 30,
                "name": "Hotel Milano",
            },
        ]
        addresses = geocode_location("Hotel", "Italy")
        assert len(addresses) == 2
        # Should be sorted by importance descending
        assert addresses[0]["address"].endswith("Milan")
        assert addresses[1]["address"].endswith("Rome")

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_empty_on_no_results(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}
        addresses = geocode_location("Nonexistent", "Nowhere")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("API error")
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_empty_list_response(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []  # Simulate API returns empty list
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    @patch("trips.utils.requests.get")
    def test_geocode_location_non_200_status_code(self, mock_get):
        """Should return [] if API response status code is not 200."""
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = [
            {
                "address": {"road": "Via Roma", "city": "Rome"},
                "lat": "41.9028",
                "lon": "12.4964",
                "importance": 0.7,
                "place_rank": 30,
                "name": "Hotel Roma",
            }
        ]
        addresses = geocode_location("Hotel", "Italy")
        assert addresses == []

    def test_geocode_location_returns_none_if_name_or_city_missing(self):
        assert geocode_location("", "Rome") is None
        assert geocode_location("Hotel", "") is None

    @patch("trips.utils.requests.get")
    def test_geocode_location_returns_cached_result(self, mock_get):
        # Prepare a fake cached result
        cached_result = [
            {
                "address": "Via Roma 1, Rome",
                "lat": 41.9028,
                "lon": 12.4964,
                "importance": 0.7,
                "place_rank": 30,
            }
        ]
        key = generate_cache_key("Hotel Roma", "Rome")
        cache.set(key, cached_result, 60)
        # Should return cached result and not call requests.get
        addresses = geocode_location("Hotel Roma", "Rome")
        assert addresses == cached_result
        assert not mock_get.called


class GeocodeLocationAddressFormatTests(TestCase):
    def test_address_format_with_only_street_and_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"road": "Via Milano", "city": "Milan"},
                    "lat": "45.4642",
                    "lon": "9.19",
                    "importance": 0.9,
                    "place_rank": 30,
                    "name": "Hotel Milano",
                }
            ]
            addresses = geocode_location("Hotel Milano", "Milan")
            assert addresses[0]["address"] == "Via Milano, Milan"

    def test_address_format_with_street_housenumber_and_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {
                        "road": "Via Roma",
                        "house_number": "1",
                        "city": "Rome",
                    },
                    "lat": "41.9028",
                    "lon": "12.4964",
                    "importance": 0.7,
                    "place_rank": 30,
                    "name": "Hotel Roma",
                }
            ]
            addresses = geocode_location("Hotel Roma", "Rome")
            assert addresses[0]["address"] == "Via Roma 1, Rome"

    def test_address_format_with_only_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"city": "Naples"},
                    "lat": "40.8522",
                    "lon": "14.2681",
                    "importance": 0.5,
                    "place_rank": 30,
                    "name": "Napoli",
                }
            ]
            addresses = geocode_location("Napoli", "Naples")
            assert addresses[0]["address"] == "Naples"

    def test_address_format_with_street_housenumber_no_city(self):
        with patch("trips.utils.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {
                    "address": {"road": "Via Firenze", "house_number": "22"},
                    "lat": "43.7696",
                    "lon": "11.2558",
                    "importance": 0.6,
                    "place_rank": 30,
                    "name": "Hotel Firenze",
                }
            ]
            addresses = geocode_location("Hotel Firenze", "Firenze")
            assert addresses[0]["address"] == "Via Firenze 22"


class SelectBestResultTests(TestCase):
    def test_select_best_result_returns_none_for_empty(self):
        from trips.utils import select_best_result

        assert select_best_result([], "Hotel", "Rome") is None

    def test_select_best_result_prefers_city_and_name(self):
        from trips.utils import select_best_result

        results = [
            {
                "display_name": "Hotel Roma, Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.5,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
            {
                "display_name": "Hotel Milano, Milan, Italy",
                "address": {"city": "Milan"},
                "importance": 0.9,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
        ]
        best = select_best_result(results, "Hotel Roma", "Rome")
        assert best["address"]["city"] == "Rome"

    def test_select_best_result_penalizes_generic_place(self):
        from trips.utils import select_best_result

        results = [
            {
                "display_name": "Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.8,
                "place_rank": 20,
                "class": "place",
                "type": "city",
            },
            {
                "display_name": "Hotel Roma, Rome, Italy",
                "address": {"city": "Rome"},
                "importance": 0.5,
                "place_rank": 30,
                "class": "tourism",
                "type": "hotel",
            },
        ]
        best = select_best_result(results, "Hotel Roma", "Rome")
        assert best["class"] == "tourism"
        assert best["type"] == "hotel"

    def test_select_best_result_returns_first_if_no_scores(self):
        from trips.utils import select_best_result

        results = [
            {"display_name": "A", "address": {}, "importance": 0.1, "place_rank": 99},
            {"display_name": "B", "address": {}, "importance": 0.1, "place_rank": 99},
        ]
        best = select_best_result(results, "", "")
        assert best == results[0]


class GeocodeAddressViewTests(TestCase):
    @patch("trips.views.geocode_location")
    def test_geocode_address_post_found(self, mock_geocode_location):
        from django.urls import reverse

        mock_geocode_location.return_value = [
            {
                "name": "Hotel Roma",
                "address": "Via Roma 1, Rome",
                "lat": 41.9,
                "lon": 12.5,
                "importance": 0.9,
                "place_rank": 30,
            }
        ]
        response = self.client.post(
            reverse("trips:geocode-address"), {"name": "Hotel Roma", "city": "Rome"}
        )
        assert response.status_code == 200
        assert b"Hotel Roma" in response.content
        assert b"Via Roma 1, Rome" in response.content

    @patch("trips.views.geocode_location")
    def test_geocode_address_post_not_found(self, mock_geocode_location):
        from django.urls import reverse

        mock_geocode_location.return_value = []
        response = self.client.post(
            reverse("trips:geocode-address"), {"name": "Hotel Roma", "city": "Rome"}
        )
        assert response.status_code == 200
        assert (
            b"No address found" in response.content or b"found" not in response.content
        )

    def test_geocode_address_post_missing_fields(self):
        from django.urls import reverse

        response = self.client.post(
            reverse("trips:geocode-address"), {"name": "", "city": "Rome"}
        )
        assert response.status_code == 200
        assert (
            b"No address found" in response.content or b"found" not in response.content
        )

    def test_geocode_address_get(self):
        from django.urls import reverse

        response = self.client.get(reverse("trips:geocode-address"))
        assert response.status_code == 200
        assert (
            b"No address found" in response.content or b"found" not in response.content
        )


class DayMapViewTests(TestCase):
    """Test cases for DayMapView"""

    def test_get_day_map_view_success(self):
        """Test successful retrieval of day map view"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(latitude=45.4642, longitude=9.1900)
        day.stay = stay
        day.save()
        EventFactory(name="Event 1", day=day, latitude=45.4642, longitude=9.1900)
        EventFactory(name="Event 2", day=day, latitude=45.4652, longitude=9.1910)

        with self.login(user):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/day-map.html")
        assert response.context["day"] == day
        assert "map" in response.context
        assert response.context["map"] is not None
        assert "folium-map" in response.context["map"]

    def test_get_day_map_view_with_next_day_stay(self):
        """Test day map view with a different stay on the next day."""
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        day1, day2 = trip.days.all()
        stay1 = StayFactory()
        stay2 = StayFactory()
        day1.stay = stay1
        day1.save()
        day2.stay = stay2
        day2.save()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day1.pk)

        self.response_200(response)
        assert response.context["locations"]["next_day_stay"] == stay2

    def test_get_day_map_view_first_day(self):
        """Test day map view for the first day of a stay."""
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        day1, day2 = trip.days.all()
        stay = StayFactory()
        day2.stay = stay
        day2.save()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day2.pk)

        self.response_200(response)
        assert response.context["locations"]["first_day"] is True

    def test_get_day_map_view_not_first_day(self):
        """Test day map view for a day that is not the first day of a stay."""
        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        day1, day2 = trip.days.all()
        stay = StayFactory()
        day1.stay = stay
        day1.save()
        day2.stay = stay
        day2.save()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day2.pk)

        self.response_200(response)
        assert "first_day" not in response.context["locations"]

    def test_get_day_map_view_no_events(self):
        """Test day map view with no events"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/day-map.html")
        assert response.context["day"] == day
        assert response.context["map"] is None

    def test_get_day_map_view_events_no_location(self):
        """Test day map view with events that have no location"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        EventFactory(day=day, latitude=None, longitude=None)

        with self.login(user):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/day-map.html")
        assert response.context["day"] == day

    def test_get_day_map_view_not_found(self):
        """Test 404 response for non-existent day"""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:day-map", day_id=99999)

        self.response_404(response)

    def test_get_day_map_view_unauthenticated(self):
        """Test that unauthenticated users are redirected to login"""
        trip = TripFactory()
        day = trip.days.first()
        response = self.get("trips:day-map", day_id=day.pk)
        self.response_302(response)
        assert "/login/" in response.url

    def test_get_day_map_view_unauthorized(self):
        """Test that users cannot access other users' day maps"""
        user1 = self.make_user("user1")
        trip = TripFactory(author=user1)
        day = trip.days.first()

        user2 = self.make_user("user2")
        with self.login(user2):
            response = self.get("trips:day-map", day_id=day.pk)

        self.response_404(response)


class SingleEventViewTest(TestCase):
    """Test cases for single_event view"""

    def test_get_single_event_success(self):
        """Test successful retrieval of a single event"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, trip=trip)

        with self.login(user):
            response = self.get("trips:single-event", pk=event.pk)

        self.response_200(response)
        assert response.context["event"] == event


@patch("trips.views.requests.get")
@patch("trips.views.requests.post")
class EnrichEventViewTest(TestCase):
    """Test cases for enrich_event view"""

    def test_enrich_event_success(self, mock_post, mock_get):
        """Test successful enrichment of an event - returns preview"""
        # Mock Google Places API responses
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            "regularOpeningHours": {
                "periods": [
                    {
                        "open": {"day": 1, "hour": 9, "minute": 0},
                        "close": {"day": 1, "hour": 17, "minute": 0},
                    }
                ]
            },
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        # Event should NOT be saved yet (preview mode)
        event.refresh_from_db()
        assert event.place_id == ""
        assert event.enriched is False
        # Check that enriched_data is in context for preview
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["place_id"] == "test_place_id"
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert "monday" in response.context["enriched_data"]["opening_hours"]
        assert response.context["show_preview"] is True

    def test_enrich_event_success_no_opening_hours(self, mock_post, mock_get):
        """Test successful enrichment without opening hours"""
        # Mock Google Places API responses without opening hours
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            # No regularOpeningHours
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        # Check that enriched_data is in context without opening_hours
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert response.context["enriched_data"]["opening_hours"] is None
        assert "opening_hours_json" not in response.context["enriched_data"]
        assert response.context["show_preview"] is True

    def test_enrich_event_no_name_or_address(self, mock_post, mock_get):
        """Test enrichment with no name or address"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(day=day, trip=trip, name="", address="")

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert (
            response.context["error_message"]
            == "Event must have a name and an address to be enriched."
        )

    def test_enrich_event_no_api_key(self, mock_post, mock_get):
        """Test enrichment with no API key"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY=""):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API key is not configured."
            in response.context["error_message"]
        )

    def test_enrich_event_search_request_fails(self, mock_post, mock_get):
        """Test enrichment when search request fails"""
        mock_post.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_event_search_request_fails_with_response(self, mock_post, mock_get):
        """Test enrichment when search request fails with a response"""
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_post.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_event_no_place_found(self, mock_post, mock_get):
        """Test enrichment when no place is found"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": []}

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "Could not find a matching place." in response.context["error_message"]

    def test_enrich_event_details_request_fails(self, mock_post, mock_get):
        """Test enrichment when details request fails"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_event_details_request_fails_with_response(
        self, mock_post, mock_get
    ):
        """Test enrichment when details request fails with a response"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_get.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_event_search_timeout(self, mock_post, mock_get):
        """Test enrichment when search request times out"""
        mock_post.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )

    def test_enrich_event_details_timeout(self, mock_post, mock_get):
        """Test enrichment when details request times out"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-event", event_id=event.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )


class ConfirmEnrichEventViewTest(TestCase):
    """Test cases for confirm_enrich_event view"""

    def test_confirm_enrich_event_success(self):
        """Test successful confirmation and saving of enriched data"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": '{"monday": {"open": "9:00 AM", "close": "5:00 PM"}}',
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should return 200 with event detail view and HX-Trigger header
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == f"eventModified{event.pk}"
        assert "success_message" in response.context
        assert response.context["success_message"] == "Event enriched successfully!"

        # Event should be saved with enriched data
        event.refresh_from_db()
        assert event.place_id == "test_place_id"
        assert event.website == "https://example.com"
        assert event.phone_number == "+1234567890"
        assert event.opening_hours == {
            "monday": {"open": "9:00 AM", "close": "5:00 PM"}
        }
        assert event.enriched is True

    def test_confirm_enrich_event_no_opening_hours(self):
        """Test confirmation without opening_hours"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            # No opening_hours field
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == f"eventModified{event.pk}"
        event.refresh_from_db()
        assert event.place_id == "test_place_id"
        assert event.website == "https://example.com"
        assert event.phone_number == "+1234567890"
        assert event.opening_hours is None
        assert event.enriched is True

    def test_confirm_enrich_event_invalid_json(self):
        """Test confirmation with invalid opening_hours JSON"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": "invalid json",
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should still save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == f"eventModified{event.pk}"
        event.refresh_from_db()
        assert event.place_id == "test_place_id"
        assert event.opening_hours is None
        assert event.enriched is True

    def test_confirm_enrich_event_unauthorized(self):
        """Test confirmation by unauthorized user"""
        user = self.make_user("user")
        other_user = self.make_user("other_user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = ExperienceFactory(
            day=day, trip=trip, name="Test Event", address="Test Address"
        )

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
        }

        with self.login(other_user):
            response = self.post(
                "trips:confirm-enrich-event", event_id=event.pk, data=enriched_data
            )

        # Should return 404 for unauthorized access
        self.response_404(response)
        event.refresh_from_db()
        assert event.enriched is False


@patch("trips.views.requests.get")
@patch("trips.views.requests.post")
class EnrichStayViewTest(TestCase):
    """Test cases for enrich_stay view"""

    def test_enrich_stay_success(self, mock_post, mock_get):
        """Test successful enrichment of a stay - returns preview"""
        # Mock Google Places API responses
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            "regularOpeningHours": {
                "periods": [
                    {
                        "open": {"day": 1, "hour": 9, "minute": 0},
                        "close": {"day": 1, "hour": 17, "minute": 0},
                    }
                ]
            },
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        # Stay should NOT be saved yet (preview mode)
        stay.refresh_from_db()
        assert stay.place_id == ""
        assert stay.enriched is False
        # Check that enriched_data is in context for preview
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["place_id"] == "test_place_id"
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert "monday" in response.context["enriched_data"]["opening_hours"]
        assert response.context["show_preview"] is True

    def test_enrich_stay_no_name_or_address(self, mock_post, mock_get):
        """Test enrichment with no name or address"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="", address="")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert (
            response.context["error_message"]
            == "Stay must have a name and an address to be enriched."
        )

    def test_enrich_stay_no_api_key(self, mock_post, mock_get):
        """Test enrichment with no API key"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY=""):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)
        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API key is not configured."
            in response.context["error_message"]
        )

    def test_enrich_stay_search_request_fails(self, mock_post, mock_get):
        """Test enrichment when search request fails"""
        mock_post.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_stay_search_request_fails_with_response(self, mock_post, mock_get):
        """Test enrichment when search request fails with a response"""
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_post.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_stay_no_place_found(self, mock_post, mock_get):
        """Test enrichment when no place is found"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": []}

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "Could not find a matching place." in response.context["error_message"]

    def test_enrich_stay_details_request_fails(self, mock_post, mock_get):
        """Test enrichment when details request fails"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.RequestException("Test error")

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Error calling Google Places API: Test error"
            in response.context["error_message"]
        )

    def test_enrich_stay_details_request_fails_with_response(self, mock_post, mock_get):
        """Test enrichment when details request fails with a response"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        exception = requests.RequestException("Test error")
        exception.response = Mock(text="API error details")
        mock_get.side_effect = exception

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert "API Error: API error details" in response.context["error_message"]

    def test_enrich_stay_search_timeout(self, mock_post, mock_get):
        """Test enrichment when search request times out"""
        mock_post.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )

    def test_enrich_stay_details_timeout(self, mock_post, mock_get):
        """Test enrichment when details request times out"""
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.side_effect = requests.exceptions.Timeout

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        assert "error_message" in response.context
        assert (
            "Google Places API request timed out" in response.context["error_message"]
        )

    def test_enrich_stay_success_no_opening_hours(self, mock_post, mock_get):
        """Test successful enrichment without opening hours"""
        # Mock Google Places API responses without opening hours
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"places": [{"id": "test_place_id"}]}
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = {
            "websiteUri": "https://example.com",
            "internationalPhoneNumber": "+1234567890",
            # No regularOpeningHours
        }

        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        with self.login(user), override_settings(GOOGLE_PLACES_API_KEY="test_key"):
            response = self.post("trips:enrich-stay", stay_id=stay.pk)

        self.response_200(response)
        # Check that enriched_data is in context without opening_hours
        assert "enriched_data" in response.context
        assert response.context["enriched_data"]["website"] == "https://example.com"
        assert response.context["enriched_data"]["phone_number"] == "+1234567890"
        assert response.context["enriched_data"]["opening_hours"] is None
        assert "opening_hours_json" not in response.context["enriched_data"]
        assert response.context["show_preview"] is True


class ConfirmEnrichStayViewTest(TestCase):
    """Test cases for confirm_enrich_stay view"""

    def test_confirm_enrich_stay_success(self):
        """Test successful confirmation and saving of enriched data"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": '{"monday": {"open": "9:00 AM", "close": "5:00 PM"}}',
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should return 200 with stay detail view and HX-Trigger header
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        # Check that it triggers update for the day
        triggers = json.loads(response.headers["HX-Trigger"])
        assert f"dayModified{day.pk}" in triggers
        assert "success_message" in response.context
        assert response.context["success_message"] == "Stay enriched successfully!"

        # Stay should be saved with enriched data
        stay.refresh_from_db()
        assert stay.place_id == "test_place_id"
        assert stay.website == "https://example.com"
        assert stay.phone_number == "+1234567890"
        assert stay.opening_hours == {"monday": {"open": "9:00 AM", "close": "5:00 PM"}}
        assert stay.enriched is True

    def test_confirm_enrich_stay_no_opening_hours(self):
        """Test confirmation without opening_hours"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            # No opening_hours field
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        # Check that it triggers update for the day
        triggers = json.loads(response.headers["HX-Trigger"])
        assert f"dayModified{day.pk}" in triggers
        stay.refresh_from_db()
        assert stay.place_id == "test_place_id"
        assert stay.website == "https://example.com"
        assert stay.phone_number == "+1234567890"
        assert stay.opening_hours is None
        assert stay.enriched is True

    def test_confirm_enrich_stay_invalid_json(self):
        """Test confirmation with invalid opening_hours JSON"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
            "phone_number": "+1234567890",
            "opening_hours": "invalid json",
        }

        with self.login(user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should still save successfully, opening_hours will be None
        self.response_200(response)
        assert "HX-Trigger" in response.headers
        # Check that it triggers update for the day
        triggers = json.loads(response.headers["HX-Trigger"])
        assert f"dayModified{day.pk}" in triggers
        stay.refresh_from_db()
        assert stay.place_id == "test_place_id"
        assert stay.opening_hours is None
        assert stay.enriched is True

    def test_confirm_enrich_stay_unauthorized(self):
        """Test confirmation by unauthorized user"""
        user = self.make_user("user")
        other_user = self.make_user("other_user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Test Stay", address="Test Address")
        stay.days.add(day)

        enriched_data = {
            "place_id": "test_place_id",
            "website": "https://example.com",
        }

        with self.login(other_user):
            response = self.post(
                "trips:confirm-enrich-stay", stay_id=stay.pk, data=enriched_data
            )

        # Should return 404 for unauthorized access
        self.response_404(response)
        stay.refresh_from_db()
        assert stay.enriched is False


class TestGetTripAddresses(TestCase):
    def test_get_trip_addresses_with_events(self):
        """Test fetching addresses from trip events."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        ExperienceFactory(
            day=day, trip=trip, name="Museum", address="123 Main St", city="Roma"
        )

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/trip-address-results.html")
        content = str(response.content)
        assert "Museum" in content
        assert "123 Main St" in content
        assert (
            "Experiences &amp; Restaurants" in content
            or "Experiences & Restaurants" in content
        )

    def test_get_trip_addresses_with_stays(self):
        """Test fetching addresses from trip stays."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        stay = StayFactory(name="Hotel Roma", address="456 Via Roma", city="Roma")
        day.stay = stay
        day.save()

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "destination"},
            )

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/trip-address-results.html")
        content = str(response.content)
        assert "Hotel Roma" in content
        assert "456 Via Roma" in content
        assert "Hotels &amp; Stays" in content or "Hotels & Stays" in content

    def test_get_trip_addresses_mixed(self):
        """Test fetching addresses from both events and stays."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Add an event
        ExperienceFactory(
            day=day, trip=trip, name="Restaurant", address="789 Food St", city="Milano"
        )

        # Add a stay
        stay = StayFactory(name="Hotel Milano", address="101 Sleep Ave", city="Milano")
        day.stay = stay
        day.save()

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        content = str(response.content)
        # Check both sections are present
        assert "Hotels &amp; Stays" in content or "Hotels & Stays" in content
        assert (
            "Experiences &amp; Restaurants" in content
            or "Experiences & Restaurants" in content
        )
        # Check content
        assert "Restaurant" in content
        assert "789 Food St" in content
        assert "Hotel Milano" in content
        assert "101 Sleep Ave" in content

    def test_get_trip_addresses_no_addresses(self):
        """Test when trip has no addresses."""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        # Should return empty content when not found
        content = response.content.decode().strip()
        assert content == "" or "No addresses found" in content

    def test_get_trip_addresses_unauthorized(self):
        """Test unauthorized access to another user's trip."""
        user = self.make_user("user")
        other_user = self.make_user("other_user")
        trip = TripFactory(author=user)

        with self.login(other_user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_404(response)

    def test_get_trip_addresses_no_trip_id(self):
        """Test when no trip_id is provided."""
        user = self.make_user("user")

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses", data={"field_type": "origin"}
            )

        self.response_200(response)
        # Should return empty content when not found
        content = response.content.decode().strip()
        assert content == "" or "No addresses found" in content

    def test_get_trip_addresses_excludes_empty_addresses(self):
        """Test that events/stays with empty addresses are excluded."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Event with address
        ExperienceFactory(
            day=day, trip=trip, name="Museum", address="123 Main St", city="Roma"
        )

        # Event without address
        ExperienceFactory(day=day, trip=trip, name="Park", address="", city="")

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        content = str(response.content)
        assert "Museum" in content
        assert "Park" not in content

    def test_get_trip_addresses_get_request(self):
        """Test GET request returns empty result."""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:get-trip-addresses")

        self.response_200(response)
        # Should return empty content when not found
        content = response.content.decode().strip()
        assert content == "" or "No addresses found" in content

    def test_get_trip_addresses_excludes_transports(self):
        """Test that Transport events are excluded from suggestions."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Add an Experience
        ExperienceFactory(
            day=day, trip=trip, name="Museum Visit", address="123 Art St", city="Roma"
        )

        # Add a Transport (should be excluded)
        transport = TransportFactory(
            day=day,
            trip=trip,
            origin_city="Roma",
            origin_address="456 Station Rd",
        )

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        content = str(response.content)
        # Experience should be in results
        assert "Museum Visit" in content
        # Transport should NOT be in results
        assert transport.name not in content

    def test_get_trip_addresses_all_events_shown(self):
        """Test that all events are shown without pagination."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Create 10 events
        for i in range(10):
            ExperienceFactory(
                day=day,
                trip=trip,
                name=f"Event {i}",
                address=f"{i} Street",
                city="Roma",
            )

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/trip-address-results.html")
        content = str(response.content)

        # All 10 events should be present
        for i in range(10):
            assert f"Event {i}" in content

        # No "Show more" button should be present
        assert "Show more" not in content

    def test_get_trip_addresses_stays_always_shown_in_full(self):
        """Test that all stays are shown."""
        user = self.make_user("user")
        # Create trip with enough days
        start_date = timezone.now().date()
        end_date = start_date + timezone.timedelta(days=7)
        trip = TripFactory(author=user, start_date=start_date, end_date=end_date)

        # Create 7 unique stays across different days
        days = list(trip.days.all()[:7])
        for i, day in enumerate(days):
            stay = StayFactory(name=f"Hotel {i}", address=f"{i} Hotel St", city="Roma")
            day.stay = stay
            day.save()

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        content = str(response.content)

        # All stays should be present
        for i in range(len(days)):
            assert f"Hotel {i}" in content

    def test_get_trip_addresses_stays_before_events(self):
        """Test that stays section appears before events section."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        # Add a stay
        stay = StayFactory(name="Hotel First", address="1 Hotel St", city="Roma")
        day.stay = stay
        day.save()

        # Add an event
        ExperienceFactory(
            day=day, trip=trip, name="Event Second", address="2 Event St", city="Roma"
        )

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        content = str(response.content)

        # Find positions of stays and events sections
        stays_pos = content.find("Hotels")
        events_pos = content.find("Experiences")

        # Stays section should come before events section
        assert stays_pos < events_pos
        assert events_pos > 0  # Make sure events section was found

    def test_get_trip_addresses_deduplicates_events(self):
        """Test that duplicate events are only shown once."""
        user = self.make_user("user")
        trip = TripFactory(author=user)

        # Create multiple days
        start_date = timezone.now().date()
        end_date = start_date + timezone.timedelta(days=3)
        trip.start_date = start_date
        trip.end_date = end_date
        trip.save()

        days = list(trip.days.all()[:3])

        # Add the same event on multiple days
        for day in days:
            ExperienceFactory(
                day=day,
                trip=trip,
                name="Colosseum Tour",
                address="Piazza del Colosseo",
                city="Roma",
            )

        # Add a different event to ensure there are multiple events
        ExperienceFactory(
            day=days[0],
            trip=trip,
            name="Vatican Museum",
            address="Viale Vaticano",
            city="Roma",
        )

        with self.login(user):
            response = self.post(
                "trips:get-trip-addresses",
                data={"trip_id": trip.pk, "field_type": "origin"},
            )

        self.response_200(response)
        content = str(response.content)

        # Count occurrences of "Colosseum Tour" - should appear only once
        colosseum_count = content.count("Colosseum Tour")
        assert colosseum_count == 1, (
            f"Expected 1 occurrence of 'Colosseum Tour', found {colosseum_count}"
        )

        # Vatican Museum should also appear
        assert "Vatican Museum" in content
