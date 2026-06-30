from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from suggestions.fields import EncryptedTextField


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

    class Pace(models.TextChoices):
        RELAXED = "relaxed", _("Relaxed")
        MODERATE = "moderate", _("Moderate")
        PACKED = "packed", _("Packed")

    class Budget(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")

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
    pace = models.CharField(
        max_length=20,
        choices=Pace.choices,
        default=Pace.MODERATE,
    )
    budget = models.CharField(
        max_length=20,
        choices=Budget.choices,
        default=Budget.MEDIUM,
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Suggestion preferences")
        verbose_name_plural = _("Suggestion preferences")

    def __str__(self) -> str:
        return f"Suggestion preferences for {self.user.email}"
