import uuid
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote

import geocoder
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def days_between(start_date, end_date):
    delta = end_date - start_date
    return delta.days


# Kept in sync with accounts.models.Profile.CURRENCY_CHOICES (asserted in tests)
CURRENCY_CHOICES = [
    ("EUR", "Euro (€)"),
    ("USD", "US Dollar ($)"),
    ("GBP", "Pound Sterling (£)"),
]


class Trip(models.Model):
    class Status(models.IntegerChoices):
        NOT_STARTED = 1, _("Not started")
        IMPENDING = 2, _("Impending")
        IN_PROGRESS = 3, _("In progress")
        COMPLETED = 4, _("Completed")
        ARCHIVED = 5, _("Archived")

    title = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    destination_latitude = models.FloatField(null=True, blank=True)
    destination_longitude = models.FloatField(null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.IntegerField(choices=Status, default=Status.NOT_STARTED)
    links = models.ManyToManyField("Link", related_name="trips", blank=True)
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TripCollaboration",
        through_fields=("trip", "user"),
        related_name="collaborated_trips",
        blank=True,
    )
    image = models.ImageField(
        upload_to="trips/%Y/%m/",
        blank=True,
        null=True,
        help_text="Trip cover image (landscape, max 2MB)",
    )
    image_metadata = models.JSONField(
        default=dict, blank=True, help_text="Image source and attribution data"
    )
    checklist_reminder_days = models.PositiveSmallIntegerField(null=True, blank=True)
    checklist_reminder_sent_at = models.DateField(null=True, blank=True)
    weather_reminder_sent_at = models.DateField(null=True, blank=True)
    daily_digest_sent_on = models.DateField(null=True, blank=True)
    calendar_token = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, null=True
    )
    expenses_enabled = models.BooleanField(default=False)
    expense_currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOICES, default="EUR"
    )

    class Meta:
        ordering = ("status",)
        indexes = [
            models.Index(fields=["author", "status"]),
            models.Index(fields=["author", "-start_date"]),
        ]

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
            else:
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

    @property
    def checklist_total(self):
        return self.checklist_items.count()

    @property
    def checklist_completed(self):
        return self.checklist_items.filter(completed=True).count()

    @property
    def is_multi_destination(self):
        """Returns True if the trip has days with different destinations."""
        if not self.pk:
            return False
        # Reuse prefetched days when available to avoid extra queries
        destinations = {day.destination for day in self.days.all()}
        return len(destinations) > 1


@receiver(pre_save, sender="trips.Trip")
def capture_trip_old_destination(sender, instance, **kwargs):
    """Store old destination and geocode when destination changes."""
    if instance.pk:
        try:
            old = Trip.objects.get(pk=instance.pk)
            instance._old_destination = old.destination
        except Trip.DoesNotExist:
            instance._old_destination = None
    else:
        instance._old_destination = None

    destination_changed = instance._old_destination != instance.destination
    if destination_changed and instance.destination:
        # Constrain to place-level results so an ambiguous name (e.g. "Roma")
        # resolves to the city and cannot match a country (e.g. România).
        g = geocoder.mapbox(
            instance.destination,
            access_token=settings.MAPBOX_ACCESS_TOKEN,
            types="place",
        )
        if g.latlng:
            instance.destination_latitude, instance.destination_longitude = g.latlng
        else:
            instance.destination_latitude = None
            instance.destination_longitude = None


