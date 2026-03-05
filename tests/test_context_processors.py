import pytest
from django.conf import settings
from django.test import RequestFactory

from core.context_processors import app_version

pytestmark = pytest.mark.django_db


def test_app_version_context_processor():
    request = RequestFactory().get("/")
    context = app_version(request)
    assert context == {"APP_VERSION": settings.APP_VERSION}
