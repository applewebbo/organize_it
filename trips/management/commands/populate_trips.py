import logging
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

logger = logging.getLogger("task")

NUMBER_OF_USERS = 1
TRIPS_PER_USER = 2

User = get_user_model()


class Command(BaseCommand):
    help = "Generates dummy trips with stays and events"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        faker = Faker("it_IT")
        self.stdout.write("Deleting old data...")
        User.objects.exclude(is_superuser=True).delete()
        models = [Trip, Stay, Event]
        for model in models:
            model.objects.all().delete()

        self.stdout.write("Creating new data...")
        UserFactory.create_batch(NUMBER_OF_USERS)
        users = User.objects.all()

        ITALIAN_CITIES_COORDS = [
            {"name": "Roma", "lat": 41.902782, "lon": 12.496366},
            {"name": "Milano", "lat": 45.464211, "lon": 9.191383},
            {"name": "Firenze", "lat": 43.769562, "lon": 11.255814},
            {"name": "Napoli", "lat": 40.851799, "lon": 14.26812},
            {"name": "Venezia", "lat": 45.440847, "lon": 12.315515},
            {"name": "Torino", "lat": 45.070339, "lon": 7.686864},
            {"name": "Bologna", "lat": 44.494887, "lon": 11.342616},
            {"name": "Genova", "lat": 44.40565, "lon": 8.946256},
            {"name": "Palermo", "lat": 38.115688, "lon": 13.361267},
            {"name": "Verona", "lat": 45.438384, "lon": 10.991622},
        ]

        for user in users:
            for _ in range(TRIPS_PER_USER):
                trip = TripFactory(
                    author=user,
                    start_date=date.today() + timedelta(days=random.randint(1, 3)),
                    end_date=date.today() + timedelta(days=random.randint(4, 6)),
                )

                city_coords = next(
                    (
                        city
                        for city in ITALIAN_CITIES_COORDS
                        if city["name"] == trip.title
                    ),
                    None,
                )
                base_lat, base_lon = city_coords["lat"], city_coords["lon"]

                all_days = list(trip.days.all())
                if len(all_days) > 2:
                    stay1 = StayFactory()
                    stay1.days.set(all_days[:2])
                    stay2 = StayFactory()
                    stay2.days.set(all_days[2:])
                else:
                    stay = StayFactory()
                    stay.days.set(all_days)

                for i, day in enumerate(trip.days.all()):
                    day_center_lat = base_lat + (i * random.uniform(-0.05, 0.05))
                    day_center_lon = base_lon + (i * random.uniform(-0.05, 0.05))
                    radius_in_degrees = 0.027  # Approx 3km

                    # Create transport
                    if i == 0 or random.random() < 0.3:
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
                            website=faker.url() if random.random() < 0.5 else "",
                            latitude=day_center_lat
                            + random.uniform(-radius_in_degrees, radius_in_degrees),
                            longitude=day_center_lon
                            + random.uniform(-radius_in_degrees, radius_in_degrees),
                        )

                    # Create meals
                    MealFactory.create(
                        day=day,
                        trip=trip,
                        type=2,
                        start_time=time(13, 0),
                        end_time=time(14, 30),
                        website=faker.url() if random.random() < 0.3 else "",
                        latitude=day_center_lat
                        + random.uniform(-radius_in_degrees, radius_in_degrees),
                        longitude=day_center_lon
                        + random.uniform(-radius_in_degrees, radius_in_degrees),
                    )
                    MealFactory.create(
                        day=day,
                        trip=trip,
                        type=3,
                        start_time=time(20, 0),
                        end_time=time(21, 30),
                        website=faker.url() if random.random() < 0.3 else "",
                        latitude=day_center_lat
                        + random.uniform(-radius_in_degrees, radius_in_degrees),
                        longitude=day_center_lon
                        + random.uniform(-radius_in_degrees, radius_in_degrees),
                    )

                    # Create experiences
                    for _ in range(random.randint(1, 4)):
                        start_time = time(
                            random.randint(8, 19), random.randrange(0, 59, 15)
                        )
                        end_time = (
                            datetime.combine(day.date, start_time)
                            + timedelta(minutes=random.randrange(0, 120, 15))
                        ).time()
                        ExperienceFactory.create(
                            day=day,
                            trip=trip,
                            start_time=start_time,
                            end_time=end_time,
                            website=faker.url() if random.random() < 0.3 else "",
                            latitude=day_center_lat
                            + random.uniform(-radius_in_degrees, radius_in_degrees),
                            longitude=day_center_lon
                            + random.uniform(-radius_in_degrees, radius_in_degrees),
                        )

        logger.info("Trips populated correctly!")
        self.stdout.write(self.style.SUCCESS("Successfully populated database"))
