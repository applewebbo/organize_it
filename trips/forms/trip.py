from datetime import date, timedelta

import geocoder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from trips.forms.base import urlfields_assume_https
from trips.models import (
    ChecklistItem,
    Link,
    ShareLink,
    Trip,
)


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
        if self.instance and self.instance.pk:
            validate_url += f"?trip_id={self.instance.pk}"
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
        # place-level lookup so an ambiguous name cannot validate as a country
        g = geocoder.mapbox(destination, types="place")
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


class NamedParticipantForm(forms.Form):
    """Add a named participant (no account). A child requires an age (0–17)."""

    name = forms.CharField(max_length=100, label=_("Name"))
    is_child = forms.BooleanField(required=False, label=_("Child"))
    age = forms.IntegerField(required=False, min_value=0, max_value=17, label=_("Age"))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_child"):
            if cleaned.get("age") is None:
                self.add_error("age", _("Age is required for a child."))
        else:
            cleaned["age"] = None
        return cleaned


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
