from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from trips.models import Experience, Meal


class SuggestionKind(str, Enum):
    EXPERIENCE = "experience"
    MEAL = "meal"
    STAY = "stay"


# Valid `type` values per kind, derived from the Django models so the schema
# stays in sync with Experience.Type / Meal.Type.
EXPERIENCE_TYPES = {choice.value for choice in Experience.Type}
MEAL_TYPES = {choice.value for choice in Meal.Type}


class Suggestion(BaseModel):
    """A single AI-proposed experience, meal or stay. Returned by every
    provider and validated before it reaches the review UI."""

    kind: SuggestionKind
    name: str = Field(min_length=1)
    description: str = ""
    address: str = ""
    city: str = ""
    type: int | None = None

    @model_validator(mode="after")
    def normalize_type_for_kind(self):
        # The provider JSON schema cannot express the per-kind valid integers,
        # so the model may return an out-of-range or missing type. Coerce an
        # invalid type to None instead of raising: rejecting the item would make
        # the whole structured response fail to parse, and the type only drives a
        # display label (accept endpoints persist the category, not the type).
        if self.kind is SuggestionKind.EXPERIENCE and self.type not in EXPERIENCE_TYPES:
            self.type = None
        elif self.kind is SuggestionKind.MEAL and self.type not in MEAL_TYPES:
            self.type = None
        elif self.kind is SuggestionKind.STAY:
            self.type = None
        return self


class TripContext(BaseModel):
    """Context about the trip fed to the prompt."""

    destination: str
    latitude: float | None = None
    longitude: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    language: str = "en"
    # Names of places already planned (events + stays), scoped to the selected
    # stage when one is chosen. Fed to the prompt so the model avoids duplicates
    # and favours nearby proposals.
    existing_places: list[str] = Field(default_factory=list)
    # Compact per-day weather lines for days that already have a forecast,
    # scoped to the selected stage when one is chosen.
    weather: list[str] = Field(default_factory=list)


class SuggestionPrefs(BaseModel):
    """Merged user + per-trip preferences fed to the prompt."""

    favored_experience_types: list[int] = Field(default_factory=list)
    dietary: str = "none"
    budget: str = "medium"
    travel_party: str = "unspecified"
    travel_style: str = "balanced"
    interests: list[str] = Field(default_factory=list)
    cuisine: str = "any"
    search_radius: str = "nearby"
    notes: str = ""
    result_count: int = 8
    # Empty means "all kinds"; otherwise restrict to these SuggestionKind values.
    kinds: list[str] = Field(default_factory=list)
