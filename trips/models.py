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
    start_time = models.TimeField(help_text="Departure time")
    end_time = models.TimeField(help_text="Arrival time")
    booking_reference = models.CharField(
        max_length=100, blank=True, help_text="Booking/reservation reference"
    )
    ticket_url = models.URLField(blank=True, help_text="Link to ticket or booking")
    notes = models.TextField(blank=True, help_text="Additional notes")

    # Type-specific data (JSONField for flexibility)
    type_specific_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Type-specific fields: company, flight_number, train_number, etc.",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    @property
    def carriage(self):
        return self.type_specific_data.get("carriage", "")

    @property
    def seat(self):
        return self.type_specific_data.get("seat", "")

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


class SimpleTransfer(models.Model):
    """Transfer between two events on the same day"""

    class TransportMode(models.TextChoices):
        DRIVING = "driving", _("Driving")
        WALKING = "walking", _("Walking")
        BICYCLING = "bicycling", _("Bicycling")
        TRANSIT = "transit", _("Transit")

    # 1-to-1 relationships (max 1 transfer in/out per event)
    from_event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="transfer_from"
    )
    to_event = models.OneToOneField(
        Event, on_delete=models.CASCADE, related_name="transfer_to"
    )

    # Auto-populated from events
    day = models.ForeignKey(
        Day, on_delete=models.CASCADE, related_name="simple_transfers"
    )
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="simple_transfers"
    )

    # Transfer details
    transport_mode = models.CharField(
        max_length=50, choices=TransportMode.choices, default=TransportMode.DRIVING
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trips_simple_transfer"
        verbose_name = _("Simple Transfer")
        verbose_name_plural = _("Simple Transfers")
        ordering = ["day__number", "from_event__start_time"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(from_event=models.F("to_event")),
                name="simple_transfer_different_events",
            )
        ]
        indexes = [
            models.Index(fields=["day", "from_event"]),
            models.Index(fields=["trip"]),
        ]

    def __str__(self):
        return f"{self.from_event.name} → {self.to_event.name}"

    @property
    def from_location(self):
        """Get from_event location name"""
        return self.from_event.name

    @property
    def to_location(self):
        """Get to_event location name"""
        return self.to_event.name

    @property
    def from_coordinates(self):
        """Get from_event coordinates as tuple"""
        return (self.from_event.latitude, self.from_event.longitude)

    @property
    def to_coordinates(self):
        """Get to_event coordinates as tuple"""
        return (self.to_event.latitude, self.to_event.longitude)

    @property
    def google_maps_url(self):
        """Generate Google Maps URL from coordinates with travel mode"""
        from_lat, from_lng = self.from_coordinates
        to_lat, to_lng = self.to_coordinates

        if all([from_lat, from_lng, to_lat, to_lng]):
            return (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={from_lat},{from_lng}"
                f"&destination={to_lat},{to_lng}"
                f"&travelmode={self.transport_mode}"
            )
        return None

    def clean(self):
        """Validate SimpleTransfer constraints"""
        super().clean()

        # Check from_event != to_event
        if self.from_event_id and self.to_event_id:
            if self.from_event_id == self.to_event_id:
                raise ValidationError(
                    {"to_event": _("Cannot create transfer to the same event")}
                )

        # Check same day
        if self.from_event.day_id and self.to_event.day_id:
            if self.from_event.day_id != self.to_event.day_id:
                raise ValidationError(
                    {
                        "to_event": _(
                            "Both events must be on the same day for SimpleTransfer"
                        )
                    }
                )

        # Check same trip
        if self.from_event.trip_id and self.to_event.trip_id:
            if self.from_event.trip_id != self.to_event.trip_id:
                raise ValidationError(
                    {"to_event": _("Both events must belong to the same trip")}
                )

    def save(self, *args, **kwargs):
        """Auto-populate day and trip from events"""
        if self.from_event.day_id:
            self.day_id = self.from_event.day_id
        if self.from_event.trip_id:
            self.trip_id = self.from_event.trip_id

        super().save(*args, **kwargs)


