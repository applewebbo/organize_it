import logging
import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TransportFactory,
    TripFactory,
)
from trips.models import Event, Stay, Trip

logger = logging.getLogger("task")

NUMBER_OF_USERS = 1
TRIPS_PER_USER = 2

User = get_user_model()


class Command(BaseCommand):
    help = "Generates dummy trips with stays and events"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        User.objects.exclude(is_superuser=True).delete()
        models = [Trip, Stay, Event]
        for model in models:
            model.objects.all().delete()

        self.stdout.write("Creating new data...")
        UserFactory.create_batch(NUMBER_OF_USERS)
        users = User.objects.all()

        for user in users:
            for _ in range(TRIPS_PER_USER):
                trip = TripFactory(
                    author=user,
                    start_date=date.today() + timedelta(days=random.randint(1, 3)),
                    end_date=date.today() + timedelta(days=random.randint(4, 6)),
                )

                all_days = list(trip.days.all())
                if len(all_days) > 2:
                    stay1 = StayFactory(trip_destination=trip.destination)
                    stay1.days.set(all_days[:2])
                    stay2 = StayFactory(trip_destination=trip.destination)
                    stay2.days.set(all_days[2:])
                else:
                    stay = StayFactory(trip_destination=trip.destination)
                    stay.days.set(all_days)

                for day in trip.days.all():
                    # Create transport
                    if random.random() < 0.3:
                        start_time = time(
                            random.randint(8, 14), random.randrange(0, 59, 15)
                        )
                        end_time = (
                            datetime.combine(day.date, start_time)
                            + timedelta(hours=random.randint(1, 4))
                        ).time()
                        TransportFactory.create(
                            day=day,
                            trip=trip,
                            start_time=start_time,
                            end_time=end_time,
                        )

                    # Create meals
                    MealFactory.create(
                        day=day,
                        trip=trip,
                        type=2,
                        start_time=time(13, 0),
                        end_time=time(14, 30),
                    )
                    MealFactory.create(
                        day=day,
                        trip=trip,
                        type=3,
                        start_time=time(20, 0),
                        end_time=time(21, 30),
                    )

                    # Create experiences
                    for _ in range(random.randint(1, 2)):
                        start_time = time(
                            random.randint(8, 19), random.randrange(0, 59, 15)
                        )
                        end_time = (
                            datetime.combine(day.date, start_time)
                            + timedelta(minutes=random.randrange(30, 120, 15))
                        ).time()
                        ExperienceFactory.create(
                            day=day,
                            trip=trip,
                            start_time=start_time,
                            end_time=end_time,
                        )

        logger.info("Trips populated correctly!")
        self.stdout.write(self.style.SUCCESS("Successfully populated database"))
