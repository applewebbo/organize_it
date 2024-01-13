# FILEPATH: /tests/test_views.py
import pytest
from django.test import Client
from django.urls import reverse

from .factories import UserFactory

pytestmark = pytest.mark.django_db


class TestAccountViews:
    def setup_method(self):
        self.client = Client()
        self.user = UserFactory()

    def test_profile_view(self):
        # Login the user
        self.client.force_login(self.user)

        # Get the profile view
        response = self.client.get(reverse("accounts:profile"))

        # Check the status code and template used
        assert response.status_code == 200
        assert "account/profile.html" in [t.name for t in response.templates]

    def test_profile_view_unauthenticated(self):
        # Get the profile view
        response = self.client.get(reverse("accounts:profile"))

        # Check the status code and redirect location
        assert response.status_code == 302