class StayTransfer(models.Model):
    """Transfer between stays on consecutive days (when different)"""

    class TransportMode(models.TextChoices):
        DRIVING = "driving", _("Driving")
        WALKING = "walking", _("Walking")
        BICYCLING = "bicycling", _("Bicycling")
        TRANSIT = "transit", _("Transit")

    # 1-to-1 relationships (max 1 transfer in/out per stay)
    from_stay = models.OneToOneField(
        Stay, on_delete=models.CASCADE, related_name="transfer_from"
    )
    to_stay = models.OneToOneField(
        Stay, on_delete=models.CASCADE, related_name="transfer_to"
    )

    # Auto-populated from stays
    from_day = models.ForeignKey(
        Day, on_delete=models.CASCADE, related_name="stay_transfers_from"
    )
    to_day = models.ForeignKey(
        Day, on_delete=models.CASCADE, related_name="stay_transfers_to"
    )
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="stay_transfers"
    )

    # Transfer details
    transport_mode = models.CharField(
        max_length=50, choices=TransportMode.choices, default=TransportMode.DRIVING
    )
    notes = models.TextField(blank=True)

    # Optional time fields
    departure_time = models.TimeField(blank=True, null=True)
    estimated_duration = models.DurationField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trips_stay_transfer"
        verbose_name = _("Stay Transfer")
        verbose_name_plural = _("Stay Transfers")
        ordering = ["from_day__number"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(from_stay=models.F("to_stay")),
                name="stay_transfer_different_stays",
            )
        ]
        indexes = [
            models.Index(fields=["from_day", "to_day"]),
            models.Index(fields=["trip"]),
        ]

    def __str__(self):
        return f"{self.from_stay.name} → {self.to_stay.name}"

    @property
    def from_location(self):
        """Get from_stay location name"""
        return self.from_stay.name

    @property
    def to_location(self):
        """Get to_stay location name"""
        return self.to_stay.name

    @property
    def from_coordinates(self):
        """Get from_stay coordinates as tuple"""
        return (self.from_stay.latitude, self.from_stay.longitude)

    @property
    def to_coordinates(self):
        """Get to_stay coordinates as tuple"""
        return (self.to_stay.latitude, self.to_stay.longitude)

    @property
    def arrival_time(self):
        """Calculate arrival time if departure_time and estimated_duration present"""
        if self.departure_time and self.estimated_duration:
            from datetime import datetime

            start = datetime.combine(datetime.today(), self.departure_time)
            arrival = start + self.estimated_duration
            return arrival.time()
        return None

    @property
    def google_maps_url(self):
        """Generate Google Maps URL from coordinates with travel mode"""
        from_lat, from_lng = self.from_coordinates
        to_lat, to_lng = self.to_coordinates

        if all([from_lat, from_lng, to_lat, to_lng]):
            return (
                f"https://www.google.com/maps/dir/?api=1"
                f"&origin={from_lat},{from_lng}"
                f"&destination={to_lat},{to_lng}"
                f"&travelmode={self.transport_mode}"
            )
        return None

    def clean(self):
        """Validate StayTransfer constraints"""
        super().clean()

        # Check from_stay != to_stay
        if self.from_stay_id and self.to_stay_id:
            if self.from_stay_id == self.to_stay_id:
                raise ValidationError(
                    {"to_stay": _("Cannot create transfer to the same stay")}
                )

        # Check consecutive days
        if hasattr(self, "from_day") and hasattr(self, "to_day"):
            from_day_num = self.from_day.number
            to_day_num = self.to_day.number

            if to_day_num != from_day_num + 1:
                raise ValidationError(
                    {
                        "to_stay": _(
                            "Stays must be on consecutive days (day N and day N+1)"
                        )
                    }
                )

        # Check same trip
        if hasattr(self, "from_day") and hasattr(self, "to_day"):
            if self.from_day.trip_id != self.to_day.trip_id:
                raise ValidationError(
                    {"to_stay": _("Both stays must belong to the same trip")}
                )

    def save(self, *args, **kwargs):
        """Auto-populate days and trip from stays"""
        # Get last day for from_stay (departure day - last day of the stay)
        if self.from_stay.days.exists():
            self.from_day = self.from_stay.days.order_by("date").last()

        # Get first day for to_stay (arrival day - first day of the stay)
        if self.to_stay.days.exists():
            self.to_day = self.to_stay.days.order_by("date").first()

        # Set trip from from_day
        if hasattr(self, "from_day"):
            self.trip_id = self.from_day.trip_id

        super().save(*args, **kwargs)


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
