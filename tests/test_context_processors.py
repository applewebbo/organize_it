import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from accounts.context_processors import user_theme
from core.context_processors import app_version
from tests.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_app_version_context_processor():
    request = RequestFactory().get("/")
    context = app_version(request)
    assert context == {"APP_VERSION": settings.APP_VERSION}


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
