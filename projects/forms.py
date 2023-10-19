from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms

from .models import Link, Place, Project


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
