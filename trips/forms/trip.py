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
    selected_photo_source = forms.CharField(
        required=False, widget=forms.HiddenInput(), initial="unsplash"
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
                "x-on:input.debounce.600ms": (
                    "if ($el.value.trim() && $el.value !== lastSearchQuery) {"
                    " lastSearchQuery = $el.value;"
                    " document.getElementById('search-unsplash-tab')"
                    ".dispatchEvent(new Event('doSearch'));"
                    " }"
                ),
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
            Field("selected_photo_source"),
            # Hidden element wiring the image search request; triggered
            # automatically while typing the destination (see the
            # destination field's x-on:input handler above) and when the
            # current cover is clicked to be replaced.
            HTML(
                '<span id="search-unsplash-tab" class="hidden" hx-post='
                + f'"{reverse("trips:search-images")}"'
                + """
                      hx-trigger="doSearch"
                      hx-target="#image-results"
                      hx-indicator="#search-spinner"
                      hx-include="[name='destination'], [name='trip_id']"></span>
                """
            ),
            # Single cover-image container: when a cover is already set it
            # shows as a clickable preview (hover overlay / caption invite
            # replacing it); clicking it — or starting from scratch when no
            # cover exists yet — reveals the suggested-photos picker
            # (Unsplash + Wikimedia Commons) plus the manual upload field.
            Div(
                HTML(
                    f"""
                    <div x-data="{{
                        originalImageUrl: '{current_image_url}',
                        previewUrl: '{current_image_url}',
                        uploadPreviewUrl: '',
                        showPicker: {"false" if current_image_url else "true"},
                        triggerSearch() {{
                            const dest = document.querySelector('[name=destination]');
                            if (dest && dest.value.trim()) {{
                                document.getElementById('search-unsplash-tab').dispatchEvent(new Event('doSearch'));
                            }}
                        }},
                        openPicker() {{
                            this.showPicker = true;
                            this.triggerSearch();
                        }},
                        cancelPicker() {{
                            this.showPicker = false;
                            this.uploadPreviewUrl = '';
                            document.getElementById('id_selected_photo_id').value = '';
                            document.getElementById('id_selected_photo_source').value = 'unsplash';
                            const fileInput = document.getElementById('id_image');
                            if (fileInput) fileInput.value = '';
                        }},
                        onFileChange(e) {{
                            const file = e.target.files[0];
                            if (!file) return;
                            const reader = new FileReader();
                            reader.onload = (ev) => {{ this.uploadPreviewUrl = ev.target.result; }};
                            reader.readAsDataURL(file);
                        }}
                    }}"
                         x-init="if (showPicker) triggerSearch()">
                        <!-- Current cover: click to replace -->
                        <div x-show="!showPicker && previewUrl" x-cloak class="flex flex-col gap-1">
                            <button type="button"
                                    @click="openPicker()"
                                    class="group relative block w-full overflow-hidden rounded-lg border border-base-300">
                                <img :src="previewUrl"
                                     class="h-32 w-full object-cover transition-transform duration-200 group-hover:scale-105"
                                     alt="{str(_("Trip cover"))}">
                                <div class="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-all duration-200 group-hover:bg-black/50 group-hover:opacity-100">
                                    <span class="flex items-center gap-1.5 text-sm font-medium text-white">
                                        <i class="ph-bold ph-pencil-simple" aria-hidden="true"></i>
                                        {str(_("Change image"))}
                                    </span>
                                </div>
                            </button>
                            <p class="text-base-content/60 text-sm leading-snug text-center italic">{
                        str(_("Tap the photo to replace it"))
                    }</p>
                        </div>
                        <!-- Picker: suggested photos + manual upload (replaces the current cover view entirely).
                             bg-base-200 (no border) sets it apart as the section Cancel closes. -->
                        <div x-show="showPicker" x-cloak class="bg-base-200 flex flex-col gap-3 rounded-lg p-3">
                            <div class="flex items-center justify-between gap-2">
                                <p class="text-base-content/60 text-sm leading-snug italic">{
                        str(
                            _(
                                "Pick one of the suggested photos below, or upload your own — whichever you choose becomes the cover."
                            )
                        )
                    }</p>
                                <button type="button"
                                        x-show="originalImageUrl"
                                        x-cloak
                                        @click="cancelPicker()"
                                        class="btn btn-xs btn-soft btn-error shrink-0 gap-1">
                                    <i class="ph-bold ph-x" aria-hidden="true"></i>
                                    {str(_("Cancel"))}
                                </button>
                            </div>
                            <!-- Skeleton placeholder matching the real results grid
                                 (same row/grid-cell shape), so the layout doesn't
                                 jump once Unsplash + Wikimedia photos swap in. -->
                            <div id="search-spinner" class="htmx-indicator w-full">
                                <div class="mb-3">
                                    <div class="skeleton mb-1 h-3 w-20"></div>
                                    <div class="grid grid-cols-3 gap-1.5 sm:grid-cols-5">
                                        <div class="skeleton h-20 w-full rounded-lg"></div>
                                        <div class="skeleton h-20 w-full rounded-lg"></div>
                                        <div class="skeleton h-20 w-full rounded-lg"></div>
                                        <div class="skeleton hidden h-20 w-full rounded-lg sm:block"></div>
                                        <div class="skeleton hidden h-20 w-full rounded-lg sm:block"></div>
                                    </div>
                                </div>
                                <div>
                                    <div class="skeleton mb-1 h-3 w-28"></div>
                                    <div class="grid grid-cols-3 gap-1.5 sm:grid-cols-5">
                                        <div class="skeleton h-20 w-full rounded-lg"></div>
                                        <div class="skeleton h-20 w-full rounded-lg"></div>
                                        <div class="skeleton h-20 w-full rounded-lg"></div>
                                        <div class="skeleton hidden h-20 w-full rounded-lg sm:block"></div>
                                        <div class="skeleton hidden h-20 w-full rounded-lg sm:block"></div>
                                    </div>
                                </div>
                            </div>
                            <div id="image-results"></div>
                            <div class="flex flex-col gap-2">
                                <template x-if="uploadPreviewUrl">
                                    <img :src="uploadPreviewUrl"
                                         class="object-cover w-full h-32 rounded-lg border border-base-300"
                                         alt="preview">
                                </template>
                                <label for="id_image"
                                       class="text-base-content/60 text-xs leading-snug">{
                        str(_("Or upload your own"))
                    }</label>
                                <input type="file"
                                       name="image"
                                       accept="image/*"
                                       id="id_image"
                                       class="file-input w-full"
                                       @change="onFileChange($event)">
                            </div>
                        </div>
                    </div>
                    """
                ),
                css_class="sm:col-span-2 mt-1",
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
