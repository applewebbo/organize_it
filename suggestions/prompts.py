from suggestions.schemas import SuggestionPrefs, TripContext
from trips.models import Experience, Meal

# Legend so the model emits valid per-kind `type` ids (kind "stay" has no type).
_TYPE_LEGEND = "; ".join(
    [
        "experience type ids: "
        + ", ".join(f"{c.value}={c.label}" for c in Experience.Type),
        "meal type ids: " + ", ".join(f"{c.value}={c.label}" for c in Meal.Type),
    ]
)

# Intro line per language; everything else is data the model can read in any
# language, so we only localise the instruction wrapper.
_INTRO = {
    "it": (
        "Sei un assistente di viaggio. Proponi esperienze, pasti e alloggi "
        "concreti e reali per il seguente viaggio. Rispondi in italiano."
    ),
    "en": (
        "You are a travel assistant. Propose concrete, real experiences, meals "
        "and stays for the following trip. Answer in English."
    ),
}


def _intro(language: str) -> str:
    return _INTRO.get(language, _INTRO["en"])


def build_prompt(context: TripContext, prefs: SuggestionPrefs) -> str:
    """Build the text prompt fed to the provider from trip context + prefs."""
    lines = [_intro(context.language), "", f"Destination: {context.destination}"]
    if context.start_date and context.end_date:
        lines.append(f"Dates: {context.start_date} to {context.end_date}")
    if prefs.favored_experience_types:
        favored = ", ".join(str(t) for t in prefs.favored_experience_types)
        lines.append(f"Favoured experience type ids: {favored}")
    lines.append(f"Dietary preference: {prefs.dietary}")
    lines.append(f"Pace: {prefs.pace}")
    lines.append(f"Budget: {prefs.budget}")
    if prefs.notes:
        lines.append(f"Extra notes: {prefs.notes}")
    lines.append("")
    lines.append(
        "For each suggestion provide a real name and a precise postal address "
        "so it can be located on a map."
    )
    lines.append(
        "Set the integer 'type' field from this legend (omit it for stays): "
        + _TYPE_LEGEND
    )
    return "\n".join(lines)
