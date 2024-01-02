from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CharField, Value
from django.db.models.functions import Concat

from .models import Day, Link, Note, Place, Trip


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
    start_date = forms.DateField(
        label="Inizio", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        label="Fine", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Trip
        fields = ["title", "description", "start_date", "end_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "title",
                css_class="sm:col-span-2",
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
        if cleaned_data.get("start_date") and cleaned_data.get("end_date"):
            if cleaned_data.get("start_date") > cleaned_data.get("end_date"):
                raise ValidationError("End date must be after start date")
        return cleaned_data

    def clean_start_date(self):
        start_date = self.cleaned_data.get("start_date")
        if start_date:
            if start_date < date.today():
                raise ValidationError("Start date must be after today")
        return start_date


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
        if cleaned_data.get("start_date") and cleaned_data.get("end_date"):
            if cleaned_data.get("start_date") > cleaned_data.get("end_date"):
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


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ["name", "url", "address", "day"]
        formfield_callback = urlfields_assume_https
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "name"}),
            "url": forms.URLInput(attrs={"placeholder": "URL"}),
            "address": forms.TextInput(attrs={"placeholder": "address"}),
            "day": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "title": "Title",
            "url": "URL",
            "address": "Address",
            "day": "Day",
        }

    def __init__(self, *args, parent=False, **kwargs):
        super().__init__(*args, **kwargs)
        if parent:
            trip = parent
        else:
            trip = self.instance.trip
        self.fields["day"].choices = (
            Day.objects.filter(trip=trip)
            .annotate(
                formatted_choice=Concat(
                    "date",
                    Value(" (Day "),
                    "number",
                    Value(")"),
                    output_field=CharField(),
                )
            )
            .values_list("id", "formatted_choice")
        )
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("name"),
            Field("url"),
            Field("address"),
            "day",
        )


class PlaceAssignForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ("day",)
        widgets = {
            "day": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "day": "Day",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        trip = self.instance.trip
        self.fields["day"].choices = (
            Day.objects.filter(trip=trip)
            .annotate(
                formatted_choice=Concat(
                    "date",
                    Value(" (Day "),
                    "number",
                    Value(")"),
                    output_field=CharField(),
                )
            )
            .values_list("id", "formatted_choice")
        )
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "day",
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
        fields = ("content", "place", "link")
        widgets = {
            "content": forms.Textarea(attrs={"placeholder": "content"}),
        }
        labels = {
            "content": "Content",
        }

    def __init__(self, trip, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["place"].queryset = Place.objects.filter(trip=trip)
        self.fields["link"].queryset = Link.objects.filter(trips=trip)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field("content", css_class="fl-textarea"),
            Div(
                HTML(FIELDSET_CONTENT),
                Div("place", x_show="open == 1"),
                Div("link", x_show="open == 2"),
                x_data="{ open: 0}",
                x_init="$watch('open', () => resetInput())",
            ),
        )
