from datetime import date, datetime, timedelta

import geocoder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Fieldset, Layout
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from .models import (
    ChecklistItem,
    Day,
    Event,
    Experience,
    Link,
    MainTransfer,
    MainTransferConnection,
    Meal,
    ShareLink,
    Stay,
    StayTransfer,
    Trip,
)
from .widgets import TransportModeRadioSelect


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
    destination = forms.CharField(label=_("Destination"))
    destination_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    destination_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    start_date = forms.DateField(
        label=_("Start date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    end_date = forms.DateField(
        label=_("End date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    selected_photo_id = forms.CharField(
        required=False, widget=forms.HiddenInput(), initial=""
    )

    class Meta:
        model = Trip
        fields = [
            "title",
            "destination",
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

        geocode_city_url = reverse("trips:geocode-city")
        self.fields["destination"].widget.attrs.update(
            {
                "hx-post": geocode_city_url,
                "hx-trigger": "input changed delay:600ms",
                "hx-target": "#city-results-trip",
                "hx-swap": "innerHTML",
            }
        )
        self.fields["destination"].help_text = _(
            "Select from suggestions for accurate geolocation"
        )

        # Configure image upload field
        self.fields["image"].required = False
        self.fields["image"].widget.attrs.update({"accept": "image/*"})

        current_image_url = (
            self.instance.image.url if self.instance.pk and self.instance.image else ""
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
                Field("destination_latitude"),
                Field("destination_longitude"),
                css_class="w-full",
            ),
            Div(
                HTML('<div id="city-results-trip"></div>'),
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
            <div class="sm:col-span-2" x-data="{ showDestinationError: false }">
                <div role="tablist" class="tabs tabs-border tabs-sm">
                    <button type="button"
                            role="tab"
                            class="gap-1 tab"
                            :class="imageMode === 'search' ? 'tab-active' : ''"
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
                            role="tab"
                            class="gap-1 tab"
                            :class="imageMode === 'upload' ? 'tab-active' : ''"
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
                HTML(
                    f"""
                    <div x-data="{{
                        previewUrl: '{current_image_url}',
                        fileName: '',
                        onFileChange(e) {{
                            const file = e.target.files[0];
                            if (!file) return;
                            this.fileName = file.name;
                            const reader = new FileReader();
                            reader.onload = (ev) => {{ this.previewUrl = ev.target.result; }};
                            reader.readAsDataURL(file);
                        }}
                    }}" class="flex flex-col gap-2">
                        <template x-if="previewUrl">
                            <img :src="previewUrl"
                                 class="object-cover w-full h-32 rounded-lg border border-base-300"
                                 alt="preview">
                        </template>
                        <label for="id_image"
                               class="flex gap-2 justify-center items-center w-full h-12 rounded-lg border-2 border-dashed cursor-pointer border-base-300 hover:border-primary hover:bg-base-200">
                            <i class="ph-bold ph-upload-simple text-base-content/50"></i>
                            <span class="text-sm text-base-content/60"
                                  x-text="fileName || '{_("Click to select an image")}'"
                            ></span>
                        </label>
                        <input type="file" name="image" accept="image/*" class="hidden" id="id_image" @change="onFileChange($event)">
                    </div>
                    """
                ),
                css_class="upload-section sm:col-span-2 mt-4",
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
        if start_date and start_date < date.today() and not self.instance.pk:
            raise ValidationError(_("Start date must be after today"))
        return start_date

    def clean_destination(self):
        destination = self.cleaned_data.get("destination")
        g = geocoder.mapbox(destination)
        if not g.ok:
            raise ValidationError(_("Destination not found"))
        return destination


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

TAG_RESULTS_HTML = """
    <div id="tag-results" class="sm:col-start-3 sm:col-span-2 -mt-3">
    </div>
"""


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


class MainTransferBaseForm(forms.ModelForm):
    """
    Base form for MainTransfer - common fields for all transport types.
    Must be extended by type-specific forms.
    """

    direction = forms.ChoiceField(
        choices=MainTransfer.Direction.choices,
        label=_("Direction"),
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = MainTransfer
        fields = [
            "direction",
            "start_time",
            "end_time",
            "notes",
        ]
        labels = {
            "start_time": _("Departure Time"),
            "end_time": _("Arrival Time"),
            "notes": _("Notes"),
        }
        help_texts = {
            "start_time": "",
            "end_time": "",
            "notes": "",
        }
        widgets = {
            "start_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "end_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop("trip", None)
        kwargs.pop("home_address", None)  # Consumed by car/other subforms; ignored here
        super().__init__(*args, **kwargs)
        self.fields["start_time"].required = True
        self.fields["end_time"].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.trip:  # pragma: no cover
            instance.trip = self.trip

        # Save type-specific data in JSONField
        type_specific_data = self.get_type_specific_data()
        if type_specific_data:  # pragma: no cover
            instance.type_specific_data = type_specific_data

        if commit:  # pragma: no cover
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

    origin_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    origin_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

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

    destination_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    destination_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    # Flight-specific fields
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

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_airport",
            "origin_iata",
            "origin_latitude",
            "origin_longitude",
            "destination_airport",
            "destination_iata",
            "destination_latitude",
            "destination_longitude",
        ]

    def __init__(self, *args, **kwargs):
        autocomplete = kwargs.pop("autocomplete", True)
        super().__init__(*args, **kwargs)

        # Add HTMX attributes for airport autocomplete (similar to EventForm geocode)
        if autocomplete:
            search_url_origin = f"{reverse('trips:search-airports')}?field_type=origin"
            search_url_dest = (
                f"{reverse('trips:search-airports')}?field_type=destination"
            )
            origin_htmx_attrs = {
                "hx-post": search_url_origin,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#origin-airport-results",
                "hx-vals": "js:{airport_query: (event && event.target) ? event.target.value : this.value}",
            }
            dest_htmx_attrs = {
                "hx-post": search_url_dest,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#destination-airport-results",
                "hx-vals": "js:{airport_query: (event && event.target) ? event.target.value : this.value}",
            }
            self.fields["origin_airport"].widget.attrs.update(origin_htmx_attrs)
            self.fields["destination_airport"].widget.attrs.update(dest_htmx_attrs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_airport"].initial = self.instance.origin_name
            self.fields["origin_iata"].initial = self.instance.origin_code
            self.fields["destination_airport"].initial = self.instance.destination_name
            self.fields["destination_iata"].initial = self.instance.destination_code

            # Populate type-specific fields
            if self.instance.type_specific_data:
                self.fields["flight_number"].initial = self.instance.flight_number
                self.fields["terminal"].initial = self.instance.terminal

        # Pre-fill from arrival if this is a new departure
        if (
            self.trip
            and not self.instance.pk
            and self.initial.get("direction") == MainTransfer.Direction.DEPARTURE
        ):
            arrival = MainTransfer.objects.filter(
                trip=self.trip,
                direction=MainTransfer.Direction.ARRIVAL,
                type=MainTransfer.Type.PLANE,
            ).first()

            if arrival:
                # Invert origin ↔ destination
                self.fields["origin_airport"].initial = arrival.destination_name
                self.fields["origin_iata"].initial = arrival.destination_code
                self.fields["origin_latitude"].initial = arrival.destination_latitude
                self.fields["origin_longitude"].initial = arrival.destination_longitude

                self.fields["destination_airport"].initial = arrival.origin_name
                self.fields["destination_iata"].initial = arrival.origin_code
                self.fields["destination_latitude"].initial = arrival.origin_latitude
                self.fields["destination_longitude"].initial = arrival.origin_longitude

                # Set flag for message display
                self.prefilled_from_arrival = True

    def clean(self):
        cleaned_data = super().clean()

        # Use coordinate values from hidden fields (populated by autocomplete JS)
        origin_lat = cleaned_data.get("origin_latitude")
        origin_lon = cleaned_data.get("origin_longitude")
        dest_lat = cleaned_data.get("destination_latitude")
        dest_lon = cleaned_data.get("destination_longitude")

        # Store coordinates for save() method
        if origin_lat and origin_lon:
            self._origin_coords = (origin_lat, origin_lon)
        if dest_lat and dest_lon:
            self._destination_coords = (dest_lat, dest_lon)

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

        if self.cleaned_data.get("flight_number"):
            data["flight_number"] = self.cleaned_data["flight_number"]
        if self.cleaned_data.get("terminal"):
            data["terminal"] = self.cleaned_data["terminal"]

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

    origin_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    origin_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

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

    destination_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    destination_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    train_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Train Number"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "FR9612"}
        ),
        help_text=_(
            "Optional. If provided, enables direct train status lookup on Viaggiatreno."
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_station",
            "origin_station_id",
            "origin_latitude",
            "origin_longitude",
            "destination_station",
            "destination_station_id",
            "destination_latitude",
            "destination_longitude",
        ]

    def __init__(self, *args, **kwargs):
        autocomplete = kwargs.pop("autocomplete", True)
        super().__init__(*args, **kwargs)

        # Add HTMX attributes for station autocomplete (similar to EventForm geocode)
        if autocomplete:
            search_url_origin = f"{reverse('trips:search-stations')}?field_type=origin"
            search_url_dest = (
                f"{reverse('trips:search-stations')}?field_type=destination"
            )
            origin_htmx_attrs = {
                "hx-post": search_url_origin,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#origin-station-results",
                "hx-vals": "js:{station_query: (event && event.target) ? event.target.value : this.value}",
            }
            dest_htmx_attrs = {
                "hx-post": search_url_dest,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#destination-station-results",
                "hx-vals": "js:{station_query: (event && event.target) ? event.target.value : this.value}",
            }
            self.fields["origin_station"].widget.attrs.update(origin_htmx_attrs)
            self.fields["destination_station"].widget.attrs.update(dest_htmx_attrs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_station"].initial = self.instance.origin_name
            # Note: station_id is stored in origin_code field (reusing)
            self.fields["origin_station_id"].initial = self.instance.origin_code
            self.fields["destination_station"].initial = self.instance.destination_name
            self.fields[
                "destination_station_id"
            ].initial = self.instance.destination_code
            if self.instance.type_specific_data:
                self.fields["train_number"].initial = self.instance.train_number

        # Pre-fill from arrival if this is a new departure
        if (
            self.trip
            and not self.instance.pk
            and self.initial.get("direction") == MainTransfer.Direction.DEPARTURE
        ):
            arrival = MainTransfer.objects.filter(
                trip=self.trip,
                direction=MainTransfer.Direction.ARRIVAL,
                type=MainTransfer.Type.TRAIN,
            ).first()

            if arrival:
                # Invert origin ↔ destination
                self.fields["origin_station"].initial = arrival.destination_name
                self.fields["origin_station_id"].initial = arrival.destination_code
                self.fields["origin_latitude"].initial = arrival.destination_latitude
                self.fields["origin_longitude"].initial = arrival.destination_longitude

                self.fields["destination_station"].initial = arrival.origin_name
                self.fields["destination_station_id"].initial = arrival.origin_code
                self.fields["destination_latitude"].initial = arrival.origin_latitude
                self.fields["destination_longitude"].initial = arrival.origin_longitude

                # Set flag for message display
                self.prefilled_from_arrival = True

    def clean(self):
        cleaned_data = super().clean()

        # Use coordinate values from hidden fields (populated by autocomplete JS)
        origin_lat = cleaned_data.get("origin_latitude")
        origin_lon = cleaned_data.get("origin_longitude")
        dest_lat = cleaned_data.get("destination_latitude")
        dest_lon = cleaned_data.get("destination_longitude")

        # Store coordinates for save() method
        if origin_lat and origin_lon:
            self._origin_coords = (origin_lat, origin_lon)
        if dest_lat and dest_lon:
            self._destination_coords = (dest_lat, dest_lon)

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
        data = {}
        if self.cleaned_data.get("train_number"):
            data["train_number"] = self.cleaned_data["train_number"]
        return data


class CarMainTransferForm(MainTransferBaseForm):
    """Form for car main transfers with geocoding"""

    origin_address = forms.CharField(
        label=_("Departure Location"),
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
        label=_("Arrival Location"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address (street, city, country)"),
            }
        ),
        help_text=_("Full address for geocoding"),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_address",
            "destination_address",
        ]

    def __init__(self, *args, **kwargs):
        kwargs.pop("autocomplete", None)
        home_address = kwargs.pop("home_address", "")
        super().__init__(*args, **kwargs)
        self.fields["start_time"].required = False
        self.fields["end_time"].required = False

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_address"].initial = self.instance.origin_address
            self.fields[
                "destination_address"
            ].initial = self.instance.destination_address
        else:
            # Pre-fill origin with home address for arrival, destination for departure
            direction = self.initial.get("direction")
            if home_address:
                if direction == MainTransfer.Direction.ARRIVAL:
                    self.fields["origin_address"].initial = home_address
                elif direction == MainTransfer.Direction.DEPARTURE:
                    self.fields["destination_address"].initial = home_address

            # Pre-fill from arrival if this is a new departure
            if self.trip and direction == MainTransfer.Direction.DEPARTURE:
                arrival = MainTransfer.objects.filter(
                    trip=self.trip,
                    direction=MainTransfer.Direction.ARRIVAL,
                    type=MainTransfer.Type.CAR,
                ).first()
                if arrival:
                    self.fields["origin_address"].initial = arrival.destination_address
                    self.fields["destination_address"].initial = arrival.origin_address
                    self.prefilled_from_arrival = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = MainTransfer.Type.CAR
        instance.origin_address = self.cleaned_data["origin_address"]
        instance.destination_address = self.cleaned_data["destination_address"]

        if commit:  # pragma: no cover
            instance.save()

        return instance


class OtherMainTransferForm(MainTransferBaseForm):
    """Form for other transport types (ferry, bus, taxi, etc.) with free vehicle type"""

    vehicle_type = forms.CharField(
        label=_("Vehicle type"),
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("e.g. Ferry to Venice, Flixbus to Milan"),
            }
        ),
    )

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
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_address",
            "destination_address",
        ]

    def __init__(self, *args, **kwargs):
        kwargs.pop("autocomplete", None)
        kwargs.pop("home_address", None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["origin_address"].initial = self.instance.origin_address
            self.fields[
                "destination_address"
            ].initial = self.instance.destination_address
            self.fields["vehicle_type"].initial = self.instance.type_specific_data.get(
                "vehicle_type", ""
            )

    def get_type_specific_data(self):
        vehicle_type = self.cleaned_data.get("vehicle_type", "")
        return {"vehicle_type": vehicle_type} if vehicle_type else {}

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = MainTransfer.Type.OTHER
        instance.origin_address = self.cleaned_data["origin_address"]
        instance.destination_address = self.cleaned_data["destination_address"]
        type_specific_data = self.get_type_specific_data()
        if type_specific_data:
            instance.type_specific_data = type_specific_data

        if commit:  # pragma: no cover
            instance.save()

        return instance


# ============================================================================
# StayTransfer Forms
# ============================================================================


class StayTransferCreateForm(forms.ModelForm):
    """Form for creating a StayTransfer between stays of consecutive days (auto-populates from/to stays)"""

    class Meta:
        model = StayTransfer
        fields = ["transport_mode", "notes"]
        labels = {
            "transport_mode": _("Transport Mode"),
            "notes": _("Notes"),
        }
        widgets = {
            "transport_mode": TransportModeRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": _("Notes")}),
        }

    def __init__(self, *args, **kwargs):
        self.from_stay = kwargs.pop("from_stay", None)
        self.to_stay = kwargs.pop("to_stay", None)

        # Create instance with from_stay and to_stay already set to avoid validation errors
        if "instance" not in kwargs and self.from_stay and self.to_stay:
            kwargs["instance"] = StayTransfer(
                from_stay=self.from_stay, to_stay=self.to_stay
            )

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields["transport_mode"].choices = StayTransfer.TransportMode.choices

        self.helper.layout = Layout(
            Field("transport_mode", wrapper_class="col-span-full"),
            Field("notes", wrapper_class="col-span-full"),
        )

    def clean(self):
        cleaned_data = super().clean()

        if self.from_stay and self.to_stay:  # pragma: no branch
            # Check that stays are different
            if self.from_stay == self.to_stay:
                raise ValidationError(_("From stay and to stay must be different."))

            # Check that from_stay doesn't already have an outgoing transfer (excluding current instance)
            # Use explicit DB query to avoid Django's reverse relation caching issues
            from_qs = StayTransfer.objects.filter(from_stay=self.from_stay)
            if self.instance.pk:
                from_qs = from_qs.exclude(pk=self.instance.pk)
            if from_qs.exists():
                raise ValidationError(
                    _("The from stay already has an outgoing transfer.")
                )

            # Check that to_stay doesn't already have an incoming transfer (excluding current instance)
            to_qs = StayTransfer.objects.filter(to_stay=self.to_stay)
            if self.instance.pk:
                to_qs = to_qs.exclude(pk=self.instance.pk)
            if to_qs.exists():
                raise ValidationError(
                    _("The to stay already has an incoming transfer.")
                )

        return cleaned_data


class StayTransferEditForm(forms.ModelForm):
    """Form for editing an existing StayTransfer"""

    class Meta:
        model = StayTransfer
        fields = ["transport_mode", "notes"]
        labels = {
            "transport_mode": _("Transport Mode"),
            "notes": _("Notes"),
        }
        widgets = {
            "transport_mode": TransportModeRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": _("Notes")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields["transport_mode"].choices = StayTransfer.TransportMode.choices

        self.helper.layout = Layout(
            Field("transport_mode", wrapper_class="col-span-full"),
            Field("notes", wrapper_class="col-span-full"),
        )

    def save(self, commit=True):
        """Override save to handle estimated_duration conversion"""
        instance = super().save(commit=False)

        # estimated_duration is already a timedelta from clean_estimated_duration
        if commit:
            instance.save()

        return instance


# ============================================================================
# MainTransferConnection Forms
# ============================================================================


class MainTransferConnectionForm(forms.ModelForm):
    """Form for creating a MainTransferConnection (auto-populates main_transfer and destination)"""

    class Meta:
        model = MainTransferConnection
        fields = ["transport_mode", "notes"]
        labels = {
            "transport_mode": _("Transport Mode"),
            "notes": _("Notes"),
        }
        widgets = {
            "transport_mode": TransportModeRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": _("Notes")}),
        }

    def __init__(self, *args, **kwargs):
        self.main_transfer = kwargs.pop("main_transfer", None)
        self.destination = kwargs.pop("destination", None)
        self.destination_type = kwargs.pop("destination_type", None)

        # Create instance with main_transfer and destination already set to avoid validation errors
        if "instance" not in kwargs and self.main_transfer and self.destination:
            if self.destination_type == "event":
                kwargs["instance"] = MainTransferConnection(
                    main_transfer=self.main_transfer, event=self.destination
                )
            else:
                kwargs["instance"] = MainTransferConnection(
                    main_transfer=self.main_transfer, stay=self.destination
                )

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields["transport_mode"].choices = StayTransfer.TransportMode.choices

        self.helper.layout = Layout(
            Field("transport_mode", wrapper_class="col-span-full"),
            Field("notes", wrapper_class="col-span-full"),
        )


class MainTransferConnectionEditForm(forms.ModelForm):
    """Form for editing an existing MainTransferConnection"""

    class Meta:
        model = MainTransferConnection
        fields = ["transport_mode", "notes"]
        labels = {
            "transport_mode": _("Transport Mode"),
            "notes": _("Notes"),
        }
        widgets = {
            "transport_mode": TransportModeRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": _("Notes")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields["transport_mode"].choices = StayTransfer.TransportMode.choices

        self.helper.layout = Layout(
            Field("transport_mode", wrapper_class="col-span-full"),
            Field("notes", wrapper_class="col-span-full"),
        )


class ShareLinkCreateForm(forms.Form):
    EXPIRATION_CHOICES = [
        (7, _("7 days")),
        (30, _("30 days")),
        (90, _("90 days")),
        (0, _("Never expires")),
    ]

    label = forms.CharField(
        max_length=100,
        required=False,
        label=_("Label"),
        help_text=_("Optional label to identify this link"),
    )
    expiration_days = forms.ChoiceField(
        choices=EXPIRATION_CHOICES,
        initial=30,
        label=_("Expires after"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("label", wrapper_class="col-span-full"),
            Field("expiration_days", wrapper_class="col-span-full"),
        )

    def save(self, trip, created_by):
        from django.utils import timezone as tz

        label = self.cleaned_data["label"]
        expiration_days = int(self.cleaned_data["expiration_days"])
        expires_at = (
            tz.now() + timedelta(days=expiration_days) if expiration_days > 0 else None
        )
        return ShareLink.objects.create(
            trip=trip,
            created_by=created_by,
            label=label,
            expires_at=expires_at,
        )


class ChecklistItemForm(forms.ModelForm):
    class Meta:
        model = ChecklistItem
        fields = ["text"]
        widgets = {
            "text": forms.TextInput(attrs={"placeholder": _("Add an item…")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.label_class = "hidden"
        self.fields["text"].label = ""


class ChecklistReminderForm(forms.Form):
    REMINDER_CHOICES = [
        ("", _("Off")),
        (1, _("1 day before")),
        (3, _("3 days before")),
        (7, _("7 days before")),
        (14, _("14 days before")),
        (30, _("30 days before")),
    ]

    reminder_days = forms.ChoiceField(
        choices=REMINDER_CHOICES,
        required=False,
        label=_("Email reminder"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
