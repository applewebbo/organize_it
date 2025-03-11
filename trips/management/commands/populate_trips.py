import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from tests.accounts.factories import UserFactory
from tests.trips.factories import (
    ExperienceFactory,
    MealFactory,
    StayFactory,
    TransportFactory,
    TripFactory,
)
from trips.models import Event, Stay, Trip

NUMBER_OF_USERS = 1
TRIPS_PER_USER = 2

User = get_user_model()


class Command(BaseCommand):
    help = "Generates dummy trips with stays and events"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        faker = Faker()
        self.stdout.write("Deleting old data...")
        User.objects.exclude(is_superuser=True).delete()
        models = [Trip, Stay, Event]
        for model in models:
            model.objects.all().delete()

        self.stdout.write("Creating new data...")
        # Create users
        UserFactory.create_batch(NUMBER_OF_USERS)
        users = User.objects.all()

        for user in users:
            # Create trips for each user
            for _ in range(TRIPS_PER_USER):
                trip = TripFactory(
                    author=user,
                    start_date=date.today() + timedelta(days=random.randint(1, 3)),
                    end_date=date.today() + timedelta(days=random.randint(4, 6)),
                )

                # Create stays for the trip
                all_days = list(trip.days.all())
                num_stays = 2 if len(all_days) > 2 else 1

                # First stay always covers days 1-2
                url = faker.url() if random.random() < 0.9 else None
                first_stay = StayFactory(
                    check_in=time(random.randint(14, 16), 0),
                    check_out=time(random.randint(10, 12), 0),
                    url=url,
                )
                first_stay.days.set(all_days[:2])

                # Second stay covers remaining days if they exist
                if num_stays == 2 and len(all_days) > 2:
                    url = faker.url() if random.random() < 0.9 else None
                    second_stay = StayFactory(
                        check_in=time(random.randint(14, 16), 0),
                        check_out=time(random.randint(10, 12), 0),
                        url=url,
                    )
                    second_stay.days.set(all_days[2:])

                # Create events for each day
                for i, day in enumerate(trip.days.all()):
                    # Create transport for first day and randomly for other days
                    if i == 0 or random.random() < 0.3:
                        # Add URL with 50% probability for transports
                        url = faker.url() if random.random() < 0.5 else None
                        # Generate random start time between 8:00 and 14:00
                        start_hour = random.randint(8, 14)
                        start_minute = random.randrange(0, 59, 15)
                        start_time = time(start_hour, start_minute)

                        # Generate end time 1-4 hours after start time
                        start_datetime = datetime.combine(day.date, start_time)
                        duration = timedelta(hours=random.randint(1, 4))
                        end_datetime = start_datetime + duration
                        end_time = end_datetime.time()

                        TransportFactory(
                            day=day, start_time=start_time, end_time=end_time, url=url
                        )

                    # Create two meals (lunch and dinner)
                    # Add URL with 60% probability for meals
                    url = faker.url() if random.random() < 0.6 else None
                    MealFactory(
                        day=day,
                        type=2,  # Lunch
                        start_time=time(13, 0),
                        end_time=time(14, 30),
                        url=url,
                    )
                    # Add URL with 60% probability for meals
                    url = faker.url() if random.random() < 0.6 else None
                    MealFactory(
                        day=day,
                        type=3,  # Dinner
                        start_time=time(20, 0),
                        end_time=time(21, 30),
                        url=url,
                    )

                    # Create 1-4 experiences
                    for _ in range(random.randint(1, 4)):
                        # Add URL with 60% probability for experiences
                        url = faker.url() if random.random() < 0.6 else None
                        # Generate random start time between 8:00 and 19:00
                        start_hour = random.randint(8, 19)
                        start_minute = random.randrange(0, 59, 15)
                        start_time = time(start_hour, start_minute)

                        # Generate end time up to 2 hours after start time
                        start_datetime = datetime.combine(day.date, start_time)
                        duration = timedelta(minutes=random.randrange(0, 120, 15))
                        end_datetime = start_datetime + duration
                        end_time = end_datetime.time()

                        ExperienceFactory(
                            day=day, start_time=start_time, end_time=end_time, url=url
                        )

        self.stdout.write(self.style.SUCCESS("Successfully populated database"))
