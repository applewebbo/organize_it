import pytest

from accounts.forms import CustomLoginForm, ProfileUpdateForm
from tests.trips.factories import TripFactory

pytestmark = pytest.mark.django_db


class TestCustomLoginForm:
    def test_password_help_text_is_cleared(self):
        """allauth adds a reset link as password help_text; clear it to avoid
        a duplicate of the template's own Forgot Password link."""
        form = CustomLoginForm()
        assert form.fields["password"].help_text == ""

    def test_login_page_renders_single_reset_link(self, client):
        """The login page must expose the password reset URL only once."""
        html = client.get("/accounts/login/").content.decode()
        assert html.count('href="/accounts/password/reset/"') == 1


class TestProfileUpdateForm:
    def test_fav_trip_queryset_excludes_archived_trips(self, user_factory):
        """Test that fav_trip field only includes non-archived trips"""
        user = user_factory()
        active_trip = TripFactory(author=user, status=1)  # NOT_STARTED
        archived_trip = TripFactory(author=user, status=5)  # ARCHIVED

        form = ProfileUpdateForm(instance=user.profile)

        # Check that queryset includes active trip but not archived
        fav_trip_queryset = form.fields["fav_trip"].queryset
        assert active_trip in fav_trip_queryset
        assert archived_trip not in fav_trip_queryset

    def test_home_address_field_present_in_form(self, user_factory):
        """Test that home_address field is present in ProfileUpdateForm"""
        user = user_factory()
        form = ProfileUpdateForm(instance=user.profile)
        assert "home_address" in form.fields

    def test_fav_trip_queryset_filters_by_user(self, user_factory):
        """Test that fav_trip field only includes trips from the user"""
        user1 = user_factory()
        user2 = user_factory()
        user1_trip = TripFactory(author=user1, status=1)
        user2_trip = TripFactory(author=user2, status=1)

        form = ProfileUpdateForm(instance=user1.profile)

        fav_trip_queryset = form.fields["fav_trip"].queryset
        assert user1_trip in fav_trip_queryset
        assert user2_trip not in fav_trip_queryset

    def test_fav_trip_queryset_includes_collaborated_trips(self, user_factory):
        """Test that fav_trip field includes trips where user is a collaborator"""
        from trips.models import TripCollaboration

        owner = user_factory()
        collab_user = user_factory()
        collab_trip = TripFactory(author=owner, status=1)
        TripCollaboration.objects.create(
            trip=collab_trip, user=collab_user, color="blue", added_by=owner
        )

        form = ProfileUpdateForm(instance=collab_user.profile)
        fav_trip_queryset = form.fields["fav_trip"].queryset
        assert collab_trip in fav_trip_queryset

    def test_fav_trip_queryset_excludes_archived_collaborated_trips(self, user_factory):
        """Test that archived collaborated trips are not in fav_trip queryset"""
        from trips.models import TripCollaboration

        owner = user_factory()
        collab_user = user_factory()
        archived_trip = TripFactory(author=owner, status=5)
        TripCollaboration.objects.create(
            trip=archived_trip, user=collab_user, color="green", added_by=owner
        )

        form = ProfileUpdateForm(instance=collab_user.profile)
        fav_trip_queryset = form.fields["fav_trip"].queryset
        assert archived_trip not in fav_trip_queryset


class TestProfileLanguageField:
    def test_language_field_in_form(self, user_factory):
        user = user_factory()
        form = ProfileUpdateForm(instance=user.profile)
        assert "language" in form.fields

    def test_language_default_is_italian(self, user_factory):
        user = user_factory()
        assert user.profile.language == "it"

    def test_language_choices_include_it_and_en(self, user_factory):
        user = user_factory()
        form = ProfileUpdateForm(instance=user.profile)
        choices = [c[0] for c in form.fields["language"].choices]
        assert "it" in choices
        assert "en" in choices
