import json
from datetime import date

import pytest

from tests.suggestions.factories import AICredentialsFactory
from tests.test import TestCase
from tests.trips.factories import TripFactory
from trips.forms.wizard import WizardBasicsForm
from trips.models import Trip
from trips.utils.stages import apply_stage

pytestmark = pytest.mark.django_db


def _stages_json(*stages):
    return json.dumps(list(stages))


class TestApplyStage(TestCase):
    def test_assigns_destination_to_days(self):
        trip = TripFactory(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 5), destination="Roma"
        )
        days = list(trip.days.order_by("number"))
        apply_stage(trip, [d.pk for d in days[2:]], "Firenze")
        for d in days[2:]:
            d.refresh_from_db()
            assert d.destination == "Firenze"
        days[0].refresh_from_db()
        assert days[0].destination == "Roma"

    def test_assigns_coords(self):
        trip = TripFactory(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3), destination="Roma"
        )
        day = trip.days.order_by("number").last()
        apply_stage(trip, [day.pk], "Firenze", latitude=43.77, longitude=11.25)
        day.refresh_from_db()
        assert day.destination == "Firenze"
        assert day.destination_latitude == 43.77

    def test_noop_without_destination_or_days(self):
        trip = TripFactory(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3), destination="Roma"
        )
        day = trip.days.first()
        apply_stage(trip, [], "Firenze")
        apply_stage(trip, [day.pk], "")
        day.refresh_from_db()
        assert day.destination == "Roma"

    def test_noop_when_day_pks_dont_belong_to_trip(self):
        trip = TripFactory(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3), destination="Roma"
        )
        other = TripFactory(
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 3), destination="Milano"
        )
        other_day = other.days.first()
        apply_stage(trip, [other_day.pk], "Firenze")
        other_day.refresh_from_db()
        assert other_day.destination == "Milano"