@receiver(post_save, sender=Trip)
def update_trip_days(sender, instance, **kwargs):
    """
    Update the days for a trip when start_date or end_date changes.
    Retain the order of days and shift existing days and their related objects accordingly.
    New days are assigned trip.destination; existing days with the old destination are updated too.
    """
    if not instance.start_date or not instance.end_date:
        return

    days_total = days_between(instance.start_date, instance.end_date) + 1
    desired_dates = [instance.start_date + timedelta(days=i) for i in range(days_total)]

    # Build a mapping of current days by date
    current_days_by_date = {day.date: day for day in instance.days.all()}

    old_destination = getattr(instance, "_old_destination", None)
    destination_changed = old_destination and old_destination != instance.destination

    # Delete days outside the new range
    for day in instance.days.all():
        if day.date not in desired_dates:
            day.delete()

    # Get all days ordered by date (after deletion)
    list(instance.days.order_by("date"))

    # For each desired date, either update an existing day or create a new one
    for idx, day_date in enumerate(desired_dates):
        if day_date in current_days_by_date:
            day = current_days_by_date[day_date]
            update_fields = []
            if day.number != idx + 1:
                day.number = idx + 1
                update_fields.append("number")
            # Update destination only if it still matches the old trip destination
            if (
                destination_changed
                and day.destination == old_destination
                and instance.destination
            ):
                day.destination = instance.destination
                update_fields.append("destination")
            if update_fields:
                day.save(update_fields=update_fields)
        else:
            Day.objects.create(
                trip=instance,
                number=idx + 1,
                date=day_date,
                destination=instance.destination,
            )

    # Trigger home transfer calculation for first and last day
    from django_q.tasks import async_task

    days = list(instance.days.order_by("number"))
    async_task("trips.tasks.calculate_day_transfer", days[0].pk)
    if len(days) > 1:
        async_task("trips.tasks.calculate_day_transfer", days[-1].pk)


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
    notes = models.TextField(blank=True)
    place_id = models.CharField(max_length=255, blank=True)
    opening_hours = models.JSONField(blank=True, null=True)
    enriched = models.BooleanField(default=False, db_index=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_stays",
    )
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_stays",
    )

    class Meta:
        indexes = [
            models.Index(fields=["place_id"]),
        ]

    def save(self, *args, **kwargs):
        """
        Convert address to coordinates for displaying on the map,
        only if the address has changed or coordinates are not set.
        Skips geocoding when explicit coordinates are already provided.
        """
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        address_changed = old and old.address != self.address
        coords_missing = self.latitude is None or self.longitude is None
        coords_provided = self.latitude is not None and self.longitude is not None
        complete_address = self.address
        if self.city:
            complete_address = f"{self.address}, {self.city}"

        if not coords_provided and (address_changed or coords_missing):
            g = geocoder.mapbox(
                complete_address, access_token=settings.MAPBOX_ACCESS_TOKEN
            )
            if g.latlng:
                self.latitude, self.longitude = g.latlng

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        first_day = self.days.first()
        return f"{self.name} - {first_day.trip.title}" if first_day else self.name

    @property
    def google_maps_directions_url(self):
        """Google Maps directions URL from current location to this stay's address."""
        address = self.address or ""
        if self.city:
            address = f"{address}, {self.city}"
        if address.strip():
            return f"https://www.google.com/maps/dir/?api=1&destination={quote(address.strip())}"
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps/dir/?api=1&destination={self.latitude},{self.longitude}"
        return None


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


