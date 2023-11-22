from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse

from .forms import ProfileUpdateForm


@login_required
def profile(request):
    form = ProfileUpdateForm(instance=request.user.profile)
    context = {
        "user": request.user,
        "profile_form": form,
    }
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Profile modified succesfully",
            )
            return TemplateResponse(request, "account/profile.html", context)
        form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        return TemplateResponse(request, "account/profile.html", context)

    return TemplateResponse(request, "account/profile.html", context)
