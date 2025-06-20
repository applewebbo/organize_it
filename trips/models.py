from datetime import date, timedelta

import geocoder
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


def days_between(start_date, end_date):
    delta = end_date - start_date
    return delta.days


class Trip(models.Model):
    class Status(models.IntegerChoices):
        NOT_STARTED = 1, _("Not started")
        IMPENDING = 2, _("Impending")
        IN_PROGRESS = 3, _("In progress")
        COMPLETED = 4, _("Completed")
        ARCHIVED = 5, _("Archived")

    title = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True)
    destination = models.CharField(max_length=100)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.IntegerField(choices=Status, default=Status.NOT_STARTED)
    links = models.ManyToManyField("Link", related_name="trips", blank=True)

    class Meta:
        ordering = ("status",)

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        today = date.today()
        seven_days_after = today + timedelta(days=7)
        if self.start_date and self.end_date:
            # add the case for when status is 5 to bypass date checks
            if self.status == 5:
                super().save(*args, **kwargs)
                return
            # after end date
            if self.end_date < today:
                self.status = 4
            # between start date and end date
            elif self.start_date <= today and self.end_date >= today:
                self.status = 3
            # less than 7 days from start date
            elif self.start_date < seven_days_after and self.start_date > today:
                self.status = 2
            # more than 7 days from start date
            elif self.start_date <= seven_days_after:
                self.status = 1

        super().save(*args, **kwargs)


@receiver(post_save, sender=Trip)
def update_trip_days(sender, instance, **kwargs):
    """
    Update the days for a trip when start_date or end_date changes.
    Retain the order of days and shift existing days and their related objects accordingly.
    """
    if not instance.start_date or not instance.end_date:
        return

    days_total = days_between(instance.start_date, instance.end_date) + 1
    desired_dates = [instance.start_date + timedelta(days=i) for i in range(days_total)]

    # Build a mapping of current days by date
    current_days_by_date = {day.date: day for day in instance.days.all()}
    # Delete days outside the new range
    for day in instance.days.all():
        if day.date not in desired_dates:
            day.delete()

    # Get all days ordered by date (after deletion)
    list(instance.days.order_by("date"))

    # For each desired date, either update an existing day or create a new one
    for idx, day_date in enumerate(desired_dates):
        if day_date in current_days_by_date:
            # Update number if needed
            day = current_days_by_date[day_date]
            if day.number != idx + 1:
                day.number = idx + 1
                day.save(update_fields=["number"])
        else:
            # Insert a new day at the correct position
            Day.objects.create(
                trip=instance,
                number=idx + 1,
                date=day_date,
            )


class Stay(models.Model):
    name = models.CharField(max_length=100)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    cancellation_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(
        max_length=30,
        blank=True,
        validators=[
            RegexValidator(
                # Allow at most 2 spaces anywhere after the first digit
                regex=r"^\+?\d(?: ?\d){7,19}$",
                message=_(
                    "Enter a valid phone number (with or without international prefix, and at most 2 spaces)."
                ),
            ),
            RegexValidator(
                # Disallow more than 2 spaces
                regex=r"^(?:[^ ]* ?){0,3}$|^\+?\d(?: ?\d){7,19}$",
                message=_("Phone number can contain at most 2 spaces."),
            ),
        ],
    )
    url = models.URLField(null=True, blank=True)
    address = models.CharField(max_length=200)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)

    def save(self, *args, **kwargs):
        """convert address to coordinates for displaying on the map"""
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        # if address is not changed, don't update coordinates
        if old and old.address == self.address:
            return super().save(*args, **kwargs)
        g = geocoder.mapbox(self.address, access_token=settings.MAPBOX_ACCESS_TOKEN)
        self.latitude, self.longitude = g.latlng
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        first_day = self.days.first()
        return f"{self.name} - {first_day.trip.title}" if first_day else self.name


@receiver(post_save, sender=Stay)
def update_stay_days(sender, instance, **kwargs):
    """
    When days are assigned to a stay, remove those days from any previous stays
    """
    # Get all days that are now assigned to this stay
    related_days = instance.days.all()

    # For each day, remove any other stay relationships
    for day in related_days:
        # Find other stays linked to this day (excluding the current stay)
        Day.objects.filter(stay__isnull=False, pk=day.pk).exclude(stay=instance).update(
            stay=None
        )


class Day(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="days")
    stay = models.ForeignKey(
        Stay, on_delete=models.SET_NULL, null=True, blank=True, related_name="days"
    )
    number = models.PositiveSmallIntegerField()
    date = models.DateField()

    class Meta:
        ordering = ["number"]

    @property
    def next_day(self):
        """Get next day using prefetched data"""
        days = [d for d in self.trip.days.all()]
        try:
            current_index = days.index(self)
            return days[current_index + 1] if current_index + 1 < len(days) else None
        except (ValueError, IndexError):
            return None

    @property
    def prev_day(self):
        """Get previous day using prefetched data"""
        days = [d for d in self.trip.days.all()]
        try:
            current_index = days.index(self)
            return days[current_index - 1] if current_index > 0 else None
        except (ValueError, IndexError):
            return None

    def __str__(self) -> str:
        day = _("Day")
        return f"{day} {self.number} [{self.trip.title}]"


