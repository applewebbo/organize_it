from datetime import date, datetime, timedelta

import geocoder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Fieldset, Layout
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from .models import Day, Event, Experience, Link, Meal, Stay, Transport, Trip


def urlfields_assume_https(db_field, **kwargs):
    """
    ModelForm.Meta.formfield_callback function to assume HTTPS for scheme-less
    domains in URLFields.
    """
    if isinstance(db_field, models.URLField):
        kwargs["assume_scheme"] = "https"
    return db_field.formfield(**kwargs)


class TripForm(forms.ModelForm):
    title = forms.CharField(label=_("Title"))
    description = forms.CharField(
        widget=forms.Textarea(), label=_("Description"), required=False
    )
    destination = forms.CharField(label=_("Destination"))
    start_date = forms.DateField(
        label=_("Start date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        label=_("End date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Trip
        fields = ["title", "destination", "description", "start_date", "end_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        validate_url = reverse("trips:validate-dates")
        htmx_attrs = {
            "hx-post": validate_url,
            "hx-trigger": "change",
            "hx-target": "#validate_dates",
            "hx-include": "#id_start_date,#id_end_date",
        }
        self.fields["start_date"].widget.attrs.update(htmx_attrs)
        self.fields["end_date"].widget.attrs.update(htmx_attrs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "title",
                css_class="w-full",
            ),
            Div(
                "destination",
                css_class="w-full",
            ),
            Div(
                Field("description", css_class="fl-textarea"),
                css_class="sm:col-span-2",
            ),
            Div(
                "start_date",
                css_class="w-full",
            ),
            Div(
                "end_date",
                css_class="w-full",
            ),
            Div(
                HTML('<div id="validate_dates"></div>'),
                css_class="sm:col-span-2",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("start_date")
            and cleaned_data.get("end_date")
            and cleaned_data.get("start_date") > cleaned_data.get("end_date")
        ):
            raise ValidationError(_("End date must be after start date"))
        return cleaned_data

    def clean_start_date(self):
        start_date = self.cleaned_data.get("start_date")
        if start_date and start_date < date.today():
            raise ValidationError(_("Start date must be after today"))
        return start_date

    def clean_destination(self):
        destination = self.cleaned_data.get("destination")
        g = geocoder.mapbox(destination)
        if not g.ok:
            raise ValidationError(_("Destination not found"))
        return destination


class TripDateUpdateForm(forms.ModelForm):
    start_date = forms.DateField(
        label=_("Start date"),
        required=False,
    )
    end_date = forms.DateField(
        label=_("End date"),
        required=False,
    )

    class Meta:
        model = Trip
        fields = (
            "start_date",
            "end_date",
        )

    def __init__(self, *args, **kwargs):
        """
        Initialize the form and set initial values for start_date and end_date
        from the instance if available.
        """
        super().__init__(*args, **kwargs)

        # Detect the current language
        current_language = get_language()

        # Set the date format dynamically
        if current_language == "en":
            date_format = "%m/%d/%Y"  # MM/DD/YYYY for English
        elif current_language == "it":
            date_format = "%d/%m/%Y"  # DD/MM/YYYY for Italian
        else:
            date_format = "%Y-%m-%d"  # Default to ISO format

        # Update the widget and input_formats for both fields
        self.fields["start_date"].widget = forms.DateInput(format=date_format)
        self.fields["start_date"].input_formats = [date_format]
        self.fields["end_date"].widget = forms.DateInput(format=date_format)
        self.fields["end_date"].input_formats = [date_format]

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Field("start_date", autocomplete="Inizio"),
                css_class="w-full",
            ),
            Div(
                Field("end_date", autocomplete="Fine"),
                css_class="w-full",
            ),
        )

    def clean(self):
        """
        Validate that the end date is after the start date.
        """
        cleaned_data = super().clean()
        if (
            cleaned_data.get("start_date")
            and cleaned_data.get("end_date")
            and cleaned_data.get("start_date") > cleaned_data.get("end_date")
        ):
            raise ValidationError("End date must be after start date")
        return cleaned_data


class LinkForm(forms.ModelForm):
    class Meta:
        model = Link
        fields = ["title", "url"]
        formfield_callback = urlfields_assume_https
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Title"}),
            "url": forms.URLInput(attrs={"placeholder": "URL"}),
        }
        labels = {
            "title": "Title",
            "url": "URL",
        }
        help_texts = {
            "title": "Please provide a name otherwise the Url will be used as a name"
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "title",
            "url",
        )


