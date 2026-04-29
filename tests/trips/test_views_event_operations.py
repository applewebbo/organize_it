import json

import pytest

from tests.test import TestCase
from tests.trips.factories import (
    EventFactory,
    ExperienceFactory,
    MealFactory,
    TripFactory,
)

pytestmark = pytest.mark.django_db


class TestReorderEvents(TestCase):
    """Test cases for event drag & drop reorder"""

    def test_reorder_success(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        e1 = EventFactory(day=day, order=0)
        e2 = EventFactory(day=day, order=1)
        e3 = EventFactory(day=day, order=2)

        with self.login(user):
            response = self.client.post(
                f"/days/{day.pk}/reorder-events/",
                data=json.dumps({"order": [e3.pk, e1.pk, e2.pk]}),
                content_type="application/json",
            )

        self.response_204(response)
        e1.refresh_from_db()
        e2.refresh_from_db()
        e3.refresh_from_db()
        assert e3.order == 0
        assert e1.order == 1
        assert e2.order == 2

    def test_reorder_invalid_json(self):
        user = self.make_user("user2")
        trip = TripFactory(author=user)
        day = trip.days.first()

        self.client.force_login(user)
        response = self.client.post(
            f"/days/{day.pk}/reorder-events/",
            data="not-json",
            content_type="application/json",
        )

        self.response_400(response)

    def test_reorder_unauthorized(self):
        other = self.make_user("other")
        trip = TripFactory(author=other)
        day = trip.days.first()

        user = self.make_user("user")
        with self.login(user):
            response = self.client.post(
                f"/days/{day.pk}/reorder-events/",
                data=json.dumps({"order": []}),
                content_type="application/json",
            )

        self.response_404(response)

    def test_reorder_with_unknown_pk(self):
        """PKs not belonging to the day are silently skipped"""
        user = self.make_user("user3")
        trip = TripFactory(author=user)
        day = trip.days.first()
        e1 = EventFactory(day=day, order=0)

        with self.login(user):
            response = self.client.post(
                f"/days/{day.pk}/reorder-events/",
                data=json.dumps({"order": [e1.pk, 99999]}),
                content_type="application/json",
            )

        self.response_204(response)
        e1.refresh_from_db()
        assert e1.order == 0


class TestEventDetail(TestCase):
    """Test cases for event detail view"""

    def test_get_experience_detail(self):
        """Test successful retrieval of experience event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        experience = ExperienceFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=experience.pk)

        self.response_200(response)
        assert response.context["event"] == experience

    def test_get_meal_detail(self):
        """Test successful retrieval of meal event detail"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        meal = MealFactory(day=day)

        with self.login(user):
            response = self.get("trips:event-detail", pk=meal.pk)

        self.response_200(response)
        assert response.context["event"] == meal

    def test_get_detail_unauthorized(self):
        """Test unauthorized access to event detail"""
        other_user = self.make_user("other")
        trip = TripFactory(author=other_user)
        day = trip.days.first()
        event = EventFactory(day=day)

        user = self.make_user("user")
        with self.login(user):
            response = self.get("trips:event-detail", pk=event.pk)

        self.response_404(response)

    def test_get_detail_invalid_category(self):
        """Test event detail with invalid category"""
        user = self.make_user("user")
        trip = TripFactory(author=user)
        day = trip.days.first()
        event = EventFactory(day=day, category=99)  # Invalid category

        with self.login(user):
            response = self.get("trips:event-detail", pk=event.pk)

        self.response_404(response)
