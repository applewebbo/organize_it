from datetime import date

from suggestions.prompts import build_prompt
from suggestions.schemas import SuggestionPrefs, TripContext


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
