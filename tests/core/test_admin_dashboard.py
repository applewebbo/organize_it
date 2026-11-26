import json
import re
from datetime import datetime
from datetime import timezone as dt_timezone

import pytest
from django.urls import reverse

from accounts.models import CustomUser, Profile
from tests.accounts.factories import UserFactory
from trips.models import Trip

pytestmark = pytest.mark.django_db


def test_anonymous_user_redirected_to_login(client):
    url = reverse("admin-stats")
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("account_login") in response.url


def test_non_staff_user_denied(client):
    user = UserFactory(is_staff=False, is_active=True)
    client.force_login(user)
    response = client.get(reverse("admin-stats"))
    assert response.status_code == 302
    assert reverse("admin:login") in response.url


def test_inactive_staff_user_denied(client):
    user = UserFactory(is_staff=True, is_active=False)
    client.force_login(user)
    response = client.get(reverse("admin-stats"))
    assert response.status_code == 302
    assert reverse("account_login") in response.url


def test_staff_dashboard_context_and_aggregates(client):
    staff = UserFactory(is_staff=True, is_active=True)
    user_jan = UserFactory(is_active=True)
    user_inactive = UserFactory(is_active=False)

    CustomUser.objects.filter(pk=staff.pk).update(
        date_joined=datetime(2026, 1, 10, tzinfo=dt_timezone.utc)
    )
    CustomUser.objects.filter(pk=user_jan.pk).update(
        date_joined=datetime(2026, 1, 20, tzinfo=dt_timezone.utc)
    )
    CustomUser.objects.filter(pk=user_inactive.pk).update(
        date_joined=datetime(2026, 2, 5, tzinfo=dt_timezone.utc)
    )

    Profile.objects.filter(user=staff).update(ai_suggestions_enabled=True)
    Profile.objects.filter(user=user_jan).update(ai_suggestions_enabled=True)
    Profile.objects.filter(user=user_inactive).update(ai_suggestions_enabled=False)

    trip_1 = Trip.objects.create(
        title="Trip Jan",
        destination="Rome",
        author=staff,
        status=Trip.Status.NOT_STARTED,
    )
    trip_2 = Trip.objects.create(
        title="Trip Feb 1",
        destination="Paris",
        author=user_jan,
        status=Trip.Status.ARCHIVED,
    )
    trip_3 = Trip.objects.create(
        title="Trip Feb 2",
        destination="Tokyo",
        author=user_jan,
        status=Trip.Status.ARCHIVED,
    )

    Trip.objects.filter(pk=trip_1.pk).update(
        created_at=datetime(2026, 1, 15, tzinfo=dt_timezone.utc)
    )
    Trip.objects.filter(pk=trip_2.pk).update(
        created_at=datetime(2026, 2, 10, tzinfo=dt_timezone.utc)
    )
    Trip.objects.filter(pk=trip_3.pk).update(
        created_at=datetime(2026, 2, 12, tzinfo=dt_timezone.utc)
    )

    client.force_login(staff)
    response = client.get(reverse("admin-stats"))

    assert response.status_code == 200
    assert "admin/stats_dashboard.html" in [t.name for t in response.templates]

    expected_keys = {
        "total_users",
        "active_users",
        "new_users_per_month",
        "total_trips",
        "trips_per_month",
        "trips_by_status",
        "ai_total_profiles",
        "ai_enabled_count",
        "ai_adoption_rate",
        "chart_data",
    }
    assert expected_keys.issubset(response.context.keys())

    assert response.context["total_users"] == 3
    assert response.context["active_users"] == 2
    assert response.context["new_users_per_month"] == [
        {"month": "2026-01", "count": 2},
        {"month": "2026-02", "count": 1},
    ]

    assert response.context["total_trips"] == 3
    assert response.context["trips_per_month"] == [
        {"month": "2026-01", "count": 1},
        {"month": "2026-02", "count": 2},
    ]
    assert response.context["trips_by_status"] == [
        {
            "status": Trip.Status.NOT_STARTED,
            "label": str(Trip.Status.NOT_STARTED.label),
            "count": 1,
        },
        {
            "status": Trip.Status.ARCHIVED,
            "label": str(Trip.Status.ARCHIVED.label),
            "count": 2,
        },
    ]

    assert response.context["ai_total_profiles"] == 3
    assert response.context["ai_enabled_count"] == 2
    assert response.context["ai_adoption_rate"] == 66.7

    html = response.content.decode()
    match = re.search(
        r'<script id="admin-stats-data" type="application/json">(.*?)</script>',
        html,
    )
    assert match is not None
    parsed = json.loads(match.group(1))
    assert parsed == response.context["chart_data"]


def test_staff_dashboard_zero_profiles(client):
    staff = UserFactory(is_staff=True, is_active=True)
    Profile.objects.all().delete()

    client.force_login(staff)
    response = client.get(reverse("admin-stats"))

    assert response.status_code == 200
    assert response.context["ai_total_profiles"] == 0
    assert response.context["ai_enabled_count"] == 0
    assert response.context["ai_adoption_rate"] == 0.0
