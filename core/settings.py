import logging
import os
import warnings
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

# Silence a DeprecationWarning raised by google-genai on Python 3.14+ (it relies
# on a typing internal slated for removal); upstream library issue, not ours.
warnings.filterwarnings(
    "ignore",
    message=".*_UnionGenericAlias.*",
    category=DeprecationWarning,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

env = environ.Env(
    ACCOUNT_DEFAULT_HTTP_PROTOCOL=(str, "https"),
    ALLOWED_HOSTS=(list, []),
    CSRF_COOKIE_SECURE=(bool, True),
    DATABASE_CONN_MAX_AGE=(int, 600),
    DATABASE_SSL_REQUIRE=(bool, True),
    DEBUG=(bool, True),
    POSTGRES_LOCALLY=(bool, False),
    SESSION_COOKIE_SECURE=(bool, True),
    SECURE_HSTS_SECONDS=(int, 60 * 60 * 24 * 365),
    SECURE_SSL_REDIRECT=(bool, True),
)


SECRET_KEY = env("SECRET_KEY")
ENVIRONMENT = env("ENVIRONMENT", default="prod")
APP_VERSION = "2026.9"

DEBUG = env.bool("DEBUG")

ALLOWED_HOSTS: list[str] = env("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # THIRD_PARTY
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "crispy_tailwind",
    "crispy_forms",
    "django_browser_reload",
    "django_cotton.apps.SimpleAppConfig",
    "django_extensions",
    "django_htmx",
    "django_tailwind_cli",
    "django_q",
    "storages",
    "cloudinary_storage",
    "dbbackup",
    # INTERNAL_APP
    "trips",
    "accounts",
    "suggestions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django_cotton.cotton_loader.Loader",
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                )
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.app_version",
                "accounts.context_processors.user_theme",
            ],
            "builtins": [
                "django_cotton.templatetags.cotton",
            ],
            "debug": True,
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Rome"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field


AUTH_USER_MODEL = "accounts.CustomUser"

LOGIN_REDIRECT_URL = "/"


# SITES

SITE_ID = 1

# SECURITY
if not DEBUG:
    CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
    SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")

# DJANGO-ALLAUTH

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by email
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "ORGANIZE IT! - "
ACCOUNT_DEFAULT_HTTP_PROTOCOL = env("ACCOUNT_DEFAULT_HTTP_PROTOCOL")
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None


# DJANGO CRISPY FORMS

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# MAPBOX

MAPBOX_ACCESS_TOKEN = env("MAPBOX_ACCESS_TOKEN")

# DJANGO-Q
# Environment-specific configuration will be set below in respective sections

# DJANGO-TAILWIND-CLI

TAILWIND_CLI_SRC_CSS = "src/source.css"
TAILWIND_CLI_USE_DAISY_UI = True

# I18N
LANGUAGES = (
    ("it", _("Italian")),
    ("en", _("English")),
)

LOCALE_PATHS = [
    BASE_DIR / "locale/",
]

# LOGGING
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime:s} [{name}] {message}",
            "style": "{",
        },
        "verbose": {
            "format": "{levelname} {asctime:s} {name} {module}.py (line {lineno:d}) {funcName} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "task": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "formatter": "simple",
            "filename": BASE_DIR / "tasks.log",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "task": {
            "handlers": ["task"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

DATE_INPUT_FORMATS = [
    "%d/%m/%Y",  # Italiano: 25/12/2009
    "%m/%d/%Y",  # Inglese: 12/25/2009
    "%Y-%m-%d",  # ISO: 2009-12-25
]

GOOGLE_PLACES_API_KEY = env("GOOGLE_PLACES_API_KEY", default="")
UNSPLASH_ACCESS_KEY = env("UNSPLASH_ACCESS_KEY", default="")

# Fernet key used to encrypt BYOK AI credentials at rest (suggestions app)
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

# DJANGO-DBBACKUP with Django Storages
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "dbbackup": {
        "BACKEND": "storages.backends.dropbox.DropboxStorage",
        "OPTIONS": {
            "app_key": env("DROPBOX_APP_KEY", default=""),
            "app_secret": env("DROPBOX_APP_SECRET", default=""),
            "oauth2_access_token": env("DROPBOX_OAUTH2_ACCESS_TOKEN", default=""),
            "oauth2_refresh_token": env("DROPBOX_OAUTH2_REFRESH_TOKEN", default=""),
            "root_path": env(
                "DBBACKUP_DROPBOX_FILE_PATH", default="/organize-it-backups/"
            ),
        },
    },
}

DBBACKUP_CLEANUP_KEEP = env.int("DBBACKUP_CLEANUP_KEEP", default=10)
DBBACKUP_CLEANUP_KEEP_MEDIA = env.int("DBBACKUP_CLEANUP_KEEP_MEDIA", default=10)

# DEVELOPMENT SPECIFIC SETTINGS
if ENVIRONMENT == "dev":
    DEBUG = True
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="localhost")
    EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
    EMAIL_USE_TLS = False
    DEFAULT_FROM_EMAIL = env(
        "DEFAULT_FROM_EMAIL",
        default="Organize It <noreply@localhost>",
    )
    INTERNAL_IPS = [
        "127.0.0.1",
    ]
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "ATOMIC_REQUESTS": True,
            "CONN_MAX_AGE": 0,  # Close connections after each request
            "OPTIONS": {
                "init_command": (
                    "PRAGMA foreign_keys=ON;"
                    "PRAGMA journal_mode = WAL;"
                    "PRAGMA synchronous = NORMAL;"
                    "PRAGMA busy_timeout = 5000;"
                    "PRAGMA temp_store = MEMORY;"
                    "PRAGMA mmap_size = 134217728;"
                    "PRAGMA journal_size_limit = 67108864;"
                    "PRAGMA cache_size = 2000;"
                ),
                "transaction_mode": "IMMEDIATE",
            },
        }
    }
    INSTALLED_APPS += [
        "django_watchfiles",
    ]

    # django-devbar: insert middleware right after SecurityMiddleware
    _security_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
    MIDDLEWARE.insert(_security_idx + 1, "django_devbar.DevBarMiddleware")

    # DJANGO-Q configuration for development
    Q_CLUSTER = {
        "name": "organize_it",
        "workers": env.int("Q_CLUSTER_WORKERS", default=4),
        "timeout": env.int("Q_CLUSTER_TIMEOUT", default=90),
        "retry": env.int("Q_CLUSTER_RETRY", default=120),
        "max_attempts": env.int("Q_CLUSTER_MAX_ATTEMPTS", default=3),
        "queue_limit": env.int("Q_CLUSTER_QUEUE_LIMIT", default=50),
        "bulk": 10,
        "orm": "default",  # Use Django ORM in development for simplicity
        "catch_up": False,
        "save_limit": 250,  # Keep last 250 successful tasks
        "error_reporter": {},
    }

