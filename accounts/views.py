from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

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
                "Profile modified succesfully",
            )
            return redirect(reverse("trips:home"))
        form = ProfileUpdateForm(request.POST, instance=profile)
        return TemplateResponse(request, "account/profile.html", context)

    return TemplateResponse(request, "account/profile.html", context)
