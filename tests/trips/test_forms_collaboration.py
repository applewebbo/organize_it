import pytest

from trips.forms import NamedParticipantForm

pytestmark = pytest.mark.django_db


class TestNamedParticipantForm:
    def test_valid_adult(self):
        form = NamedParticipantForm({"name": "Marco"})
        assert form.is_valid()
        assert form.cleaned_data["is_child"] is False
        assert form.cleaned_data["age"] is None

    def test_empty_name_invalid(self):
        form = NamedParticipantForm({"name": ""})
        assert not form.is_valid()
        assert "name" in form.errors

    def test_valid_child_with_age(self):
        form = NamedParticipantForm({"name": "Sofia", "is_child": "on", "age": "8"})
        assert form.is_valid()
        assert form.cleaned_data["is_child"] is True
        assert form.cleaned_data["age"] == 8

    def test_child_without_age_invalid(self):
        form = NamedParticipantForm({"name": "Sofia", "is_child": "on"})
        assert not form.is_valid()
        assert "age" in form.errors

    def test_age_above_max_invalid(self):
        form = NamedParticipantForm({"name": "Sofia", "is_child": "on", "age": "18"})
        assert not form.is_valid()
        assert "age" in form.errors

    def test_adult_with_age_clears_age(self):
        form = NamedParticipantForm({"name": "Marco", "age": "10"})
        assert form.is_valid()
        assert form.cleaned_data["age"] is None
