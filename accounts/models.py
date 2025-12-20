from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


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
    fav_trip = models.OneToOneField(
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
    city = models.CharField(
        _("City"),
        max_length=255,
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

    # Display Preferences (Phase 2)
    use_system_theme = models.BooleanField(
        _("Use system theme"),
        default=False,
        help_text=_(
            "Follow your device's theme preference instead of manual selection"
        ),
    )

    def __str__(self):
        return str(self.user)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
