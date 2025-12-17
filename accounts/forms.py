from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from trips.models import Trip

from .models import CustomUser, Profile
from .widgets import AvatarRadioSelect


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("email",)


class ProfileUpdateForm(forms.ModelForm):
    """Form for Profile that allows the user to update personal information and preferences"""

    class Meta:
        model = Profile
        fields = ("first_name", "last_name", "city", "avatar", "fav_trip")
        labels = {
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "city": _("City"),
            "avatar": _("Avatar"),
            "fav_trip": _("Favourite trip"),
        }
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full"}
            ),
            "city": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "avatar": AvatarRadioSelect(),
            "fav_trip": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fav_trip"].queryset = Trip.objects.filter(
            author=self.instance.user
        )
