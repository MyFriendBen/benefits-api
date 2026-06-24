"""
Unit tests for household-level PolicyEngine dependencies.

These tests verify all classes in
programs/programs/policyengine/calculators/dependencies/household.py:
state-code dependencies, county dependencies, zip-code dependency, and
the public-housing dependency.
"""

from django.test import TestCase
from screener.models import Expense, Screen, WhiteLabel
from programs.programs.policyengine.calculators.dependencies import household


class TestCoStateCodeDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="80202", county="Denver County", household_size=1, completed=False
        )

    def test_value_returns_co_state_code(self):
        dep = household.CoStateCodeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), "CO")
        self.assertEqual(dep.field, "state_code")


class TestNcStateCodeDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="27601", county="Wake County", household_size=1, completed=False
        )

    def test_value_returns_nc_state_code(self):
        dep = household.NcStateCodeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), "NC")
        self.assertEqual(dep.field, "state_code")


class TestMaStateCodeDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="02101", county="Suffolk", household_size=1, completed=False
        )

    def test_value_returns_ma_state_code(self):
        dep = household.MaStateCodeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), "MA")
        self.assertEqual(dep.field, "state_code")


class TestIlStateCodeDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60601", county="Cook County", household_size=1, completed=False
        )

    def test_value_returns_il_state_code(self):
        dep = household.IlStateCodeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), "IL")
        self.assertEqual(dep.field, "state_code")


class TestTxStateCodeDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
        )

    def test_value_returns_tx_state_code(self):
        dep = household.TxStateCodeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), "TX")
        self.assertEqual(dep.field, "state_code")


class TestWaStateCodeDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="98101", county="King County", household_size=1, completed=False
        )

    def test_value_returns_wa_state_code(self):
        dep = household.WaStateCodeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), "WA")
        self.assertEqual(dep.field, "state_code")


class TestCountyDependency(TestCase):
    """Tests for CountyDependency base class and all concrete subclasses."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    # --- subclass configuration ---

    def test_nc_county_dependency_state_dependency_class(self):
        self.assertIs(household.NcCountyDependency.state_dependency_class, household.NcStateCodeDependency)

    def test_il_county_dependency_state_dependency_class(self):
        self.assertIs(household.IlCountyDependency.state_dependency_class, household.IlStateCodeDependency)

    def test_ma_county_dependency_state_dependency_class(self):
        self.assertIs(household.MaCountyDependency.state_dependency_class, household.MaStateCodeDependency)

    def test_tx_county_dependency_state_dependency_class(self):
        self.assertIs(household.TxCountyDependency.state_dependency_class, household.TxStateCodeDependency)

    def test_ma_county_dependency_value_formats_correctly(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="02101", county="Suffolk", household_size=1, completed=False
        )
        dep = household.MaCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "SUFFOLK_COUNTY_MA")

    # --- shared normalization (via NcCountyDependency as representative subclass) ---

    def test_county_without_county_suffix_appends_county(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Suffolk", household_size=1, completed=False
        )
        dep = household.NcCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "SUFFOLK_COUNTY_NC")

    def test_county_with_county_suffix_does_not_duplicate(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Denver County", household_size=1, completed=False
        )
        dep = household.NcCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "DENVER_COUNTY_NC")

    def test_county_normalization_removes_special_characters(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="St. Mary's County", household_size=1, completed=False
        )
        dep = household.TxCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "ST_MARYS_COUNTY_TX")

    def test_county_normalization_handles_multiple_spaces(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="New   York", household_size=1, completed=False
        )
        dep = household.IlCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "NEW_YORK_COUNTY_IL")

    def test_county_strips_whitespace(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="  Travis County  ", household_size=1, completed=False
        )
        dep = household.TxCountyDependency(screen, None, {})
        self.assertEqual(dep.value(), "TRAVIS_COUNTY_TX")

    def test_county_missing_raises_error(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county=None, household_size=1, completed=False
        )
        dep = household.TxCountyDependency(screen, None, {})
        with self.assertRaises(ValueError) as context:
            dep.value()
        self.assertEqual(str(context.exception), "county missing")

    def test_base_class_without_state_dependency_raises_error(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
        )
        dep = household.CountyDependency(screen, None, {})
        with self.assertRaises(ValueError) as context:
            dep.value()
        self.assertIn("must define state_dependency_class", str(context.exception))


class TestZipCodeDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def test_value_returns_zipcode(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="02101", county="Suffolk", household_size=1, completed=False
        )
        dep = household.ZipCodeDependency(screen, None, {})
        self.assertEqual(dep.value(), "02101")

    def test_field_and_dependencies(self):
        self.assertEqual(household.ZipCodeDependency.field, "zip_code")
        self.assertIn("zipcode", household.ZipCodeDependency.dependencies)


class TestIsInPublicHousingDependency(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def test_returns_true_when_subsidized_rent_expense_present(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="02101", county="Suffolk", household_size=1, completed=False
        )
        Expense.objects.create(screen=screen, type="subsidizedRent", amount=500, frequency="monthly")
        dep = household.IsInPublicHousingDependency(screen, None, {})
        self.assertTrue(dep.value())

    def test_returns_false_when_no_subsidized_rent_expense(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="02101", county="Suffolk", household_size=1, completed=False
        )
        Expense.objects.create(screen=screen, type="rent", amount=1000, frequency="monthly")
        dep = household.IsInPublicHousingDependency(screen, None, {})
        self.assertFalse(dep.value())

    def test_returns_false_when_no_expenses(self):
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="02101", county="Suffolk", household_size=1, completed=False
        )
        dep = household.IsInPublicHousingDependency(screen, None, {})
        self.assertFalse(dep.value())

    def test_field(self):
        self.assertEqual(household.IsInPublicHousingDependency.field, "is_in_public_housing")
