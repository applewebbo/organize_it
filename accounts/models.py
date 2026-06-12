import geocoder
from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_q.tasks import async_task

from .managers import CustomUserManager

PROFILE_CACHE_TIMEOUT = 300  # 5 minutes


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Profile(models.Model):
    """Profile holds user informations not related to auth"""

    AVATAR_CHOICES = [
        ("passport.png", "Passport"),
        ("camping.png", "Camping"),
        ("car.png", "Car"),
        ("desert.png", "Desert"),
        ("hiker.png", "Hiker"),
        ("scuba-diving.png", "Scuba Diving"),
        ("tourist.png", "Tourist"),
        ("traveller.png", "Traveller"),
    ]

    CURRENCY_CHOICES = [
        ("EUR", "Euro (€)"),
        ("USD", "US Dollar ($)"),
        ("GBP", "Pound Sterling (£)"),
    ]

    LANGUAGE_CHOICES = [
        ("it", _("Italian")),
        ("en", _("English")),
    ]

    MAP_VIEW_CHOICES = [
        ("list", _("List")),
        ("map", _("Map")),
    ]

    SORT_CHOICES = [
        ("date_asc", _("Date (oldest first)")),
        ("date_desc", _("Date (newest first)")),
        ("name_asc", _("Name (A-Z)")),
        ("name_desc", _("Name (Z-A)")),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    fav_trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Personal Information (Phase 1)
    first_name = models.CharField(
        _("First name"),
        max_length=150,
        blank=True,
        default="",
    )
    last_name = models.CharField(
        _("Last name"),
        max_length=150,
        blank=True,
        default="",
    )
    avatar = models.CharField(
        _("Avatar"),
        max_length=50,
        choices=AVATAR_CHOICES,
        blank=True,
        default="",
    )

    # Travel Preferences (Phase 1)
    currency = models.CharField(
        _("Preferred currency"),
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="EUR",
        blank=True,
    )
    default_map_view = models.CharField(
        _("Default map view"),
        max_length=4,
        choices=MAP_VIEW_CHOICES,
        default="list",
    )
    trip_sort_preference = models.CharField(
        _("Trip sorting"),
        max_length=10,
        choices=SORT_CHOICES,
        default="date_asc",
    )

    # Home Address (for transfer pre-fill)
    home_address = models.CharField(
        _("Home address"),
        max_length=500,
        blank=True,
        default="",
        help_text=_(
            "Used to pre-fill the origin/destination field in car transfers. "
            "It is not shared or used for any other purpose."
        ),
    )
    home_address_latitude = models.FloatField(null=True, blank=True)
    home_address_longitude = models.FloatField(null=True, blank=True)

    language = models.CharField(
        _("Language"),
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="it",
    )

    # Display Preferences (Phase 2)
    use_system_theme = models.BooleanField(
        _("Use system theme"),
        default=False,
        help_text=_("Use your device's light/dark system setting."),
    )
    show_transfer_info = models.BooleanField(
        _("Show transfer info"),
        default=True,
        help_text=_("Show duration and distance info between trip stages."),
    )
    show_weather = models.BooleanField(
        _("Show weather forecast"),
        default=True,
        help_text=_("When disabled, weather data is not fetched from the API."),
    )
    notify_daily_digest = models.BooleanField(
        _("Daily digest email"),
        default=True,
        help_text=_("Receive a daily summary email of your trip plan during the trip."),
    )

    def save(self, *args, **kwargs):
        old = Profile.objects.filter(pk=self.pk).first()
        self._pre_save_instance = old
        # Geocode home_address when set and coordinates are missing
        if self.home_address and not (
            self.home_address_latitude and self.home_address_longitude
        ):
            address_changed = not old or old.home_address != self.home_address
            if address_changed:
                g = geocoder.mapbox(
                    self.home_address, access_token=settings.MAPBOX_ACCESS_TOKEN
                )
                if g.latlng:
                    self.home_address_latitude, self.home_address_longitude = g.latlng
        super().save(*args, **kwargs)
        cache.delete(f"profile_{self.user_id}")

    def __str__(self):
        return str(self.user)


def get_profile(user):
    """Return Profile for user, using cache to avoid repeated DB queries."""
    cache_key = f"profile_{user.pk}"
    profile = cache.get(cache_key)
    if profile is None:
        profile = Profile.objects.select_related("fav_trip").get(user=user)
        cache.set(cache_key, profile, PROFILE_CACHE_TIMEOUT)
    return profile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(user_signed_up)
def accept_invitation_on_signup(sender, request, user, **kwargs):
    """Auto-accept a TripInvitation if token was stored in session before signup."""
    from trips.models import TripCollaboration, TripInvitation

    token = request.session.pop("invitation_token", None)
    if not token:
        return

    try:
        invitation = TripInvitation.objects.get(token=token)
    except TripInvitation.DoesNotExist:
        return

    if not invitation.is_valid:
        return

    invitation.is_accepted = True
    invitation.accepted_at = timezone.now()
    invitation.save()

    trip = invitation.trip
    color = TripCollaboration.next_free_color(trip)
    TripCollaboration.objects.get_or_create(
        trip=trip,
        user=user,
        defaults={"color": color, "added_by": invitation.invited_by},
    )


@receiver(post_save, sender=Profile)
def recalculate_home_transfers(sender, instance, **kwargs):
    """When home coords change, recalculate first/last day transfers for active trips."""
    from trips.models import Trip

    old = getattr(instance, "_pre_save_instance", None)
    coords_changed = old is None or (
        old.home_address_latitude != instance.home_address_latitude
        or old.home_address_longitude != instance.home_address_longitude
    )
    if not coords_changed:
        return

    excluded = [Trip.Status.COMPLETED, Trip.Status.ARCHIVED]
    trips = Trip.objects.filter(author=instance.user).exclude(status__in=excluded)
    for trip in trips:
        days = trip.days.order_by("number")
        if not days.exists():
            continue
        first_day = days.first()
        last_day = days.last()
        async_task("trips.tasks.calculate_day_transfer", first_day.pk)
        if last_day.pk != first_day.pk:
            async_task("trips.tasks.calculate_day_transfer", last_day.pk)
