import pytest
from pydantic import ValidationError

from suggestions.schemas import Suggestion, SuggestionKind


class TestSuggestionSchema:
    def test_valid_experience(self):
        s = Suggestion(kind="experience", name="Louvre", type=1)
        assert s.kind is SuggestionKind.EXPERIENCE
        assert s.type == 1

    def test_invalid_experience_type_coerced_to_none(self):
        s = Suggestion(kind="experience", name="X", type=99)
        assert s.type is None

    def test_experience_without_type_stays_none(self):
        s = Suggestion(kind="experience", name="X")
        assert s.type is None

    def test_valid_meal(self):
        s = Suggestion(kind="meal", name="Trattoria", type=3)
        assert s.type == 3

    def test_invalid_meal_type_coerced_to_none(self):
        s = Suggestion(kind="meal", name="X", type=99)
        assert s.type is None

    def test_stay_type_is_forced_to_none(self):
        s = Suggestion(kind="stay", name="Hotel", type=4)
        assert s.type is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            Suggestion(kind="stay", name="")
