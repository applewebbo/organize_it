from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout
from django import forms
from django.core.validators import RegexValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from trips.forms.base import ADDRESS_RESULTS_HTML, urlfields_assume_https
from trips.models import (
    Day,
    Stay,
)


class StayForm(forms.ModelForm):
    apply_to_days = (
        forms.ModelMultipleChoiceField(  # New field for multiple day selection
            queryset=None,
            widget=forms.CheckboxSelectMultiple,
            required=True,
            label=_("Period of stay"),  # Customize the label as needed
        )
    )

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": _("Name")}),
        label=_("Name"),
    )

    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("City")}),
        label=_("City"),
    )

    phone_number = forms.CharField(
        max_length=50,
        required=False,
        validators=[
            RegexValidator(
                regex=r"^\+?\d(?: ?\d){7,19}$",
                message=_(
                    "Enter a valid phone number (with or without international prefix, and at most 2 spaces)."
                ),
            ),
            RegexValidator(
                regex=r"^(?:[^ ]* ?){0,3}$|^\+?\d(?: ?\d){7,19}$",
                message=_("Phone number can contain at most 2 spaces."),
            ),
        ],
        widget=forms.TextInput(attrs={"placeholder": _("Phone number")}),
        label=_("Phone number"),
    )

    class Meta:
        model = Stay
        fields = [
            "name",
            "city",
            "check_in",
            "check_out",
            "cancellation_date",
            "phone_number",
            "website",
            "address",
            "latitude",
            "longitude",
            "notes",
            "apply_to_days",
        ]
        formfield_callback = urlfields_assume_https
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Name")}),
            "website": forms.TextInput(attrs={"placeholder": _("Website")}),
            "address": forms.TextInput(attrs={"placeholder": _("Address")}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "check_in": forms.TimeInput(attrs={"type": "time"}),
            "check_out": forms.TimeInput(attrs={"type": "time"}),
            "cancellation_date": forms.DateInput(attrs={"type": "date"}),
            "phone_number": forms.TextInput(attrs={"placeholder": _("Phone number")}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "name": _("Name"),
            "check_in": _("Check-in"),
            "check_out": _("Check-out"),
            "cancellation_date": _("Cancellation date"),
            "phone_number": _("Phone number"),
            "website": _("Website"),
            "address": _("Address"),
        }

    def __init__(self, trip, *args, **kwargs):
        geocode = kwargs.pop("geocode", False)
        super().__init__(*args, **kwargs)
        layout_fields = []
        if geocode:
            geocode_url = reverse("trips:geocode-address")
            name_htmx_attrs = {
                "x-ref": "name",
                "@input": "checkAndTrigger",
                "hx-post": geocode_url,
                "hx-trigger": "trigger-geocode",
                "hx-target": "#address-results",
                "hx-include": "[name='name'], [name='city']",
                "hx-indicator": "#address-spinner",
                ":class": "{ 'animate-pulse ring-2 ring-primary/60': nameFilled }",
            }
            city_htmx_attrs = {
                "x-ref": "city",
                "@input": "checkAndTrigger",
                "hx-post": geocode_url,
                "hx-trigger": "trigger-geocode",
                "hx-target": "#address-results",
                "hx-include": "[name='name'], [name='city']",
                "hx-indicator": "#address-spinner",
            }
            address_htmx_attrs = {
                "x-ref": "address",
                ":class": "{ 'animate-pulse ring-2 ring-primary/60': addressFilled }",
            }
            self.fields["name"].widget.attrs.update(name_htmx_attrs)
            self.fields["city"].widget.attrs.update(city_htmx_attrs)
            self.fields["address"].widget.attrs.update(address_htmx_attrs)
        layout_fields.append(Field("name", wrapper_class="sm:col-span-2"))
        layout_fields.append(Field("city", wrapper_class="sm:col-span-2"))
        self.fields["apply_to_days"].queryset = Day.objects.filter(trip=trip)
        self.fields["apply_to_days"].label_from_instance = lambda obj: (
            f"{_('Day')} {obj.number}"
        )
        # Only set initial values if we're editing an existing stay
        if self.instance.pk:
            self.fields["apply_to_days"].initial = Day.objects.filter(
                trip=trip, stay=self.instance
            ).values_list("pk", flat=True)
        self.helper = FormHelper()
        self.helper.form_tag = False
        layout_fields += [
            Div(
                Field("address", wrapper_class="sm:col-span-4"),
                HTML("""
                    <span id="address-spinner" class="absolute right-2 top-1/2 -translate-y-1/2">
                        <span class="loading loading-bars loading-lg text-primary mt-3.5 htmx-indicator"></span>
                    </span>
                    """),
                css_class="relative sm:col-span-4",
            ),
            HTML(ADDRESS_RESULTS_HTML),
            Field("check_in", wrapper_class="sm:col-span-2"),
            Field("check_out", wrapper_class="sm:col-span-2"),
            Field("cancellation_date", wrapper_class="sm:col-span-2"),
            Field("phone_number", wrapper_class="sm:col-span-2"),
            Field("website", wrapper_class="sm:col-span-4"),
            Field("notes", css_class="fl-textarea", wrapper_class="sm:col-span-4"),
            Field("apply_to_days", wrapper_class="sm:col-span-4"),
        ]
        self.helper.layout = Layout(*layout_fields)

    def save(self, commit=True):
        stay = super().save(commit=False)
        if commit:  # pragma: no cover
            stay.save()
        days = self.cleaned_data["apply_to_days"]
        for day in days:
            day.stay = stay
            day.save()
        return stay


class AddNoteToStayForm(forms.ModelForm):
    """
    Form to add notes to a Stay instance.
    """

    notes = forms.CharField(
        label=_("Notes"),
        widget=forms.Textarea(attrs={"placeholder": _("Add notes...")}),
        required=True,
    )

    class Meta:
        model = Stay
        fields = ["notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Div, Field, Layout

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Field("notes", css_class="fl-textarea"),
                css_class="sm:col-span-2",
            ),
        )


# =============================================================================
# MAIN TRANSFER FORMS (for trip arrival/departure)
# =============================================================================