class MainTransfer(models.Model):
    """
    Main transfers (arrival/departure) for a trip.
    """

    class Type(models.IntegerChoices):
        PLANE = 1, _("Plane")
        TRAIN = 2, _("Train")
        CAR = 3, _("Car")
        OTHER = 4, _("Other")

    class Direction(models.IntegerChoices):
        ARRIVAL = 1, _("Arrival")
        DEPARTURE = 2, _("Departure")

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="main_transfers"
    )
    type = models.IntegerField(
        choices=Type.choices, help_text="Type of transport (plane, train, car, other)"
    )
    direction = models.IntegerField(
        choices=Direction.choices,
        help_text="Arrival (to destination) or Departure (from destination)",
    )

    # Location fields - two approaches:
    # For PLANE: IATA code + airport name (from CSV)
    # For TRAIN: station ID stored in origin_code + station name (from CSV)
    origin_code = models.CharField(
        max_length=10, blank=True, help_text="IATA code (plane) or station ID (train)"
    )
    origin_name = models.CharField(max_length=200, help_text="Airport/station name")
    destination_code = models.CharField(
        max_length=10, blank=True, help_text="IATA code (plane) or station ID (train)"
    )
    destination_name = models.CharField(
        max_length=200, help_text="Airport/station name"
    )

    # For CAR/OTHER: address (with geocoding like events)
    origin_address = models.CharField(
        max_length=500, blank=True, help_text="Full address for car/other transport"
    )
    destination_address = models.CharField(
        max_length=500, blank=True, help_text="Full address for car/other transport"
    )

    # Coordinates (populated from CSV or geocoding)
    origin_latitude = models.FloatField(null=True, blank=True)
    origin_longitude = models.FloatField(null=True, blank=True)
    destination_latitude = models.FloatField(null=True, blank=True)
    destination_longitude = models.FloatField(null=True, blank=True)

    # Common fields
    start_time = models.TimeField(null=True, blank=True, help_text=_("Departure time"))
    end_time = models.TimeField(null=True, blank=True, help_text=_("Arrival time"))
    notes = models.TextField(blank=True, help_text=_("Additional notes"))

    # Type-specific data (JSONField for flexibility)
    type_specific_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Type-specific fields: company, flight_number, train_number, etc.",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_main_transfers",
    )

    class Meta:
        db_table = "trips_main_transfer"
        verbose_name = _("Main Transfer")
        verbose_name_plural = _("Main Transfers")
        ordering = ["direction", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["trip", "direction"], name="unique_trip_maintransfer_direction"
            )
        ]
        indexes = [
            models.Index(fields=["trip", "direction"]),
        ]

    def __str__(self):
        direction_str = (
            "Arrival" if self.direction == self.Direction.ARRIVAL else "Departure"
        )
        return f"{self.trip.title} - {direction_str} ({self.get_type_display()})"

    def clean(self):
        """Custom validations"""
        super().clean()

        # Plane/Train MUST have origin/destination names
        if self.type in [self.Type.PLANE, self.Type.TRAIN]:
            if not self.origin_name or not self.destination_name:
                raise ValidationError(
                    {
                        "origin_name": "Airport/station name required for plane/train",
                        "destination_name": "Airport/station name required for plane/train",
                    }
                )

        # Car/Other MUST have addresses
        if self.type in [self.Type.CAR, self.Type.OTHER]:
            if not self.origin_address or not self.destination_address:
                raise ValidationError(
                    {
                        "origin_address": "Full address required for car/other transport",
                        "destination_address": "Full address required for car/other transport",
                    }
                )

    def save(self, *args, **kwargs):
        """Override save for automatic geocoding (car/other only)"""

        # Geocoding for CAR/OTHER (like events)
        if self.type in [self.Type.CAR, self.Type.OTHER]:
            # Origin geocoding
            if self.origin_address and not (
                self.origin_latitude and self.origin_longitude
            ):
                g = geocoder.mapbox(
                    self.origin_address, access_token=settings.MAPBOX_ACCESS_TOKEN
                )
                if g.latlng:
                    self.origin_latitude, self.origin_longitude = g.latlng

            # Destination geocoding
            if self.destination_address and not (
                self.destination_latitude and self.destination_longitude
            ):
                g = geocoder.mapbox(
                    self.destination_address, access_token=settings.MAPBOX_ACCESS_TOKEN
                )
                if g.latlng:
                    self.destination_latitude, self.destination_longitude = g.latlng

        super().save(*args, **kwargs)

    # Properties for type-specific field access

    # Common (all types)
    @property
    def company(self):
        return self.type_specific_data.get("company", "")

    @property
    def company_website(self):
        return self.type_specific_data.get("company_website", "")

    # Flight specific
    @property
    def flight_number(self):
        return self.type_specific_data.get("flight_number", "")

    @property
    def terminal(self):
        return self.type_specific_data.get("terminal", "")

    # Train specific
    @property
    def train_number(self):
        return self.type_specific_data.get("train_number", "")

    # Car specific
    @property
    def is_rental(self):
        return self.type_specific_data.get("is_rental", False)


