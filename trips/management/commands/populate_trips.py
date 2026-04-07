import logging
import random
from datetime import date, datetime, time, timedelta

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
                start_time=time(13, 0),
                end_time=time(14, 30),
                city=destination,
                chosen_place=chosen_restaurants[0],
                last_modified_by=creator,
            )
            MealFactory.create(
                day=day,
                trip=trip,
                type=3,
                start_time=time(20, 0),
                end_time=time(21, 30),
                city=destination,
                chosen_place=chosen_restaurants[1],
                last_modified_by=creator,
            )
        else:
            MealFactory.create(
                day=day,
                trip=trip,
                type=2,
                start_time=time(13, 0),
                end_time=time(14, 30),
                city=destination,
                last_modified_by=creator,
            )

        start_time = time(random.randint(8, 11), random.randrange(0, 59, 15))
        end_time = (
            datetime.combine(day.date, start_time)
            + timedelta(minutes=random.randrange(60, 120, 15))
        ).time()
        ExperienceFactory.create(
            day=day,
            trip=trip,
            start_time=start_time,
            end_time=end_time,
            city=destination,
            last_modified_by=creator,
        )


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
                    start_time=time(8, 0),
                    end_time=time(10, 30),
                )
                MainTransferFactory(
                    trip=trip,
                    direction=2,
                    start_time=time(16, 0),
                    end_time=time(18, 30),
                )
                all_days = list(trip.days.all())
                _create_stay_and_events(trip, all_days, author=user, creator=user)

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
                    start_time=time(9, 0),
                    end_time=time(11, 0),
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
                        start_time=time(13, 0),
                        end_time=time(14, 30),
                        city=destination,
                        chosen_place=chosen[0] if chosen else None,
                        last_modified_by=owner,
                    )
                    # Meal by collaborator
                    MealFactory.create(
                        day=day,
                        trip=shared_trip,
                        type=3,
                        start_time=time(20, 0),
                        end_time=time(21, 30),
                        city=destination,
                        chosen_place=chosen[1] if len(chosen) > 1 else None,
                        last_modified_by=collab,
                    )
                    # Experience by owner
                    ExperienceFactory.create(
                        day=day,
                        trip=shared_trip,
                        start_time=time(10, 0),
                        end_time=time(12, 0),
                        city=destination,
                        last_modified_by=owner,
                    )
                    # Experience by collaborator
                    ExperienceFactory.create(
                        day=day,
                        trip=shared_trip,
                        start_time=time(15, 0),
                        end_time=time(17, 0),
                        city=destination,
                        last_modified_by=collab,
                    )

        logger.info("Trips populated correctly!")
        self.stdout.write(self.style.SUCCESS("Successfully populated database"))
