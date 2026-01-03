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

from .models import (
    Day,
    Event,
    Experience,
    Link,
    MainTransfer,
    Meal,
    Stay,
    Transport,
    Trip,
)
from .utils import get_airport_by_iata, get_station_by_id


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
    selected_photo_id = forms.CharField(
        required=False, widget=forms.HiddenInput(), initial=""
    )

    class Meta:
        model = Trip
        fields = [
            "title",
            "destination",
            "description",
            "start_date",
            "end_date",
            "image",
        ]

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

        # Configure image upload field
        self.fields["image"].required = False
        self.fields["image"].widget.attrs.update(
            {"accept": "image/*", "x-show": "imageMode === 'upload'"}
        )

        trip_id = self.instance.pk if self.instance.pk else "new"

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
            # Trip Image Section
            # HTML("<hr class='my-4 sm:col-span-2'>"),
            HTML(
                '<div class="divider my-4 sm:col-span-2"><span class="text-gray-400">'
                + str(_("Trip Image"))
                + "</span></div>"
            ),
            HTML(
                f'<input type="hidden" name="trip_id" value="{trip_id}" id="trip_id">'
            ),
            Field("selected_photo_id"),
            # Mode Toggle
            HTML(
                """
            <div class="mb-4 sm:col-span-2" x-data="{ showDestinationError: false }">
                <div class="flex gap-2">
                    <button type="button"
                            class="btn btn-outline dark:btn-soft"
                            :class="imageMode === 'search' ? 'btn-primary' : ''"
                            @click="
                                const destValue = document.querySelector('[name=destination]').value;
                                if (!destValue || destValue.trim() === '') {
                                    showDestinationError = true;
                                    document.querySelector('[name=destination]').classList.add('input-error', 'border-error', 'border-2');
                                    setTimeout(() => {
                                        showDestinationError = false;
                                        document.querySelector('[name=destination]').classList.remove('input-error', 'border-error', 'border-2');
                                    }, 5000);
                                    return;
                                }
                                imageMode = 'search';
                                if (destValue !== lastSearchQuery) {
                                    lastSearchQuery = destValue;
                                    $el.dispatchEvent(new Event('doSearch'));
                                }
                            "
                            hx-post="""
                + f'"{reverse("trips:search-images")}"'
                + """
                            hx-trigger="doSearch"
                            hx-target="#image-results"
                            hx-indicator="#search-spinner"
                            hx-include="[name='destination'], [name='trip_id']">
                        <i class="ph-bold ph-magnifying-glass"></i>
                        """
                + str(_("Search Unsplash"))
                + """
                    </button>
                    <button type="button"
                            class="btn btn-outline dark:btn-soft"
                            :class="imageMode === 'upload' ? 'btn-primary' : ''"
                            @click="imageMode = 'upload'">
                        <i class="ph-bold ph-upload"></i>
                        """
                + str(_("Upload Image"))
                + """
                    </button>
                </div>
                <div x-show="showDestinationError"
                     x-transition
                     class="mt-2 text-sm text-error">
                    """
                + str(_("Please fill in the destination field to search for images"))
                + """
                </div>
            </div>
            """
            ),
            # Search results section
            Div(
                HTML(
                    '<div id="search-spinner" class="loading loading-spinner htmx-indicator"></div>'
                ),
                HTML('<div id="image-results" class="mt-4"></div>'),
                css_class="search-section sm:col-span-2",
                x_show="imageMode === 'search'",
            ),
            # Upload section
            Div(
                Field("image", wrapper_class="w-full"),
                HTML('<div id="upload-preview" class="mt-4"></div>'),
                css_class="upload-section sm:col-span-2",
                x_show="imageMode === 'upload'",
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
            "origin_city": _("City"),
            "origin_address": _("Address"),
            "destination_city": _("City"),
            "destination_address": _("Address"),
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
            "origin_city": forms.TextInput(attrs={"placeholder": _("Origin City")}),
            "origin_address": forms.TextInput(attrs={"placeholder": _("Address")}),
            "destination_city": forms.TextInput(
                attrs={"placeholder": _("Destination City")}
            ),
            "destination_address": forms.TextInput(attrs={"placeholder": _("Address")}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "company": forms.TextInput(attrs={"placeholder": _("Company")}),
            "booking_reference": forms.TextInput(
                attrs={"placeholder": _("Booking Reference")}
            ),
            "ticket_url": forms.TextInput(attrs={"placeholder": _("Ticket URL")}),
            "price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
            "website": forms.TextInput(attrs={"placeholder": _("Website")}),
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
            self.fields["destination_city"].initial = trip.destination

        # Store trip_id for HTMX requests
        trip_id = trip.pk if trip else ""
        trip_addresses_url = reverse("trips:get-trip-addresses")

        self.helper.layout = Layout(
            HTML(
                f'<input type="hidden" name="trip_id" value="{trip_id}" id="trip_id">'
            ),
            Fieldset(
                _("Origin"),
                "origin_city",
                "origin_address",
                HTML(
                    f"""
                    <div class="sm:col-span-2">
                        <div class="flex items-center gap-4 -mt-6 mb-2 cursor-pointer" @click.stop="showOriginSuggestions = !showOriginSuggestions">
                            <h2 class="text-sm font-semibold">Quick fill from trip locations</h2>
                            <button type="button" @click.stop="showOriginSuggestions = !showOriginSuggestions" class="btn btn-xs btn-ghost me-2">
                                <i class="" :class="showOriginSuggestions ? 'ph-bold ph-caret-up i-md text-base-content/60' : 'ph-bold ph-caret-down i-md text-base-content/60'"></i>
                            </button>
                        </div>
                        <div x-show="showOriginSuggestions"
                             x-collapse
                             id="origin-trip-addresses"
                             hx-post="{trip_addresses_url}"
                             hx-trigger="intersect once"
                             hx-target="#origin-trip-addresses"
                             hx-swap="innerHTML"
                             hx-include="#trip_id"
                             hx-vals='{{"field_type": "origin"}}'>
                        </div>
                    </div>
                    """
                ),
                css_class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:col-span-4",
            ),
            Fieldset(
                _("Destination"),
                "destination_city",
                "destination_address",
                HTML(
                    f"""
                    <div class="sm:col-span-2">
                        <div class="flex items-center gap-4 -mt-6 mb-2 cursor-pointer" @click.stop="showDestinationSuggestions = !showDestinationSuggestions">
                            <h2 class="text-sm font-semibold">Quick fill from trip locations</h2>
                            <button type="button" @click.stop="showDestinationSuggestions = !showDestinationSuggestions" class="btn btn-xs btn-ghost me-2">
                                <i class="" :class="showDestinationSuggestions ? 'ph-bold ph-caret-up i-md text-base-content/60' : 'ph-bold ph-caret-down i-md text-base-content/60'"></i>
                            </button>
                        </div>
                        <div x-show="showDestinationSuggestions"
                             x-collapse
                             id="destination-trip-addresses"
                             hx-post="{trip_addresses_url}"
                             hx-trigger="intersect once"
                             hx-target="#destination-trip-addresses"
                             hx-swap="innerHTML"
                             hx-include="#trip_id"
                             hx-vals='{{"field_type": "destination"}}'>
                        </div>
                    </div>
                    """
                ),
                css_class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:col-span-4",
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
            HTML(
                """
                    <div x-data="{ openDetails: false }" x-on:click.stop class="sm:col-span-4">
                        <div class="flex items-center gap-4 mt-2 py-2 cursor-pointer" @click.stop="openDetails = !openDetails">
                            <h2 class="text-sm font-semibold">%s</h2>
                            <button type="button" @click.stop="openDetails = !openDetails" class="btn btn-xs btn-ghost me-2">
                                <i class="" :class="openDetails ? 'ph-bold ph-caret-up i-md text-base-content/60' : 'ph-bold ph-caret-down i-md text-base-content/60'"></i>
                            </button>
                        </div>
                        <div x-show="openDetails" >
                 """
                % _("Booking Reference (optional)")
            ),
            Div(
                "company",
                "booking_reference",
                "ticket_url",
                "price",
                css_class="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:col-span-4",
            ),
            HTML("""
                                    </div>
                                </div>
                                """),
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


# ==================== MAIN TRANSFER FORMS ====================


class MainTransferForm(forms.ModelForm):
    """Base form for main transfers (arrival/departure)"""

    class Meta:
        model = Transport
        fields = [
            "type",
            "direction",
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
            "type": _("Transport Type"),
        }
        widgets = {
            "type": forms.Select(attrs={"class": "select select-primary"}),
            "direction": forms.HiddenInput(),
            "origin_city": forms.TextInput(
                attrs={"class": "input input-bordered", "placeholder": _("City")}
            ),
            "origin_address": forms.TextInput(
                attrs={"class": "input input-bordered", "placeholder": _("Address")}
            ),
            "destination_city": forms.TextInput(
                attrs={"class": "input input-bordered", "placeholder": _("City")}
            ),
            "destination_address": forms.TextInput(
                attrs={"class": "input input-bordered", "placeholder": _("Address")}
            ),
            "start_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "end_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "company": forms.TextInput(
                attrs={"class": "input input-bordered", "placeholder": _("Company")}
            ),
            "booking_reference": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": _("Booking Reference"),
                }
            ),
            "ticket_url": forms.URLInput(
                attrs={"class": "input input-bordered", "placeholder": _("Ticket URL")}
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": "0.00",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop("trip", None)
        self.direction = kwargs.pop("direction", None)
        super().__init__(*args, **kwargs)

        # Set initial direction if provided (from URL parameter)
        if self.direction and not self.instance.pk:
            self.fields["direction"].initial = self.direction

        # Prepopulate destination with trip destination
        if self.trip and not self.instance.pk:
            self.fields["destination_city"].initial = self.trip.destination

        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean(self):
        cleaned_data = super().clean()
        # Set is_main_transfer and trip before model validation runs
        self.instance.is_main_transfer = True
        self.instance.trip = self.trip
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.is_main_transfer = True
        instance.day = None  # Main transfers never have a day
        instance.category = Transport.Category.TRANSPORT
        instance.name = (
            f"{self.cleaned_data['origin_city']} → "
            f"{self.cleaned_data['destination_city']}"
        )

        if commit:
            instance.save()
        return instance


class FlightSpecificForm(forms.Form):
    """Fields specific to flight transfers"""

    flight_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Flight Number"),
        widget=forms.TextInput(
            attrs={
                "placeholder": "AZ1234",
                "class": "input input-bordered input-sm",
            }
        ),
    )
    gate = forms.CharField(
        max_length=10,
        required=False,
        label=_("Gate"),
        widget=forms.TextInput(
            attrs={"placeholder": "A12", "class": "input input-bordered input-sm"}
        ),
    )
    terminal = forms.CharField(
        max_length=10,
        required=False,
        label=_("Terminal"),
        widget=forms.TextInput(
            attrs={"placeholder": "T1", "class": "input input-bordered input-sm"}
        ),
    )
    checked_baggage = forms.IntegerField(
        required=False,
        min_value=0,
        label=_("Checked Baggage"),
        widget=forms.NumberInput(
            attrs={"placeholder": "0", "class": "input input-bordered input-sm"}
        ),
    )
    company_link = forms.URLField(
        required=False,
        label=_("Airline Website"),
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://...",
                "class": "input input-bordered input-sm",
            }
        ),
    )


class TrainSpecificForm(forms.Form):
    """Fields specific to train transfers"""

    train_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Train Number"),
        widget=forms.TextInput(
            attrs={
                "placeholder": "FR9612",
                "class": "input input-bordered input-sm",
            }
        ),
    )
    carriage = forms.CharField(
        max_length=10,
        required=False,
        label=_("Carriage"),
        widget=forms.TextInput(
            attrs={"placeholder": "7", "class": "input input-bordered input-sm"}
        ),
    )
    seat = forms.CharField(
        max_length=10,
        required=False,
        label=_("Seat"),
        widget=forms.TextInput(
            attrs={"placeholder": "42A", "class": "input input-bordered input-sm"}
        ),
    )
    platform = forms.CharField(
        max_length=10,
        required=False,
        label=_("Platform"),
        widget=forms.TextInput(
            attrs={"placeholder": "3", "class": "input input-bordered input-sm"}
        ),
    )
    company_link = forms.URLField(
        required=False,
        label=_("Train Company Website"),
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://...",
                "class": "input input-bordered input-sm",
            }
        ),
    )