class Day(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="days")
    stay = models.ForeignKey(
        Stay, on_delete=models.SET_NULL, null=True, blank=True, related_name="days"
    )
    number = models.PositiveSmallIntegerField()
    date = models.DateField()
    destination = models.CharField(max_length=100, blank=True)
    destination_latitude = models.FloatField(null=True, blank=True)
    destination_longitude = models.FloatField(null=True, blank=True)
    transfer_duration_from_prev = models.PositiveIntegerField(null=True, blank=True)
    transfer_distance_from_prev = models.PositiveIntegerField(null=True, blank=True)
    transfer_to_home_duration = models.PositiveIntegerField(null=True, blank=True)
    transfer_to_home_distance = models.PositiveIntegerField(null=True, blank=True)
    weather_data = models.JSONField(null=True, blank=True)
    weather_fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["number"]
        indexes = [
            models.Index(fields=["trip", "date"]),
        ]

    def save(self, *args, **kwargs):
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        destination_changed = old and old.destination != self.destination

        super().save(*args, **kwargs)

        if destination_changed:
            from django_q.tasks import async_task

            async_task("trips.tasks.calculate_day_transfer", self.pk)
            prev = Day.objects.filter(trip=self.trip, number=self.number - 1).first()
            if prev:
                async_task("trips.tasks.calculate_day_transfer", prev.pk)

    @property
    def next_day(self):
        """Get next day using prefetched data"""
        days = [d for d in self.trip.days.all()]
        try:
            current_index = days.index(self)
            return days[current_index + 1] if current_index + 1 < len(days) else None
        except ValueError, IndexError:
            return None

    @property
    def prev_day(self):
        """Get previous day using prefetched data"""
        days = [d for d in self.trip.days.all()]
        try:
            current_index = days.index(self)
            return days[current_index - 1] if current_index > 0 else None
        except ValueError, IndexError:
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
        EXPERIENCE = 2, _("Experience")
        MEAL = 3, _("Meal")

    day = models.ForeignKey(
        Day, on_delete=models.SET_NULL, related_name="events", null=True, blank=True
    )
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="all_events")
    name = models.CharField(max_length=100)
    start_time = models.TimeField(null=True, blank=True)
    estimated_duration = models.DurationField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    category = models.PositiveSmallIntegerField(
        choices=Category.choices, default=Category.EXPERIENCE
    )
    notes = models.TextField(blank=True)
    # Additional fields for Google Places data
    place_id = models.CharField(max_length=255, blank=True)
    website = models.URLField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    opening_hours = models.JSONField(blank=True, null=True)
    enriched = models.BooleanField(default=False, db_index=True)
    tag = models.CharField(max_length=20, blank=True)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_events",
    )

    class Meta:
        ordering = ["order", "pk"]
        indexes = [
            models.Index(fields=["trip_id"]),
            models.Index(fields=["day_id", "order"]),
            models.Index(fields=["city"]),
        ]

    def save(self, *args, **kwargs):
        """
        Convert address to coordinates for displaying on the map,
        only if the address has changed or coordinates are not set.
        Skips geocoding when explicit coordinates are already provided.
        """
        old = type(self).objects.get(pk=self.pk) if self.pk else None
        address_changed = old and old.address != self.address
        coords_missing = self.latitude is None or self.longitude is None
        coords_provided = self.latitude is not None and self.longitude is not None
        complete_address = self.address
        if self.city:
            complete_address = f"{self.address}, {self.city}"

        if not coords_provided and (address_changed or coords_missing):
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
        return self.name

    @property
    def google_maps_directions_url(self):
        """Google Maps directions URL from current location to this event's address."""
        address = self.address or ""
        if self.city:
            address = f"{address}, {self.city}"
        if address.strip():
            return f"https://www.google.com/maps/dir/?api=1&destination={quote(address.strip())}"
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps/dir/?api=1&destination={self.latitude},{self.longitude}"
        return None


@receiver(pre_save, sender=Event)
def update_event_trip(sender, instance, **kwargs):
    """
    Ensure event's trip is always set correctly based on its day
    """
    if instance.day_id:
        if not instance.trip_id or instance.trip_id != instance.day.trip_id:
            instance.trip = instance.day.trip


