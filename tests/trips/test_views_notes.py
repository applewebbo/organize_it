import pytest
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import EventFactory, StayFactory, TripFactory

pytestmark = pytest.mark.django_db


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
