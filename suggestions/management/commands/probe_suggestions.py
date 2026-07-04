"""Dev-only probe for the AI suggestions pipeline.

Runs the real provider + Google Places calls against an existing trip and
prints every stage (prompt, raw AI response, grounding outcome with per-item
reasons) so the effect of prompt/context changes can be inspected by eye.

Usage:
    uv run python manage.py probe_suggestions <trip_id> [--stage "Firenze"]
        [--count 5] [--kinds experience,meal] [--language it]
        [--user user@example.com] [--no-ground]
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from suggestions.ai.factory import get_provider
from suggestions.models import AICredentials, SuggestionPreferences
from suggestions.prompts import build_prompt
from suggestions.services import (
    _GROUNDING_RADIUS,
    _MAX_BIAS_RADIUS,
    _OVERFETCH_FACTOR,
    _RADIUS_METERS,
    _apply_stage,
    _haversine_m,
    build_trip_context,
    merge_preferences,
)
from trips.models import Trip
from trips.services import GooglePlacesClient, GooglePlacesError


class Command(BaseCommand):
    help = "Probe the AI suggestions pipeline end-to-end against a real trip."

    def add_arguments(self, parser):
        parser.add_argument("trip_id", type=int, help="Trip primary key to probe")
        parser.add_argument(
            "--user",
            help="Email of the user whose BYOK key to use (default: trip author)",
        )
        parser.add_argument("--stage", help="Restrict to a stage (destination name)")
        parser.add_argument("--language", default="it", help="Prompt language")
        parser.add_argument("--count", type=int, help="Override result_count")
        parser.add_argument(
            "--kinds", help="Comma-separated kinds (experience,meal,stay)"
        )
        parser.add_argument(
            "--radius",
            choices=("city", "nearby", "day_trips"),
            help="Override the stored search_radius preference",
        )
        parser.add_argument(
            "--no-ground",
            action="store_true",
            help="Skip Google Places grounding (only show the raw AI response)",
        )

    def handle(self, *args, **opts):
        trip = Trip.objects.filter(pk=opts["trip_id"]).first()
        if trip is None:
            raise CommandError(f"Trip {opts['trip_id']} not found")

        user = self._resolve_user(trip, opts["user"])
        credentials = AICredentials.objects.filter(user=user).first()
        if credentials is None or not credentials.api_key_encrypted:
            raise CommandError(f"No AI credentials configured for {user.email}")

        stage = opts["stage"]
        prefs = self._build_prefs(user, opts)
        context = build_trip_context(trip, language=opts["language"], stage=stage)
        if stage:
            _apply_stage(context, trip, stage)

        # Over-request exactly like generate_suggestions does.
        fetch_prefs = prefs.model_copy(
            update={"result_count": prefs.result_count * _OVERFETCH_FACTOR}
        )

        self._section("PROMPT")
        self.stdout.write(build_prompt(context, fetch_prefs))

        provider = get_provider(credentials.provider, credentials.api_key_encrypted)
        raw = provider.generate(context, fetch_prefs)
        if prefs.kinds:
            raw = [s for s in raw if s.kind.value in prefs.kinds]

        self._section(f"RAW AI SUGGESTIONS ({len(raw)})")
        for i, s in enumerate(raw, 1):
            where = s.address or s.city or "-"
            self.stdout.write(
                f"{i}. [{s.kind.value}] {s.name} — {where} (type={s.type})"
            )
            if s.description:
                self.stdout.write(f"     {s.description}")

        if opts["no_ground"]:
            return

        radius = _RADIUS_METERS.get(prefs.search_radius, _GROUNDING_RADIUS)
        self._ground_all(raw, context, prefs.result_count, radius)

    def _resolve_user(self, trip, email):
        if not email:
            return trip.author
        user = get_user_model().objects.filter(email=email).first()
        if user is None:
            raise CommandError(f"User {email} not found")
        return user

    def _build_prefs(self, user, opts):
        overrides = {}
        if opts["kinds"]:
            overrides["kinds"] = [
                k.strip() for k in opts["kinds"].split(",") if k.strip()
            ]
        prefs = merge_preferences(
            SuggestionPreferences.objects.filter(user=user).first(), overrides
        )
        updates = {}
        if opts["count"]:
            updates["result_count"] = opts["count"]
        if opts["radius"]:
            updates["search_radius"] = opts["radius"]
        if updates:
            prefs = prefs.model_copy(update=updates)
        return prefs

    def _ground_all(self, raw, context, target, radius=_GROUNDING_RADIUS):
        self._section(f"GROUNDING (Google Places, radius {radius / 1000:.0f}km)")
        client = GooglePlacesClient()
        bias = None
        if context.latitude is not None and context.longitude is not None:
            bias = (
                context.latitude,
                context.longitude,
                min(radius, _MAX_BIAS_RADIUS),
            )

        grounded = 0
        for i, s in enumerate(raw, 1):
            if grounded >= target:
                self.stdout.write(f"{i}. {s.name}: skipped (target {target} reached)")
                continue
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

        self._section(f"GROUNDED TOTAL: {grounded}/{target}")

    def _section(self, title):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"=== {title} ==="))
