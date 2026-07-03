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
    if context.existing_places:
        lines.append("")
        lines.append(
            "Already planned for this trip (do NOT propose these or close "
            "duplicates, and favour suggestions geographically close to them):"
        )
        lines.extend(f"- {place}" for place in context.existing_places)
    if context.weather:
        lines.append("")
        lines.append("Weather forecast for the trip days:")
        lines.extend(f"- {line}" for line in context.weather)
        lines.append(
            "Favour indoor options on cold or rainy days and outdoor ones on "
            "clear days."
        )
    lines.append("")
    kind_labels = {"experience": "experiences", "meal": "meals", "stay": "stays"}
    if prefs.kinds:
        spanning = ", ".join(kind_labels[k] for k in prefs.kinds)
    else:
        spanning = "experiences, meals and stays"
    lines.append(
        f"Propose about {prefs.result_count} suggestions in total, spanning {spanning}."
    )
    if prefs.kinds:
        lines.append(f"Only propose suggestions of these kinds: {spanning}.")
    lines.append(
        "For each suggestion provide a real name and a precise postal address "
        "so it can be located on a map."
    )
    lines.append(
        "Set the integer 'type' field from this legend (omit it for stays): "
        + _TYPE_LEGEND
    )
    return "\n".join(lines)
