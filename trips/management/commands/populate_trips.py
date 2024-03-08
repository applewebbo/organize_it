import datetime
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from tests.accounts.factories import UserFactory
from tests.trips.factories import LinkFactory, NoteFactory, PlaceItFactory, TripFactory
from trips.models import Link, Note, Place, Trip

NUMBER_OF_USERS = 2
MAX_ACTIVE_TRIPS_PER_USER = 4
MAX_COMPLETED_TRIPS_PER_USER = 3
MAX_ARCHIVED_TRIPS_PER_USER = 3
MAX_LINKS_PER_USER = 15
MAX_NOTES_PER_TRIP = 5
MAX_PLACES_PER_TRIP = 8

User = get_user_model()


class Command(BaseCommand):
    help = "Generates dummy trips"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        # deleting all user except superuser
        User.objects.exclude(is_superuser=True).delete()
        # deleting all trips, notes, links, places
        models = [Trip, Note, Link, Place]
        for model in models:
            model.objects.all().delete()

        self.stdout.write("Creating new data...")
        # creating users with email=user_*@test.com and password=1234
        UserFactory.create_batch(NUMBER_OF_USERS)
        # creating trips
        for user in User.objects.all():
            TripFactory.create_batch(
                random.randint(2, MAX_ACTIVE_TRIPS_PER_USER), author=user
            )
            TripFactory.create_batch(
                random.randint(1, MAX_ARCHIVED_TRIPS_PER_USER), author=user, status=5
            )
            TripFactory.create_batch(
                random.randint(1, MAX_COMPLETED_TRIPS_PER_USER),
                author=user,
                start_date=datetime.date.today() - datetime.timedelta(days=30),
                end_date=datetime.date.today() - datetime.timedelta(days=25),
            )
        # creating links
        for user in User.objects.all():
            links = LinkFactory.create_batch(
                random.randint(5, MAX_LINKS_PER_USER),
                author=user,
            )
            for link in links:
                link.trips.add(
                    *random.choices(
                        Trip.objects.filter(author=user),
                        k=random.randint(2, MAX_ACTIVE_TRIPS_PER_USER),
                    )
                )

        # creating notes
        for trip in Trip.objects.all():
            NoteFactory.create_batch(random.randint(1, MAX_NOTES_PER_TRIP), trip=trip)
        # creating places
        # TODO: create address, lat and long without using mapbox to speed up command and avoid needing internet connection
        for trip in Trip.objects.all():
            places = PlaceItFactory.create_batch(
                random.randint(3, MAX_PLACES_PER_TRIP), trip=trip
            )
            # assign places ro random days
            for place in places:
                place.day = random.choice(trip.days.all())
                place.save()
