from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import prefilled_password_reset

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path(
        "accounts/password/reset/",
        prefilled_password_reset,
        name="account_reset_password",
    ),
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("suggestions/", include("suggestions.urls", namespace="suggestions")),
    path("", include("trips.urls", namespace="trips")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
