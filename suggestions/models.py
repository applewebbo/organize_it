from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from suggestions.fields import EncryptedTextField

# Bounds for the per-user number of suggestions requested per generation.
MIN_RESULT_COUNT = 3
MAX_RESULT_COUNT = 15
DEFAULT_RESULT_COUNT = 8


class AICredentials(models.Model):
    """Per-user BYOK credentials for an AI provider. The API key is stored
    encrypted at rest and is never returned in clear in __str__ or logs."""

    class Provider(models.TextChoices):
        GEMINI = "gemini", _("Google Gemini")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_credentials",
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.GEMINI,
    )
    api_key_encrypted = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI credentials")
        verbose_name_plural = _("AI credentials")

    def __str__(self) -> str:
        return f"AI credentials for {self.user.email} ({self.get_provider_display()})"


class SuggestionPreferences(models.Model):
    """Per-user persistent defaults that feed the AI suggestion prompt."""

    class Dietary(models.TextChoices):
        NONE = "none", _("No preference")
        VEGETARIAN = "vegetarian", _("Vegetarian")
        VEGAN = "vegan", _("Vegan")
        GLUTEN_FREE = "gluten_free", _("Gluten-free")

    class Budget(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")

    class TravelParty(models.TextChoices):
        UNSPECIFIED = "unspecified", _("Not specified")
        SOLO = "solo", _("Solo")
        COUPLE = "couple", _("Couple")
        FAMILY = "family", _("Family with children")
        FRIENDS = "friends", _("Group of friends")

    class TravelStyle(models.TextChoices):
        ICONIC = "iconic", _("Iconic must-sees")
        BALANCED = "balanced", _("Balanced")
        OFFBEAT = "offbeat", _("Off the beaten path")

    class Interest(models.TextChoices):
        HISTORY = "history", _("History")
        ART = "art", _("Art")
        NATURE = "nature", _("Nature")
        NIGHTLIFE = "nightlife", _("Nightlife")
        SHOPPING = "shopping", _("Shopping")
        LOCAL_FOOD = "local_food", _("Local food")
        RELAX = "relax", _("Relax")

    class Cuisine(models.TextChoices):
        ANY = "any", _("No preference")
        LOCAL = "local", _("Local traditional")
        STREET_FOOD = "street_food", _("Street food")
        INTERNATIONAL = "international", _("International")

    class SearchRadius(models.TextChoices):
        CITY = "city", _("Within the city")
        NEARBY = "nearby", _("City and surroundings")
        DAY_TRIPS = "day_trips", _("Include day trips")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="suggestion_preferences",
    )
    favored_experience_types = models.JSONField(default=list, blank=True)
    dietary = models.CharField(
        max_length=20,
        choices=Dietary.choices,
        default=Dietary.NONE,
    )
    budget = models.CharField(
        max_length=20,
        choices=Budget.choices,
        default=Budget.MEDIUM,
    )
    travel_party = models.CharField(
        max_length=20,
        choices=TravelParty.choices,
        default=TravelParty.UNSPECIFIED,
    )
    travel_style = models.CharField(
        max_length=20,
        choices=TravelStyle.choices,
        default=TravelStyle.BALANCED,
    )
    interests = models.JSONField(default=list, blank=True)
    cuisine = models.CharField(
        max_length=20,
        choices=Cuisine.choices,
        default=Cuisine.ANY,
    )
    search_radius = models.CharField(
        max_length=20,
        choices=SearchRadius.choices,
        default=SearchRadius.NEARBY,
    )
    notes = models.TextField(blank=True)
    result_count = models.PositiveSmallIntegerField(
        default=DEFAULT_RESULT_COUNT,
        validators=[
            MinValueValidator(MIN_RESULT_COUNT),
            MaxValueValidator(MAX_RESULT_COUNT),
        ],
    )

    class Meta:
        verbose_name = _("Suggestion preferences")
        verbose_name_plural = _("Suggestion preferences")

    def __str__(self) -> str:
        return f"Suggestion preferences for {self.user.email}"