class MainTransferConnection(models.Model):
    """
    Connection between a MainTransfer and the first/last event or stay.
    - For ARRIVAL: transfer goes FROM main_transfer destination TO event/stay
    - For DEPARTURE: transfer goes FROM event/stay TO main_transfer origin
    Direction is determined by main_transfer.direction field.
    """

    class TransportMode(models.TextChoices):
        DRIVING = "driving", _("Driving")
        WALKING = "walking", _("Walking")
        BICYCLING = "bicycling", _("Bicycling")
        TRANSIT = "transit", _("Transit")

    main_transfer = models.OneToOneField(
        MainTransfer, on_delete=models.CASCADE, related_name="connection"
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    stay = models.ForeignKey(
        Stay, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )

    transport_mode = models.CharField(
        max_length=50,
        choices=TransportMode.choices,
        default=TransportMode.DRIVING,
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trips_main_transfer_connection"
        verbose_name = _("Main Transfer Connection")
        verbose_name_plural = _("Main Transfer Connections")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(event__isnull=False, stay__isnull=True)
                    | models.Q(event__isnull=True, stay__isnull=False)
                ),
                name="main_transfer_connection_one_destination",
            )
        ]

    def __str__(self):
        destination = self.event.name if self.event else self.stay.name
        direction = self.main_transfer.get_direction_display()
        return f"{direction} Connection → {destination}"

    @property
    def destination_type(self):
        """Returns 'event' or 'stay' to identify destination type"""
        return "event" if self.event else "stay"

    @property
    def destination(self):
        """Returns the actual event or stay object"""
        return self.event if self.event else self.stay

    @property
    def from_location(self):
        """Get origin location based on direction"""
        if self.main_transfer.direction == MainTransfer.Direction.ARRIVAL:
            # ARRIVAL: from main_transfer destination to event/stay
            return (
                self.main_transfer.destination_name
                or self.main_transfer.destination_address
            )
        else:
            # DEPARTURE: from event/stay to main_transfer origin
            return self.event.name if self.event else self.stay.name

    @property
    def to_location(self):
        """Get destination location based on direction"""
        if self.main_transfer.direction == MainTransfer.Direction.ARRIVAL:
            # ARRIVAL: from main_transfer destination to event/stay
            return self.event.name if self.event else self.stay.name
        else:
            # DEPARTURE: from event/stay to main_transfer origin
            return self.main_transfer.origin_name or self.main_transfer.origin_address

    @property
    def from_coordinates(self):
        """Get origin coordinates based on direction"""
        if self.main_transfer.direction == MainTransfer.Direction.ARRIVAL:
            return (
                self.main_transfer.destination_latitude,
                self.main_transfer.destination_longitude,
            )
        else:
            if self.event:
                return (self.event.latitude, self.event.longitude)
            else:
                return (self.stay.latitude, self.stay.longitude)

    @property
    def to_coordinates(self):
        """Get destination coordinates based on direction"""
        if self.main_transfer.direction == MainTransfer.Direction.ARRIVAL:
            if self.event:
                return (self.event.latitude, self.event.longitude)
            else:
                return (self.stay.latitude, self.stay.longitude)
        else:
            return (
                self.main_transfer.origin_latitude,
                self.main_transfer.origin_longitude,
            )

    @property
    def google_maps_url(self):
        """Generate Google Maps URL from addresses with travel mode"""
        from_coords = self.from_coordinates
        to_coords = self.to_coordinates

        if from_coords and to_coords and all(from_coords) and all(to_coords):
            return (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={from_coords[0]},{from_coords[1]}"
                f"&destination={to_coords[0]},{to_coords[1]}"
                f"&travelmode={self.transport_mode}"
            )
        return None

    def clean(self):
        """Validate MainTransferConnection constraints"""
        super().clean()

        # Exactly one of event or stay must be set (enforced by DB constraint)
        if not self.event_id and not self.stay_id:
            raise ValidationError(
                _("Either event or stay must be set for the connection")
            )

        if self.event_id and self.stay_id:  # pragma: no branch
            raise ValidationError(
                _("Cannot set both event and stay - choose only one destination")
            )


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
        UNDEFINED = 0, _("To be defined")
        BREAKFAST = 1, _("Breakfast")
        LUNCH = 2, _("Lunch")
        DINNER = 3, _("Dinner")
        SNACK = 4, _("Snack")

    type = models.IntegerField(choices=Type.choices, default=Type.UNDEFINED)

    def __str__(self) -> str:
        return f"{self.name} ({self.day.trip.title} - Day {self.day.number})"

    def save(self, *args, **kwargs):
        """autosave category for meal"""
        self.category = self.Category.MEAL
        return super().save(*args, **kwargs)


