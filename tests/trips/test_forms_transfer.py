"""Tests for SimpleTransfer and StayTransfer forms"""

from datetime import date, timedelta

import pytest

from tests.trips.factories import ExperienceFactory, StayFactory, TripFactory
from trips.forms import (
    SimpleTransferCreateForm,
    SimpleTransferEditForm,
    StayTransferCreateForm,
    StayTransferEditForm,
)
from trips.models import SimpleTransfer, StayTransfer

pytestmark = pytest.mark.django_db


class TestSimpleTransferCreateForm:
    """Tests for SimpleTransferCreateForm"""

    def test_form_creates_instance_with_events(self):
        """Test form creates instance with from_event and to_event"""
        trip = TripFactory()
        day = trip.days.first()
        event1 = ExperienceFactory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = ExperienceFactory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        form = SimpleTransferCreateForm(from_event=event1, to_event=event2)

        assert form.instance.from_event == event1
        assert form.instance.to_event == event2

    def test_form_valid_data(self):
        """Test form is valid with correct data"""
        trip = TripFactory()
        day = trip.days.first()
        event1 = ExperienceFactory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = ExperienceFactory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        form = SimpleTransferCreateForm(
            data={"transport_mode": "driving", "notes": ""},
            from_event=event1,
            to_event=event2,
        )

        assert form.is_valid()

    def test_form_invalid_same_event(self):
        """Test form is invalid when from_event and to_event are the same"""
        trip = TripFactory()
        day = trip.days.first()
        event = ExperienceFactory(trip=trip, day=day)

        form = SimpleTransferCreateForm(
            data={"transport_mode": "driving"},
            from_event=event,
            to_event=event,
        )

        assert not form.is_valid()
        assert "From event and to event must be different events" in str(
            form.non_field_errors()
        )

    def test_form_invalid_different_days(self):
        """Test form is invalid when events are on different days"""
        trip = TripFactory()
        days = list(trip.days.all())
        event1 = ExperienceFactory(trip=trip, day=days[0])
        event2 = ExperienceFactory(trip=trip, day=days[1])

        form = SimpleTransferCreateForm(
            data={"transport_mode": "driving"},
            from_event=event1,
            to_event=event2,
        )

        assert not form.is_valid()
        assert "Events must be on the same day" in str(form.non_field_errors())

    def test_form_invalid_from_event_has_transfer(self):
        """Test form is invalid when from_event already has an outgoing transfer"""
        trip = TripFactory()
        day = trip.days.first()
        event1 = ExperienceFactory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = ExperienceFactory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )
        event3 = ExperienceFactory(
            trip=trip, day=day, start_time="16:00", end_time="17:00"
        )

        # Create existing transfer from event1
        SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )

        form = SimpleTransferCreateForm(
            data={"transport_mode": "driving"},
            from_event=event1,
            to_event=event3,
        )

        assert not form.is_valid()
        assert "The from event already has an outgoing transfer" in str(
            form.non_field_errors()
        )

    def test_form_invalid_to_event_has_transfer(self):
        """Test form is invalid when to_event already has an incoming transfer"""
        trip = TripFactory()
        day = trip.days.first()
        event1 = ExperienceFactory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = ExperienceFactory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )
        event3 = ExperienceFactory(
            trip=trip, day=day, start_time="12:00", end_time="13:00"
        )

        # Create existing transfer to event2
        SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )

        form = SimpleTransferCreateForm(
            data={"transport_mode": "driving"},
            from_event=event3,
            to_event=event2,
        )

        assert not form.is_valid()
        assert "The to event already has an incoming transfer" in str(
            form.non_field_errors()
        )

    def test_form_valid_edit_existing_excludes_self_from_event(self):
        """Test that editing existing transfer excludes self from from_event check"""
        trip = TripFactory()
        day = trip.days.first()
        event1 = ExperienceFactory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = ExperienceFactory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        # Create existing transfer
        transfer = SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )

        # Edit the transfer using CreateForm with instance - should be valid
        form = SimpleTransferCreateForm(
            data={"transport_mode": "walking"},
            from_event=event1,
            to_event=event2,
            instance=transfer,
        )

        assert form.is_valid()

    def test_form_valid_edit_existing_excludes_self_to_event(self):
        """Test that editing existing transfer excludes self from to_event check"""
        trip = TripFactory()
        day = trip.days.first()
        event1 = ExperienceFactory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = ExperienceFactory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        # Create existing transfer
        transfer = SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )

        # Edit the transfer using CreateForm with instance - should be valid
        form = SimpleTransferCreateForm(
            data={"transport_mode": "transit"},
            from_event=event1,
            to_event=event2,
            instance=transfer,
        )

        assert form.is_valid()


