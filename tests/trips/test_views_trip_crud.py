import datetime
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.template.loader import render_to_string
from django.utils import translation
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import (
    ExpenseFactory,
    ExpenseParticipantFactory,
    ExpenseShareFactory,
    ExperienceFactory,
    LinkFactory,
    MainTransferFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.models import Expense, Trip, TripCollaboration
from trips.views.trips import build_pdf_export_context

pytestmark = pytest.mark.django_db


class TestTripCreateView(TestCase):
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

    @patch("geocoder.mapbox")
    def test_post_with_next_redirects_to_list(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "destination": "Novara",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.client.post(
                self.reverse("trips:trip-create") + "?next=list", data=data
            )

        self.response_204(response)
        assert response.headers.get("HX-Redirect") == self.reverse("trips:trip-list")

    @patch("geocoder.mapbox")
    def test_post_with_coords_updates_days(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        data = {
            "title": "Trip to Novara",
            "destination": "Novara",
            "destination_latitude": "45.4473",
            "destination_longitude": "8.6218",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=2),
        }

        with self.login(user):
            response = self.post("trips:trip-create", data=data)

        self.response_204(response)
        from trips.models import Day

        trip = Trip.objects.filter(author=user).first()
        day = Day.objects.filter(trip=trip).first()
        assert day.destination_latitude == 45.4473

    def test_post_with_invalid_start_date(self):
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "start_date": datetime.date.today() + datetime.timedelta(days=3),
            "end_date": datetime.date.today(),
        }

        with self.login(user):
            response = self.post("trips:trip-create", data=data)

        self.response_200(response)
        assert Trip.objects.filter(author=user).count() == 0


class TestTripDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.delete("trips:trip-delete", pk=trip.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{trip.title}</strong> deleted successfully"
        assert Trip.objects.filter(author=user).count() == 0

    def test_delete_trip_with_expenses(self):
        """A trip carrying expenses deletes without ProtectedError (#410)."""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        participant = ExpenseParticipantFactory(trip=trip)
        expense = ExpenseFactory(trip=trip, payer=participant)
        ExpenseShareFactory(expense=expense, participant=participant)

        with self.login(user):
            response = self.delete("trips:trip-delete", pk=trip.pk)

        self.response_204(response)
        assert Trip.objects.filter(pk=trip.pk).count() == 0
        assert Expense.objects.filter(pk=expense.pk).count() == 0


class TestTripUpdateView(TestCase):
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

    @patch("geocoder.mapbox")
    def test_post_with_coords_updates_days(self, mock_geocoder):
        mock_geocoder.return_value.ok = True
        mock_geocoder.return_value.latlng = [45.4773, 9.1815]
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Trip to Novara",
            "destination": "Novara",
            "destination_latitude": "45.4473",
            "destination_longitude": "8.6218",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=2),
        }

        with self.login(user):
            response = self.post("trips:trip-update", pk=trip.pk, data=data)

        self.response_204(response)
        from trips.models import Day

        day = Day.objects.filter(trip=trip).first()
        assert day.destination_latitude == 45.4473

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Trip to Paris",
        }

        with self.login(user):
            response = self.post("trips:trip-update", pk=trip.pk, data=data)

        self.response_200(response)


class TestTripArchiveView(TestCase):
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


class TestTripUnarchiveView(TestCase):
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


class TestTripDestinationsView(TestCase):
    def test_get_modal(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-destinations", trip_pk=trip.pk)

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/trip-destinations-modal.html")

    def test_get_modal_main_stage_is_last(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.order_by("number"))
        days[0].destination = f"NOT_{trip.destination}"
        days[0].save()

        with self.login(user):
            response = self.get("trips:trip-destinations", trip_pk=trip.pk)

        stages = response.context["stages"]
        assert stages[-1]["is_main"] is True

    def test_get_modal_forbidden_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)

        with self.login(other):
            response = self.get("trips:trip-destinations", trip_pk=trip.pk)

        self.response_404(response)


