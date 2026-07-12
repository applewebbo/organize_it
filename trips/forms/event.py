from datetime import datetime, timedelta

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Fieldset, Layout
from django import forms
from django.core.validators import RegexValidator
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from trips.forms.base import (
    ADDRESS_RESULTS_HTML,
    TAG_RESULTS_HTML,
    urlfields_assume_https,
)
from trips.models import (
    Event,
    Experience,
    Meal,
)


class EventForm(forms.ModelForm):
    start_time = forms.TimeField(
        required=False,
        label=_("Start time"),
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    duration = forms.ChoiceField(
        choices=[
            (
                i * 30,
                (datetime.min + timedelta(minutes=i * 30)).strftime("%H h %M min")
                if i > 0
                else _("Not specified"),
            )
            for i in range(16)
        ],
        label=_("Duration"),
        initial=0,
        required=False,
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
        model = Event
        fields = [
            "name",
            "city",
            "address",
            "latitude",
            "longitude",
            "start_time",
            "duration",
            "website",
            "phone_number",
        ]
        formfield_callback = urlfields_assume_https
        labels = {
            "address": _("Address"),
            "website": _("Website"),
            "tag": _("Tag"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Name")}),
            "city": forms.TextInput(attrs={"placeholder": _("City")}),
            "website": forms.TextInput(attrs={"placeholder": _("Website")}),
            "address": forms.TextInput(attrs={"placeholder": _("Address")}),
            "tag": forms.TextInput(attrs={"placeholder": _("Tag"), "maxlength": "20"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
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
        if self.instance.pk and self.instance.estimated_duration:
            duration_minutes = int(
                self.instance.estimated_duration.total_seconds() // 60
            )
            self.initial["duration"] = duration_minutes

        # Opening hours dynamic fields
        days = [
            ("monday", _("Monday")),
            ("tuesday", _("Tuesday")),
            ("wednesday", _("Wednesday")),
            ("thursday", _("Thursday")),
            ("friday", _("Friday")),
            ("saturday", _("Saturday")),
            ("sunday", _("Sunday")),
        ]
        for key, _label in days:
            self.fields[f"{key}_closed"] = forms.BooleanField(
                required=False,
                label=_("Closed"),
            )
            self.fields[f"{key}_open"] = forms.TimeField(
                required=False,
                label="",
                widget=forms.TimeInput(
                    attrs={"type": "time", "placeholder": _("Open")}
                ),
            )
            self.fields[f"{key}_close"] = forms.TimeField(
                required=False,
                label="",
                widget=forms.TimeInput(
                    attrs={"type": "time", "placeholder": _("Close")}
                ),
            )

        # Defaults: assume closed for all days
        for key, _label in days:
            self.initial[f"{key}_closed"] = True
            self.fields[f"{key}_closed"].initial = True

        # Populate initial from instance.opening_hours
        oh = getattr(self.instance, "opening_hours", None)
        if isinstance(oh, dict):
            for key, _label in days:
                day_data = oh.get(key)
                if day_data and day_data.get("open") and day_data.get("close"):
                    # Mark as open and set times
                    self.initial[f"{key}_closed"] = False
                    self.fields[f"{key}_closed"].initial = False
                    self.initial[f"{key}_open"] = day_data.get("open")
                    self.initial[f"{key}_close"] = day_data.get("close")
        elif oh in ("", None):
            # Special case: empty string means not configured yet -> all checkboxes unchecked and inputs visible
            for key, _label in days:
                self.initial[f"{key}_closed"] = False
                self.fields[f"{key}_closed"].initial = False

        self.helper = FormHelper()
        self.helper.form_tag = False
        layout_fields += [
            Div(
                Field("address"),
                HTML("""
                    <span id="address-spinner" class="absolute right-2 top-1/2 -translate-y-1/2">
                        <span class="loading loading-bars loading-lg text-primary mt-3.5 htmx-indicator"></span>
                    </span>
                    """),
                css_class="relative sm:col-span-4",
            ),
            HTML(ADDRESS_RESULTS_HTML),
            Field("start_time", wrapper_class="sm:col-span-1"),
            Field(
                "duration",
                wrapper_class="sm:col-span-1",
            ),
            Field(
                "tag",
                wrapper_class="sm:col-span-2",
                **{
                    "hx-get": reverse_lazy("trips:tag-suggestions"),
                    "hx-trigger": "input delay:300ms",
                    "hx-target": "#tag-results",
                    "hx-include": "[name='tag']",
                },
            ),
            HTML(TAG_RESULTS_HTML),
        ]
        if "type" in self.fields:
            layout_fields.append(
                Field(
                    "type",
                    css_class="select select-primary",
                    wrapper_class="sm:col-span-2",
                )
            )
        layout_fields += [
            Field("website", wrapper_class="sm:col-span-4"),
            Field("phone_number", wrapper_class="sm:col-span-4"),
            HTML(
                """
                    <div x-data="{ openHours: false }" x-on:click.stop class="sm:col-span-4">
                        <div class="flex items-center gap-4 mt-2 py-2 cursor-pointer" @click.stop="openHours = !openHours">
                            <h2 class="text-sm font-semibold">%s</h2>
                            <button type="button" @click.stop="openHours = !openHours" class="btn btn-xs btn-ghost me-2">
                                <i class="" :class="openHours ? 'ph-bold ph-caret-up i-md text-base-content/60' : 'ph-bold ph-caret-down i-md text-base-content/60'"></i>
                            </button>
                        </div>
                        <div x-show="openHours" >
                 """
                % _("Opening hours")
            ),
        ]
        # Add per-day fields to layout using Fieldset for legend
        for key, label in days:
            if self.is_bound:
                bound_val = self.data.get(f"{key}_closed")
                is_checked = str(bound_val).lower() in {"on", "true", "1", "checked"}
            else:
                is_checked = bool(self.initial.get(f"{key}_closed"))
            checked_attr = ' checked="checked"' if is_checked else ""
            closed_txt = _("Closed")

            layout_fields += [
                Div(
                    Fieldset(
                        "",  # Empty legend
                        Div(  # New flex div for label and checkbox
                            HTML(
                                f'<h3 class="text-base font-semibold">{label}</h3>'
                            ),  # Custom label
                            HTML(
                                f'<input x-model="closed" type="checkbox" name="{key}_closed" id="id_{key}_closed" class="h-3 w-3 text-primary" {checked_attr}><label for="id_{key}_closed">{closed_txt}</label>'
                            ),
                            css_class="flex items-center gap-4 mb-2",  # Flex classes
                        ),
                        Div(
                            Field(f"{key}_open"),
                            Field(f"{key}_close"),
                            css_class="grid grid-cols-2 gap-2",
                            **{"x-show": "!closed", "x-cloak": ""},
                        ),
                    ),
                    **{"x-data": f"{{ closed: {str(is_checked).lower()} }}"},
                    css_class="sm:col-span-4",
                )
            ]
        layout_fields += [
            HTML("""
                                    </div>
                                </div>
                                """)
        ]
        self.helper.layout = Layout(*layout_fields)

    def save(self, commit=True):
        instance = super().save(commit=False)
        duration_minutes = int(self.cleaned_data.get("duration") or 0)
        instance.estimated_duration = (
            timedelta(minutes=duration_minutes) if duration_minutes > 0 else None
        )

        # Build opening_hours JSON from form fields
        opening_hours = {}
        days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        for key in days:
            if self.cleaned_data.get(f"{key}_closed"):
                continue
            open_v = self.cleaned_data.get(f"{key}_open")
            close_v = self.cleaned_data.get(f"{key}_close")
            if open_v and close_v:
                opening_hours[key] = {
                    "open": open_v.strftime("%H:%M"),
                    "close": close_v.strftime("%H:%M"),
                }
        instance.opening_hours = opening_hours or None

        if commit:  # pragma: no cover
            instance.save()
        return instance


class ExperienceForm(EventForm):
    class Meta(EventForm.Meta):
        model = Experience
        fields = EventForm.Meta.fields + ["tag"]
        labels = {
            **EventForm.Meta.labels,
            "tag": _("Experience type"),
        }
        widgets = {
            **EventForm.Meta.widgets,
            "tag": forms.TextInput(
                attrs={"placeholder": _("Experience type"), "maxlength": "20"}
            ),
        }


class MealForm(EventForm):
    class Meta(EventForm.Meta):
        model = Meal
        fields = EventForm.Meta.fields + ["type"]
        labels = {
            **EventForm.Meta.labels,
            "type": _("Meal Type"),
        }
        widgets = {
            **EventForm.Meta.widgets,
            "type": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = Meal.Type.choices


class NoteForm(forms.ModelForm):
    """
    Form to edit the notes field of an Event instance.
    """

    notes = forms.CharField(
        label=_("Notes"),
        widget=forms.Textarea(attrs={"placeholder": _("Add notes...")}),
        required=True,
    )

    class Meta:
        model = Event
        fields = ("notes",)

    def __init__(self, *args, **kwargs):
        """
        Initialize the NoteForm for editing the notes field of an Event.
        """
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Field("notes", css_class="fl-textarea"),
                css_class="sm:col-span-2",
            ),
        )
