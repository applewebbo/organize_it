from django.conf import settings


def app_version(request):
    return {
        "APP_VERSION": settings.APP_VERSION,
        "PWA_ENABLED": settings.PWA_ENABLED,
    }
