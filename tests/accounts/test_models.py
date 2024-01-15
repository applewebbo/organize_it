import pytest

pytestmark = pytest.mark.django_db


class TestCustomUser:
    def test_create_user(self, user_factory):
        """Test creating a new user"""
        user = user_factory()

        assert user.__str__() == user.email

    def test_automatic_profile_creation(self, user_factory):
        """Test automatic profile creation"""
        user = user_factory()

        assert hasattr(user, "profile")
        assert user.profile.__str__() == user.email
        assert user.profile.fav_trip is None
