from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout
from django import forms
from django.utils.translation import gettext_lazy as _

from trips.models import Expense, ExpenseParticipant, FamilyUnit, Trip


class ExpenseSettingsForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ["expenses_enabled", "expense_currency"]
        labels = {
            "expenses_enabled": _("Enable expense sharing"),
            "expense_currency": _("Trip currency"),
        }
        widgets = {
            "expense_currency": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
        }


class FamilyUnitForm(forms.ModelForm):
    class Meta:
        model = FamilyUnit
        fields = ["name", "shared_wallet"]
        labels = {
            "name": _("Family name"),
            "shared_wallet": _("Shared wallet"),
        }


class ExpenseForm(forms.ModelForm):
    shared_with = forms.ModelMultipleChoiceField(
        queryset=ExpenseParticipant.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label=_("Shared with"),
        required=False,
    )

    class Meta:
        model = Expense
        fields = ["title", "amount", "date", "category", "payer"]
        labels = {
            "title": _("Description"),
            "amount": _("Amount"),
            "date": _("Date"),
            "category": _("Category"),
            "payer": _("Paid by"),
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, trip=None, linked=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.trip = trip
        participants = ExpenseParticipant.objects.filter(trip=trip, is_active=True)
        self.fields["payer"].queryset = participants
        self.fields["shared_with"].queryset = participants
        if not self.is_bound and self.initial.get("shared_with") is None:
            self.initial["shared_with"] = list(
                participants.values_list("pk", flat=True)
            )
        # Linked expenses derive their category from the linked object.
        if linked:
            del self.fields["category"]

        self.helper = FormHelper()
        self.helper.form_tag = False
        layout_fields = [Field("title"), Field("amount"), Field("date")]
        if not linked:
            layout_fields.append(Field("category"))
        layout_fields += [Field("payer"), Field("shared_with")]
        self.helper.layout = Layout(*layout_fields)

    def clean_shared_with(self):
        shared_with = self.cleaned_data["shared_with"]
        if not shared_with:
            raise forms.ValidationError(_("Select at least one participant."))
        return shared_with
