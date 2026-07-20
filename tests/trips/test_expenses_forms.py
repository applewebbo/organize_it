import pytest

from tests.trips.factories import (
    ExpenseParticipantFactory,
    FamilyUnitFactory,
    TripFactory,
)
from trips.forms import ExpenseForm

pytestmark = pytest.mark.django_db


class TestPartyChoices:
    def test_singles_become_person_tokens(self):
        trip = TripFactory()
        anna = ExpenseParticipantFactory(trip=trip, name_snapshot="Anna")
        bruno = ExpenseParticipantFactory(trip=trip, name_snapshot="Bruno")
        form = ExpenseForm(trip=trip)
        assert form._choices == [
            (f"p{anna.pk}", "Anna"),
            (f"p{bruno.pk}", "Bruno"),
        ]
        assert form._token_members[f"p{anna.pk}"] == [anna.pk]
        assert form._token_payer[f"p{anna.pk}"] == anna.pk

    def test_group_lists_before_singles_and_expands_members(self):
        trip = TripFactory()
        unit = FamilyUnitFactory(trip=trip, name="Rossi")
        marco = ExpenseParticipantFactory(
            trip=trip, name_snapshot="Marco", family_unit=unit
        )
        laura = ExpenseParticipantFactory(
            trip=trip, name_snapshot="Laura", family_unit=unit
        )
        carla = ExpenseParticipantFactory(trip=trip, name_snapshot="Carla")
        form = ExpenseForm(trip=trip)
        # Units come before singles.
        assert form._choices[0] == (f"u{unit.pk}", "Rossi")
        assert form._choices[1] == (f"p{carla.pk}", "Carla")
        assert sorted(form._token_members[f"u{unit.pk}"]) == sorted(
            [marco.pk, laura.pk]
        )

    def test_group_payer_is_first_adult(self):
        trip = TripFactory()
        unit = FamilyUnitFactory(trip=trip, name="Rossi")
        kid = ExpenseParticipantFactory(
            trip=trip, name_snapshot="Kid", family_unit=unit, is_child=True
        )
        adult = ExpenseParticipantFactory(
            trip=trip, name_snapshot="Marco", family_unit=unit
        )
        form = ExpenseForm(trip=trip)
        assert form._token_payer[f"u{unit.pk}"] == adult.pk
        assert kid.pk in form._token_members[f"u{unit.pk}"]

    def test_children_only_group_falls_back_to_first_member(self):
        trip = TripFactory()
        unit = FamilyUnitFactory(trip=trip, name="Kids")
        first = ExpenseParticipantFactory(
            trip=trip, name_snapshot="A", family_unit=unit, is_child=True
        )
        ExpenseParticipantFactory(
            trip=trip, name_snapshot="B", family_unit=unit, is_child=True
        )
        form = ExpenseForm(trip=trip)
        assert form._token_payer[f"u{unit.pk}"] == first.pk

    def test_resolvers_expand_tokens(self):
        trip = TripFactory()
        unit = FamilyUnitFactory(trip=trip, name="Rossi")
        marco = ExpenseParticipantFactory(
            trip=trip, name_snapshot="Marco", family_unit=unit
        )
        laura = ExpenseParticipantFactory(
            trip=trip, name_snapshot="Laura", family_unit=unit
        )
        carla = ExpenseParticipantFactory(trip=trip, name_snapshot="Carla")
        form = ExpenseForm(
            data={
                "title": "Dinner",
                "amount": "30.00",
                "date": trip.start_date.isoformat(),
                "payer": f"u{unit.pk}",
                "shared_with": [f"u{unit.pk}", f"p{carla.pk}"],
            },
            trip=trip,
        )
        assert form.is_valid(), form.errors
        assert form.payer_participant_id in {marco.pk, laura.pk}
        assert set(form.sharer_participant_ids) == {marco.pk, laura.pk, carla.pk}
