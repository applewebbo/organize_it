from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse

from suggestions.forms import AICredentialsForm, SuggestionPreferencesForm
from suggestions.models import AICredentials, SuggestionPreferences


@login_required
def settings_view(request):
    """Render and save the per-user AI settings (BYOK key + preferences).

    Loaded into the profile page via HTMX and re-renders itself on save.
    """
    credentials = AICredentials.objects.filter(user=request.user).first()
    preferences, _ = SuggestionPreferences.objects.get_or_create(user=request.user)

    credentials_form = AICredentialsForm(request.POST or None, instance=credentials)
    preferences_form = SuggestionPreferencesForm(
        request.POST or None, instance=preferences
    )

    saved = False
    if request.method == "POST":
        if credentials_form.is_valid() and preferences_form.is_valid():
            preferences_form.save()
            api_key = credentials_form.cleaned_data["api_key_encrypted"]
            if api_key:
                creds = credentials_form.save(commit=False)
                creds.user = request.user
                creds.save()
            saved = True

    return TemplateResponse(
        request,
        "suggestions/settings.html",
        {
            "credentials_form": credentials_form,
            "preferences_form": preferences_form,
            "has_credentials": credentials is not None,
            "saved": saved,
        },
    )