class TestWizardBasicsForm(TestCase):
    def _data(self, stages_json, **overrides):
        data = {
            "title": "Grand Tour",
            "start_date": "2026-06-01",
            "end_date": "2026-06-08",
            "stages": stages_json,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        stages = _stages_json(
            {"destination": "Roma", "nights": 3},
            {"destination": "Firenze", "nights": 2},
            {"destination": "Venezia", "nights": 2},
        )
        form = WizardBasicsForm(data=self._data(stages))
        assert form.is_valid(), form.errors
        assert len(form.cleaned_data["stages_list"]) == 3
        assert form.cleaned_data["stages_list"][0]["destination"] == "Roma"

    def test_nights_sum_must_match_duration(self):
        stages = _stages_json(
            {"destination": "Roma", "nights": 3},
            {"destination": "Firenze", "nights": 2},
        )
        form = WizardBasicsForm(data=self._data(stages))
        assert not form.is_valid()
        assert "stages" in form.errors

    def test_empty_stages_invalid(self):
        form = WizardBasicsForm(data=self._data("[]"))
        assert not form.is_valid()
        assert "stages" in form.errors

    def test_invalid_json_invalid(self):
        form = WizardBasicsForm(data=self._data("not json"))
        assert not form.is_valid()
        assert "stages" in form.errors

    def test_nights_below_one_invalid(self):
        stages = _stages_json({"destination": "Roma", "nights": 0})
        form = WizardBasicsForm(data=self._data(stages))
        assert not form.is_valid()
        assert "stages" in form.errors

    def test_blank_destination_invalid(self):
        stages = _stages_json(
            {"destination": "Roma", "nights": 4},
            {"destination": "", "nights": 3},
        )
        form = WizardBasicsForm(data=self._data(stages))
        assert not form.is_valid()
        assert "stages" in form.errors

    def test_non_numeric_nights_invalid(self):
        stages = _stages_json({"destination": "Roma"})
        form = WizardBasicsForm(data=self._data(stages))
        assert not form.is_valid()
        assert "stages" in form.errors

    def test_invalid_coords_are_dropped(self):
        stages = _stages_json(
            {"destination": "Roma", "nights": 7, "latitude": "x", "longitude": "y"}
        )
        form = WizardBasicsForm(data=self._data(stages))
        assert form.is_valid(), form.errors
        assert "latitude" not in form.cleaned_data["stages_list"][0]

    def test_missing_date_skips_cross_validation(self):
        stages = _stages_json({"destination": "Roma", "nights": 7})
        form = WizardBasicsForm(data=self._data(stages, end_date=""))
        assert not form.is_valid()
        assert "stages" not in form.errors

    def test_end_before_start_invalid(self):
        stages = _stages_json({"destination": "Roma", "nights": 7})
        form = WizardBasicsForm(
            data=self._data(stages, start_date="2026-06-08", end_date="2026-06-01")
        )
        assert not form.is_valid()


class TestWizardBasicsView(TestCase):
    def _post_data(self):
        return {
            "title": "Grand Tour",
            "start_date": "2026-06-01",
            "end_date": "2026-06-08",
            "stages": _stages_json(
                {
                    "destination": "Roma",
                    "nights": 3,
                    "latitude": 41.9028,
                    "longitude": 12.4964,
                },
                {"destination": "Firenze", "nights": 2},
                {"destination": "Venezia", "nights": 2},
            ),
        }

    def test_get_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        with self.login(user):
            response = self.get("trips:wizard-start")
        assert response.status_code == 403

    def test_get_renders_shell_with_key(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        with self.login(user):
            response = self.get("trips:wizard-start")
        self.response_200(response)

    def test_post_creates_draft_trip(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        with self.login(user):
            response = self.post("trips:wizard-basics", data=self._post_data())
        assert response.status_code == 200
        assert response["HX-Trigger"] == "wizard-draft-created"
        trip = Trip.objects.get(author=user)
        assert trip.wizard_completed is False
        assert trip.wizard_started_at is not None
        assert trip.wizard_step >= 1
        assert trip.destination == "Roma"
        assert trip.start_date == date(2026, 6, 1)
        assert trip.end_date == date(2026, 6, 8)

    def test_post_assigns_stages_to_days(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        with self.login(user):
            self.post("trips:wizard-basics", data=self._post_data())
        trip = Trip.objects.get(author=user)
        days = list(trip.days.order_by("number"))
        assert len(days) == 8
        assert days[0].destination == "Roma"
        assert days[2].destination == "Roma"
        assert days[3].destination == "Firenze"
        assert days[5].destination == "Venezia"
        assert days[7].destination == "Venezia"

    def test_post_invalid_rerenders(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        data = self._post_data()
        data["title"] = ""
        with self.login(user):
            response = self.post("trips:wizard-basics", data=data)
        assert response.status_code == 200
        assert not Trip.objects.filter(author=user).exists()

    def test_post_requires_ai_key(self):
        user = self.make_user("nokey@example.com")
        with self.login(user):
            response = self.post("trips:wizard-basics", data=self._post_data())
        assert response.status_code == 403


class TestWizardBasicsRehydration(TestCase):
    """A failed Basics step must re-render everything the user typed (issue #425)."""

    def _invalid_post(self, user):
        data = {
            "title": "Grand Tour",
            "start_date": "2026-06-01",
            "end_date": "2026-06-08",
            "stages": _stages_json(
                {"destination": "", "nights": 5},
                {"destination": "Firenze", "nights": 2},
            ),
        }
        with self.login(user):
            return self.post("trips:wizard-basics", data=data)

    def _stages_payload(self, content):
        marker = '<script id="wizard-stages-data" type="application/json">'
        start = content.index(marker) + len(marker)
        return json.loads(content[start : content.index("</script>", start)])

    def test_dates_are_kept(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        content = self._invalid_post(user).content.decode()
        assert 'value="2026-06-01"' in content
        assert 'value="2026-06-08"' in content

    def test_stages_payload_is_valid_json(self):
        user = self.make_user("owner@example.com")
        AICredentialsFactory(user=user)
        content = self._invalid_post(user).content.decode()
        assert self._stages_payload(content) == [
            {"destination": "", "nights": 5},
            {"destination": "Firenze", "nights": 2},
        ]

    def test_stages_form_initial_unbound(self):
        assert WizardBasicsForm().stages_initial == []

    def test_stages_form_initial_with_malformed_json(self):
        form = WizardBasicsForm({"stages": "not json"})
        assert form.stages_initial == []

    def test_stages_form_initial_with_non_list_json(self):
        form = WizardBasicsForm({"stages": '{"destination": "Roma"}'})
        assert form.stages_initial == []
