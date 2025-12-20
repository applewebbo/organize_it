from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import ProfileUpdateForm
from .models import Profile


@login_required
def profile(request):
    profile = get_object_or_404(Profile, user=request.user)
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


@login_required
@require_POST
def update_theme(request):
    """Update user theme preference via AJAX (stores in localStorage only if use_system_theme is enabled)"""
    # This endpoint is called when user manually toggles theme in navbar
    # We don't need to save anything server-side since:
    # - If use_system_theme is True, we follow system preference
    # - If use_system_theme is False, theme is stored in localStorage by frontend
    return HttpResponse(status=204)
