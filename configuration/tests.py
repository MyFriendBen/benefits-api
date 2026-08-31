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


class TestPublicChargeRuleConfiguration(SimpleTestCase):
    """
    Asserts every white label's public charge rule carries both a link and a visible label. The
    frontend renders the anchor as <a href={link}>{text}</a>, so a config with a link but no text
    ships an invisible, unclickable link rather than failing loudly.
    """

    def test_public_charge_rule_has_link_and_text(self):
        """A configured link must come with the label the anchor renders as its content."""
        for code, white_label_data in white_label_config.items():
            public_charge_rule = white_label_data.public_charge_rule

            with self.subTest(white_label=code):
                link = public_charge_rule.get("link", "")

                # The base class ships an empty link so white labels can opt out entirely; only
                # a white label that actually points somewhere needs a label to go with it.
                if not link:
                    continue

                text = public_charge_rule.get("text")
                self.assertIsNotNone(
                    text,
                    f'White label "{code}" sets a public charge link but no "text". The frontend '
                    "renders the anchor with no children, so nothing is visible to click.",
                )
                self.assertTrue(
                    text.get("_label") and text.get("_default_message"),
                    f'White label "{code}" has a public charge "text" missing "_label" or '
                    '"_default_message". Both are required for the frontend to build a '
                    "FormattedMessage, which falls back to the default message when no "
                    "translation row exists.",
                )
