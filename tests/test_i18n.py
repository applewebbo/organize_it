import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestSetLanguage:
    def test_anonymous_visitor_can_switch_language(self, client):
        response = client.post(reverse("set_language"), {"language": "en"})

        assert response.status_code == 302
        assert response.cookies["django_language"].value == "en"

    def test_redirects_back_instead_of_to_login(self, client):
        response = client.post(
            reverse("set_language"), {"language": "en"}, HTTP_REFERER="/"
        )

        assert response.status_code == 302
        assert "/accounts/login/" not in response["Location"]
