"""
Unit tests for Configuration app serializers.
"""

from unittest.mock import MagicMock, patch
from urllib.parse import urlparse
from django.test import SimpleTestCase, TestCase
from configuration.models import Configuration
from configuration.serializers import ConfigurationSerializer
from configuration.white_labels import state_options, white_label_config
from screener.models import WhiteLabel
from screener.feature_flags import FeatureFlagConfig


class TestConfigurationSerializerFeatureFlags(TestCase):
    """
    Tests for ConfigurationSerializer.get_feature_flags() method.
    """

    def setUp(self):
        """Set up test data for feature flag serialization tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.configuration = Configuration.objects.create(
            white_label=self.white_label, name="Test Config", data={}, active=True
        )
        self.serializer = ConfigurationSerializer()

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "frontend_flag": FeatureFlagConfig(
                label="Frontend Flag",
                description="A frontend flag",
                scope="frontend",
                default=False,
            ),
            "backend_flag": FeatureFlagConfig(
                label="Backend Flag",
                description="A backend flag",
                scope="backend",
                default=False,
            ),
            "both_flag": FeatureFlagConfig(
                label="Both Flag",
                description="A flag for both",
                scope="both",
                default=False,
            ),
        },
    )
    def test_get_feature_flags_filters_to_frontend_and_both_scopes(self):
        """Test that get_feature_flags only returns frontend and both scoped flags."""
        self.white_label.feature_flags = {
            "frontend_flag": True,
            "backend_flag": True,
            "both_flag": True,
        }
        self.white_label.save()

        feature_flags = self.serializer.get_feature_flags(self.configuration)

        # Should include frontend and both scoped flags
        self.assertIn("frontend_flag", feature_flags)
        self.assertIn("both_flag", feature_flags)

        # Should NOT include backend-only flags
        self.assertNotIn("backend_flag", feature_flags)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "frontend_flag": FeatureFlagConfig(
                label="Frontend Flag",
                description="A frontend flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_get_feature_flags_returns_stored_values(self):
        """Test that get_feature_flags returns the stored flag values."""
        self.white_label.feature_flags = {"frontend_flag": True}
        self.white_label.save()

        feature_flags = self.serializer.get_feature_flags(self.configuration)

        self.assertTrue(feature_flags["frontend_flag"])

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "frontend_flag": FeatureFlagConfig(
                label="Frontend Flag",
                description="A frontend flag",
                scope="frontend",
                default=True,
            ),
        },
    )
    def test_get_feature_flags_returns_defaults_when_not_stored(self):
        """Test that get_feature_flags returns default values when flag is not stored."""
        self.white_label.feature_flags = {}
        self.white_label.save()

        feature_flags = self.serializer.get_feature_flags(self.configuration)

        # Should return default value (True)
        self.assertTrue(feature_flags["frontend_flag"])

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "frontend_flag": FeatureFlagConfig(
                label="Frontend Flag",
                description="A frontend flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_get_feature_flags_returns_empty_dict_when_no_white_label(self):
        """Test that get_feature_flags returns empty dict when configuration has no white_label."""
        config_no_wl = MagicMock()
        config_no_wl.white_label = None

        feature_flags = self.serializer.get_feature_flags(config_no_wl)

        self.assertEqual(feature_flags, {})

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "frontend_flag": FeatureFlagConfig(
                label="Frontend Flag",
                description="A frontend flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_get_feature_flags_handles_empty_feature_flags(self):
        """Test that get_feature_flags handles empty feature_flags dict."""
        self.white_label.feature_flags = {}
        self.white_label.save()

        feature_flags = self.serializer.get_feature_flags(self.configuration)

        # Should return default value
        self.assertFalse(feature_flags["frontend_flag"])


class TestLegalLinkConfiguration(SimpleTestCase):
    """
    Asserts every white label's effective privacy policy and consent links are real URLs, so an
    empty or relative value fails CI instead of shipping a dead link.
    """

    LEGAL_LINK_KEYS = ("privacy_policy", "consent_to_contact")

    def test_legal_links_are_populated_urls(self):
        """Every locale must map to a real URL, not an empty or relative value."""
        for code, white_label_data in white_label_config.items():
            for key in self.LEGAL_LINK_KEYS:
                links = getattr(white_label_data, key)

                with self.subTest(white_label=code, key=key):
                    self.assertIn(
                        "en-us",
                        links,
                        f'White label "{code}" is missing the "en-us" fallback for {key}. The frontend '
                        "falls back to en-us for every locale without its own translated page.",
                    )

                for locale, link in links.items():
                    # Parse rather than string-match the prefix: "https://" and
                    # "https:///privacy-policy/" both start with the scheme but name no host,
                    # so they reach the browser as dead links just like the empty string did.
                    parsed = urlparse(link)

                    with self.subTest(white_label=code, key=key, locale=locale):
                        self.assertTrue(
                            parsed.scheme == "https" and bool(parsed.netloc),
                            f'White label "{code}" has a {key} link for "{locale}" that is not an '
                            f"absolute https URL: {link!r}. An empty string here renders as a link "
                            "with an empty href.",
                        )


class TestStateOptionsConfiguration(SimpleTestCase):
    """Guards the state dropdown's derived catalog and the per-referrer overrides that select from it."""

    def test_catalog_covers_every_state_white_label(self):
        """Every state white label appears once, with a name to show in the dropdown."""
        catalog = state_options()
        codes = [state["code"] for state in catalog]

        self.assertEqual(len(codes), len(set(codes)))
        for code, white_label_data in white_label_config.items():
            expected = white_label_data.is_state and not white_label_data.is_default
            with self.subTest(white_label=code):
                self.assertEqual(code in codes, expected)

        for state in catalog:
            with self.subTest(white_label=state["code"]):
                self.assertTrue(state["name"], f'White label "{state["code"]}" has no state name to display.')

    def test_default_white_label_declares_state_options(self):
        """
        The "_default" config backs the state-agnostic /select-state route, so it stays the
        generic every-public-state list. A partner narrowing the dropdown belongs in the config
        for the state path it is handed out under, where the screener actually reads it.
        """
        state_options_config = white_label_config["_default"].referrer_data.get("stateOptions")

        self.assertIsNotNone(state_options_config, '"_default" must declare "stateOptions".')
        self.assertEqual(
            state_options_config,
            {"default": []},
            '"_default" should offer every publicly launched state and nothing partner-specific. '
            f"Found {state_options_config!r}; move any referrer entry to that referrer's state "
            "config.",
        )

    def test_multi_state_referrers_are_configured_in_every_state_they_offer(self):
        """
        A referrer whose dropdown offers several states is handed out under each of those state
        paths, and each path loads its own config. Configuring it in only one of them leaves the
        others on generic branding with an unscoped dropdown.
        """
        branding_keys = ("theme", "logoSource", "logoClass", "stateOptions")

        for code, white_label_data in white_label_config.items():
            for referrer, states in white_label_data.referrer_data.get("stateOptions", {}).items():
                if referrer == "default" or code not in states:
                    continue

                for state in states:
                    state_referrer_data = white_label_config[state].referrer_data

                    for key in branding_keys:
                        with self.subTest(referrer=referrer, configured_in=code, missing_from=state, key=key):
                            self.assertIn(
                                referrer,
                                state_referrer_data.get(key, {}),
                                f'"{referrer}" is configured in white label "{code}" and offers '
                                f'"{state}", but white label "{state}" has no "{referrer}" entry '
                                f'for "{key}".',
                            )

    def test_referrer_overrides_name_states_in_the_catalog(self):
        """An override naming a state outside the catalog would render an empty dropdown."""
        codes = {state["code"] for state in state_options()}

        for code, white_label_data in white_label_config.items():
            for referrer, states in white_label_data.referrer_data.get("stateOptions", {}).items():
                for state in states:
                    with self.subTest(white_label=code, referrer=referrer, state=state):
                        self.assertIn(
                            state,
                            codes,
                            f'"{referrer}" in white label "{code}" offers "{state}", which the state '
                            "dropdown has no entry for.",
                        )


