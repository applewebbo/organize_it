from accounts.models import Profile, get_profile


def user_theme(request):
    """Expose the user's theme preference once per request.

    Avoids the repeated ``user.profile`` lookups in the navbar and theme
    templates by reusing ``get_profile`` (which is cached).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"use_system_theme": False}
    try:
        return {"use_system_theme": get_profile(user).use_system_theme}
    except Profile.DoesNotExist:
        return {"use_system_theme": False}
