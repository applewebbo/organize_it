"""Dev-only probe for the AI day-itinerary pipeline.

Runs the real provider + Google Places calls for a single day of an existing
trip and prints every stage (prompt, raw AI itinerary, grounding outcome). By
default it probes BOTH providers (Gemini + Mistral) so their day plans can be
compared side by side; each provider uses the first AICredentials found for it.

Usage:
    uv run python manage.py probe_day_itinerary <trip_id> [--day-number 2]
        [--strategy add|unpair|delete] [--notes "…"] [--language it]
        [--radius city|nearby|day_trips] [--provider gemini|mistral|both]
        [--user user@example.com] [--no-ground]
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from suggestions.ai.factory import get_provider
from suggestions.models import AICredentials, SuggestionPreferences
from suggestions.prompts import build_day_prompt
from suggestions.services import (
    _GROUNDING_RADIUS,
    _MAX_BIAS_RADIUS,
    _RADIUS_METERS,
    DAY_STRATEGY_ADD,
    DAY_STRATEGY_DELETE,
    DAY_STRATEGY_UNPAIR,
    _haversine_m,
    build_day_context,
    merge_preferences,
)
from trips.models import Trip
from trips.services import GooglePlacesClient, GooglePlacesError

_STRATEGIES = (DAY_STRATEGY_ADD, DAY_STRATEGY_UNPAIR, DAY_STRATEGY_DELETE)


class Command(BaseCommand):
    help = "Probe the AI day-itinerary pipeline end-to-end against a real trip day."

    def add_arguments(self, parser):
        parser.add_argument("trip_id", type=int, help="Trip primary key to probe")
        parser.add_argument(
            "--day-number",
            type=int,
            help="Day number within the trip (default: first day)",
        )
        parser.add_argument(
            "--strategy",
            choices=_STRATEGIES,
            default=DAY_STRATEGY_ADD,
            help="How existing events are treated (only 'add' feeds them to the model)",
        )
        parser.add_argument("--notes", help="Extra per-day notes for the prompt")
        parser.add_argument("--language", default="it", help="Prompt language")
        parser.add_argument(
            "--radius",
            choices=("city", "nearby", "day_trips"),
            help="Override the stored search_radius preference",
        )
        parser.add_argument(
            "--provider",
            choices=("gemini", "mistral", "both"),
            default="both",
            help="Which provider(s) to probe (default: both)",
        )
        parser.add_argument(
            "--user",
            help="Email of the user whose preferences to use (default: trip author)",
        )
        parser.add_argument(
            "--no-ground",
            action="store_true",
            help="Skip Google Places grounding (only show the raw AI itinerary)",
        )

    def handle(self, *args, **opts):
        trip = Trip.objects.filter(pk=opts["trip_id"]).first()
        if trip is None:
            raise CommandError(f"Trip {opts['trip_id']} not found")

        day = self._resolve_day(trip, opts["day_number"])
        user = self._resolve_user(trip, opts["user"])

        prefs = self._build_prefs(user, opts)
        existing_events = (
            list(day.events.all()) if opts["strategy"] == DAY_STRATEGY_ADD else []
        )
        day_stops = [e.name for e in existing_events] or None
        context = build_day_context(
            trip, day, language=opts["language"], exclude_names=day_stops
        )

        self._section(
            f"DAY {day.number} — {day.date} ({day.destination or trip.destination})"
        )
        self.stdout.write(f"strategy: {opts['strategy']}")
        if existing_events:
            self.stdout.write(
                "existing events fed to model: "
                + ", ".join(e.name for e in existing_events)
            )

        prompt = build_day_prompt(context, prefs, day.date, day_stops)
        self._section("PROMPT")
        self.stdout.write(prompt)

        radius = _RADIUS_METERS.get(prefs.search_radius, _GROUNDING_RADIUS)
        for provider_name in self._selected_providers(opts["provider"]):
            self._probe_provider(
                provider_name, context, prefs, day, day_stops, radius, opts["no_ground"]
            )

    def _probe_provider(
        self, provider_name, context, prefs, day, day_stops, radius, no_ground
    ):
        creds = (
            AICredentials.objects.filter(provider=provider_name)
            .exclude(api_key_encrypted="")
            .first()
        )
        self._section(f"PROVIDER: {provider_name.upper()}")
        if creds is None:
            self.stdout.write(self.style.WARNING("no API key configured — skipped"))
            return

        provider = get_provider(provider_name, creds.api_key_encrypted)
        try:
            itinerary = provider.generate_day(context, prefs, day.date, day_stops)
        except Exception as exc:  # surface provider errors instead of a traceback
            self.stdout.write(self.style.ERROR(f"generation failed: {exc}"))
            return

        stops = itinerary.stops
        self.stdout.write(f"raw stops ({len(stops)}):")
        for i, s in enumerate(stops, 1):
            where = s.address or s.city or "-"
            duration = (
                f"{s.estimated_duration_minutes}min"
                if s.estimated_duration_minutes
                else "?"
            )
            self.stdout.write(
                f"{i}. [{s.kind.value}] {s.name} — {where} (type={s.type}, {duration})"
            )
            if s.description:
                self.stdout.write(f"     {s.description}")

        if not no_ground:
            self._ground_all(stops, context, radius)

    def _ground_all(self, stops, context, radius):
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_LABEL(f"grounding (radius {radius / 1000:.0f}km):")
        )
        client = GooglePlacesClient()
        bias = None
        if context.latitude is not None and context.longitude is not None:
            bias = (context.latitude, context.longitude, min(radius, _MAX_BIAS_RADIUS))

        grounded = 0
        for i, s in enumerate(stops, 1):
            query = " ".join(p for p in (s.name, s.address or s.city) if p)
            try:
                results = client.search_text(
                    query,
                    max_results=1,
                    location_bias=bias,
                    language_code=context.language,
                )
            except GooglePlacesError as exc:
                self.stdout.write(f"{i}. {s.name}: places error ({exc})")
                continue
            if not results:
                self.stdout.write(f"{i}. {s.name}: NOT FOUND")
                continue
            place = results[0]
            if bias is not None:
                dist = _haversine_m(bias[0], bias[1], place.lat, place.lng)
                if dist > radius:
                    self.stdout.write(
                        f"{i}. {s.name}: REJECTED "
                        f"({dist / 1000:.1f}km > {radius / 1000:.0f}km radius)"
                    )
                    continue
            grounded += 1
            self.stdout.write(
                f"{i}. {s.name} ✓ -> {place.address} "
                f"[{place.lat:.4f},{place.lng:.4f}] {place.place_id}"
            )
        self.stdout.write(f"grounded total: {grounded}/{len(stops)}")

    def _selected_providers(self, provider):
        return ("gemini", "mistral") if provider == "both" else (provider,)

    def _resolve_day(self, trip, day_number):
        if day_number is None:
            day = trip.days.order_by("number").first()
            if day is None:
                raise CommandError(f"Trip {trip.pk} has no days")
            return day
        day = trip.days.filter(number=day_number).first()
        if day is None:
            raise CommandError(f"Day {day_number} not found in trip {trip.pk}")
        return day

    def _resolve_user(self, trip, email):
        if not email:
            return trip.author
        user = get_user_model().objects.filter(email=email).first()
        if user is None:
            raise CommandError(f"User {email} not found")
        return user

    def _build_prefs(self, user, opts):
        overrides = {}
        if opts["notes"]:
            overrides["notes"] = opts["notes"]
        prefs = merge_preferences(
            SuggestionPreferences.objects.filter(user=user).first(), overrides
        )
        if opts["radius"]:
            prefs = prefs.model_copy(update={"search_radius": opts["radius"]})
        return prefs

    def _section(self, title):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"=== {title} ==="))