class TestUpdateDayDestinationView(TestCase):
    def test_post_updates_destination(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.post(
                "trips:update-day-destination",
                trip_pk=trip.pk,
                day_pk=day.pk,
                data={"destination": "Firenze"},
            )

        self.response_204(response)
        day.refresh_from_db()
        assert day.destination == "Firenze"

    def test_post_forbidden_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        day = trip.days.first()

        with self.login(other):
            response = self.post(
                "trips:update-day-destination",
                trip_pk=trip.pk,
                day_pk=day.pk,
                data={"destination": "Firenze"},
            )

        self.response_404(response)

    def test_get_returns_card(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.get(
                "trips:update-day-destination",
                trip_pk=trip.pk,
                day_pk=day.pk,
            )

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/day-destination-card.html")


class TestCreateStageView(TestCase):
    def test_get_returns_create_stage_modal(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:create-stage", trip_pk=trip.pk)

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/create-stage-modal.html")

    def test_get_forbidden_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)

        with self.login(other):
            response = self.get("trips:create-stage", trip_pk=trip.pk)

        self.response_404(response)

    def test_post_updates_day_destinations(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze", "days": [str(day.pk)]},
            )

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/trip-destinations-modal.html")
        assert response.headers.get("HX-Trigger") == "destinationModified"
        day.refresh_from_db()
        assert day.destination == "Firenze"

    def test_post_ignores_already_custom_days(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.order_by("number"))
        existing_custom = f"NOT_{trip.destination}"
        days[0].destination = existing_custom
        days[0].save()

        with self.login(user):
            response = self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": f"OTHER_{trip.destination}",
                    "days": [str(days[0].pk)],
                },
            )

        self.response_200(response)
        days[0].refresh_from_db()
        assert days[0].destination == existing_custom

    def test_post_without_destination_does_not_update(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            response = self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={"destination": "", "days": [str(day.pk)]},
            )

        self.response_200(response)
        day.refresh_from_db()
        assert day.destination == trip.destination or day.destination == ""

    def test_post_creates_stage_for_non_first_day(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.order_by("number"))
        target_day = days[1]

        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": f"NOT_{trip.destination}",
                    "days": [str(target_day.pk)],
                },
            )

        target_day.refresh_from_db()
        assert target_day.destination == f"NOT_{trip.destination}"

    def test_post_forbidden_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        day = trip.days.first()

        with self.login(other):
            response = self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze", "days": [str(day.pk)]},
            )

        self.response_404(response)

    def test_post_saves_destination_coords_when_provided(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": "Firenze",
                    "destination_latitude": "43.7697",
                    "destination_longitude": "11.2556",
                    "days": [str(day.pk)],
                },
            )

        day.refresh_from_db()
        assert day.destination == "Firenze"
        assert day.destination_latitude == 43.7697
        assert day.destination_longitude == 11.2556

    def test_post_ignores_invalid_coords(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()

        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": "Firenze",
                    "destination_latitude": "not-a-number",
                    "destination_longitude": "also-invalid",
                    "days": [str(day.pk)],
                },
            )

        day.refresh_from_db()
        assert day.destination == "Firenze"
        assert day.destination_latitude is None
        assert day.destination_longitude is None

    def test_get_shows_all_days_including_last(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.order_by("number"))
        last_day = days[-1]

        with self.login(user):
            response = self.get("trips:create-stage", trip_pk=trip.pk)

        self.response_200(response)
        context_days = response.context["days"]
        assert last_day in context_days

    def test_post_can_assign_last_day_to_custom_stage(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        last_day = trip.days.order_by("number").last()

        with self.login(user):
            self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": f"NOT_{trip.destination}",
                    "days": [str(last_day.pk)],
                },
            )

        last_day.refresh_from_db()
        assert last_day.destination == f"NOT_{trip.destination}"

    def test_post_enqueues_transfer_for_day_after_stage(self):
        """When a new stage borders another stage, the day after it is also re-queued."""
        from datetime import date, timedelta

        from trips.models import Day

        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=3),
        )
        days = list(trip.days.order_by("number"))
        # Assign last day to a pre-existing stage
        Day.objects.filter(pk=days[-1].pk).update(destination="OtherCity")

        with self.login(user):
            response = self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": "MidCity",
                    "days": [str(days[1].pk)],
                },
            )

        self.response_200(response)
        days[1].refresh_from_db()
        assert days[1].destination == "MidCity"

    def test_post_no_next_day_after_last_stage(self):
        """Stage assigned to the last day — no day after it to re-queue."""
        from datetime import date, timedelta

        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )
        days = list(trip.days.order_by("number"))
        last_day = days[-1]

        with self.login(user):
            response = self.post(
                "trips:create-stage",
                trip_pk=trip.pk,
                data={
                    "destination": "LastCity",
                    "days": [str(last_day.pk)],
                },
            )

        self.response_200(response)
        last_day.refresh_from_db()
        assert last_day.destination == "LastCity"


