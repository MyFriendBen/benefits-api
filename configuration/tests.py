"""
Unit tests for Configuration app serializers.
"""

from unittest.mock import MagicMock, patch
from urllib.parse import urlparse
from django.test import SimpleTestCase, TestCase
from configuration.models import Configuration
from configuration.serializers import ConfigurationSerializer
from configuration.white_labels import white_label_config
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
    """
    Guards the referrer-scoped state dropdown config. The dropdown renders before a state is
    chosen, so it only ever reads the "_default" white label, and a code that is not a real
    white label silently falls back to the public state list — a typo here would look like the
    feature was never configured.
    """

    def test_default_white_label_declares_state_options(self):
        """The "_default" config is the only one the state dropdown reads."""
        self.assertIn("stateOptions", white_label_config["_default"].referrer_data)

    def test_state_options_codes_are_real_white_labels(self):
        """Every state code offered to a referrer must be a white label the screener can route to."""
        for code, white_label_data in white_label_config.items():
            state_options = white_label_data.referrer_data.get("stateOptions", {})

            for referrer, states in state_options.items():
                for state in states:
                    with self.subTest(white_label=code, referrer=referrer, state=state):
                        self.assertIn(
                            state,
                            white_label_config,
                            f'"{referrer}" in white label "{code}" offers state "{state}", which '
                            "is not a white label. The dropdown would drop it.",
                        )
                        self.assertNotEqual(
                            state,
                            "_default",
                            f'"{referrer}" in white label "{code}" offers "_default", which is not a state.',
                        )