class TripCollaboration(models.Model):
    """Through model for Trip.collaborators M2M, stores role and color per participant."""

    PALETTE = [
        ("blue", _("Blue")),
        ("green", _("Green")),
        ("purple", _("Purple")),
        ("orange", _("Orange")),
        ("pink", _("Pink")),
        ("teal", _("Teal")),
        ("red", _("Red")),
        ("indigo", _("Indigo")),
    ]
    PALETTE_VALUES = [c[0] for c in PALETTE]
    COLOR_BADGE_CLASSES = {
        "blue": "bg-blue-500",
        "green": "bg-green-600",
        "purple": "bg-purple-500",
        "orange": "bg-orange-500",
        "pink": "bg-pink-500",
        "teal": "bg-teal-500",
        "red": "bg-red-500",
        "indigo": "bg-indigo-500",
    }

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="collaborations"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="trip_collaborations",
    )
    participant_name = models.CharField(max_length=100, blank=True)
    participant_email = models.EmailField(blank=True)
    share_link = models.OneToOneField(
        "ShareLink",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collaboration",
    )
    color = models.CharField(max_length=20, choices=PALETTE)
    is_child = models.BooleanField(default=False)
    age = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(17)]
    )
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collaborations_added",
    )
    can_edit = models.BooleanField(default=True)

    class Meta:
        unique_together = ("trip", "user")
        ordering = ("added_at",)

    def __str__(self) -> str:
        label = self.display_name
        return f"{label} → {self.trip.title} ({self.color})"

    @property
    def display_name(self) -> str:
        if self.user:
            return self.user.profile.first_name or self.user.email
        return self.participant_name or self.participant_email or "—"

    @property
    def is_named_only(self) -> bool:
        """True for participants added by name only (no account, no email)."""
        return not self.user and not self.participant_email

    @property
    def badge_bg_class(self):
        return self.COLOR_BADGE_CLASSES.get(self.color, "bg-base-300")

    def delete(self, *args, **kwargs):
        link = self.share_link
        super().delete(*args, **kwargs)
        if link:
            link.delete()

    @classmethod
    def next_free_color(cls, trip):
        """Return the first palette color not yet used by this trip's collaborators."""
        used = set(cls.objects.filter(trip=trip).values_list("color", flat=True))
        for color in cls.PALETTE_VALUES:
            if color not in used:
                return color
        return cls.PALETTE_VALUES[0]


class TripInvitation(models.Model):
    """Pending invitation for a non-registered user to join a trip as collaborator."""

    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Invitation for {self.email} → {self.trip.title}"

    @property
    def is_valid(self) -> bool:
        return not self.is_accepted and timezone.now() < self.expires_at

    def get_absolute_url(self) -> str:
        return reverse("trips:accept-invitation", kwargs={"token": self.token})


class ShareLink(models.Model):
    class PermissionLevel(models.TextChoices):
        VIEW = "view", _("View only")
        EDIT = "edit", _("Can edit")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(
        "Trip", on_delete=models.CASCADE, related_name="share_links"
    )
    permission_level = models.CharField(
        max_length=10,
        choices=PermissionLevel.choices,
        default=PermissionLevel.VIEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    label = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Share link for {self.trip.title}"

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    @property
    def display_label(self) -> str:
        return self.label if self.label else self.created_at.strftime("%d/%m/%Y %H:%M")

    def get_absolute_url(self) -> str:
        return reverse("trips:shared-trip", kwargs={"token": self.id})


class ChecklistItem(models.Model):
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="checklist_items"
    )
    text = models.CharField(max_length=500)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["completed", "created_at"]
        verbose_name = "Checklist Item"
        verbose_name_plural = "Checklist Items"

    def __str__(self) -> str:
        return f"{self.text} [{self.trip.title}]"


def _attachment_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"attachments/{instance.content_type_id}/{instance.object_id}/{uuid.uuid4().hex}.{ext}"


class Attachment(models.Model):
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
    MAX_PER_TRIP = 5
    MAX_PER_SUB_ENTITY = 2

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    file = models.FileField(upload_to=_attachment_upload_path)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_attachments",
    )
    include_in_pdf = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return self.original_name

    @property
    def is_pdf(self) -> bool:
        return self.mime_type == "application/pdf"

    @property
    def is_image(self) -> bool:
        return self.mime_type.startswith("image/")

    def _normalize_event_content_type(self):
        obj = self.content_object
        if obj is not None and isinstance(obj, Event) and type(obj) is not Event:
            self.content_type = ContentType.objects.get_for_model(Event)

    def save(self, *args, **kwargs):
        self._normalize_event_content_type()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self._normalize_event_content_type()
        if self.mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValidationError({"mime_type": _("File type not allowed.")})
        if self.size and self.size > self.MAX_FILE_SIZE:
            raise ValidationError({"file": _("File exceeds the 2 MB size limit.")})
        model = self.content_type.model_class()
        siblings = Attachment.objects.filter(
            content_type=self.content_type, object_id=self.object_id
        ).exclude(pk=self.pk)
        limit = (
            self.MAX_PER_TRIP if model.__name__ == "Trip" else self.MAX_PER_SUB_ENTITY
        )
        if siblings.count() >= limit:
            raise ValidationError(_("Attachment limit reached for this item."))