class TestDeleteStageView(TestCase):
    def test_post_resets_days_to_trip_destination(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        custom_dest = f"NOT_{trip.destination}"
        day.destination = custom_dest
        day.save()

        with self.login(user):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": custom_dest},
            )

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/trip-destinations-modal.html")
        assert response.headers.get("HX-Trigger") == "destinationModified"
        day.refresh_from_db()
        assert day.destination == trip.destination

    def test_post_unpairs_events(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        custom_dest = f"NOT_{trip.destination}"
        day.destination = custom_dest
        day.save()
        event = ExperienceFactory(trip=trip, day=day)

        with self.login(user):
            self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": custom_dest},
            )

        event.refresh_from_db()
        assert event.day is None

    def test_post_ignores_main_destination(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        original_dest = day.destination

        with self.login(user):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": trip.destination},
            )

        self.response_200(response)
        day.refresh_from_db()
        assert day.destination == original_dest

    def test_post_resets_transfer_fields_immediately(self):
        from trips.models import Day

        user = self.make_user("user")
        trip = TripFactory(author=user)
        days = list(trip.days.order_by("number"))
        custom_dest = f"NOT_{trip.destination}"
        days[1].destination = custom_dest
        days[1].save()
        Day.objects.filter(pk=days[1].pk).update(
            transfer_duration_from_prev=60, transfer_distance_from_prev=100
        )

        with self.login(user):
            self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": custom_dest},
            )

        days[1].refresh_from_db()
        assert days[1].destination == trip.destination
        assert days[1].transfer_duration_from_prev is None
        assert days[1].transfer_distance_from_prev is None

    def test_post_no_next_stage_after_last_deleted(self):
        """Deleting the last stage — no next day exists, no crash."""
        from datetime import date, timedelta

        user = self.make_user("user")
        trip = TripFactory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )
        days = list(trip.days.order_by("number"))
        custom_dest = f"NOT_{trip.destination}"
        days[-1].destination = custom_dest
        days[-1].save()

        with self.login(user):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": custom_dest},
            )

        self.response_200(response)
        days[-1].refresh_from_db()
        assert days[-1].destination == trip.destination

    def test_get_returns_step1_modal(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:delete-stage", trip_pk=trip.pk)

        self.response_200(response)
        self.assertTemplateUsed(response, "trips/includes/trip-destinations-modal.html")

    def test_post_forbidden_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)

        with self.login(other):
            response = self.post(
                "trips:delete-stage",
                trip_pk=trip.pk,
                data={"destination": "Firenze"},
            )

        self.response_404(response)