class Link(models.Model):
    title = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="links"
    )

    def __str__(self) -> str:
        return self.url


class Event(models.Model):
    class Category(models.IntegerChoices):
        TRANSPORT = 1, _("Transport")
        EXPERIENCE = 2, _("Experience")
        MEAL = 3, _("Meal")

    day = models.ForeignKey(
        Day, on_delete=models.SET_NULL, related_name="events", null=True
    )
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="all_events")
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    url = models.URLField(null=True, blank=True)
    address = models.CharField(max_length=200)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    category = models.PositiveSmallIntegerField(
        choices=Category.choices, default=Category.EXPERIENCE
    )
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["day_id", "start_time"]),
        ]

    def save(self, *args, **kwargs):
        """convert address to coordinates for displaying on the map"""
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        # if address is not changed, don't update coordinates
        if old and old.address == self.address:
            return super().save(*args, **kwargs)
        g = geocoder.mapbox(self.address, access_token=settings.MAPBOX_ACCESS_TOKEN)
        self.latitude, self.longitude = g.latlng
        # Ensure trip is set from day if not already set
        if self.day and not self.trip_id:
            self.trip = self.day.trip
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.start_time})"

    def swap_times_with(self, other_event):
        """
        Swap start and end times with another event.
        Both events must belong to the same day.
        """
        if self.day_id != other_event.day_id:
            raise ValueError("Can only swap events within the same day")

        self.start_time, other_event.start_time = (
            other_event.start_time,
            self.start_time,
        )
        self.end_time, other_event.end_time = other_event.end_time, self.end_time

        # Save both events
        self.save()
        other_event.save()


@receiver(pre_save, sender=Event)
def update_event_trip(sender, instance, **kwargs):
    """
    Ensure event's trip is always set correctly based on its day
    """
    if instance.day_id:
        if not instance.trip_id or instance.trip_id != instance.day.trip_id:
            instance.trip = instance.day.trip


class Transport(Event):
    class Type(models.IntegerChoices):
        CAR = 1, _("Car")
        PLANE = 2, _("Plane")
        TRAIN = 3, _("Train")
        BOAT = 4, _("Boat")
        BUS = 5, _("Bus")
        TAXI = 6, _("Taxi")
        OTHER = 7, _("Other")

    type = models.IntegerField(choices=Type.choices, default=Type.CAR)
    destination = models.CharField(max_length=100)
    dest_latitude = models.FloatField(null=True, blank=True)
    dest_longitude = models.FloatField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """convert destination to coordinates for displaying on the map"""
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        # if address is not changed, don't update coordinates
        if old and old.destination == self.destination:
            return super().save(*args, **kwargs)
        g = geocoder.mapbox(self.destination, access_token=settings.MAPBOX_ACCESS_TOKEN)
        self.dest_latitude, self.dest_longitude = g.latlng
        # autosave category for transport
        self.category = self.Category.TRANSPORT

        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.day.trip.title} - Day {self.day.number})"


class Experience(Event):
    class Type(models.IntegerChoices):
        MUSEUM = 1, _("Museum")
        PARK = 2, _("Park")
        WALK = 3, _("Walk")
        SPORT = 4, _("Sport")
        OTHER = 6, _("Other")

    type = models.IntegerField(choices=Type.choices, default=Type.MUSEUM)

    def __str__(self) -> str:
        return f"{self.name} ({self.day.trip.title} - Day {self.day.number})"

    def save(self, *args, **kwargs):
        """autosave category for experience"""
        self.category = self.Category.EXPERIENCE
        return super().save(*args, **kwargs)


class Meal(Event):
    class Type(models.IntegerChoices):
        BREAKFAST = 1, _("Breakfast")
        LUNCH = 2, _("Lunch")
        DINNER = 3, _("Dinner")
        SNACK = 4, _("Snack")

    type = models.IntegerField(choices=Type.choices, default=Type.LUNCH)

    def __str__(self) -> str:
        return f"{self.name} ({self.day.trip.title} - Day {self.day.number})"

    def save(self, *args, **kwargs):
        """autosave category for meal"""
        self.category = self.Category.MEAL
        return super().save(*args, **kwargs)


# class Note(models.Model):
#     content = models.CharField(max_length=500)
#     event = models.OneToOneField(
#         Event, on_delete=models.CASCADE, null=True, blank=True, related_name="note"
#     )
#     stay = models.OneToOneField(
#         Stay, on_delete=models.CASCADE, null=True, blank=True, related_name="note"
#     )

#     def __str__(self) -> str:
#         return f"{self.content[:35]} ..."
