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
        fields = ["name"]
        labels = {
            "name": _("Family name"),
        }


class ExpenseForm(forms.ModelForm):
    """Expense form whose payer/split choices are "parties".

    A party is either a family unit (all its members share as one) or an
    ungrouped participant. Under the hood shares and the payer are still stored
    per participant: a group choice expands to every member.
    """

    payer = forms.ChoiceField(label=_("Paid by"))
    shared_with = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label=_("Split the expense between"),
        required=False,
    )

    class Meta:
        model = Expense
        fields = ["title", "amount", "date"]
        labels = {
            "title": _("Description"),
            "amount": _("Amount"),
            "date": _("Date"),
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, trip=None, current_participant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.trip = trip
        self._build_party_choices(trip)
        self.fields["payer"].choices = self._choices
        self.fields["shared_with"].choices = self._choices

        if not self.is_bound:
            self._set_initial_payer(current_participant)
            self._set_initial_shared_with()

        self.helper = FormHelper()
        self.helper.form_tag = False
        # On sm+ (6-column grid): row 1 is description + amount, row 2 is
        # date + payer, row 3 is the "split between" checkboxes.
        layout_fields = [
            Field("title", wrapper_class="sm:col-span-4"),
            Field("amount", wrapper_class="sm:col-span-2"),
            Field("date", wrapper_class="sm:col-span-3"),
            Field("payer", wrapper_class="sm:col-span-3"),
            Field("shared_with", wrapper_class="sm:col-span-6"),
        ]
        self.helper.layout = Layout(*layout_fields)

    def _build_party_choices(self, trip):
        """Map participants to party tokens (``u<unit>`` groups, ``p<pid>`` singles)."""
        participants = ExpenseParticipant.objects.filter(
            trip=trip, is_active=True
        ).select_related("family_unit")
        units = {}
        singles = []
        for participant in participants:
            if participant.family_unit_id is not None:
                units.setdefault(
                    participant.family_unit_id,
                    {"unit": participant.family_unit, "members": []},
                )["members"].append(participant)
            else:
                singles.append(participant)

        self._token_members = {}
        self._token_payer = {}
        self._pk_to_token = {}
        unit_choices = []
        for unit_id, info in units.items():
            token = f"u{unit_id}"
            members = info["members"]
            self._token_members[token] = [m.pk for m in members]
            adults = [m for m in members if not m.is_child]
            self._token_payer[token] = (adults[0] if adults else members[0]).pk
            for member in members:
                self._pk_to_token[member.pk] = token
            unit_choices.append((token, info["unit"].display_name))
        single_choices = []
        for participant in singles:
            token = f"p{participant.pk}"
            self._token_members[token] = [participant.pk]
            self._token_payer[token] = participant.pk
            self._pk_to_token[participant.pk] = token
            single_choices.append((token, participant.display_name))

        unit_choices.sort(key=lambda c: c[1].lower())
        single_choices.sort(key=lambda c: c[1].lower())
        self._choices = unit_choices + single_choices

    def _set_initial_payer(self, current_participant):
        if self.instance.pk:
            payer_pk = self.instance.payer_id
        else:
            payer_pk = getattr(current_participant, "pk", None)
        self.initial["payer"] = self._pk_to_token.get(payer_pk)

    def _set_initial_shared_with(self):
        if self.instance.pk:
            member_ids = self.instance.shares.values_list("participant_id", flat=True)
            tokens = {self._pk_to_token.get(pid) for pid in member_ids}
            tokens.discard(None)
            self.initial["shared_with"] = sorted(tokens)
        else:
            self.initial["shared_with"] = [token for token, _label in self._choices]

    @property
    def payer_participant_id(self):
        return self._token_payer[self.cleaned_data["payer"]]

    @property
    def sharer_participant_ids(self):
        ids = []
        for token in self.cleaned_data["shared_with"]:
            ids.extend(self._token_members[token])
        return ids

    def clean_shared_with(self):
        shared_with = self.cleaned_data["shared_with"]
        if not shared_with:
            raise forms.ValidationError(_("Select at least one participant."))
        return shared_with