class TestExportTripPdfView(TestCase):
    def test_owner_gets_pdf_response(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-export-pdf", pk=trip.pk)

        self.response_200(response)
        assert response["Content-Type"] == "application/pdf"
        assert "attachment" in response["Content-Disposition"]

    def test_collaborator_gets_pdf_response(self):
        owner = self.make_user("owner")
        collaborator = self.make_user("collaborator")
        trip = TripFactory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collaborator, color="blue", added_by=owner
        )

        with self.login(collaborator):
            response = self.get("trips:trip-export-pdf", pk=trip.pk)

        self.response_200(response)
        assert response["Content-Type"] == "application/pdf"

    def test_non_member_gets_404(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)

        with self.login(other):
            response = self.get("trips:trip-export-pdf", pk=trip.pk)

        self.response_404(response)

    def test_unauthenticated_redirects(self):
        trip = TripFactory()
        response = self.get("trips:trip-export-pdf", pk=trip.pk)
        self.response_302(response)

    def test_trip_with_stay_sets_show_stay(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        stay = StayFactory()
        day = trip.days.first()
        day.stay = stay
        day.save()

        with self.login(user):
            response = self.get("trips:trip-export-pdf", pk=trip.pk)

        self.response_200(response)
        assert response["Content-Type"] == "application/pdf"

    def test_context_includes_summary_counts(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        ExperienceFactory(trip=trip, day=day)
        MealFactory(trip=trip, day=day)
        stay = StayFactory()
        day.stay = stay
        day.save()
        trip.links.add(LinkFactory(author=user))

        context = build_pdf_export_context(trip)

        summary = context["summary"]
        assert summary["days"] == trip.days.count()
        assert summary["events"] == 2
        assert summary["stays"] == 1
        assert summary["links"] == 1

    def test_context_summary_empty_trip(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        context = build_pdf_export_context(trip)

        summary = context["summary"]
        assert summary["events"] == 0
        assert summary["stays"] == 0
        assert summary["links"] == 0

    def test_trip_image_resolved_as_absolute_file_url(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        user = self.make_user("user")
        trip = TripFactory(author=user)
        trip.image = SimpleUploadedFile(
            "cover.jpg", b"fakejpegbytes", content_type="image/jpeg"
        )
        trip.save()

        context = build_pdf_export_context(trip)

        assert context["trip_image_url"].startswith("file://")
        assert context["trip_image_url"].endswith(trip.image.name)

    def test_trip_image_falls_back_to_url_when_path_not_supported(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        user = self.make_user("user")
        trip = TripFactory(author=user)
        trip.image = SimpleUploadedFile(
            "cover.jpg", b"fakejpegbytes", content_type="image/jpeg"
        )
        trip.save()

        with patch(
            "django.core.files.storage.FileSystemStorage.path",
            side_effect=NotImplementedError,
        ):
            context = build_pdf_export_context(trip)

        assert context["trip_image_url"] == trip.image.url

    def test_trip_image_absent_returns_none(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        context = build_pdf_export_context(trip)

        assert context["trip_image_url"] is None

    def test_template_renders_main_transfer_details(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        MainTransferFactory(
            trip=trip,
            direction=1,
            type=1,
            origin_name="Bologna Airport",
            destination_name="Venice Marco Polo",
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
        )
        context = build_pdf_export_context(trip)

        html = render_to_string("trips/trip-pdf.html", context)

        assert "Bologna Airport" in html
        assert "Venice Marco Polo" in html
        assert "10:00" in html
        assert "12:00" in html

    def test_template_renders_stay_phone_and_website(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        stay = StayFactory(
            phone_number="+39 0412345678", website="https://hotel.example"
        )
        day = trip.days.first()
        day.stay = stay
        day.save()
        context = build_pdf_export_context(trip)

        html = render_to_string("trips/trip-pdf.html", context)

        assert "+39 0412345678" in html
        assert "hotel.example" in html

    def test_template_uses_active_language_and_page_footer(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        context = build_pdf_export_context(trip)

        with translation.override("it"):
            html = render_to_string("trips/trip-pdf.html", context)

        assert 'lang="it"' in html
        assert "counter(page)" in html
        assert "counter(pages)" in html