class CarSpecificForm(forms.Form):
    """Fields specific to car/rental transfers"""

    is_rental = forms.BooleanField(
        required=False,
        label=_("Rental Car"),
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
    )
    license_plate = forms.CharField(
        max_length=20,
        required=False,
        label=_("License Plate"),
        widget=forms.TextInput(
            attrs={
                "placeholder": "AB123CD",
                "class": "input input-bordered input-sm",
            }
        ),
    )
    car_type = forms.CharField(
        max_length=50,
        required=False,
        label=_("Car Type"),
        widget=forms.TextInput(
            attrs={
                "placeholder": "Sedan, SUV, etc.",
                "class": "input input-bordered input-sm",
            }
        ),
    )
    rental_booking_reference = forms.CharField(
        max_length=50,
        required=False,
        label=_("Rental Booking Reference"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Only if rental"),
                "class": "input input-bordered input-sm",
            }
        ),
    )
    company_link = forms.URLField(
        required=False,
        label=_("Rental Company Website"),
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://...",
                "class": "input input-bordered input-sm",
            }
        ),
    )


class MainTransferCombinedForm(MainTransferForm):
    """Combined form with dynamically added type-specific fields"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get transport type from form data or instance
        transport_type = None
        if self.data:
            transport_type = self.data.get("type")
            if transport_type:
                transport_type = int(transport_type)
        elif self.instance.pk:
            transport_type = self.instance.type

        # Add type-specific fields based on transport type
        if transport_type == Transport.Type.PLANE:
            self._add_flight_fields()
        elif transport_type == Transport.Type.TRAIN:
            self._add_train_fields()
        elif transport_type == Transport.Type.CAR:
            self._add_car_fields()

    def _add_flight_fields(self):
        """Add flight-specific fields to the form"""
        flight_form = FlightSpecificForm()
        for field_name, field in flight_form.fields.items():
            prefixed_name = f"specific_{field_name}"
            self.fields[prefixed_name] = field

            # Populate with existing data if editing
            if self.instance.pk and self.instance.type_specific_data:
                field.initial = self.instance.type_specific_data.get(field_name)

    def _add_train_fields(self):
        """Add train-specific fields to the form"""
        train_form = TrainSpecificForm()
        for field_name, field in train_form.fields.items():
            prefixed_name = f"specific_{field_name}"
            self.fields[prefixed_name] = field

            # Populate with existing data if editing
            if self.instance.pk and self.instance.type_specific_data:
                field.initial = self.instance.type_specific_data.get(field_name)

    def _add_car_fields(self):
        """Add car-specific fields to the form"""
        car_form = CarSpecificForm()
        for field_name, field in car_form.fields.items():
            prefixed_name = f"specific_{field_name}"
            self.fields[prefixed_name] = field

            # Populate with existing data if editing
            if self.instance.pk and self.instance.type_specific_data:
                field.initial = self.instance.type_specific_data.get(field_name)

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Extract and save type-specific data
        specific_data = {}
        for field_name in list(self.fields.keys()):
            if field_name.startswith("specific_"):
                key = field_name.replace("specific_", "")
                value = self.cleaned_data.get(field_name)
                # Only save non-empty values
                if value not in [None, "", []]:
                    specific_data[key] = value

        instance.type_specific_data = specific_data

        if commit:
            instance.save()
        return instance


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


# =============================================================================
# MAIN TRANSFER FORMS (for trip arrival/departure)
# =============================================================================


class MainTransferBaseForm(forms.ModelForm):
    """
    Base form for MainTransfer - common fields for all transport types.
    Must be extended by type-specific forms.
    """

    direction = forms.ChoiceField(
        choices=MainTransfer.Direction.choices,
        label=_("Direction"),
        widget=forms.RadioSelect(attrs={"class": "radio radio-primary"}),
    )

    class Meta:
        model = MainTransfer
        fields = [
            "direction",
            "start_time",
            "end_time",
            "booking_reference",
            "ticket_url",
            "notes",
        ]
        widgets = {
            "start_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "end_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "booking_reference": forms.TextInput(
                attrs={
                    "class": "input input-bordered",
                    "placeholder": _("Booking reference"),
                }
            ),
            "ticket_url": forms.URLInput(
                attrs={"class": "input input-bordered", "placeholder": "https://..."}
            ),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop("trip", None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.trip:
            instance.trip = self.trip

        # Save type-specific data in JSONField
        type_specific_data = self.get_type_specific_data()
        if type_specific_data:
            instance.type_specific_data = type_specific_data

        if commit:
            instance.save()

        return instance

    def get_type_specific_data(self):
        """
        Override in child forms to populate type_specific_data.
        Returns a dict with type-specific fields.
        """
        return {}


class FlightMainTransferForm(MainTransferBaseForm):
    """Form for flight main transfers with airport autocomplete"""

    # Airport fields (autocomplete with CSV lookup)
    origin_airport = forms.CharField(
        label=_("Departure Airport"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by name or IATA code (e.g., FCO, Rome)"),
                "autocomplete": "off",
                "data-autocomplete-type": "airport",
            }
        ),
        help_text=_("Search for airport by name, city, or IATA code"),
    )

    origin_iata = forms.CharField(
        max_length=10, required=False, widget=forms.HiddenInput()
    )

    destination_airport = forms.CharField(
        label=_("Arrival Airport"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by name or IATA code"),
                "autocomplete": "off",
                "data-autocomplete-type": "airport",
            }
        ),
        help_text=_("Search for airport by name, city, or IATA code"),
    )

    destination_iata = forms.CharField(
        max_length=10, required=False, widget=forms.HiddenInput()
    )

    # Flight-specific fields
    company = forms.CharField(
        max_length=100,
        required=False,
        label=_("Airline"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": _("Airline name")}
        ),
    )

    flight_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Flight Number"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "AZ1234"}
        ),
    )

    terminal = forms.CharField(
        max_length=10,
        required=False,
        label=_("Terminal"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "T1"}
        ),
    )

    company_website = forms.URLField(
        required=False,
        label=_("Airline Website"),
        widget=forms.URLInput(
            attrs={"class": "input input-bordered", "placeholder": "https://..."}
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_airport",
            "origin_iata",
            "destination_airport",
            "destination_iata",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_airport"].initial = self.instance.origin_name
            self.fields["origin_iata"].initial = self.instance.origin_code
            self.fields["destination_airport"].initial = self.instance.destination_name
            self.fields["destination_iata"].initial = self.instance.destination_code

            # Populate type-specific fields
            if self.instance.type_specific_data:
                self.fields["company"].initial = self.instance.company
                self.fields["flight_number"].initial = self.instance.flight_number
                self.fields["terminal"].initial = self.instance.terminal
                self.fields["company_website"].initial = self.instance.company_website

    def clean(self):
        cleaned_data = super().clean()

        # Lookup coordinates from CSV
        origin_iata = cleaned_data.get("origin_iata")
        destination_iata = cleaned_data.get("destination_iata")

        if origin_iata:
            airport = get_airport_by_iata(origin_iata)
            if airport:
                # Store temporarily for save()
                self._origin_coords = (airport["latitude"], airport["longitude"])
            else:
                raise forms.ValidationError("Invalid origin airport IATA code")

        if destination_iata:
            airport = get_airport_by_iata(destination_iata)
            if airport:
                self._destination_coords = (airport["latitude"], airport["longitude"])
            else:
                raise forms.ValidationError("Invalid destination airport IATA code")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Populate model fields
        instance.type = MainTransfer.Type.PLANE
        instance.origin_code = self.cleaned_data["origin_iata"]
        instance.origin_name = self.cleaned_data["origin_airport"]
        instance.destination_code = self.cleaned_data["destination_iata"]
        instance.destination_name = self.cleaned_data["destination_airport"]

        # Coordinates from CSV
        if hasattr(self, "_origin_coords"):
            instance.origin_latitude, instance.origin_longitude = self._origin_coords
        if hasattr(self, "_destination_coords"):
            (
                instance.destination_latitude,
                instance.destination_longitude,
            ) = self._destination_coords

        if commit:
            instance.save()

        return instance

    def get_type_specific_data(self):
        """Populate flight-specific fields in JSONField"""
        data = {}

        if self.cleaned_data.get("company"):
            data["company"] = self.cleaned_data["company"]
        if self.cleaned_data.get("flight_number"):
            data["flight_number"] = self.cleaned_data["flight_number"]
        if self.cleaned_data.get("terminal"):
            data["terminal"] = self.cleaned_data["terminal"]
        if self.cleaned_data.get("company_website"):
            data["company_website"] = self.cleaned_data["company_website"]

        return data


class TrainMainTransferForm(MainTransferBaseForm):
    """Form for train main transfers with station autocomplete"""

    # Station fields (autocomplete with CSV lookup)
    origin_station = forms.CharField(
        label=_("Departure Station"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by station name"),
                "autocomplete": "off",
                "data-autocomplete-type": "station",
            }
        ),
        help_text=_("Search for train station by name"),
    )

    origin_station_id = forms.CharField(
        max_length=20, required=False, widget=forms.HiddenInput()
    )

    destination_station = forms.CharField(
        label=_("Arrival Station"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by station name"),
                "autocomplete": "off",
                "data-autocomplete-type": "station",
            }
        ),
        help_text=_("Search for train station by name"),
    )

    destination_station_id = forms.CharField(
        max_length=20, required=False, widget=forms.HiddenInput()
    )

    # Train-specific fields
    company = forms.CharField(
        max_length=100,
        required=False,
        label=_("Train Operator"),
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Train operator name"),
            }
        ),
    )

    train_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Train Number"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "FR9612"}
        ),
    )

    carriage = forms.CharField(
        max_length=10,
        required=False,
        label=_("Carriage"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "7"}
        ),
    )

    seat = forms.CharField(
        max_length=10,
        required=False,
        label=_("Seat"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "42A"}
        ),
    )

    company_website = forms.URLField(
        required=False,
        label=_("Train Operator Website"),
        widget=forms.URLInput(
            attrs={"class": "input input-bordered", "placeholder": "https://..."}
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_station",
            "origin_station_id",
            "destination_station",
            "destination_station_id",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_station"].initial = self.instance.origin_name
            # Note: station_id is stored in origin_code field (reusing)
            self.fields["origin_station_id"].initial = self.instance.origin_code
            self.fields["destination_station"].initial = self.instance.destination_name
            self.fields[
                "destination_station_id"
            ].initial = self.instance.destination_code

            # Populate type-specific fields
            if self.instance.type_specific_data:
                self.fields["company"].initial = self.instance.company
                self.fields["train_number"].initial = self.instance.train_number
                self.fields["carriage"].initial = self.instance.carriage
                self.fields["seat"].initial = self.instance.seat
                self.fields["company_website"].initial = self.instance.company_website

    def clean(self):
        cleaned_data = super().clean()

        # Lookup coordinates from CSV using station ID
        origin_id = cleaned_data.get("origin_station_id")
        destination_id = cleaned_data.get("destination_station_id")

        if origin_id:
            station = get_station_by_id(origin_id)
            if station:
                self._origin_coords = (station["latitude"], station["longitude"])
            else:
                raise forms.ValidationError("Invalid origin station ID")

        if destination_id:
            station = get_station_by_id(destination_id)
            if station:
                self._destination_coords = (station["latitude"], station["longitude"])
            else:
                raise forms.ValidationError("Invalid destination station ID")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Populate model fields
        instance.type = MainTransfer.Type.TRAIN
        # Note: Reusing origin_code/destination_code fields to store station IDs for trains
        instance.origin_code = self.cleaned_data["origin_station_id"]
        instance.origin_name = self.cleaned_data["origin_station"]
        instance.destination_code = self.cleaned_data["destination_station_id"]
        instance.destination_name = self.cleaned_data["destination_station"]

        # Coordinates from CSV
        if hasattr(self, "_origin_coords"):
            instance.origin_latitude, instance.origin_longitude = self._origin_coords
        if hasattr(self, "_destination_coords"):
            (
                instance.destination_latitude,
                instance.destination_longitude,
            ) = self._destination_coords

        if commit:
            instance.save()

        return instance

    def get_type_specific_data(self):
        """Populate train-specific fields in JSONField"""
        data = {}

        if self.cleaned_data.get("company"):
            data["company"] = self.cleaned_data["company"]
        if self.cleaned_data.get("train_number"):
            data["train_number"] = self.cleaned_data["train_number"]
        if self.cleaned_data.get("carriage"):
            data["carriage"] = self.cleaned_data["carriage"]
        if self.cleaned_data.get("seat"):
            data["seat"] = self.cleaned_data["seat"]
        if self.cleaned_data.get("company_website"):
            data["company_website"] = self.cleaned_data["company_website"]

        return data


class CarMainTransferForm(MainTransferBaseForm):
    """Form for car main transfers with geocoding"""

    # Address fields (geocoding like events)
    origin_address = forms.CharField(
        label=_("Departure Address"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address (street, city, country)"),
            }
        ),
        help_text=_("Full address for geocoding"),
    )

    destination_address = forms.CharField(
        label=_("Arrival Address"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address (street, city, country)"),
            }
        ),
        help_text=_("Full address for geocoding"),
    )

    # Car-specific fields
    company = forms.CharField(
        max_length=100,
        required=False,
        label=_("Rental Company"),
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Rental company name (if applicable)"),
            }
        ),
    )

    is_rental = forms.BooleanField(
        required=False,
        label=_("Rental Car"),
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
    )

    company_website = forms.URLField(
        required=False,
        label=_("Rental Company Website"),
        widget=forms.URLInput(
            attrs={"class": "input input-bordered", "placeholder": "https://..."}
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_address",
            "destination_address",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_address"].initial = self.instance.origin_address
            self.fields[
                "destination_address"
            ].initial = self.instance.destination_address

            # Populate type-specific fields
            if self.instance.type_specific_data:
                self.fields["company"].initial = self.instance.company
                self.fields["is_rental"].initial = self.instance.is_rental
                self.fields["company_website"].initial = self.instance.company_website

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Populate model fields
        instance.type = MainTransfer.Type.CAR
        instance.origin_address = self.cleaned_data["origin_address"]
        instance.destination_address = self.cleaned_data["destination_address"]

        # Geocoding will happen automatically in model save()

        if commit:
            instance.save()

        return instance

    def get_type_specific_data(self):
        """Populate car-specific fields in JSONField"""
        data = {}

        if self.cleaned_data.get("company"):
            data["company"] = self.cleaned_data["company"]
        if self.cleaned_data.get("is_rental"):
            data["is_rental"] = True
        if self.cleaned_data.get("company_website"):
            data["company_website"] = self.cleaned_data["company_website"]

        return data


class OtherMainTransferForm(MainTransferBaseForm):
    """Form for other transport types (bus, boat, taxi, etc.) with geocoding"""

    # Address fields (geocoding like events)
    origin_address = forms.CharField(
        label=_("Departure Location"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address or location name"),
            }
        ),
        help_text=_("Full address for geocoding"),
    )

    destination_address = forms.CharField(
        label=_("Arrival Location"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address or location name"),
            }
        ),
        help_text=_("Full address for geocoding"),
    )

    # Generic fields
    company = forms.CharField(
        max_length=100,
        required=False,
        label=_("Transport Company"),
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Company name (if applicable)"),
            }
        ),
    )

    company_website = forms.URLField(
        required=False,
        label=_("Company Website"),
        widget=forms.URLInput(
            attrs={"class": "input input-bordered", "placeholder": "https://..."}
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_address",
            "destination_address",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_address"].initial = self.instance.origin_address
            self.fields[
                "destination_address"
            ].initial = self.instance.destination_address

            # Populate type-specific fields
            if self.instance.type_specific_data:
                self.fields["company"].initial = self.instance.company
                self.fields["company_website"].initial = self.instance.company_website

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Populate model fields
        instance.type = MainTransfer.Type.OTHER
        instance.origin_address = self.cleaned_data["origin_address"]
        instance.destination_address = self.cleaned_data["destination_address"]

        # Geocoding will happen automatically in model save()

        if commit:
            instance.save()

        return instance

    def get_type_specific_data(self):
        """Populate generic fields in JSONField"""
        data = {}

        if self.cleaned_data.get("company"):
            data["company"] = self.cleaned_data["company"]
        if self.cleaned_data.get("company_website"):
            data["company_website"] = self.cleaned_data["company_website"]

        return data
