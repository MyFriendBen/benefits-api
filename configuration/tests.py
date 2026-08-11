"""
Unit tests for Configuration app serializers.
"""

from unittest.mock import MagicMock, patch
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
    Guards the privacy policy and terms links that every white label puts in its footer,
    step-1 disclaimer, and sign-up consent copy.

    KS, MO, and WA each shipped with these keys unset and inherited an empty-string
    default, which renders as a link with an empty href — visibly a link, silently going
    nowhere. Nothing caught it: the base class supplied a value, so no error was raised,
    and the health check skips empty links entirely.

    Both keys now have real defaults in the base class, so a missing override degrades to
    the generic MyFriendBen pages instead of a dead link. These tests additionally require
    each white label to declare both keys in its own class body, so that using the generic
    pages stays a deliberate choice — a new white label cannot inherit legal links by
    accident.
    """

    LEGAL_LINK_KEYS = ("privacy_policy", "consent_to_contact")

    def test_every_white_label_declares_its_own_legal_links(self):
        """Each white label must set both keys itself rather than inheriting them."""
        for code, white_label_data in white_label_config.items():
            for key in self.LEGAL_LINK_KEYS:
                with self.subTest(white_label=code, key=key):
                    self.assertIn(
                        key,
                        white_label_data.__dict__,
                        f'White label "{code}" does not declare {key}. Add it to the white label config '
                        f"(configuration/white_labels/{code}.py), even if the generic MyFriendBen page "
                        "is the right link, so the choice is explicit.",
                    )

    def test_legal_links_are_populated_urls(self):
        """Every declared locale must map to a real URL, not an empty or relative value."""
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
                    with self.subTest(white_label=code, key=key, locale=locale):
                        self.assertTrue(
                            link.startswith("https://"),
                            f'White label "{code}" has a {key} link for "{locale}" that is not an '
                            f"https URL: {link!r}. An empty string here renders as a link with an "
                            "empty href.",
                        )
