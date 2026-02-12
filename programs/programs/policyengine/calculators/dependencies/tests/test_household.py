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


class TestCountyDependency(TestCase):
    """Tests for CountyDependency class and its subclasses."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def test_county_without_county_suffix_appends_county(self):
        """County names without 'County' should have '_COUNTY_' appended."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Suffolk", household_size=1, completed=False
        )
        dep = household.NcCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "SUFFOLK_COUNTY_NC")

    def test_county_with_county_suffix_does_not_duplicate(self):
        """County names already containing 'County' should not get it duplicated."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Denver County", household_size=1, completed=False
        )
        dep = household.NcCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "DENVER_COUNTY_NC")

    def test_county_normalization_removes_special_characters(self):
        """Special characters should be removed from county names."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="St. Mary's County", household_size=1, completed=False
        )
        dep = household.TxCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "ST_MARYS_COUNTY_TX")

    def test_county_normalization_handles_multiple_spaces(self):
        """Multiple spaces should be normalized to single underscores."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="New   York", household_size=1, completed=False
        )
        dep = household.IlCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "NEW_YORK_COUNTY_IL")

    def test_county_strips_whitespace(self):
        """Leading and trailing whitespace should be stripped."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="  Travis County  ", household_size=1, completed=False
        )
        dep = household.TxCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "TRAVIS_COUNTY_TX")

    def test_county_missing_raises_error(self):
        """Missing county should raise ValueError."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county=None, household_size=1, completed=False
        )
        dep = household.TxCountyDependency(screen, None, {})
        with self.assertRaises(ValueError) as context:
            dep.value()
        self.assertEqual(str(context.exception), "county missing")

    def test_base_class_without_state_dependency_raises_error(self):
        """Base CountyDependency without state_dependency_class should raise ValueError."""
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
        )
        dep = household.CountyDependency(screen, None, {})
        with self.assertRaises(ValueError) as context:
            dep.value()
        self.assertIn("must define state_dependency_class", str(context.exception))
