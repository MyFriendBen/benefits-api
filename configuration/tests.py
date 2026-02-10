"""
Unit tests for Configuration app serializers.
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase
from configuration.models import Configuration
from configuration.serializers import ConfigurationSerializer
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
