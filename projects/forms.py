from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms

from .models import Link, Project


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
            "title": forms.TextInput(attrs={"placeholder": "Titolo"}),
            "url": forms.URLInput(attrs={"placeholder": "URL"}),
        }
        labels = {
            "title": "Titolo",
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
