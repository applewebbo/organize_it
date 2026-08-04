from datetime import date

from suggestions.prompts import build_day_prompt, build_prompt, build_trip_prompt
from suggestions.schemas import SuggestionPrefs, TripContext, TripStage


class TestBuildPrompt:
    def test_italian_intro_and_destination(self):
        context = TripContext(destination="Roma", language="it")
        prompt = build_prompt(context, SuggestionPrefs())
        assert "italiano" in prompt
        assert "Destination: Roma" in prompt

    def test_unknown_language_falls_back_to_english(self):
        context = TripContext(destination="Rome", language="xx")
        prompt = build_prompt(context, SuggestionPrefs())
        assert "English" in prompt

    def test_includes_dates_and_prefs(self):
        context = TripContext(
            destination="Rome",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 5),
        )
        prefs = SuggestionPrefs(
            favored_experience_types=[1, 3],
            notes="with kids",
        )
        prompt = build_prompt(context, prefs)
        assert "2026-07-01 to 2026-07-05" in prompt
        assert "1, 3" in prompt
        assert "with kids" in prompt

    def test_omits_optional_sections_when_empty(self):
        prompt = build_prompt(TripContext(destination="Rome"), SuggestionPrefs())
        assert "Dates:" not in prompt
        assert "Favoured experience type ids:" not in prompt
        assert "Extra notes:" not in prompt

    def test_requests_the_configured_result_count(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(result_count=11)
        )
        assert "about 11 suggestions" in prompt

    def test_spans_all_kinds_by_default(self):
        prompt = build_prompt(TripContext(destination="Rome"), SuggestionPrefs())
        assert "spanning experiences, meals and stays." in prompt
        assert "Only propose" not in prompt

    def test_restricts_to_selected_kinds(self):
        prompt = build_prompt(
            TripContext(destination="Rome"),
            SuggestionPrefs(kinds=["meal", "stay"]),
        )
        assert "Only propose suggestions of these kinds: meals, stays." in prompt
        assert "spanning meals, stays." in prompt

    def test_lists_existing_places_to_avoid(self):
        context = TripContext(
            destination="Rome",
            existing_places=["Colosseo (Roma)", "Hotel Rex (Roma)"],
        )
        prompt = build_prompt(context, SuggestionPrefs())
        assert "Already planned" in prompt
        assert "- Colosseo (Roma)" in prompt
        assert "- Hotel Rex (Roma)" in prompt

    def test_includes_weather_forecast(self):
        context = TripContext(
            destination="Rome",
            weather=["2026-07-01: Clear sky, 15–28°C, 0.0mm rain"],
        )
        prompt = build_prompt(context, SuggestionPrefs())
        assert "Weather forecast" in prompt
        assert "2026-07-01: Clear sky" in prompt
        assert "indoor options" in prompt

    def test_omits_context_sections_when_empty(self):
        prompt = build_prompt(TripContext(destination="Rome"), SuggestionPrefs())
        assert "Already planned" not in prompt
        assert "Weather forecast" not in prompt

    def test_low_budget_becomes_operational_constraint(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(budget="low")
        )
        assert "low-cost" in prompt
        assert "avoid fine dining" in prompt

    def test_high_budget_allows_premium(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(budget="high")
        )
        assert "premium" in prompt

    def test_vegetarian_is_a_soft_constraint(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(dietary="vegetarian")
        )
        assert "vegetarian options" in prompt

    def test_vegan_is_a_strict_constraint(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(dietary="vegan")
        )
        assert "fully vegan" in prompt

    def test_gluten_free_requires_explicit_menu(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(dietary="gluten_free")
        )
        assert "explicitly" in prompt
        assert "gluten-free" in prompt

    def test_no_dietary_line_when_none(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(dietary="none")
        )
        assert "vegetarian" not in prompt
        assert "vegan" not in prompt

    def test_includes_travel_party_and_style_and_interests_and_cuisine(self):
        prefs = SuggestionPrefs(
            travel_party="family",
            travel_style="offbeat",
            interests=["history", "nightlife"],
            cuisine="street_food",
        )
        prompt = build_prompt(TripContext(destination="Rome"), prefs)
        assert "family" in prompt
        assert "off the beaten path" in prompt
        assert "history, nightlife" in prompt
        assert "street food" in prompt

    def test_omits_neutral_new_prefs(self):
        prompt = build_prompt(TripContext(destination="Rome"), SuggestionPrefs())
        assert "Travelling as:" not in prompt
        assert "Interests:" not in prompt
        assert "Cuisine:" not in prompt
        assert "day-trip" not in prompt
        assert "within Rome" not in prompt

    def test_city_radius_keeps_suggestions_in_the_destination(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(search_radius="city")
        )
        assert "within Rome" in prompt

    def test_day_trips_radius_allows_nearby_destinations(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(search_radius="day_trips")
        )
        assert "day-trip" in prompt

    def test_nearby_radius_focuses_on_surroundings(self):
        prompt = build_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(search_radius="nearby")
        )
        assert "immediate surroundings" in prompt
        assert "far-off" in prompt