ADDRESS_RESULTS_HTML = """
    <div id="address-results" class="sm:col-span-4">
    <!-- Address Results will be added here.. -->
    </div>
"""


class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = [
            "type",
            "origin_city",
            "origin_address",
            "destination_city",
            "destination_address",
            "start_time",
            "end_time",
            "company",
            "booking_reference",
            "ticket_url",
            "price",
            "website",
        ]
        formfield_callback = urlfields_assume_https
        labels = {
            "origin_city": _("Origin City"),
            "origin_address": _("Origin Address"),
            "destination_city": _("Destination City"),
            "destination_address": _("Destination Address"),
            "start_time": _("Departure Time"),
            "end_time": _("Arrival Time"),
            "company": _("Company"),
            "booking_reference": _("Booking Reference"),
            "ticket_url": _("Ticket URL"),
            "price": _("Price"),
            "website": _("Website"),
            "type": _("Type"),
        }
        widgets = {
            "type": forms.Select(),
            "origin_city": forms.TextInput(attrs={"placeholder": "Origin City"}),
            "origin_address": forms.TextInput(
                attrs={"placeholder": "Origin Address (optional)"}
            ),
            "destination_city": forms.TextInput(
                attrs={"placeholder": "Destination City"}
            ),
            "destination_address": forms.TextInput(
                attrs={"placeholder": "Destination Address (optional)"}
            ),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "company": forms.TextInput(attrs={"placeholder": "Transport Company"}),
            "booking_reference": forms.TextInput(
                attrs={"placeholder": "Booking Reference"}
            ),
            "ticket_url": forms.TextInput(attrs={"placeholder": "Ticket URL"}),
            "price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "website": forms.TextInput(attrs={"placeholder": "Website"}),
        }

    def __init__(self, *args, **kwargs):
        trip = kwargs.pop("trip", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["type"].choices = Transport.Type.choices

        # Prepopulate origin_city with trip destination if available
        if trip and not self.instance.pk:
            self.fields["origin_city"].initial = trip.destination

        self.helper.layout = Layout(
            Div(
                "origin_city",
                css_class="sm:col-span-2",
            ),
            Div(
                "origin_address",
                css_class="sm:col-span-2",
            ),
            Div(
                "destination_city",
                css_class="sm:col-span-2",
            ),
            Div(
                "destination_address",
                css_class="sm:col-span-2",
            ),
            Div(
                "start_time",
                css_class="sm:col-span-2",
            ),
            Div(
                "end_time",
                css_class="sm:col-span-2",
            ),
            Field("type", css_class="select select-primary w-full"),
            Div(
                "website",
                css_class="sm:col-span-3",
            ),
            Div(
                "company",
                css_class="sm:col-span-2",
            ),
            Div(
                "booking_reference",
                css_class="sm:col-span-2",
            ),
            Div(
                "ticket_url",
                css_class="sm:col-span-2",
            ),
            Div(
                "price",
                css_class="sm:col-span-2",
            ),
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set name based on origin and destination cities
        instance.name = f"{self.cleaned_data['origin_city']} → {self.cleaned_data['destination_city']}"
        # Ensure address field from parent Event is populated (use origin_address or city)
        instance.address = (
            self.cleaned_data.get("origin_address") or self.cleaned_data["origin_city"]
        )
        if commit:
            instance.save()
        return instance


class EventForm(forms.ModelForm):
    duration = forms.ChoiceField(
        choices=[
            (
                i * 30,
                (datetime.min + timedelta(minutes=i * 30)).strftime("%H h %M min"),
            )
            for i in range(16)
        ],
        label=_("Duration"),
        initial=60,
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
            "start_time",
            "duration",
            "website",
            "phone_number",
        ]
        formfield_callback = urlfields_assume_https
        labels = {
            "address": _("Address"),
            "start_time": _("Start Time"),
            "website": _("Website"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Name")}),
            "city": forms.TextInput(attrs={"placeholder": _("City")}),
            "website": forms.TextInput(attrs={"placeholder": _("Website")}),
            "address": forms.TextInput(attrs={"placeholder": _("Address")}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
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
        if self.instance.pk and self.instance.end_time and self.instance.start_time:
            start_time = datetime.combine(date.today(), self.instance.start_time)
            end_time = datetime.combine(date.today(), self.instance.end_time)
            duration = (end_time - start_time).total_seconds() // 60
            self.initial["duration"] = int(duration)

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
            Field(
                "start_time",
                x_ref="startTime",
                **{"x-on:change": "checkOverlap()"},
                wrapper_class="sm:col-span-2",
            ),
            Field(
                "duration",
                x_ref="duration",
                **{"x-on:change": "checkOverlap()"},
                wrapper_class="sm:col-span-1",
            ),
            Field("type", css_class="select select-primary"),
            Div(id="overlap-warning", css_class="sm:col-span-4"),
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
        # convert duration to end_time
        duration = self.cleaned_data.get("duration")
        start_time = datetime.combine(date.today(), self.cleaned_data["start_time"])
        end_time = start_time + timedelta(minutes=int(duration))
        instance.end_time = end_time.time()

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
        fields = EventForm.Meta.fields + ["type"]
        labels = {
            **EventForm.Meta.labels,
            "type": _("Type"),
        }
        widgets = {
            **EventForm.Meta.widgets,
            "type": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = Experience.Type.choices


class MealForm(EventForm):
    class Meta(EventForm.Meta):
        model = Meal
        fields = EventForm.Meta.fields + ["type"]
        labels = {
            **EventForm.Meta.labels,
            "type": _("Type"),
        }
        widgets = {
            **EventForm.Meta.widgets,
            "type": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = Meal.Type.choices


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
            "apply_to_days",
        ]
        formfield_callback = urlfields_assume_https
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Name")}),
            "website": forms.TextInput(attrs={"placeholder": _("Website")}),
            "address": forms.TextInput(attrs={"placeholder": _("Address")}),
            "check_in": forms.TimeInput(attrs={"type": "time"}),
            "check_out": forms.TimeInput(attrs={"type": "time"}),
            "cancellation_date": forms.DateInput(attrs={"type": "date"}),
            "phone_number": forms.TextInput(attrs={"placeholder": _("Phone number")}),
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
        self.fields["apply_to_days"].label_from_instance = (
            lambda obj: f"{_('Day')} {obj.number}"
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


class EventChangeTimesForm(forms.ModelForm):
    start_time = forms.TimeField(
        label="Start Time",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    end_time = forms.TimeField(
        label="End Time",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    class Meta:
        model = Event
        fields = ["start_time", "end_time"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "start_time",
                css_class="sm:col-span-2",
            ),
            Div(
                "end_time",
                css_class="sm:col-span-2",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time and start_time >= end_time:
            raise ValidationError("End time must be after start time")

        return cleaned_data


class NoteForm(forms.ModelForm):
    """
    Form to edit the notes field of an Event instance.
    """

    notes = forms.CharField(
        label="Notes",
        widget=forms.Textarea(attrs={"placeholder": "Add notes..."}),
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


class AddNoteToStayForm(forms.ModelForm):
    """
    Form to add notes to a Stay instance.
    """

    notes = forms.CharField(
        label="Notes",
        widget=forms.Textarea(attrs={"placeholder": "Add notes..."}),
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
