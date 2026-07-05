from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import Profile
from suggestions.models import (
    MAX_RESULT_COUNT,
    MIN_RESULT_COUNT,
    AICredentials,
    SuggestionPreferences,
)
from trips.models import Experience


class AISuggestionsToggleForm(forms.ModelForm):
    """Single-field form for the AI suggestions activation flag on the profile."""

    class Meta:
        model = Profile
        fields = ("ai_suggestions_enabled",)
        widgets = {
            "ai_suggestions_enabled": forms.CheckboxInput(
                attrs={"class": "toggle toggle-primary"}
            ),
        }


class AICredentialsForm(forms.ModelForm):
    """BYOK form. The API key is shown masked and left blank means "keep the
    current key", so an existing key is never echoed back to the page."""

    api_key_encrypted = forms.CharField(
        label=_("API key"),
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"class": "input input-bordered w-full", "autocomplete": "off"},
        ),
        help_text=_("Leave blank to keep the current key."),
    )

    class Meta:
        model = AICredentials
        fields = ("provider", "api_key_encrypted")
        labels = {"provider": _("Provider")}
        widgets = {
            "provider": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def clean_api_key_encrypted(self):
        value = self.cleaned_data.get("api_key_encrypted", "").strip()
        self._key_left_blank = not value and bool(self.instance.pk)
        if self._key_left_blank:
            # Keep the already-stored key when the field is left blank
            return self.instance.api_key_encrypted
        return value

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("provider")
        # The stored key belongs to the previous provider; switching provider
        # without a new key would silently pair it with the wrong provider and
        # fail at generation time, so require the new provider's key up front.
        provider_changed = self.instance.pk and provider != self.instance.provider
        if provider_changed and getattr(self, "_key_left_blank", False):
            self.add_error(
                "api_key_encrypted",
                _("Enter the API key for the new provider."),
            )
        return cleaned


class SuggestionPreferencesForm(forms.ModelForm):
    favored_experience_types = forms.MultipleChoiceField(
        label=_("Favoured activity types"),
        required=False,
        choices=Experience.Type.choices,
        widget=forms.CheckboxSelectMultiple,
    )
    interests = forms.MultipleChoiceField(
        label=_("Interests / themes"),
        required=False,
        choices=SuggestionPreferences.Interest.choices,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = SuggestionPreferences
        fields = (
            "travel_party",
            "travel_style",
            "favored_experience_types",
            "interests",
            "dietary",
            "cuisine",
            "budget",
            "search_radius",
            "result_count",
            "notes",
        )
        labels = {
            "travel_party": _("Travelling as"),
            "travel_style": _("Travel style"),
            "dietary": _("Dietary preference"),
            "cuisine": _("Cuisine type"),
            "budget": _("Budget"),
            "search_radius": _("Search area"),
            "result_count": _("Number of suggestions"),
            "notes": _("Notes"),
        }
        help_texts = {
            "result_count": _("How many suggestions to request per generation."),
        }
        widgets = {
            "travel_party": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
            "travel_style": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
            "dietary": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "cuisine": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "budget": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "search_radius": forms.Select(
                attrs={"class": "select select-bordered w-full"}
            ),
            "result_count": forms.NumberInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "min": MIN_RESULT_COUNT,
                    "max": MAX_RESULT_COUNT,
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "w-full textarea textarea-bordered",
                    "rows": 3,
                    "placeholder": _(
                        "e.g. we have a car, avoid long queues, prefer venues open late"
                    ),
                }
            ),
        }

    def clean_favored_experience_types(self):
        # MultipleChoiceField yields strings; persist ints in the JSON field
        return [int(value) for value in self.cleaned_data["favored_experience_types"]]
