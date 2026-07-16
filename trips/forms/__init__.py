"""Trip forms, split by domain.

Import paths remain backward compatible: `from trips.forms import X` keeps
working for every form thanks to the re-exports below.
"""

from trips.forms.base import urlfields_assume_https
from trips.forms.event import EventForm, ExperienceForm, MealForm, NoteForm
from trips.forms.expense import ExpenseForm, ExpenseSettingsForm, FamilyUnitForm
from trips.forms.stay import AddNoteToStayForm, StayForm
from trips.forms.transfer import (
    CarMainTransferForm,
    FlightMainTransferForm,
    MainTransferBaseForm,
    MainTransferConnectionEditForm,
    MainTransferConnectionForm,
    OtherMainTransferForm,
    TrainMainTransferForm,
)
from trips.forms.trip import (
    ChecklistItemForm,
    ChecklistReminderForm,
    LinkForm,
    ShareLinkCreateForm,
    TripForm,
)

__all__ = [
    "AddNoteToStayForm",
    "CarMainTransferForm",
    "ChecklistItemForm",
    "ChecklistReminderForm",
    "EventForm",
    "ExpenseForm",
    "ExpenseSettingsForm",
    "ExperienceForm",
    "FamilyUnitForm",
    "FlightMainTransferForm",
    "LinkForm",
    "MainTransferBaseForm",
    "MainTransferConnectionEditForm",
    "MainTransferConnectionForm",
    "MealForm",
    "NoteForm",
    "OtherMainTransferForm",
    "ShareLinkCreateForm",
    "StayForm",
    "TrainMainTransferForm",
    "TripForm",
    "urlfields_assume_https",
]
