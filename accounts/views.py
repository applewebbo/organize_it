from allauth.account.views import PasswordResetView
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from trips.services import GooglePlacesClient, GooglePlacesError

from .forms import ProfileUpdateForm
from .models import Profile


class PrefilledPasswordResetView(PasswordResetView):
    """Password reset that prefills the email from the ``email`` query string."""

    def get_initial(self):
        initial = super().get_initial() or {}
        email = self.request.GET.get("email", "").strip()
        if email:
            initial["email"] = email
        return initial


prefilled_password_reset = PrefilledPasswordResetView.as_view()


def profile(request):
    profile = get_object_or_404(
        Profile.objects.select_related("user"), user=request.user
    )
    form = ProfileUpdateForm(instance=profile)
    context = {
        "user": request.user,
        "profile_form": form,
    }
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                _("Settings modified succesfully"),
            )
            return redirect(reverse("trips:home"))
        context["profile_form"] = form
        return TemplateResponse(request, "account/profile.html", context)

    return TemplateResponse(request, "account/profile.html", context)


@require_POST
def autocomplete_home_address(request):
    """HTMX: search for a home address using Google Places API and return a list of results."""
    query = request.POST.get("home_address", "").strip()
    if query and len(query) >= 3:
        try:
            results = GooglePlacesClient().search_text(query, max_results=5)
            return TemplateResponse(
                request,
                "account/includes/home-address-results.html",
                {"places": results, "found": bool(results)},
            )
        except GooglePlacesError:
            pass
    return TemplateResponse(
        request,
        "account/includes/home-address-results.html",
        {"found": False},
    )


@require_POST
def update_theme(request):
    """Update user theme preference via AJAX (stores in localStorage only if use_system_theme is enabled)"""
    # This endpoint is called when user manually toggles theme in navbar
    # We don't need to save anything server-side since:
    # - If use_system_theme is True, we follow system preference
    # - If use_system_theme is False, theme is stored in localStorage by frontend
    return HttpResponse(status=204)
