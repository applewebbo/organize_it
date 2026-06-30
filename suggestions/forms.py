from django import forms
from django.utils.translation import gettext_lazy as _

from suggestions.models import AICredentials, SuggestionPreferences
from trips.models import Experience


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
        help_text=_("Stored encrypted. Leave blank to keep the current key."),
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
        if not value and self.instance.pk:
            # Keep the already-stored key when the field is left blank
            return self.instance.api_key_encrypted
        return value


class SuggestionPreferencesForm(forms.ModelForm):
    favored_experience_types = forms.MultipleChoiceField(
        label=_("Favoured experience types"),
        required=False,
        choices=Experience.Type.choices,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = SuggestionPreferences
        fields = ("favored_experience_types", "dietary", "pace", "budget", "notes")
        labels = {
            "dietary": _("Dietary preference"),
            "pace": _("Pace"),
            "budget": _("Budget"),
            "notes": _("Notes"),
        }
        widgets = {
            "dietary": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "pace": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "budget": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "w-full textarea textarea-bordered",
                    "rows": 3,
                    "placeholder": _("e.g. avoid tourist traps, travelling with kids"),
                }
            ),
        }

    def clean_favored_experience_types(self):
        # MultipleChoiceField yields strings; persist ints in the JSON field
        return [int(value) for value in self.cleaned_data["favored_experience_types"]]
