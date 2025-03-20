from datetime import date, time

import pytest
from django.test import TestCase

from tests.trips.factories import EventFactory, TripFactory
from trips.utils import annotate_event_overlaps

pytestmark = pytest.mark.django_db


class TestEventOverlaps(TestCase):
    """Test cases for event overlap detection"""

    def test_no_overlaps(self):
        """Test events with no time overlaps"""
        trip = TripFactory()
        day = trip.days.first()

        [
            EventFactory(day=day, start_time=time(9, 0), end_time=time(10, 0)),
            EventFactory(day=day, start_time=time(10, 30), end_time=time(11, 30)),
            EventFactory(day=day, start_time=time(12, 0), end_time=time(13, 0)),
        ]

        annotated_events = annotate_event_overlaps(day.events.all())

        for event in annotated_events:
            assert not event.has_overlap

    def test_overlapping_events(self):
        """Test events with overlapping times"""
        trip = TripFactory()
        day = trip.days.first()

        [
            EventFactory(day=day, start_time=time(9, 0), end_time=time(11, 0)),
            EventFactory(day=day, start_time=time(10, 0), end_time=time(12, 0)),
            EventFactory(
                day=day, start_time=time(12, 30), end_time=time(13, 30)
            ),  # Changed time to avoid overlap
        ]

        annotated_events = annotate_event_overlaps(day.events.all())

        # First two events should overlap
        assert all(e.has_overlap for e in annotated_events[:2])
        # Last event should not overlap
        assert not annotated_events[2].has_overlap

    def test_adjacent_events_no_overlap(self):
        """Test events that are adjacent but don't overlap"""
        trip = TripFactory()
        day = trip.days.first()

        [
            EventFactory(day=day, start_time=time(9, 0), end_time=time(10, 0)),
            EventFactory(day=day, start_time=time(10, 0), end_time=time(11, 0)),
        ]

        annotated_events = annotate_event_overlaps(day.events.all())

        for event in annotated_events:
            assert not event.has_overlap

    def test_events_different_days_no_overlap(self):
        """Test events on different days don't affect each other"""
        trip = TripFactory(start_date=date(2024, 1, 1), end_date=date(2024, 1, 2))
        day1, day2 = trip.days.all()[:2]

        # Create overlapping times but on different days
        [
            EventFactory(day=day1, start_time=time(9, 0), end_time=time(11, 0)),
            EventFactory(day=day2, start_time=time(10, 0), end_time=time(12, 0)),
        ]

        # Get all events and annotate
        annotated_events = annotate_event_overlaps(day1.events.all())

        for event in annotated_events:
            assert not event.has_overlap

    def test_single_event_no_overlap(self):
        """Test single event has no overlap"""
        trip = TripFactory()
        day = trip.days.first()

        EventFactory(day=day, start_time=time(9, 0), end_time=time(11, 0))

        annotated_events = annotate_event_overlaps(day.events.all())

        assert len(annotated_events) == 1
        assert not annotated_events[0].has_overlap
