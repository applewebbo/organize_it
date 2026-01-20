import datetime
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import time_machine
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    StayFactory,
    TripFactory,
)

pytestmark = pytest.mark.django_db


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

    @time_machine.travel("2026-01-15")
    def test_get_with_latest_trip(self):
        user = self.make_user("user")
        # With time frozen at 2026-01-15, create trips with specific statuses
        trip1 = TripFactory(
            author=user,
            status=1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 10),
        )  # NOT_STARTED (in future)
        trip2 = TripFactory(
            author=user,
            status=3,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 20),
        )  # IN_PROGRESS (includes today)

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

    def test_get_authenticated_user_without_trips_shows_empty_state(self):
        """Test that authenticated user without trips sees empty state and quick guide"""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        # Verify context shows no trips
        assert response.context["latest_trip"] is None
        assert response.context["fav_trip"] is None
        assert len(response.context["other_trips"]) == 0

        # Verify empty state content is present
        content = response.content.decode()
        assert (
            "Ready for your next adventure?" in content
            or "Pronto per la tua prossima avventura?" in content
        )
        assert (
            "Create Your First Trip" in content
            or "Crea il Tuo Primo Viaggio" in content
        )

        # Verify quick guide sections are present
        assert "How It Works" in content or "Come Funziona" in content
        assert "Trips" in content or "Viaggi" in content
        assert "Days" in content or "Giorni" in content
        assert "Stays" in content or "Soggiorni" in content
        assert "Experiences" in content or "Esperienze" in content
        assert "Meals" in content or "Pasti" in content

    def test_empty_state_cta_button_redirects_to_trip_creation(self):
        """Test that the CTA button in empty state links to trip creation"""
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        content = response.content.decode()
        trip_create_url = reverse("trips:trip-create")
        assert trip_create_url in content

    def test_authenticated_user_with_trips_hides_guide_by_default(self):
        """Test that guide is hidden by default for users with trips"""
        user = self.make_user("user")
        TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert response.context["show_guide"] is False
        content = response.content.decode()
        # Guide should not be visible
        assert "How It Works" not in content and "Come Funziona" not in content

    def test_toggle_guide_view(self):
        """Test that toggle guide view changes session state"""
        user = self.make_user("user")
        TripFactory(author=user)

        with self.login(user):
            # Initially guide is hidden (False)
            session = self.client.session
            assert session.get("show_guide", False) is False

            # Toggle to show guide
            response = self.post("trips:toggle-guide")
            self.response_204(response)

            # Check session state changed
            session = self.client.session
            assert session.get("show_guide") is True

            # Toggle again to hide guide
            response = self.post("trips:toggle-guide")
            self.response_204(response)

            # Check session state changed back
            session = self.client.session
            assert session.get("show_guide") is False

    def test_guide_visibility_respects_session_state(self):
        """Test that guide visibility changes based on session state"""
        user = self.make_user("user")
        TripFactory(author=user)

        with self.login(user):
            # Set session to show guide
            session = self.client.session
            session["show_guide"] = True
            session.save()

            # Get home page
            response = self.get("trips:home")

            self.response_200(response)
            assert response.context["show_guide"] is True
            content = response.content.decode()
            # Guide should be visible
            assert "How It Works" in content or "Come Funziona" in content

    def test_toggle_guide_with_get_request(self):
        """Test that toggle guide with GET request returns 204 without changing state"""
        user = self.make_user("user")
        TripFactory(author=user)

        with self.login(user):
            # Set initial state
            session = self.client.session
            session["show_guide"] = False
            session.save()

            # GET request should return 204 but not change state
            response = self.get("trips:toggle-guide")
            self.response_204(response)

            # State should remain unchanged
            session = self.client.session
            assert session.get("show_guide", False) is False


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

    def test_get_day_detail_map_with_departure_transfer(self):
        """Test day detail map view includes departure transfer on last day"""
        from trips.models import MainTransfer

        user = self.make_user("user")
        user.profile.default_map_view = "map"
        user.profile.save()
        trip = TripFactory(
            author=user,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
        )
        last_day = trip.days.last()
        stay = StayFactory(latitude=45.4773, longitude=9.1815)
        last_day.stay = stay
        last_day.save()

        # Create departure transfer
        departure = MainTransfer.objects.create(
            trip=trip,
            type=MainTransfer.Type.TRAIN,
            direction=MainTransfer.Direction.DEPARTURE,
            origin_name="Milano Centrale",
            origin_code="MIL",
            origin_latitude=45.4842,
            origin_longitude=9.2040,
            destination_name="Roma Termini",
            destination_code="ROM",
            destination_latitude=41.9009,
            destination_longitude=12.5028,
            start_time="15:00",
            end_time="18:30",
        )

        with self.login(user):
            response = self.get("trips:day-detail", pk=last_day.pk)

        self.response_200(response)
        assert response.context["show_map"] is True
        assert "locations" in response.context
        assert response.context["locations"]["departure_transfer"] == departure
        assert response.context["locations"]["last_day"] is True


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
