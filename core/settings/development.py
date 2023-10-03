from core.settings.common import *  # noqa

INSTALLED_APPS += [
    # DEVELOPMENT APPS
    "django_browser_reload",
]

MIDDLEWARE += [
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]
