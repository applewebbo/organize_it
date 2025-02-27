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
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 0,  # Close connections after each request
    }
}
