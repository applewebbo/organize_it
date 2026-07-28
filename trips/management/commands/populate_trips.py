import logging
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    ITALIAN_CITIES,
    PLACES,
    ChecklistItemFactory,
    ExpenseFactory,
    ExpenseParticipantFactory,
    ExpenseShareFactory,
    ExperienceFactory,
    FamilyUnitFactory,
    MainTransferFactory,
    MealFactory,
    StayBookingFactory,
    StayFactory,
    TripFactory,
)
from trips.expenses import ensure_expense_participants
from trips.models import Day, StayBooking, Trip, TripCollaboration
from trips.tasks import calculate_day_transfer

logger = logging.getLogger("task")

NUMBER_OF_USERS = 2

# Solo trip date configs: (start_offset, end_offset) relative to today
SOLO_TRIP_DATE_CONFIGS = [
    (-14, -10),  # completed: ended 10 days ago
    (10, 14),  # not started: starts in 10 days
]

# Multi-destination road trip: currently in progress, 8 days
MULTI_TRIP_DATE_CONFIG = (-3, 4)

User = get_user_model()


class _PlacePool:
    """Draws distinct places per (city, category) so a trip never repeats a name.

    Places are handed out without replacement from a per-trip shuffled copy of the
    city pool; once a category is exhausted it falls back to random reuse so
    generation never crashes on short pools.
    """

    def __init__(self):
        self._remaining = {}

    def take(self, city, category):
        """Return an unused place for the city+category, or reuse when exhausted."""
        key = (city, category)
        remaining = self._remaining.get(key)
        if remaining is None:
            remaining = PLACES[city][category].copy()
            random.shuffle(remaining)
            self._remaining[key] = remaining
        if remaining:
            return remaining.pop()
        pool = PLACES[city][category]
        return random.choice(pool) if pool else None


def _place_kwargs(place):
    """Return factory kwargs for a chosen place, empty when the pool is exhausted."""
    return {"chosen_place": place} if place else {}


def _create_stay_and_events(trip, all_days, author, creator, pool):
    """Create stay, meals and experiences for a trip."""
    destination = trip.destination
    hotels_for_city = PLACES[destination]["hotels"]

    if len(all_days) > 2 and len(hotels_for_city) >= 2:
        stay1 = StayFactory(
            city=destination,
            author=author,
            **_place_kwargs(pool.take(destination, "hotels")),
        )
        stay1.days.set(all_days[:2])
        stay2 = StayFactory(
            city=destination,
            author=author,
            **_place_kwargs(pool.take(destination, "hotels")),
        )
        stay2.days.set(all_days[2:])
    else:
        stay = StayFactory(
            city=destination,
            author=author,
            **_place_kwargs(pool.take(destination, "hotels")),
        )
        stay.days.set(all_days)

    for day in trip.days.all():
        _create_events_for_day(day, trip, destination, creator, pool)


def _create_events_for_day(day, trip, city, creator, pool):
    """Create meal and experience events for a day using the given city's places."""
    MealFactory.create(
        day=day,
        trip=trip,
        type=2,
        estimated_duration=timedelta(minutes=90),
        city=city,
        last_modified_by=creator,
        **_place_kwargs(pool.take(city, "restaurants")),
    )
    MealFactory.create(
        day=day,
        trip=trip,
        type=3,
        estimated_duration=timedelta(minutes=90),
        city=city,
        last_modified_by=creator,
        **_place_kwargs(pool.take(city, "restaurants")),
    )
    ExperienceFactory.create(
        day=day,
        trip=trip,
        estimated_duration=timedelta(minutes=random.randrange(60, 120, 15)),
        city=city,
        last_modified_by=creator,
        **_place_kwargs(pool.take(city, "attractions")),
    )


