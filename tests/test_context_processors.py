import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils import translation

from accounts.context_processors import user_theme
from core.context_processors import app_version
from tests.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_app_version_context_processor():
    request = RequestFactory().get("/")
    context = app_version(request)
    assert context == {
        "APP_VERSION": settings.APP_VERSION,
        "PWA_ENABLED": settings.PWA_ENABLED,
    }


def test_footer_version_links_to_releases():
    html = render_to_string(
        "includes/footer.html", {"APP_VERSION": settings.APP_VERSION}
    )
    assert "https://github.com/applewebbo/organize_it/releases" in html
    assert f"v{settings.APP_VERSION}" in html


def test_footer_has_menu_links():
    html = render_to_string(
        "includes/footer.html", {"APP_VERSION": settings.APP_VERSION}
    )
    # internal app pages
    assert "/trips/list" in html
    # documentation (GitHub Pages)
    assert "applewebbo.github.io/organize_it" in html
    # repository
    assert "https://github.com/applewebbo/organize_it" in html


def test_footer_shows_login_for_anonymous():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    html = render_to_string(
        "includes/footer.html",
        {"APP_VERSION": settings.APP_VERSION, "user": request.user},
    )
    assert "/accounts/login/" in html
    assert "/accounts/signup/" in html


def test_footer_shows_logout_for_authenticated():
    user = UserFactory()
    html = render_to_string(
        "includes/footer.html",
        {"APP_VERSION": settings.APP_VERSION, "user": user},
    )
    assert "/accounts/logout/" in html


def test_footer_shows_project_info():
    html = render_to_string(
        "includes/footer.html", {"APP_VERSION": settings.APP_VERSION}
    )
    assert "Organizeit!" in html
    assert "Django" in html


def test_footer_is_translated_in_italian():
    with translation.override("it"):
        html = render_to_string(
            "includes/footer.html", {"APP_VERSION": settings.APP_VERSION}
        )
    assert "Codice del progetto" in html
    assert "Documentazione" in html


def test_user_theme_anonymous():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    assert user_theme(request) == {"use_system_theme": False}


def test_user_theme_authenticated():
    user = UserFactory()
    user.profile.use_system_theme = True
    user.profile.save()

    request = RequestFactory().get("/")
    request.user = user
    assert user_theme(request) == {"use_system_theme": True}


def test_user_theme_without_profile():
    user = UserFactory()
    user.profile.delete()

    request = RequestFactory().get("/")
    request.user = user
    assert user_theme(request) == {"use_system_theme": False}
