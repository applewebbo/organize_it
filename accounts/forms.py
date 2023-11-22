from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from projects.models import Project

from .models import CustomUser, Profile


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("email",)


class ProfileUpdateForm(forms.ModelForm):
    """Form for Profile that allows the user to select only one of their projects as favourite"""

    class Meta:
        model = Profile
        fields = ("fav_project",)
        labels = {"fav_project": "Favourite project"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["fav_project"].queryset = Project.objects.filter(
                author=self.instance.user
            )
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "fav_project", Div(Submit("submit", "Salva"), css_class="mt-4 text-end")
        )
