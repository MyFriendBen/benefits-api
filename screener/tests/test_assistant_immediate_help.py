"""The Immediate Help context Benji is given (MFB-1931).

MFB-824 made the results page a third tab. The prompt is a closed-world description of
that page, so getting this wrong means Benji confidently points a household at a control
that is not on their screen — the MFB-1872 failure, reintroduced by a frontend change.

The reason this lives in the context rather than in the prompt: **the tab's presence
varies per household, not per white label.** A referrer's `uiOptions` can switch it off,
so two people on the same site see different pages, and nothing static could be right.
"""

import json

from django.test import TestCase

from configuration.models import Configuration
from screener.assistant import (
    IMMEDIATE_HELP_ABSENT,
    IMMEDIATE_HELP_BUTTON,
    IMMEDIATE_HELP_TAB,
    _immediate_help,
)
from screener.models import Screen, WhiteLabel
from translations.models import Translation


def more_help_config(*entries):
    return {"moreHelpOptions": list(entries)}


KS_211 = {
    "name": {"_default_message": "Kansas 211 (United Way of Kansas)", "_label": "moreHelp.211.name.ks"},
    "link": "https://unitedwayplains.org/211-information-and-referral/",
    "phone": {"_default_message": "Dial 2-1-1", "_label": "moreHelp.211.phone.ks"},
}


class ImmediateHelpContextTests(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(
            name="Test State", code="test", state_code="TS", feature_flags={"benbot": True}
        )
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=2, completed=True
        )

    def _config(self, name, data, white_label=None):
        Configuration.objects.update_or_create(
            white_label=white_label or self.white_label,
            name=name,
            defaults={"data": data, "active": True},
        )

    def _referrer(self, ui_options):
        self._config("referrer_data", {"uiOptions": ui_options})

    # --- entry point ---

    def test_a_configured_white_label_gets_a_tab(self):
        self._config("more_help_options", more_help_config(KS_211))

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_TAB)
        self.assertEqual(result["resources"][0]["name"], "Kansas 211 (United Way of Kansas)")

    def test_no_configured_resources_means_no_route(self):
        """`buildTabs.ts` refuses to render a tab whose panel is just a heading."""
        self._config("more_help_options", more_help_config())

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_ABSENT)

    def test_a_missing_config_means_no_route(self):
        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_ABSENT)

    def test_cesn_gets_a_button_because_it_renders_no_tab_bar(self):
        cesn = WhiteLabel.objects.create(name="CESN", code="cesn", state_code="CO", feature_flags={})
        screen = Screen.objects.create(white_label=cesn, zipcode="80014", household_size=1, completed=True)
        self._config("more_help_options", more_help_config(KS_211), white_label=cesn)

        result = _immediate_help(screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_BUTTON)

    # --- per-referrer suppression: the reason this is context, not prompt ---

    def test_a_referrer_can_switch_the_route_off(self):
        """NC sets `no_results_more_help` on 211nc, hfed, lanc and ccla."""
        self.screen.referrer_code = "211nc"
        self.screen.save()
        self._config("more_help_options", more_help_config(KS_211))
        self._referrer({"default": [], "211nc": ["no_results_more_help"]})

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_ABSENT)

    def test_a_sibling_referrer_on_the_same_white_label_still_gets_it(self):
        """The whole reason this cannot be a per-white-label statement in the prompt."""
        self.screen.referrer_code = "someone_else"
        self.screen.save()
        self._config("more_help_options", more_help_config(KS_211))
        self._referrer({"default": [], "211nc": ["no_results_more_help"]})

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_TAB)

    def test_an_unknown_referrer_code_falls_back_to_default(self):
        """Matching `getReferrer`, which falls back to "default" for an unknown code."""
        self.screen.referrer_code = "never_configured"
        self.screen.save()
        self._config("more_help_options", more_help_config(KS_211))
        self._referrer({"default": ["no_results_more_help"]})

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_ABSENT)

    def test_suppression_removes_the_button_too_not_just_the_tab(self):
        cesn = WhiteLabel.objects.create(name="CESN", code="cesn", state_code="CO", feature_flags={})
        screen = Screen.objects.create(
            white_label=cesn, zipcode="80014", household_size=1, completed=True, referrer_code="x"
        )
        self._config("more_help_options", more_help_config(KS_211), white_label=cesn)
        self._config("referrer_data", {"uiOptions": {"default": ["no_results_more_help"]}}, white_label=cesn)

        result = _immediate_help(screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_ABSENT)

    # --- contents ---

    def test_resources_are_withheld_when_there_is_no_route(self):
        """Naming help the household cannot reach is the closed-world break in reverse."""
        self.screen.referrer_code = "off"
        self.screen.save()
        self._config("more_help_options", more_help_config(KS_211))
        self._referrer({"default": [], "off": ["no_results_more_help"]})

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["resources"], [])

    def test_the_translated_name_wins_over_the_config_default(self):
        """These are the words on the household's own screen."""
        Translation.objects.add_translation("moreHelp.211.name.ks", "Kansas 211 — translated")
        self._config("more_help_options", more_help_config(KS_211))

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["resources"][0]["name"], "Kansas 211 — translated")

    def test_the_config_default_is_used_when_no_translation_row_exists(self):
        """`add_config` seeds these, so a fresh environment can have the config without
        the rows — and an English name beats a nameless entry."""
        self._config("more_help_options", more_help_config(KS_211))

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["resources"][0]["contact"], "Dial 2-1-1")

    def test_an_unnamed_entry_is_dropped(self):
        """A blank line in a list the prompt calls complete is worse than a short list."""
        self._config("more_help_options", more_help_config({"link": "https://example.org"}, KS_211))

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(len(result["resources"]), 1)

    def test_a_non_http_link_is_dropped_but_the_entry_survives(self):
        entry = {**KS_211, "link": "javascript:alert(1)"}
        self._config("more_help_options", more_help_config(entry))

        result = _immediate_help(self.screen, "en-us")

        self.assertNotIn("link", result["resources"][0])
        self.assertIn("name", result["resources"][0])

    def test_the_config_comes_back_double_encoded_and_is_still_read(self):
        """`Configuration.data` does not round-trip as a dict, and this is the trap.

        `OrderedJSONField` json.dumps() on the way in and the column then encodes that
        string as jsonb, so writing a dict reads back as the STRING '{"a": 1}'. Verified
        directly rather than assumed. Every other test in this file depends on the
        unwrap in `_config_data`; this one says so out loud, because a reader who
        assumed a dict would delete it as dead code.
        """
        self._config("more_help_options", more_help_config(KS_211))

        raw = (
            Configuration.objects.filter(white_label=self.white_label, name="more_help_options")
            .values_list("data", flat=True)
            .first()
        )
        self.assertIsInstance(raw, str)
        self.assertEqual(json.loads(raw), more_help_config(KS_211))

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_TAB)
        self.assertEqual(len(result["resources"]), 1)

    def test_unparseable_config_degrades_to_no_route_rather_than_500ing(self):
        self._config("more_help_options", "not json at all {{{")

        result = _immediate_help(self.screen, "en-us")

        self.assertEqual(result["entry_point"], IMMEDIATE_HELP_ABSENT)
        self.assertEqual(result["resources"], [])