# PRODUCTION SPECIFIC SETTINGS
elif ENVIRONMENT == "prod":
    DATABASES = {
        "default": {
            "ENGINE": env("SQL_ENGINE"),
            "NAME": env("SQL_DATABASE"),
            "USER": env("SQL_USER"),
            "PASSWORD": env("SQL_PASSWORD"),
            "HOST": env("SQL_HOST"),
            "PORT": env("SQL_PORT"),
            "CONN_MAX_AGE": 600,  # Keep connections alive for 10 min
            "CONN_HEALTH_CHECKS": True,  # Verify connection health before reuse
        }
    }

    # CSRF_TRUSTED_ORIGINS: list[str] = env("DJANGO_CSRF_TRUSTED_ORIGINS")
    CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS").split(",")

    # DJANGO_ANYMAIL
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    DEFAULT_FROM_EMAIL = env(
        "DEFAULT_FROM_EMAIL",
        default="Organize It <info@mg.webbografico.com>",
    )
    ADMIN_EMAIL = env("ADMIN_EMAIL")

    ANYMAIL = {
        "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
        "MAILGUN_API_URL": env("MAILGUN_API_URL"),
        "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN"),
    }

    # DJANGO-CLOUDINARY-STORAGE
    CLOUDINARY_STORAGE = {
        "CLOUDINARY_URL": env("CLOUDINARY_URL"),
    }

    # Override storages for production
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }
    STORAGES["staticfiles"] = {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    }

    # DJANGO-Q configuration for production (ORM broker)
    Q_CLUSTER = {
        "name": "organize_it",
        "workers": env.int("Q_CLUSTER_WORKERS", default=4),
        "timeout": env.int("Q_CLUSTER_TIMEOUT", default=90),
        "retry": env.int("Q_CLUSTER_RETRY", default=120),
        "max_attempts": env.int("Q_CLUSTER_MAX_ATTEMPTS", default=3),
        "queue_limit": env.int("Q_CLUSTER_QUEUE_LIMIT", default=50),
        "bulk": 10,
        "orm": "default",
        "catch_up": False,
        "save_limit": 250,
        "error_reporter": {},
    }

    # Redis cache configuration
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://:{env('REDIS_PASSWORD', default='')}@{env('REDIS_HOST', default='localhost')}:{env.int('REDIS_PORT', default=6379)}/1",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }

# TESTING SPECIFIC SETTINGS
elif ENVIRONMENT == "test":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

    PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

    # Fixed Fernet key so encrypted-field tests are deterministic
    FIELD_ENCRYPTION_KEY = "X96Gmf2WBHNi4IfGu474va9oI32nCcRONTmK9hLuoSc="

    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    DEFAULT_FROM_EMAIL = "Organize It <noreply@test.local>"

    # DJANGO-Q configuration for testing (synchronous)
    Q_CLUSTER = {
        "name": "organize_it",
        "workers": 1,
        "sync": True,  # Run tasks synchronously in tests
        "timeout": 60,
        "retry": 120,
    }

    logging.disable()
