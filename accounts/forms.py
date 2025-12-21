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
        fields = (
            "first_name",
            "last_name",
            "city",
            "avatar",
            "currency",
            "default_map_view",
            "trip_sort_preference",
            "use_system_theme",
            "fav_trip",
        )
        labels = {
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "city": _("City"),
            "avatar": _("Avatar"),
            "currency": _("Preferred currency"),
            "default_map_view": _("Default event view"),
            "trip_sort_preference": _("Sort trips by"),
            "use_system_theme": _("Use system theme"),
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
            "currency": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "default_map_view": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
            "trip_sort_preference": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
            "use_system_theme": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "fav_trip": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fav_trip"].queryset = Trip.objects.filter(
            author=self.instance.user
        ).exclude(status=Trip.Status.ARCHIVED)
        self.fields["trip_sort_preference"].empty_label = None
        self.fields["default_map_view"].empty_label = None