class TestPublicChargeRuleConfiguration(SimpleTestCase):
    """
    Asserts every white label's public charge rule carries both a link and a visible label. The
    frontend renders the anchor as <a href={link}>{text}</a>, so a config with a link but no text
    ships an invisible, unclickable link rather than failing loudly.
    """

    def test_public_charge_rule_has_link_and_text(self):
        """Every live white label needs both an absolute link and the label the anchor renders."""
        for code, white_label_data in white_label_config.items():
            # The base class holds the empty placeholder every white label overrides, and
            # "_default" is never served to the frontend, so neither has copy of its own.
            if white_label_data.is_default:
                continue

            public_charge_rule = white_label_data.public_charge_rule

            with self.subTest(white_label=code):
                # The disclaimer step renders <a href={link}>{text}</a> with no emptiness check,
                # so an unset value here reaches the browser as a broken anchor either way.
                link = public_charge_rule.get("link", "")
                parsed = urlparse(link)
                self.assertTrue(
                    parsed.scheme == "https" and bool(parsed.netloc),
                    f'White label "{code}" has a public charge link that is not an absolute '
                    f"https URL: {link!r}. The disclaimer step renders the anchor "
                    "unconditionally, so an empty value ships an anchor with an empty href.",
                )

                text = public_charge_rule.get("text")
                self.assertIsInstance(
                    text,
                    dict,
                    f'White label "{code}" is missing a dict "text" for its public charge link. '
                    "The frontend renders the anchor with no children, so nothing is visible "
                    "to click.",
                )
                self.assertTrue(
                    text.get("_label") and text.get("_default_message"),
                    f'White label "{code}" has a public charge "text" missing "_label" or '
                    '"_default_message". The frontend only converts an object carrying both '
                    "into a FormattedMessage; an empty _label renders as a FormattedMessage "
                    "with an empty id.",
                )
