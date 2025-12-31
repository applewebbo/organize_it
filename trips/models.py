from datetime import date, timedelta

import geocoder
from django.conf import settings
from django.core.exceptions import ValidationError
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
    image = models.ImageField(
        upload_to="trips/%Y/%m/",
        blank=True,
        null=True,
        help_text="Trip cover image (landscape, max 2MB)",
    )
    image_metadata = models.JSONField(
        default=dict, blank=True, help_text="Image source and attribution data"
    )

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

    @property
    def get_image_url(self):
        """Get image URL for template use"""
        return self.image.url if self.image else None

    @property
    def needs_attribution(self):
        """Check if Unsplash attribution required"""
        return self.image_metadata.get("source") == "unsplash"

    def get_attribution_text(self):
        """Get formatted attribution text"""
        if self.needs_attribution:
            photographer = self.image_metadata.get("photographer", "Unknown")
            return f"Photo by {photographer} on Unsplash"
        return None


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
    phone_number = models.CharField(max_length=50, blank=True)
    website = models.URLField(max_length=255, blank=True)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    place_id = models.CharField(max_length=255, blank=True)
    opening_hours = models.JSONField(blank=True, null=True)
    enriched = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        Convert address to coordinates for displaying on the map,
        only if the address has changed or coordinates are not set.
        """
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        address_changed = old and old.address != self.address
        coords_missing = self.latitude is None or self.longitude is None
        complete_address = self.address
        if self.city:
            complete_address = f"{self.address}, {self.city}"

        if address_changed or coords_missing:
            g = geocoder.mapbox(
                complete_address, access_token=settings.MAPBOX_ACCESS_TOKEN
            )
            if g.latlng:
                self.latitude, self.longitude = g.latlng

        super().save(*args, **kwargs)

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
        Day, on_delete=models.SET_NULL, related_name="events", null=True, blank=True
    )
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="all_events")
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    category = models.PositiveSmallIntegerField(
        choices=Category.choices, default=Category.EXPERIENCE
    )
    notes = models.CharField(
        max_length=500,
        blank=True,
    )
    # Additional fields for Google Places data
    place_id = models.CharField(max_length=255, blank=True)
    website = models.URLField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    opening_hours = models.JSONField(blank=True, null=True)
    enriched = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["day_id", "start_time"]),
        ]

    def save(self, *args, **kwargs):
        """
        Convert address to coordinates for displaying on the map,
        only if the address has changed or coordinates are not set.
        """
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        address_changed = old and old.address != self.address
        coords_missing = self.latitude is None or self.longitude is None
        complete_address = self.address
        if self.city:
            complete_address = f"{self.address}, {self.city}"

        if address_changed or coords_missing:
            g = geocoder.mapbox(
                complete_address, access_token=settings.MAPBOX_ACCESS_TOKEN
            )
            if g.latlng:
                self.latitude, self.longitude = g.latlng

        # Ensure trip is set from day if not already set
        if self.day and not self.trip_id:
            self.trip = self.day.trip

        super().save(*args, **kwargs)

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

    class Direction(models.IntegerChoices):
        ARRIVAL = 1, _("Arrival")
        DEPARTURE = 2, _("Departure")

    type = models.IntegerField(choices=Type.choices, default=Type.CAR)

    # Main transfer fields
    is_main_transfer = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this is a main arrival/departure transfer",
    )

    direction = models.IntegerField(
        choices=Direction.choices,
        null=True,
        blank=True,
        help_text="Required for main transfers (arrival or departure)",
    )

    type_specific_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Type-specific fields: flight_number, train_number, rental_info, etc.",
    )

    # Origin fields
    origin_city = models.CharField(max_length=100)
    origin_address = models.CharField(max_length=200, blank=True)
    origin_latitude = models.FloatField(null=True, blank=True)
    origin_longitude = models.FloatField(null=True, blank=True)

    # Destination fields
    destination_city = models.CharField(max_length=100)
    destination_address = models.CharField(max_length=200, blank=True)
    destination_latitude = models.FloatField(null=True, blank=True)
    destination_longitude = models.FloatField(null=True, blank=True)

    # Booking fields
    booking_reference = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    ticket_url = models.URLField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Properties for type-specific fields (flight)
    @property
    def flight_number(self):
        return self.type_specific_data.get("flight_number", "")

    @property
    def gate(self):
        return self.type_specific_data.get("gate", "")

    @property
    def terminal(self):
        return self.type_specific_data.get("terminal", "")

    @property
    def checked_baggage(self):
        return self.type_specific_data.get("checked_baggage", 0)

    # Properties for type-specific fields (train)
    @property
    def train_number(self):
        return self.type_specific_data.get("train_number", "")

    @property
    def carriage(self):
        return self.type_specific_data.get("carriage", "")

    @property
    def seat(self):
        return self.type_specific_data.get("seat", "")

    @property
    def platform(self):
        return self.type_specific_data.get("platform", "")

    # Properties for type-specific fields (car)
    @property
    def is_rental(self):
        return self.type_specific_data.get("is_rental", False)

    @property
    def license_plate(self):
        return self.type_specific_data.get("license_plate", "")

    @property
    def car_type(self):
        return self.type_specific_data.get("car_type", "")

    @property
    def rental_booking_reference(self):
        return self.type_specific_data.get("rental_booking_reference", "")

    # Properties for common fields
    @property
    def company_link(self):
        return self.type_specific_data.get("company_link", "")

    @property
    def duration(self):
        """Calculate duration between start_time and end_time"""
        from datetime import datetime, timedelta

        # Handle both time objects and string representations
        start_time = self.start_time
        end_time = self.end_time

        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, "%H:%M").time()
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, "%H:%M").time()

        # Convert times to datetime for calculation
        start = datetime.combine(datetime.today(), start_time)
        end = datetime.combine(datetime.today(), end_time)

        # Handle overnight transports (end time is next day)
        if end < start:
            end += timedelta(days=1)

        return end - start

    def clean(self):
        super().clean()

        # MainTransfer MUST have day=None
        if self.is_main_transfer and self.day is not None:
            raise ValidationError(
                {"day": _("Main transfers cannot be assigned to a specific day")}
            )

        # MainTransfer MUST have direction
        if self.is_main_transfer and not self.direction:
            raise ValidationError(
                {
                    "direction": _(
                        "Main transfers must have a direction (arrival/departure)"
                    )
                }
            )

        # Normal transport should NOT have direction
        if not self.is_main_transfer and self.direction:
            raise ValidationError(
                {"direction": _("Only main transfers can have a direction")}
            )

        # Only 1 MainTransfer per direction per trip
        if self.is_main_transfer:
            existing = Transport.objects.filter(
                trip=self.trip, is_main_transfer=True, direction=self.direction
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    {
                        "direction": _(
                            "A %(direction)s transfer already exists for this trip"
                        )
                        % {"direction": self.get_direction_display()}
                    }
                )

    def save(self, *args, **kwargs):
        """Geocode origin and destination addresses for displaying on the map"""
        # Force day=None for main transfers
        if self.is_main_transfer:
            self.day = None

        old = type(self).objects.get(pk=self.pk) if self.pk else None

        # Geocode origin
        origin_changed = old and (
            old.origin_city != self.origin_city
            or old.origin_address != self.origin_address
        )
        origin_coords_missing = (
            self.origin_latitude is None or self.origin_longitude is None
        )

        if origin_changed or origin_coords_missing:
            # Build complete origin address
            complete_origin = self.origin_city
            if self.origin_address:
                complete_origin = f"{self.origin_address}, {self.origin_city}"

            g = geocoder.mapbox(
                complete_origin, access_token=settings.MAPBOX_ACCESS_TOKEN
            )
            if g.latlng:
                self.origin_latitude, self.origin_longitude = g.latlng

        # Geocode destination
        destination_changed = old and (
            old.destination_city != self.destination_city
            or old.destination_address != self.destination_address
        )
        dest_coords_missing = (
            self.destination_latitude is None or self.destination_longitude is None
        )

        if destination_changed or dest_coords_missing:
            # Build complete destination address
            complete_destination = self.destination_city
            if self.destination_address:
                complete_destination = (
                    f"{self.destination_address}, {self.destination_city}"
                )

            g = geocoder.mapbox(
                complete_destination, access_token=settings.MAPBOX_ACCESS_TOKEN
            )
            if g.latlng:
                self.destination_latitude, self.destination_longitude = g.latlng

        # Autosave category for transport
        self.category = self.Category.TRANSPORT

        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.origin_city} → {self.destination_city} ({self.get_type_display()})"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "direction"],
                condition=models.Q(is_main_transfer=True),
                name="unique_main_transfer_per_direction",
            )
        ]


class Experience(Event):
    class Type(models.IntegerChoices):
        MUSEUM = 1, _("Museum")
        PARK = 2, _("Park")
        WALK = 3, _("Walk")
        SPORT = 4, _("Sport")
        OTHER = 5, _("Other")

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
