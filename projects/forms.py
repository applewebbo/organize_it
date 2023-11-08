from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Layout
from django import forms
from django.core.exceptions import ValidationError

from .models import Link, Note, Place, Project


class ProjectForm(forms.ModelForm):
    title = forms.CharField(label="Titolo")
    description = forms.CharField(widget=forms.Textarea(), label="Descrizione")
    start_date = forms.DateField(
        label="Inizio", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        label="Fine", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Project
        fields = (
            "title",
            "description",
            "start_date",
            "end_date",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            FloatingField("title", autocomplete="Titolo"),
            FloatingField("description", css_class="fl-textarea"),
            Div(
                Div(
                    FloatingField("start_date", autocomplete="Inizio"),
                    css_class="col",
                ),
                Div(
                    FloatingField("end_date", autocomplete="Fine"),
                    css_class="col",
                ),
                css_class="row",
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("start_date") and cleaned_data.get("end_date"):
            if cleaned_data.get("start_date") > cleaned_data.get("end_date"):
                raise ValidationError("End date must be after start date")
        return cleaned_data


class ProjectDateUpdateForm(forms.ModelForm):
    start_date = forms.DateField(
        label="Inizio", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        label="Fine", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Project
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
                Div(
                    FloatingField("start_date", autocomplete="Inizio"),
                    css_class="col",
                ),
                Div(
                    FloatingField("end_date", autocomplete="Fine"),
                    css_class="col",
                ),
                css_class="row",
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
        fields = ("title", "url")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Title"}),
            "url": forms.URLInput(attrs={"placeholder": "URL"}),
        }
        labels = {
            "title": "Title",
            "url": "URL",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            FloatingField("title"),
            FloatingField("url"),
        )


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ("name", "url", "address")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "name"}),
            "url": forms.URLInput(attrs={"placeholder": "URL"}),
            "address": forms.TextInput(attrs={"placeholder": "address"}),
        }
        labels = {
            "title": "Title",
            "url": "URL",
            "address": "Address",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            FloatingField("name"),
            FloatingField("url"),
            FloatingField("address"),
        )


FIELDSET_CONTENT = """
            <fieldset class="row mb-3">
            <legend class="col-form-label col-sm-4 pt-0">Connect to</legend>
            <div class="col-sm-8">
              <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" name="gridRadios" id="gridRadios1" value="option1" checked
                x-on:click="open = 0">
                <label class="form-check-label" for="gridRadios1">
                  None
                </label>
              </div>
              <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" name="gridRadios" id="gridRadios2" value="option2"
                    x-on:click="open = 1" x-transition>
                <label class="form-check-label" for="gridRadios2">
                  Place
                </label>
              </div>
              <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" name="gridRadios" id="gridRadios3" value="option3"
                x-on:click="open = 2" x-transition>
                <label class="form-check-label" for="gridRadios3">
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

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["place"].queryset = Place.objects.filter(project=project)
        self.fields["link"].queryset = Link.objects.filter(projects=project)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            FloatingField("content", css_class="fl-textarea"),
            HTML('<div x-data="{ open: 0}">'),
            HTML(FIELDSET_CONTENT),
            Div("place", x_show="open == 1"),
            Div("link", x_show="open == 2"),
            HTML("</div>"),
        )
