from datetime import date, datetime, timedelta

import geocoder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .models import Day, Event, Experience, Link, Meal, Note, Stay, Transport, Trip


def urlfields_assume_https(db_field, **kwargs):
    """
    ModelForm.Meta.formfield_callback function to assume HTTPS for scheme-less
    domains in URLFields.
    """
    if isinstance(db_field, models.URLField):
        kwargs["assume_scheme"] = "https"
    return db_field.formfield(**kwargs)


class TripForm(forms.ModelForm):
    title = forms.CharField(label="Titolo")
    description = forms.CharField(widget=forms.Textarea(), label="Descrizione")
    destination = forms.CharField(label="Destinazione")
    start_date = forms.DateField(
        label="Inizio", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        label="Fine", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Trip
        fields = ["title", "destination", "description", "start_date", "end_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        )

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("start_date")
            and cleaned_data.get("end_date")
            and cleaned_data.get("start_date") > cleaned_data.get("end_date")
        ):
            raise ValidationError("End date must be after start date")
        return cleaned_data

    def clean_start_date(self):
        start_date = self.cleaned_data.get("start_date")
        if start_date and start_date < date.today():
            raise ValidationError("Start date must be after today")
        return start_date

    def clean_destination(self):
        destination = self.cleaned_data.get("destination")
        g = geocoder.mapbox(destination)
        if not g.ok:
            raise ValidationError("Destination not found")
        return destination


class TripDateUpdateForm(forms.ModelForm):
    start_date = forms.DateField(
        label="Inizio", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        label="Fine", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Trip
        fields = (
            "start_date",
            "end_date",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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


FIELDSET_CONTENT = """
            <fieldset>
            <legend class="block text-gray-700 text-sm font-bold mb-2">Connect to</legend>
            <div class="flex">
              <div class="flex items-center me-4">
                <input class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600" type="radio" name="gridRadios" id="gridRadios1" value="option1" checked
                x-on:click="open = 0">
                <label class="ms-2 text-sm font-medium text-gray-600 dark:text-gray-300" for="gridRadios1">
                  None
                </label>
              </div>
              <div class="flex items-center me-4">
                <input class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600" type="radio" name="gridRadios" id="gridRadios2" value="option2"
                    x-on:click="open = 1" x-transition>
                <label class="ms-2 text-sm font-medium text-gray-600 dark:text-gray-300" for="gridRadios2">
                  Place
                </label>
              </div>
              <div class="flex items-center me-4">
                <input class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600" type="radio" name="gridRadios" id="gridRadios3" value="option3"
                x-on:click="open = 2" x-transition>
                <label class="ms-2 text-sm font-medium text-gray-600 dark:text-gray-300" for="gridRadios3">
                  Link
                </label>
              </div>
            </div>
            </fieldset>"""


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ("content", "link")
        widgets = {
            "content": forms.Textarea(attrs={"placeholder": "content"}),
        }
        labels = {
            "content": "Content",
        }

    def __init__(self, trip, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["link"].queryset = Link.objects.filter(trips=trip)
        # self.fields["link"].empty_label = "None"
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("content", css_class="fl-textarea"),
            Div(
                HTML(FIELDSET_CONTENT),
                # adding an extra div here to overcome django-crispy-forms issue with two subsequent Divs getting nested
                Div(
                    Div("link", x_show="open == 2"),
                ),
                x_data="{ open: 0 }",
                x_init="$watch('open', () => resetInput())",
            ),
        )


class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = [
            "type",
            "address",
            "destination",
            "start_time",
            "end_time",
            "url",
        ]
        formfield_callback = urlfields_assume_https
        labels = {"address": _("Departure")}
        widgets = {
            "type": forms.Select(),
            "address": forms.TextInput(attrs={"placeholder": "Departure"}),
            "destination": forms.TextInput(attrs={"placeholder": "Destination"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "url": forms.TextInput(attrs={"placeholder": "Url"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["type"].choices = Transport.Type.choices
        self.helper.layout = Layout(
            Div(
                "address",
                css_class="sm:col-span-2",
            ),
            Div(
                "destination",
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
                "url",
                css_class="sm:col-span-3",
            ),
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.name = (
            f"{self.cleaned_data['address']} - {self.cleaned_data['destination']}"
        )
        if commit:
            instance.save()
        return instance


class ExperienceForm(forms.ModelForm):
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

    class Meta:
        model = Experience
        fields = [
            "name",
            "type",
            "address",
            "start_time",
            "duration",
            "url",
        ]
        formfield_callback = urlfields_assume_https
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Name"}),
            "type": forms.Select(),
            "url": forms.TextInput(attrs={"placeholder": "Url"}),
            "address": forms.TextInput(attrs={"placeholder": "Address"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["type"].choices = Experience.Type.choices
        if self.instance.pk and self.instance.end_time and self.instance.start_time:
            start_time = datetime.combine(date.today(), self.instance.start_time)
            end_time = datetime.combine(date.today(), self.instance.end_time)
            duration = (end_time - start_time).total_seconds() // 60
            self.initial["duration"] = int(duration)
        self.helper.layout = Layout(
            Field(
                "name",
                wrapper_class="sm:col-span-3",
            ),
            Field("type", css_class="select select-primary"),
            Field(
                "address",
                wrapper_class="sm:col-span-4",
            ),
            Field(
                "start_time",
                x_ref="startTime",
                **{"x-on:change": "checkOverlap()"},
                wrapper_class="sm:col-span-3",
            ),
            Field(
                "duration",
                x_ref="duration",
                **{"x-on:change": "checkOverlap()"},
                wrapper_class="sm:col-span-1",
            ),
            Div(id="overlap-warning", css_class="sm:col-span-4"),
            Field("url", wrapper_class="sm:col-span-4"),
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        # convert duration to end_time
        duration = self.cleaned_data.get("duration")
        start_time = datetime.combine(date.today(), self.cleaned_data["start_time"])
        end_time = start_time + timedelta(minutes=int(duration))
        instance.end_time = end_time.time()
        if commit:  # pragma: no cover
            instance.save()
        return instance


class MealForm(forms.ModelForm):
    duration = forms.ChoiceField(
        choices=[
            (
                i * 30,
                (datetime.min + timedelta(minutes=i * 15)).strftime("%H h %M min"),
            )
            for i in range(8)
        ],
        label=_("Duration"),
        initial=60,
    )

    class Meta:
        model = Meal
        fields = [
            "name",
            "type",
            "address",
            "start_time",
            "duration",
            "url",
        ]
        formfield_callback = urlfields_assume_https
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Name"}),
            "type": forms.Select(),
            "url": forms.TextInput(attrs={"placeholder": "Url"}),
            "address": forms.TextInput(attrs={"placeholder": "Address"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["type"].choices = Meal.Type.choices
        if self.instance.pk and self.instance.end_time and self.instance.start_time:
            start_time = datetime.combine(date.today(), self.instance.start_time)
            end_time = datetime.combine(date.today(), self.instance.end_time)
            duration = (end_time - start_time).total_seconds() // 60
            self.initial["duration"] = int(duration)
        self.helper.layout = Layout(
            Div(
                "name",
                css_class="sm:col-span-3",
            ),
            Field("type", css_class="select select-primary w-full"),
            Div(
                "address",
                css_class="sm:col-span-4",
            ),
            Div(
                "start_time",
                css_class="sm:col-span-3",
            ),
            Div(
                "duration",
                css_class="sm:col-span-1",
            ),
            Div(
                "url",
                css_class="sm:col-span-4",
            ),
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        # convert duration to end_time
        duration = self.cleaned_data.get("duration")
        start_time = datetime.combine(date.today(), self.cleaned_data["start_time"])
        end_time = start_time + timedelta(minutes=int(duration))
        instance.end_time = end_time.time()
        if commit:  # pragma: no cover
            instance.save()
        return instance


class StayForm(forms.ModelForm):
    apply_to_days = (
        forms.ModelMultipleChoiceField(  # New field for multiple day selection
            queryset=None,
            widget=forms.CheckboxSelectMultiple,
            required=True,
            label=_("Period of stay"),  # Customize the label as needed
        )
    )

    class Meta:
        model = Stay
        fields = [
            "name",
            "check_in",
            "check_out",
            "cancellation_date",
            "phone_number",
            "url",
            "address",
            "apply_to_days",
        ]
        formfield_callback = urlfields_assume_https
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Name"}),
            "url": forms.TextInput(attrs={"placeholder": "Url"}),
            "address": forms.TextInput(attrs={"placeholder": "Address"}),
            "check_in": forms.TimeInput(attrs={"type": "time"}),
            "check_out": forms.TimeInput(attrs={"type": "time"}),
            "cancellation_date": forms.DateInput(attrs={"type": "date"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "Phone Number"}),
        }
        labels = {
            "name": _("Name"),
            "check_in": _("Check-in"),
            "check_out": _("Check-out"),
            "cancellation_date": _("Cancellation date"),
            "phone_number": _("Phone number"),
            "url": _("Website"),
            "address": _("Address"),
        }

    def __init__(self, trip, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["apply_to_days"].queryset = Day.objects.filter(trip=trip)
        self.fields["apply_to_days"].label_from_instance = (
            lambda obj: f"Day {obj.number}"
        )
        # Only set initial values if we're editing an existing stay
        if self.instance.pk:
            self.fields["apply_to_days"].initial = Day.objects.filter(
                trip=trip, stay=self.instance
            ).values_list("pk", flat=True)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "name",
                css_class="sm:col-span-4",
            ),
            Div(
                "address",
                css_class="sm:col-span-4",
            ),
            Div(
                "check_in",
                css_class="sm:col-span-2",
            ),
            Div(
                "check_out",
                css_class="sm:col-span-2",
            ),
            Div(
                "cancellation_date",
                css_class="sm:col-span-2",
            ),
            Div(
                "phone_number",
                css_class="sm:col-span-2",
            ),
            Div(
                "url",
                css_class="sm:col-span-4",
            ),
            Div(
                "apply_to_days",
                css_class="sm:col-span-4",
            ),
        )

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