def _create_multi_destination_trip(user, cities):
    """Create a road-trip style in-progress trip spanning two cities."""
    city1, city2 = cities[0], cities[1]
    start_offset, end_offset = MULTI_TRIP_DATE_CONFIG
    trip = TripFactory(
        author=user,
        destination=city1,
        start_date=date.today() + timedelta(days=start_offset),
        end_date=date.today() + timedelta(days=end_offset),
    )
    all_days = list(trip.days.order_by("number"))
    mid = len(all_days) // 2
    pool = _PlacePool()

    # First half: main destination (city1, leave day.destination blank = inherits trip.destination)
    first_half = all_days[:mid]
    second_half = all_days[mid:]

    # Second half: assign custom destination (city2) via bulk update to skip async_task
    second_half_pks = [day.pk for day in second_half]
    Day.objects.filter(pk__in=second_half_pks).update(destination=city2)

    # Stay for city1
    if PLACES[city1]["hotels"]:
        stay1 = StayFactory(
            city=city1, author=user, **_place_kwargs(pool.take(city1, "hotels"))
        )
        stay1.days.set(first_half)

    # Stay for city2
    if PLACES[city2]["hotels"]:
        stay2 = StayFactory(
            city=city2, author=user, **_place_kwargs(pool.take(city2, "hotels"))
        )
        stay2.days.set(second_half)

    for day in first_half:
        _create_events_for_day(day, trip, city1, user, pool)
    for day in second_half:
        _create_events_for_day(day, trip, city2, user, pool)

    # Calculate transfers after stays/events are created (needs geocoded coordinates)
    for day in all_days[:-1]:
        calculate_day_transfer(day.pk)

    return trip


# (title, amount) templates for seeded expenses, split equally across participants
EXPENSE_TEMPLATES = [
    ("Hotel", Decimal("240.00")),
    ("Dinner out", Decimal("86.50")),
    ("Museum tickets", Decimal("42.00")),
    ("Groceries", Decimal("31.20")),
    ("Taxi", Decimal("18.00")),
]

CHECKLIST_ITEMS = [
    "Passport / ID",
    "Book museum tickets",
    "Pack chargers",
    "Travel insurance",
]


def _create_expenses_for_trip(trip, creator):
    """Enable expenses and seed shared costs split across all participants."""
    if not trip.expenses_enabled:
        trip.expenses_enabled = True
        trip.save(update_fields=["expenses_enabled"])
    ensure_expense_participants(trip)
    participants = list(trip.expense_participants.filter(is_active=True))
    if not participants:
        return
    for i, (title, amount) in enumerate(EXPENSE_TEMPLATES):
        payer = participants[i % len(participants)]
        expense = ExpenseFactory(
            trip=trip,
            title=title,
            amount=amount,
            date=trip.start_date,
            payer=payer,
            created_by=creator,
        )
        for participant in participants:
            ExpenseShareFactory(expense=expense, participant=participant)


def _add_family_with_child(trip):
    """Group the author with a named-only child into a shared family unit.

    Must run after expenses exist: the child shares them to gain expense
    history, otherwise a later ensure_expense_participants() would prune it as
    a historyless orphan.
    """
    unit = FamilyUnitFactory(trip=trip, name="")
    child = ExpenseParticipantFactory(
        trip=trip, name_snapshot="Leo", is_child=True, family_unit=unit
    )
    author_participant = trip.expense_participants.filter(
        user=trip.author, collaboration__isnull=True
    ).first()
    if author_participant:
        author_participant.family_unit = unit
        author_participant.save(update_fields=["family_unit"])
    for expense in trip.expenses.all():
        ExpenseShareFactory(expense=expense, participant=child)


def _create_booking(trip, destination, creator, provider=StayBooking.Provider.SMART):
    """Seed a Stay22 accommodation search for a trip stage (destination)."""
    StayBookingFactory(
        trip=trip, destination=destination, created_by=creator, provider=provider
    )


def _create_checklist(trip):
    """Seed a short packing/todo checklist for a trip."""
    for i, text in enumerate(CHECKLIST_ITEMS):
        ChecklistItemFactory(trip=trip, text=text, completed=(i == 0))