class TestSimpleTransferEditForm:
    """Tests for SimpleTransferEditForm"""

    def test_form_valid_edit(self):
        """Test form is valid when editing existing transfer"""
        trip = TripFactory()
        day = trip.days.first()
        event1 = ExperienceFactory(
            trip=trip, day=day, start_time="10:00", end_time="11:00"
        )
        event2 = ExperienceFactory(
            trip=trip, day=day, start_time="14:00", end_time="15:00"
        )

        transfer = SimpleTransfer.objects.create(
            from_event=event1, to_event=event2, transport_mode="driving"
        )

        form = SimpleTransferEditForm(
            data={"transport_mode": "walking", "notes": "Updated notes"},
            instance=transfer,
        )

        assert form.is_valid()


class TestStayTransferCreateForm:
    """Tests for StayTransferCreateForm"""

    def test_form_creates_instance_with_stays(self):
        """Test form creates instance with from_stay and to_stay"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        form = StayTransferCreateForm(from_stay=stay1, to_stay=stay2)

        assert form.instance.from_stay == stay1
        assert form.instance.to_stay == stay2

    def test_form_valid_data(self):
        """Test form is valid with correct data"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        form = StayTransferCreateForm(
            data={"transport_mode": "transit", "notes": ""},
            from_stay=stay1,
            to_stay=stay2,
        )

        assert form.is_valid()

    def test_form_invalid_same_stay(self):
        """Test form is invalid when from_stay and to_stay are the same"""
        trip = TripFactory()
        day = trip.days.first()
        stay = StayFactory()

        day.stay = stay
        day.save()

        form = StayTransferCreateForm(
            data={"transport_mode": "transit"},
            from_stay=stay,
            to_stay=stay,
        )

        assert not form.is_valid()
        assert "From stay and to stay must be different" in str(form.non_field_errors())

    def test_form_invalid_from_stay_has_transfer(self):
        """Test form is invalid when from_stay already has an outgoing transfer"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=3)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()
        stay3 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()
        days[2].stay = stay3
        days[2].save()

        # Create existing transfer from stay1
        StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="transit"
        )

        form = StayTransferCreateForm(
            data={"transport_mode": "transit"},
            from_stay=stay1,
            to_stay=stay3,
        )

        assert not form.is_valid()
        assert "The from stay already has an outgoing transfer" in str(
            form.non_field_errors()
        )

    def test_form_invalid_to_stay_has_transfer(self):
        """Test form is invalid when to_stay already has an incoming transfer"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=3)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()
        stay3 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()
        days[2].stay = stay3
        days[2].save()

        # Create existing transfer to stay2
        StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="transit"
        )

        form = StayTransferCreateForm(
            data={"transport_mode": "transit"},
            from_stay=stay3,
            to_stay=stay2,
        )

        assert not form.is_valid()
        assert "The to stay already has an incoming transfer" in str(
            form.non_field_errors()
        )

    def test_form_valid_edit_existing_excludes_self_from_stay(self):
        """Test that editing existing transfer excludes self from from_stay check"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        # Create existing transfer
        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="transit"
        )

        # Edit the transfer using CreateForm with instance - should be valid
        form = StayTransferCreateForm(
            data={"transport_mode": "driving"},
            from_stay=stay1,
            to_stay=stay2,
            instance=transfer,
        )

        assert form.is_valid()

    def test_form_valid_edit_existing_excludes_self_to_stay(self):
        """Test that editing existing transfer excludes self from to_stay check"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        # Create existing transfer
        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="transit"
        )

        # Edit the transfer using CreateForm with instance - should be valid
        form = StayTransferCreateForm(
            data={"transport_mode": "walking"},
            from_stay=stay1,
            to_stay=stay2,
            instance=transfer,
        )

        assert form.is_valid()


class TestStayTransferEditForm:
    """Tests for StayTransferEditForm"""

    def test_form_valid_edit(self):
        """Test form is valid when editing existing transfer"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="transit"
        )

        form = StayTransferEditForm(
            data={"transport_mode": "driving", "notes": "Updated notes"},
            instance=transfer,
        )

        assert form.is_valid()

    def test_form_save_commit_false(self):
        """Test that save with commit=False returns unsaved instance"""
        trip = TripFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=2)
        )
        days = list(trip.days.all())
        stay1 = StayFactory()
        stay2 = StayFactory()

        days[0].stay = stay1
        days[0].save()
        days[1].stay = stay2
        days[1].save()

        transfer = StayTransfer.objects.create(
            from_stay=stay1, to_stay=stay2, transport_mode="transit"
        )

        form = StayTransferEditForm(
            data={"transport_mode": "driving", "notes": "Updated"},
            instance=transfer,
        )

        assert form.is_valid()
        instance = form.save(commit=False)
        # Instance should have changes but not saved to DB
        assert instance.transport_mode == "driving"
        # Verify original is unchanged in DB
        transfer.refresh_from_db()
        assert transfer.transport_mode == "transit"
