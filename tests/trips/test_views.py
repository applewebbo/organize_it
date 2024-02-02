import datetime

import factory
import pytest
from django.contrib.messages import get_messages
from django.db.models import signals
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import LinkFactory, NoteFactory, PlaceFactory, TripFactory
from trips.models import Day, Link, Note, Place, Trip

pytestmark = pytest.mark.django_db


class HomeView(TestCase):
    def test_get(self):
        # Get the home view
        response = self.get("trips:home")
        # Check the status code and template used
        self.response_200(response)
        assertTemplateUsed(response, "trips/index.html")

    def test_get_with_authenticated_user(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert trip in response.context["other_trips"]

    def test_get_with_fav_trip(self):
        user = self.make_user("user")
        fav_trip = TripFactory(author=user)
        user.profile.fav_trip = fav_trip
        user.profile.save()

        with self.login(user):
            response = self.get("trips:home")

        self.response_200(response)
        assert response.context["fav_trip"] == fav_trip

    @factory.django.mute_signals(signals.post_save)
    def test_get_with_no_profile(self):
        user = self.make_user("user")

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


class TripDetailView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-detail.html")

    def test_map_bounds(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        PlaceFactory.create_batch(2, trip=trip)

        with self.login(user):
            response = self.get("trips:trip-detail", pk=trip.pk)

        assert response.context["map_bounds"] is not None


class TripCreateView(TestCase):
    def test_get(self):
        user = self.make_user("user")

        with self.login(user):
            response = self.get("trips:trip-create")

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-create.html")

    def test_post(self):
        user = self.make_user("user")
        data = {
            "title": "Trip to Paris",
            "description": "A trip to Paris",
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.post("trips:trip-create", data=data)

        self.response_204(response)
        trip = Trip.objects.filter(author=user).first()
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{ trip.title }</strong> added successfully"
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
        assert message == f"<strong>{ trip.title }</strong> deleted successfully"
        assert Trip.objects.filter(author=user).count() == 0


class TripUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-update", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/trip-create.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Trip to Paris",
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
        assert message == f"<strong>{ trip.title }</strong> archived successfully"
        assert Trip.objects.filter(author=user).count() == 1
        assert Trip.objects.filter(author=user, status=5).count() == 1


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
        data = {
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=3),
        }

        with self.login(user):
            response = self.post("trips:trip-dates", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        trip = Trip.objects.filter(author=user).first()
        assert message == "Dates updated successfully"
        assert trip.start_date == data["start_date"]
        assert trip.end_date == data["end_date"]


class TripAddLinkView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-add-link", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/link-create.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Google",
            "url": "https://www.google.com",
        }

        with self.login(user):
            response = self.post("trips:trip-add-link", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Link added successfully"
        assert trip.links.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Google",
        }

        with self.login(user):
            response = self.post("trips:trip-add-link", pk=trip.pk, data=data)

        self.response_200(response)
        assert trip.links.count() == 0


class LinkDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        link = LinkFactory(author=user)

        with self.login(user):
            response = self.delete("trips:link-delete", pk=link.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Link deleted successfully"
        assert LinkFactory(author=user).pk != link.pk


class LinkUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        link = LinkFactory(author=user)

        with self.login(user):
            response = self.get("trips:link-update", pk=link.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/link-create.html")

    def test_post(self):
        user = self.make_user("user")
        link = LinkFactory(author=user)
        data = {
            "title": "Google",
            "url": "https://www.google.com",
        }

        with self.login(user):
            response = self.post("trips:link-update", pk=link.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Link updated successfully"
        assert Link.objects.first().title == data["title"]
        assert Link.objects.first().url == data["url"]

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        link = LinkFactory(author=user)
        data = {
            "title": "Google",
        }

        with self.login(user):
            response = self.post("trips:link-update", pk=link.pk, data=data)

        self.response_200(response)
        assert Link.objects.first().title != data["title"]


class LinkListView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        link = LinkFactory(author=user)
        trip.links.add(link)

        with self.login(user):
            response = self.get("trips:link-list", pk=trip.pk)

        self.response_200(response)
        assert trip == response.context_data["trip"]
        assert link in response.context_data["links"]


class TripAddPlace(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-add-place", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/place-create.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user, start_date=datetime.date.today())
        data = {
            "name": factory.Faker("city"),
            "address": factory.Faker("address"),
            "day": Day.objects.filter(trip=trip).first().pk,
        }

        with self.login(user):
            response = self.post("trips:trip-add-place", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{ data['name'] }</strong> added successfully"
        assert trip.places.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "name": factory.Faker("city"),
        }

        with self.login(user):
            response = self.post("trips:trip-add-place", pk=trip.pk, data=data)

        self.response_200(response)
        assert trip.places.count() == 0


class PlaceListView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        places = PlaceFactory.create_batch(3, trip=trip)

        with self.login(user):
            response = self.get("trips:place-list", pk=trip.pk)

        self.response_200(response)
        assert trip == response.context_data["trip"]
        assert places[0] in response.context_data["places"]


class PlaceDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        place = PlaceFactory(trip=trip)

        with self.login(user):
            response = self.delete("trips:place-delete", pk=place.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Place deleted successfully"
        assert PlaceFactory(trip__author=user).pk != place.pk


class PlaceUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        place = PlaceFactory(trip=trip)

        with self.login(user):
            response = self.get("trips:place-update", pk=place.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/place-create.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        place = PlaceFactory(trip=trip)
        data = {
            "name": "Tour Eiffel",
            "address": "Champ de Mars, 5 Av. Anatole France, 75007 Paris, France",
            "day": Day.objects.filter(trip=trip).first().pk,
        }

        with self.login(user):
            response = self.post("trips:place-update", pk=place.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Place updated successfully"
        assert Place.objects.first().name == data["name"]
        assert Place.objects.first().address == data["address"]

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        place = PlaceFactory(trip=trip)
        data = {
            "name": "Tour Eiffel",
        }

        with self.login(user):
            response = self.post("trips:place-update", pk=place.pk, data=data)

        self.response_200(response)
        assert Place.objects.first().name != data["name"]


class PlaceAssignView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        place = PlaceFactory(trip=trip)

        with self.login(user):
            response = self.get("trips:place-assign", pk=place.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/place-assign.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        place = PlaceFactory(trip=trip)
        day = Day.objects.filter(trip=trip).first()
        data = {
            "day": day.pk,
        }

        with self.login(user):
            response = self.post("trips:place-assign", pk=place.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Place assigned successfully"
        assert Place.objects.first().day == day

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        place = PlaceFactory(trip=trip)
        data = {
            "day": "",
        }

        with self.login(user):
            response = self.post("trips:place-assign", pk=place.pk, data=data)

        self.response_200(response)
        assert Place.objects.first().day is None


class TripAddNoteView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)

        with self.login(user):
            response = self.get("trips:trip-add-note", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/note-create.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "content": "Note content",
        }

        with self.login(user):
            response = self.post("trips:trip-add-note", pk=trip.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Note added successfully"
        assert trip.notes.count() == 1

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        data = {
            "title": "Note title",
        }

        with self.login(user):
            response = self.post("trips:trip-add-note", pk=trip.pk, data=data)

        self.response_200(response)
        assert trip.notes.count() == 0


class NoteUpdateView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        note = NoteFactory(trip=trip)

        with self.login(user):
            response = self.get("trips:note-update", pk=note.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/note-create.html")

    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        note = NoteFactory(trip=trip)
        data = {"content": "Note content"}

        with self.login(user):
            response = self.post("trips:note-update", pk=note.pk, data=data)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Note updated successfully"
        assert Note.objects.first().content == data["content"]

    def test_post_with_invalid_data(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        note = NoteFactory(trip=trip)
        data = {
            "content": "",
        }

        with self.login(user):
            response = self.post("trips:note-update", pk=note.pk, data=data)

        self.response_200(response)
        assert Note.objects.first().content != data["content"]


class NoteListView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        note = NoteFactory(trip=trip)

        with self.login(user):
            response = self.get("trips:note-list", pk=trip.pk)

        self.response_200(response)
        assert trip == response.context_data["trip"]
        assert note in response.context_data["notes"]


class NoteDeleteView(TestCase):
    def test_delete(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        note = NoteFactory(trip=trip)

        with self.login(user):
            response = self.delete("trips:note-delete", pk=note.pk)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Note deleted successfully"
        assert NoteFactory(trip__author=user).pk != note.pk


class NoteCheckOrUncheckView(TestCase):
    def test_post(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        note = NoteFactory(trip=trip)

        with self.login(user):
            response = self.post("trips:note-check", pk=note.pk)

        self.response_204(response)
        assert Note.objects.first().checked is True

    def test_post_with_uncheck(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        note = NoteFactory(trip=trip, checked=True)

        with self.login(user):
            response = self.post("trips:note-check", pk=note.pk)

        self.response_204(response)
        assert Note.objects.first().checked is False


class MapView(TestCase):
    def test_get(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        PlaceFactory.create_batch(2, trip=trip)

        with self.login(user):
            response = self.get("trips:map", pk=trip.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/map.html")

    def test_get_with_day(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = Day.objects.filter(trip=trip).first()
        PlaceFactory.create_batch(2, trip=trip, day=day)

        with self.login(user):
            response = self.get("trips:map", pk=trip.pk, day=day.pk)

        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/map.html")