class TestBuildDayPrompt:
    def test_asks_for_single_ordered_day(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "single-day itinerary" in prompt
        assert "2026-07-01" in prompt
        assert "in order" in prompt

    def test_requests_estimated_duration(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "estimated_duration_minutes" in prompt

    def test_covers_meals(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "meal" in prompt.lower()

    def test_caps_meals_at_three(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "at most three meals" in prompt

    def test_reuses_shared_preferences(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"),
            SuggestionPrefs(budget="high", interests=["history"]),
            date(2026, 7, 1),
        )
        assert "premium" in prompt
        assert "history" in prompt

    def test_reuses_context_sections(self):
        context = TripContext(
            destination="Rome",
            existing_places=["Colosseo (Roma)"],
            weather=["2026-07-01: Clear sky, 15–28°C, 0.0mm rain"],
        )
        prompt = build_day_prompt(context, SuggestionPrefs(), date(2026, 7, 1))
        assert "- Colosseo (Roma)" in prompt
        assert "Weather forecast" in prompt

    def test_interleaves_existing_day_stops_when_given(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"),
            SuggestionPrefs(),
            date(2026, 7, 1),
            day_stops=["Colosseo", "Trattoria Luzzi"],
        )
        assert "already scheduled" in prompt.lower()
        assert "- Colosseo" in prompt
        assert "- Trattoria Luzzi" in prompt
        assert "exact" in prompt.lower()

    def test_no_interleave_section_without_day_stops(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "already scheduled" not in prompt.lower()

    def test_nearby_radius_clusters_the_day_in_one_zone(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"),
            SuggestionPrefs(search_radius="nearby"),
            date(2026, 7, 1),
        )
        assert "single locality" in prompt.lower()
        assert "close together" in prompt.lower()
        assert "do not spread" in prompt.lower()

    def test_day_trips_radius_picks_one_locality_and_clusters(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"),
            SuggestionPrefs(search_radius="day_trips"),
            date(2026, 7, 1),
        )
        assert "one day-trip locality" in prompt.lower()
        assert "outside rome" in prompt.lower()
        assert "clustered" in prompt.lower()
        assert "not how far apart" in prompt.lower()

    def test_city_radius_keeps_day_inside_destination(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"),
            SuggestionPrefs(search_radius="city"),
            date(2026, 7, 1),
        )
        assert "inside Rome" in prompt
        assert "neighbourhood" in prompt.lower()

    def test_day_prompt_omits_multi_card_spread_phrasing(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"),
            SuggestionPrefs(search_radius="day_trips"),
            date(2026, 7, 1),
        )
        assert "You may include day-trip destinations" not in prompt

    def test_day_has_pacing_guidance(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "well-paced" in prompt
        assert "4 to 6" in prompt

    def test_day_orders_stops_to_minimise_backtracking(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "minimise" in prompt
        assert "backtrack" in prompt

    def test_day_mentions_the_weekday(self):
        prompt = build_day_prompt(
            TripContext(destination="Rome"), SuggestionPrefs(), date(2026, 7, 1)
        )
        assert "Wednesday" in prompt
        assert "closed" in prompt


_STAGES = [
    TripStage(
        destination="Roma", start_date=date(2026, 6, 1), end_date=date(2026, 6, 3)
    ),
    TripStage(
        destination="Firenze", start_date=date(2026, 6, 4), end_date=date(2026, 6, 5)
    ),
]


class TestBuildTripPrompt:
    def test_asks_for_full_day_by_day_itinerary(self):
        prompt = build_trip_prompt(
            TripContext(destination="Roma"), SuggestionPrefs(), _STAGES
        )
        assert "day-by-day" in prompt.lower()
        assert "every day" in prompt.lower()

    def test_lists_each_stage_with_its_date_range(self):
        prompt = build_trip_prompt(
            TripContext(destination="Roma"), SuggestionPrefs(), _STAGES
        )
        assert "- Roma: 2026-06-01 to 2026-06-03" in prompt
        assert "- Firenze: 2026-06-04 to 2026-06-05" in prompt

    def test_requests_date_destination_and_ordered_stops_per_day(self):
        prompt = build_trip_prompt(
            TripContext(destination="Roma"), SuggestionPrefs(), _STAGES
        )
        assert "date" in prompt.lower()
        assert "ordered sequence of stops" in prompt.lower()

    def test_excludes_stays(self):
        prompt = build_trip_prompt(
            TripContext(destination="Roma"), SuggestionPrefs(), _STAGES
        )
        assert "do NOT propose accommodation" in prompt

    def test_requests_estimated_duration(self):
        prompt = build_trip_prompt(
            TripContext(destination="Roma"), SuggestionPrefs(), _STAGES
        )
        assert "estimated_duration_minutes" in prompt

    def test_caps_meals_at_three(self):
        prompt = build_trip_prompt(
            TripContext(destination="Roma"), SuggestionPrefs(), _STAGES
        )
        assert "at most three meals" in prompt

    def test_reuses_shared_preferences_and_context(self):
        context = TripContext(destination="Roma", existing_places=["Colosseo (Roma)"])
        prompt = build_trip_prompt(
            context, SuggestionPrefs(budget="high", interests=["history"]), _STAGES
        )
        assert "premium" in prompt
        assert "history" in prompt
        assert "- Colosseo (Roma)" in prompt

    def test_omits_stage_list_when_empty(self):
        prompt = build_trip_prompt(
            TripContext(destination="Roma"), SuggestionPrefs(), []
        )
        assert "organised in these stages" not in prompt
