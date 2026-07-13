from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path
from pwa import views as pwa_views

from accounts.views import prefilled_password_reset

# PWA endpoints must stay reachable without authentication (service worker
# registration, manifest fetch and the offline fallback page).
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path(
        "serviceworker.js",
        login_not_required(pwa_views.service_worker),
        name="serviceworker",
    ),
    path("manifest.json", login_not_required(pwa_views.manifest), name="manifest"),
    path("offline/", login_not_required(pwa_views.offline), name="offline"),
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
