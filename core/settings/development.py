from core.settings.common import *  # noqa

# DJANGO-BROWSER-RELOAD

INSTALLED_APPS += [
    # DEVELOPMENT APPS
    "django_browser_reload",
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]


# MAIL

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
