from .common import *  # noqa

DEBUG = True

# DJANGO-BROWSER-RELOAD

INSTALLED_APPS += [
    # DEVELOPMENT APPS
    "django_browser_reload",
    "debug_toolbar",
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# MAIL

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# DEBUG TOOLBAR

INTERNAL_IPS = [
    "127.0.0.1",
]

DATABASES = {
    "default": {
        "ENGINE": env("SQL_ENGINE"),
        "NAME": env("SQL_DATABASE"),
        "USER": env("SQL_USER"),
        "PASSWORD": env("SQL_PASSWORD"),
        "HOST": env("SQL_HOST"),
        "PORT": env("SQL_PORT"),
    }
}
