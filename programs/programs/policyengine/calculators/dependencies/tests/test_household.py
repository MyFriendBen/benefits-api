"""
Unit tests for household-level PolicyEngine dependencies used by TxSnap.

These dependencies calculate household-level values used by PolicyEngine
to determine TX SNAP eligibility and benefit amounts.
"""

from django.test import TestCase
from screener.models import Screen, WhiteLabel
from programs.programs.policyengine.calculators.dependencies import household


class TestTxStateCodeDependency(TestCase):
    """Tests for TxStateCodeDependency class used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for state dependency tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
        )

    def test_value_returns_tx_state_code(self):
        """Test value() returns TX state code."""
        dep = household.TxStateCodeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), "TX")
        self.assertEqual(dep.field, "state_code")