class Command(BaseCommand):
    help = "Generates dummy trips with stays and events (keeps existing users)"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting existing trips...")
        # Delete per-instance so Trip.delete() runs and clears each trip's
        # expenses first (they PROTECT their payer participant); a bulk
        # QuerySet delete would bypass that override and raise ProtectedError.
        for trip in Trip.objects.all():
            trip.delete()

        # Keep existing non-superuser accounts; create if fewer than NUMBER_OF_USERS
        users = list(User.objects.filter(is_superuser=False))
        if len(users) < NUMBER_OF_USERS:
            needed = NUMBER_OF_USERS - len(users)
            UserFactory.create_batch(needed)
            users = list(User.objects.filter(is_superuser=False))

        # Include existing superusers so `just crawl` (which logs in as the first
        # superuser) sees crawlable content. Never create superusers; when none
        # exist this simply adds nothing.
        users += list(User.objects.filter(is_superuser=True))

        self.stdout.write("Creating trips...")
        cities = ITALIAN_CITIES.copy()

        for user in users:
            user_cities = random.sample(cities, min(3, len(cities)))

            for i, (start_offset, end_offset) in enumerate(SOLO_TRIP_DATE_CONFIGS):
                destination = user_cities[i]
                trip = TripFactory(
                    author=user,
                    destination=destination,
                    start_date=date.today() + timedelta(days=start_offset),
                    end_date=date.today() + timedelta(days=end_offset),
                )
                MainTransferFactory(
                    trip=trip,
                    direction=1,
                )
                MainTransferFactory(
                    trip=trip,
                    direction=2,
                )
                all_days = list(trip.days.all())
                _create_stay_and_events(
                    trip, all_days, author=user, creator=user, pool=_PlacePool()
                )
                _create_checklist(trip)
                _create_booking(trip, destination, user)
                _create_expenses_for_trip(trip, user)

        # Multi-destination road trip for each user
        for user in users:
            multi_cities = random.sample(cities, 2)
            multi_trip = _create_multi_destination_trip(user, multi_cities)
            _create_checklist(multi_trip)
            _create_booking(multi_trip, multi_cities[0], user)
            _create_booking(multi_trip, multi_cities[1], user)
            _create_expenses_for_trip(multi_trip, user)
            _add_family_with_child(multi_trip)

        # Shared trips: user1 owns → user2 collabs, and vice versa
        if len(users) >= 2:
            user1, user2 = users[0], users[1]
            for owner, collab in [(user1, user2), (user2, user1)]:
                remaining_cities = [
                    c
                    for c in cities
                    if c
                    not in [t.destination for t in Trip.objects.filter(author=owner)]
                ]
                destination = (
                    remaining_cities[0] if remaining_cities else random.choice(cities)
                )
                shared_trip = TripFactory(
                    author=owner,
                    destination=destination,
                    start_date=date.today() + timedelta(days=5),
                    end_date=date.today() + timedelta(days=8),
                )
                color = TripCollaboration.next_free_color(shared_trip)
                TripCollaboration.objects.create(
                    trip=shared_trip,
                    user=collab,
                    color=color,
                    added_by=owner,
                )
                MainTransferFactory(
                    trip=shared_trip,
                    direction=1,
                )
                all_days = list(shared_trip.days.all())
                pool = _PlacePool()
                stay = StayFactory(
                    city=destination,
                    author=owner,
                    **_place_kwargs(pool.take(destination, "hotels")),
                )
                stay.days.set(all_days)

                for day in shared_trip.days.all():
                    # Meal by owner
                    MealFactory.create(
                        day=day,
                        trip=shared_trip,
                        type=2,
                        estimated_duration=timedelta(minutes=90),
                        city=destination,
                        last_modified_by=owner,
                        **_place_kwargs(pool.take(destination, "restaurants")),
                    )
                    MealFactory.create(
                        day=day,
                        trip=shared_trip,
                        type=3,
                        estimated_duration=timedelta(minutes=90),
                        city=destination,
                        last_modified_by=collab,
                        **_place_kwargs(pool.take(destination, "restaurants")),
                    )
                    ExperienceFactory.create(
                        day=day,
                        trip=shared_trip,
                        estimated_duration=timedelta(minutes=120),
                        city=destination,
                        last_modified_by=owner,
                        **_place_kwargs(pool.take(destination, "attractions")),
                    )
                    ExperienceFactory.create(
                        day=day,
                        trip=shared_trip,
                        estimated_duration=timedelta(minutes=120),
                        city=destination,
                        last_modified_by=collab,
                        **_place_kwargs(pool.take(destination, "attractions")),
                    )

                _create_checklist(shared_trip)
                _create_booking(shared_trip, destination, owner)
                _create_expenses_for_trip(shared_trip, owner)

        logger.info("Trips populated correctly!")
        self.stdout.write(self.style.SUCCESS("Successfully populated database"))
