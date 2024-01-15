from datetime import date, timedelta

import pytest

from trips.forms import TripDateUpdateForm, TripForm

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
