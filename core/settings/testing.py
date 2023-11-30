from .common import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


EMAIL_BACKEND = "django.core.mail.backends.locmemp.EmailBackend"
