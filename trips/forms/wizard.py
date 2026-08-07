import json

from django import forms
from django.utils.translation import gettext_lazy as _


class WizardBasicsForm(forms.Form):
    """Basics step of the creation wizard: title, cover image, dates and an
    ordered list of stages (destination + nights) serialized as JSON by the
    client-side repeater. The first stage is the trip's main destination and the
    sum of nights must match the trip duration.
    """

    template_name = "trips/forms/wizard-basics-form.html"

    title = forms.CharField(label=_("Title"), max_length=100)
    start_date = forms.DateField(
        label=_("Start date"),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    end_date = forms.DateField(
        label=_("End date"),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    image = forms.ImageField(required=False)
    selected_photo_id = forms.CharField(
        required=False, widget=forms.HiddenInput(), initial=""
    )
    stages = forms.CharField(widget=forms.HiddenInput())

    @property
    def stages_initial(self):
        """Stage rows the client-side repeater hydrates from, so a failed
        validation re-renders the stages the user typed (issue #425)."""
        raw = self.data.get("stages") if self.is_bound else self.initial.get("stages")
        try:
            parsed = json.loads(raw)
        except ValueError, TypeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def clean_stages(self):
        raw = self.cleaned_data["stages"]
        try:
            parsed = json.loads(raw)
        except ValueError, TypeError:
            raise forms.ValidationError(_("Invalid stages data.")) from None
        if not isinstance(parsed, list) or not parsed:
            raise forms.ValidationError(_("Add at least one stage."))
        cleaned = []
        for stage in parsed:
            destination = str(stage.get("destination", "")).strip()
            if not destination:
                raise forms.ValidationError(_("Each stage needs a destination."))
            try:
                nights = int(stage.get("nights"))
            except TypeError, ValueError:
                raise forms.ValidationError(
                    _("Each stage needs a number of nights.")
                ) from None
            if nights < 1:
                raise forms.ValidationError(_("Each stage needs at least one night."))
            entry = {"destination": destination, "nights": nights}
            lat = stage.get("latitude")
            lon = stage.get("longitude")
            if lat is not None and lon is not None:
                try:
                    entry["latitude"] = float(lat)
                    entry["longitude"] = float(lon)
                except TypeError, ValueError:
                    pass
            cleaned.append(entry)
        self.cleaned_data["stages_list"] = cleaned
        return raw

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        stages_list = cleaned.get("stages_list")
        if start and end:
            if end <= start:
                self.add_error("end_date", _("End date must be after the start date."))
            elif stages_list is not None:
                total_nights = sum(s["nights"] for s in stages_list)
                if total_nights != (end - start).days:
                    self.add_error(
                        "stages",
                        _("The nights across stages must match the trip duration."),
                    )
        return cleaned
