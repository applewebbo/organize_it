"""Tests for Google social login (for #383)."""

import pytest
from allauth.account.models import EmailAddress
from allauth.core.context import request_context
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import reverse

from tests.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture(autouse=True)
def google_provider(settings):
    """Register the Google provider regardless of the environment's credentials.

    Settings only wire the provider when GOOGLE_OAUTH_CLIENT_ID is set; tests
    inject dummy credentials so they never depend on a configured ``.env``.
    """
    settings.SOCIALACCOUNT_PROVIDERS = {
        "google": {
            "APP": {
                "client_id": "test-client-id",
                "secret": "test-secret",  # nosec B105 - dummy test credential
                "key": "",
            },
            "SCOPE": ["profile", "email"],
            "VERIFIED_EMAIL": True,
        }
    }


def _callback_request():
    """Build a request wired with session and messages for the social flow."""
    rf = RequestFactory()
    request = rf.get(reverse("google_callback"))
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)
    request.user = AnonymousUser()
    request.session.save()
    return request


def _google_sociallogin(request, email, uid="google-uid-1"):
    """Build a SocialLogin from a Google userinfo payload, bound to the request.

    Going through the provider (instead of hand-crafting a SocialAccount) wires
    the account to the settings-based OAuth app, which allauth needs to resolve
    email-based account linking.
    """
    provider = get_adapter().get_provider(request, "google")
    data = {"sub": uid, "email": email, "email_verified": True, "name": "Test User"}
    return provider.sociallogin_from_response(request, data)


class TestSocialButtons:
    def test_login_page_shows_google_button(self, client):
        response = client.get(reverse("account_login"))
        assert response.status_code == 200
        assert "Sign in with Google" in response.content.decode()
        assert "/accounts/google/login/" in response.content.decode()

    def test_signup_page_shows_google_button(self, client):
        response = client.get(reverse("account_signup"))
        assert response.status_code == 200
        assert "Sign up with Google" in response.content.decode()
        assert "/accounts/google/login/" in response.content.decode()

    def test_button_hidden_when_provider_unconfigured(self, settings, client):
        settings.SOCIALACCOUNT_PROVIDERS = {}
        login = client.get(reverse("account_login")).content.decode()
        signup = client.get(reverse("account_signup")).content.decode()
        assert "with Google" not in login
        assert "with Google" not in signup


class TestGoogleSignup:
    def test_new_user_is_created_and_verified(self):
        email = "newcomer@test.com"
        request = _callback_request()

        with request_context(request):
            complete_social_login(request, _google_sociallogin(request, email))

        user = User.objects.get(email=email)
        assert SocialAccount.objects.filter(user=user, provider="google").exists()
        assert EmailAddress.objects.filter(
            user=user, email=email, verified=True
        ).exists()
        # Social signup never sets a usable password.
        assert not user.has_usable_password()


class TestGoogleAccountLinking:
    def test_links_to_existing_email_password_account(self):
        existing = UserFactory(email="member@test.com")
        request = _callback_request()

        with request_context(request):
            complete_social_login(request, _google_sociallogin(request, existing.email))

        # No duplicate account: the Google login attaches to the existing user.
        assert User.objects.filter(email=existing.email).count() == 1
        assert SocialAccount.objects.filter(user=existing, provider="google").exists()
        # The original email/password credentials still work.
        existing.refresh_from_db()
        assert existing.check_password("1234")