class FamilyUnit(models.Model):
    """A group of participants (couple/family) sharing expenses within a trip."""

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="family_units"
    )
    name = models.CharField(max_length=100, blank=True)
    shared_wallet = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.display_name} [{self.trip.title}]"

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        first_adult = self.members.filter(is_child=False).first()
        if first_adult:
            return _("Family of %(name)s") % {"name": first_adult.display_name}
        return _("Family unit")


class ExpenseParticipant(models.Model):
    """Expense identity for a trip participant (author, collaborator or named-only).

    Decoupled from TripCollaboration so the trip author (who has no collaboration
    row) is representable and expense history survives collaborator removal.
    """

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="expense_participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    collaboration = models.OneToOneField(
        "TripCollaboration",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="expense_participant",
    )
    name_snapshot = models.CharField(max_length=100)
    family_unit = models.ForeignKey(
        FamilyUnit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    is_child = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.display_name} [{self.trip.title}]"

    @property
    def display_name(self) -> str:
        if self.collaboration_id and self.collaboration:
            return self.collaboration.display_name
        if self.user_id and self.user:
            return self.user.profile.first_name or self.user.email
        return self.name_snapshot


class Expense(models.Model):
    """A cost incurred during a trip, optionally linked to a trip item."""

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="expenses")
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    title = models.CharField(max_length=120)
    amount = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField()
    payer = models.ForeignKey(
        ExpenseParticipant, on_delete=models.PROTECT, related_name="expenses_paid"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-date", "-created_at")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["trip", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.amount})"

    @property
    def is_linked(self) -> bool:
        return self.content_type_id is not None and self.object_id is not None

    @property
    def payer_label(self) -> str:
        """Family name when the payer belongs to a unit, else their own name."""
        unit = self.payer.family_unit
        return unit.display_name if unit else self.payer.display_name

    def _normalize_event_content_type(self):
        obj = self.content_object
        if obj is not None and isinstance(obj, Event) and type(obj) is not Event:
            self.content_type = ContentType.objects.get_for_model(Event)

    def save(self, *args, **kwargs):
        self._normalize_event_content_type()
        super().save(*args, **kwargs)


class ExpenseShare(models.Model):
    """Links an Expense to a participant it is shared with (equal split in v1)."""

    expense = models.ForeignKey(
        Expense, on_delete=models.CASCADE, related_name="shares"
    )
    participant = models.ForeignKey(
        ExpenseParticipant, on_delete=models.CASCADE, related_name="expense_shares"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expense", "participant"], name="unique_expense_share"
            )
        ]

    def __str__(self) -> str:
        return f"{self.participant.display_name} → {self.expense.title}"


class StayBooking(models.Model):
    """A per-user Stay22 accommodation search saved for a trip stage (destination)."""

    class Provider(models.TextChoices):
        SMART = "smart", _("Smart")
        BOOKING = "booking", _("Booking.com")
        EXPEDIA = "expedia", _("Expedia")

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="bookings")
    destination = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stay_bookings",
    )
    participants = models.ManyToManyField(
        TripCollaboration, blank=True, related_name="stay_bookings"
    )
    includes_author = models.BooleanField(default=True)
    provider = models.CharField(
        max_length=20, choices=Provider.choices, default=Provider.SMART
    )
    hotel_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("trip", "destination", "created_by")

    def __str__(self) -> str:
        return f"{self.destination} booking for {self.trip.title}"

    @property
    def adults(self) -> int:
        count = self.participants.filter(is_child=False).count()
        if self.includes_author:
            count += 1
        return count

    @property
    def children(self) -> int:
        return self.participants.filter(is_child=True).count()


@receiver(pre_delete, sender=Event)
@receiver(pre_delete, sender=Stay)
@receiver(pre_delete, sender=MainTransfer)
def unlink_expenses_on_delete(sender, instance, **kwargs):
    """Keep an expense as free-standing when its linked trip item is deleted."""
    ct = ContentType.objects.get_for_model(
        Event if isinstance(instance, Event) else sender
    )
    Expense.objects.filter(content_type=ct, object_id=instance.pk).update(
        content_type=None, object_id=None
    )
