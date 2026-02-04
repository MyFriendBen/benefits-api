"""
Unit tests for sync_feature_flags management command.
"""

from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase
from screener.models import WhiteLabel
from screener.feature_flags import FeatureFlagConfig


TEST_FLAGS = {
    "flag_one": FeatureFlagConfig(
        label="Flag One",
        description="First flag",
        scope="frontend",
        default=False,
    ),
    "flag_two": FeatureFlagConfig(
        label="Flag Two",
        description="Second flag",
        scope="backend",
        default=True,
    ),
}


class SyncFeatureFlagsCommandTest(TestCase):
    """Tests for the sync_feature_flags management command."""

    def setUp(self):
        """Set up test data."""
        self.out = StringIO()
        self.err = StringIO()

    @patch.object(WhiteLabel, "FEATURE_FLAGS", TEST_FLAGS)
    def test_adds_new_flags_with_defaults(self):
        """Test that new flags are added with their default values."""
        wl = WhiteLabel.objects.create(name="Test", code="test", state_code="TS", feature_flags={})

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        wl.refresh_from_db()
        self.assertEqual(wl.feature_flags["flag_one"], False)
        self.assertEqual(wl.feature_flags["flag_two"], True)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "keep_flag": FeatureFlagConfig(
                label="Keep Flag",
                description="Flag to keep",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_removes_stale_flags(self):
        """Test that flags not in FEATURE_FLAGS definition are removed."""
        wl = WhiteLabel.objects.create(
            name="Test",
            code="test",
            state_code="TS",
            feature_flags={"keep_flag": True, "stale_flag": True},
        )

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        wl.refresh_from_db()
        self.assertIn("keep_flag", wl.feature_flags)
        self.assertNotIn("stale_flag", wl.feature_flags)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "existing_flag": FeatureFlagConfig(
                label="Existing Flag",
                description="An existing flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_preserves_existing_flag_values(self):
        """Test that existing flag values are preserved during sync."""
        wl = WhiteLabel.objects.create(
            name="Test",
            code="test",
            state_code="TS",
            feature_flags={"existing_flag": True},  # User enabled this flag
        )

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        wl.refresh_from_db()
        # Value should remain True (user's choice), not reset to default (False)
        self.assertTrue(wl.feature_flags["existing_flag"])

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "new_flag": FeatureFlagConfig(
                label="New Flag",
                description="A new flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_dry_run_does_not_modify_database(self):
        """Test that --dry-run shows changes without modifying database."""
        wl = WhiteLabel.objects.create(name="Test", code="test", state_code="TS", feature_flags={})

        call_command("sync_feature_flags", "--dry-run", stdout=self.out, stderr=self.err)

        wl.refresh_from_db()
        # Feature flags should still be empty
        self.assertEqual(wl.feature_flags, {})

        # Output should indicate dry run
        output = self.out.getvalue()
        self.assertIn("DRY RUN", output)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "flag_one": FeatureFlagConfig(
                label="Flag One",
                description="First flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_handles_empty_feature_flags(self):
        """Test that sync handles WhiteLabels with empty feature_flags dict."""
        wl = WhiteLabel.objects.create(name="Test", code="test", state_code="TS", feature_flags={})

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        wl.refresh_from_db()
        self.assertIn("flag_one", wl.feature_flags)
        self.assertEqual(wl.feature_flags["flag_one"], False)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "flag_one": FeatureFlagConfig(
                label="Flag One",
                description="First flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_syncs_multiple_white_labels(self):
        """Test that sync updates all WhiteLabels."""
        wl1 = WhiteLabel.objects.create(name="Test 1", code="test1", state_code="T1", feature_flags={})
        wl2 = WhiteLabel.objects.create(name="Test 2", code="test2", state_code="T2", feature_flags={})

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        wl1.refresh_from_db()
        wl2.refresh_from_db()

        self.assertIn("flag_one", wl1.feature_flags)
        self.assertIn("flag_one", wl2.feature_flags)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "flag_one": FeatureFlagConfig(
                label="Flag One",
                description="First flag",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_reports_in_sync_when_no_changes_needed(self):
        """Test that sync reports 'in sync' when no changes are needed."""
        # Ensure all existing WhiteLabels are in sync first
        for wl in WhiteLabel.objects.all():
            wl.feature_flags = {"flag_one": wl.feature_flags.get("flag_one", False)}
            wl.save()

        # Create new WhiteLabel already in sync
        WhiteLabel.objects.create(
            name="Test",
            code="test",
            state_code="TS",
            feature_flags={"flag_one": False},  # Must have exactly the keys in FEATURE_FLAGS
        )

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        output = self.out.getvalue()
        self.assertIn("All WhiteLabels are in sync", output)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "new_flag": FeatureFlagConfig(
                label="New Flag",
                description="A new flag",
                scope="frontend",
                default=True,
            ),
        },
    )
    def test_output_shows_added_flags(self):
        """Test that output shows which flags are being added."""
        WhiteLabel.objects.create(name="Test", code="test", state_code="TS", feature_flags={})

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        output = self.out.getvalue()
        self.assertIn("Adding: new_flag", output)
        self.assertIn("default: True", output)

    @patch.object(
        WhiteLabel,
        "FEATURE_FLAGS",
        {
            "keep_flag": FeatureFlagConfig(
                label="Keep Flag",
                description="Flag to keep",
                scope="frontend",
                default=False,
            ),
        },
    )
    def test_output_shows_removed_flags(self):
        """Test that output shows which flags are being removed."""
        WhiteLabel.objects.create(
            name="Test",
            code="test",
            state_code="TS",
            feature_flags={"keep_flag": True, "old_flag": True},
        )

        call_command("sync_feature_flags", stdout=self.out, stderr=self.err)

        output = self.out.getvalue()
        self.assertIn("Removing: old_flag", output)
