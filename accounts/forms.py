from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from trips.models import Trip

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
    """Form for Profile that allows the user to select only one of their trips as favourite"""

    class Meta:
        model = Profile
        fields = ("fav_trip",)
        labels = {"fav_trip": _("Favourite trip")}
        widgets = {
            "fav_trip": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fav_trip"].queryset = Trip.objects.filter(
            author=self.instance.user
        )
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML(f'<h2 class="mb-4 text-xl font-semibold">{_("Trips")}</h2>'),
            "fav_trip",
        )
