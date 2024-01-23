import logging

from .common import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)


EMAIL_BACKEND = "django.core.mail.backends.locmemp.EmailBackend"


logging.disable()
