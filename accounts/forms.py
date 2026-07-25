from allauth.account.forms import LoginForm
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from trips.models import Trip

from .models import CustomUser, Profile
from .widgets import AvatarRadioSelect


class CustomLoginForm(LoginForm):
    """Login form that drops allauth's password reset help_text.

    The login template renders its own styled Forgot Password link, so the
    default help_text link would show up as a duplicate.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].help_text = ""


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
            "home_address",
            "home_address_latitude",
            "home_address_longitude",
            "avatar",
            "currency",
            "language",
            "default_map_view",
            "trip_sort_preference",
            "use_system_theme",
            "show_transfer_info",
            "show_weather",
            "notify_daily_digest",
            "fav_trip",
        )
        labels = {
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "home_address": _("Home address"),
            "avatar": _("Avatar"),
            "currency": _("Preferred currency"),
            "language": _("Email language"),
            "default_map_view": _("Default event view"),
            "trip_sort_preference": _("Sort trips by"),
            "use_system_theme": _("Use your device's light/dark system setting."),
            "show_transfer_info": _("Show transfer info"),
            "show_weather": _("Show weather forecast"),
            "notify_daily_digest": _("Daily digest email"),
            "fav_trip": _("Favourite trip"),
        }
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full"}
            ),
            "home_address": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": _("Full address (street, city, country)"),
                }
            ),
            "avatar": AvatarRadioSelect(),
            "currency": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "default_map_view": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
            "trip_sort_preference": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
            "language": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "use_system_theme": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm"}
            ),
            "show_transfer_info": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm"}
            ),
            "show_weather": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm"}
            ),
            "notify_daily_digest": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-sm"}
            ),
            "fav_trip": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "home_address_latitude": forms.HiddenInput(),
            "home_address_longitude": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fav_trip"].queryset = (
            Trip.objects.filter(
                Q(author=self.instance.user) | Q(collaborators=self.instance.user)
            )
            .exclude(status=Trip.Status.ARCHIVED)
            .distinct()
        )
        self.fields["trip_sort_preference"].empty_label = None
        self.fields["default_map_view"].empty_label = None
