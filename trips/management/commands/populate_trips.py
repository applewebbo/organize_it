import logging
import random
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    ITALIAN_CITIES,
    PLACES,
    ExperienceFactory,
    MainTransferFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.models import Trip, TripCollaboration

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


def _create_stay_and_events(trip, all_days, author, creator):
    """Create stay, meals and experiences for a trip."""
    destination = trip.destination
    hotels_for_city = PLACES[destination]["hotels"]
    restaurants_for_city = PLACES[destination]["restaurants"]

    if len(all_days) > 2 and len(hotels_for_city) >= 2:
        chosen_hotels = random.sample(hotels_for_city, 2)
        stay1 = StayFactory(
            city=destination, chosen_place=chosen_hotels[0], author=author
        )
        stay1.days.set(all_days[:2])
        stay2 = StayFactory(
            city=destination, chosen_place=chosen_hotels[1], author=author
        )
        stay2.days.set(all_days[2:])
    else:
        stay = StayFactory(city=destination, author=author)
        stay.days.set(all_days)

    for day in trip.days.all():
        if len(restaurants_for_city) >= 2:
            chosen_restaurants = random.sample(restaurants_for_city, 2)
            MealFactory.create(
                day=day,
                trip=trip,
                type=2,
                estimated_duration=timedelta(minutes=90),
                city=destination,
                chosen_place=chosen_restaurants[0],
                last_modified_by=creator,
            )
            MealFactory.create(
                day=day,
                trip=trip,
                type=3,
                estimated_duration=timedelta(minutes=90),
                city=destination,
                chosen_place=chosen_restaurants[1],
                last_modified_by=creator,
            )
        else:
            MealFactory.create(
                day=day,
                trip=trip,
                type=2,
                estimated_duration=timedelta(minutes=90),
                city=destination,
                last_modified_by=creator,
            )

        ExperienceFactory.create(
            day=day,
            trip=trip,
            estimated_duration=timedelta(minutes=random.randrange(60, 120, 15)),
            city=destination,
            last_modified_by=creator,
        )


def _create_events_for_day(day, trip, city, creator):
    """Create meal and experience events for a day using the given city's places."""
    restaurants = PLACES[city]["restaurants"]
    if len(restaurants) >= 2:
        chosen = random.sample(restaurants, 2)
        MealFactory.create(
            day=day,
            trip=trip,
            type=2,
            estimated_duration=timedelta(minutes=90),
            city=city,
            chosen_place=chosen[0],
            last_modified_by=creator,
        )
        MealFactory.create(
            day=day,
            trip=trip,
            type=3,
            estimated_duration=timedelta(minutes=90),
            city=city,
            chosen_place=chosen[1],
            last_modified_by=creator,
        )
    else:
        MealFactory.create(
            day=day,
            trip=trip,
            type=2,
            estimated_duration=timedelta(minutes=90),
            city=city,
            last_modified_by=creator,
        )
    ExperienceFactory.create(
        day=day,
        trip=trip,
        estimated_duration=timedelta(minutes=random.randrange(60, 120, 15)),
        city=city,
        last_modified_by=creator,
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

    # First half: main destination (city1, leave day.destination blank = inherits trip.destination)
    first_half = all_days[:mid]
    second_half = all_days[mid:]

    # Second half: assign custom destination (city2)
    for day in second_half:
        day.destination = city2
        day.save(update_fields=["destination"])

    # Stay for city1
    if PLACES[city1]["hotels"]:
        stay1 = StayFactory(
            city=city1, chosen_place=PLACES[city1]["hotels"][0], author=user
        )
        stay1.days.set(first_half)

    # Stay for city2
    if PLACES[city2]["hotels"]:
        stay2 = StayFactory(
            city=city2, chosen_place=PLACES[city2]["hotels"][0], author=user
        )
        stay2.days.set(second_half)

    for day in first_half:
        _create_events_for_day(day, trip, city1, user)
    for day in second_half:
        _create_events_for_day(day, trip, city2, user)

    return trip


class Command(BaseCommand):
    help = "Generates dummy trips with stays and events (keeps existing users)"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting existing trips...")
        Trip.objects.all().delete()

        # Keep existing non-superuser accounts; create if fewer than NUMBER_OF_USERS
        users = list(User.objects.filter(is_superuser=False))
        if len(users) < NUMBER_OF_USERS:
            needed = NUMBER_OF_USERS - len(users)
            UserFactory.create_batch(needed)
            users = list(User.objects.filter(is_superuser=False))

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
                _create_stay_and_events(trip, all_days, author=user, creator=user)

        # Multi-destination road trip for each user
        for user in users:
            multi_cities = random.sample(cities, 2)
            _create_multi_destination_trip(user, multi_cities)

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
                stay = StayFactory(city=destination, author=owner)
                stay.days.set(all_days)

                for day in shared_trip.days.all():
                    restaurants = PLACES[destination]["restaurants"]
                    chosen = random.sample(restaurants, min(2, len(restaurants)))
                    # Meal by owner
                    MealFactory.create(
                        day=day,
                        trip=shared_trip,
                        type=2,
                        estimated_duration=timedelta(minutes=90),
                        city=destination,
                        chosen_place=chosen[0] if chosen else None,
                        last_modified_by=owner,
                    )
                    MealFactory.create(
                        day=day,
                        trip=shared_trip,
                        type=3,
                        estimated_duration=timedelta(minutes=90),
                        city=destination,
                        chosen_place=chosen[1] if len(chosen) > 1 else None,
                        last_modified_by=collab,
                    )
                    ExperienceFactory.create(
                        day=day,
                        trip=shared_trip,
                        estimated_duration=timedelta(minutes=120),
                        city=destination,
                        last_modified_by=owner,
                    )
                    ExperienceFactory.create(
                        day=day,
                        trip=shared_trip,
                        estimated_duration=timedelta(minutes=120),
                        city=destination,
                        last_modified_by=collab,
                    )

        logger.info("Trips populated correctly!")
        self.stdout.write(self.style.SUCCESS("Successfully populated database"))
