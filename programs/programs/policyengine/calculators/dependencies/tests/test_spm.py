"""
Unit tests for SPM (Supplemental Poverty Measure) unit-level PolicyEngine dependencies used by TxSnap.

These dependencies calculate household-level values for SPM units, which are used
by PolicyEngine to determine TX SNAP eligibility and benefit amounts.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream, Expense
from programs.programs.policyengine.calculators.dependencies import spm


class TestSnapIncomeDependency(TestCase):
    """Tests for SnapEarnedIncomeDependency and SnapUnearnedIncomeDependency classes used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add earned income
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        # Add unearned income
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="alimony", amount=500, frequency="monthly"
        )

    def test_value_calculates_annual_earned_income(self):
        """Test SnapEarnedIncomeDependency.value() calculates total annual earned income for household."""
        dep = spm.SnapEarnedIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 24000)  # $2000/month * 12
        self.assertEqual(dep.field, "snap_earned_income")

    def test_value_calculates_annual_unearned_income(self):
        """Test SnapUnearnedIncomeDependency.value() calculates total annual unearned income for household."""
        dep = spm.SnapUnearnedIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 6000)  # $500/month * 12
        self.assertEqual(dep.field, "snap_unearned_income")


class TestSnapAssetsDependency(TestCase):
    """Tests for SnapAssetsDependency class used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for asset tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            household_assets=1500,
            completed=False,
        )

    def test_value_returns_household_assets(self):
        """Test value() returns household assets value from screen."""
        dep = spm.SnapAssetsDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 1500)
        self.assertEqual(dep.field, "snap_assets")

    def test_value_returns_zero_when_assets_null(self):
        """Test value() returns 0 when household assets are null."""
        self.screen.household_assets = None
        self.screen.save()

        dep = spm.SnapAssetsDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)


class TestHousingCostDependency(TestCase):
    """Tests for HousingCostDependency class used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for housing expense tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        # Add multiple housing expenses
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")

        Expense.objects.create(screen=self.screen, type="mortgage", amount=500, frequency="monthly")

    def test_value_calculates_total_annual_housing_cost(self):
        """Test value() calculates combined annual rent and mortgage costs."""
        dep = spm.HousingCostDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 18000)  # ($1000 + $500) * 12
        self.assertEqual(dep.field, "housing_cost")

    def test_value_calculates_rent_only(self):
        """Test value() calculates annual rent when no mortgage exists."""
        # Remove mortgage expense
        Expense.objects.filter(screen=self.screen, type="mortgage").delete()

        dep = spm.HousingCostDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 12000)  # $1000 * 12


class TestUtilityExpenseDependency(TestCase):
    """Tests for utility expense dependency classes: HasHeatingCoolingExpenseDependency, HeatingCoolingExpenseDependency, HasPhoneExpenseDependency, PhoneExpenseDependency, and WaterExpenseDependency."""

    def setUp(self):
        """Set up test data for utility expense tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

    def test_value_returns_true_when_heating_expense_exists(self):
        """Test HasHeatingCoolingExpenseDependency.value() returns True when heating expense exists."""
        Expense.objects.create(screen=self.screen, type="heating", amount=100, frequency="monthly")

        dep = spm.HasHeatingCoolingExpenseDependency(self.screen, None, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "has_heating_cooling_expense")

    def test_value_returns_false_when_no_heating_cooling_expense(self):
        """Test HasHeatingCoolingExpenseDependency.value() returns False when no heating/cooling expense exists."""
        dep = spm.HasHeatingCoolingExpenseDependency(self.screen, None, {})
        self.assertFalse(dep.value())

    def test_value_calculates_annual_heating_cooling_total(self):
        """Test HeatingCoolingExpenseDependency.value() calculates combined annual heating and cooling costs."""
        Expense.objects.create(screen=self.screen, type="heating", amount=100, frequency="monthly")
        Expense.objects.create(screen=self.screen, type="cooling", amount=75, frequency="monthly")

        dep = spm.HeatingCoolingExpenseDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 2100)  # ($100 + $75) * 12
        self.assertEqual(dep.field, "heating_cooling_expense")

    def test_value_returns_true_when_phone_expense_exists(self):
        """Test HasPhoneExpenseDependency.value() returns True when telephone expense exists."""
        Expense.objects.create(screen=self.screen, type="telephone", amount=50, frequency="monthly")

        dep = spm.HasPhoneExpenseDependency(self.screen, None, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "has_phone_expense")

    def test_value_calculates_annual_phone_cost(self):
        """Test PhoneExpenseDependency.value() calculates annual telephone costs."""
        Expense.objects.create(screen=self.screen, type="telephone", amount=50, frequency="monthly")

        dep = spm.PhoneExpenseDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 600)  # $50 * 12
        self.assertEqual(dep.field, "phone_expense")

    def test_value_calculates_annual_water_from_other_utilities(self):
        """Test WaterExpenseDependency.value() calculates annual water costs from otherUtilities expense."""
        Expense.objects.create(screen=self.screen, type="otherUtilities", amount=60, frequency="monthly")

        dep = spm.WaterExpenseDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 720)  # $60 * 12
        self.assertEqual(dep.field, "water_expense")


class TestOtherExpenseDependency(TestCase):
    """Tests for other expense dependency classes: SnapDependentCareDeductionDependency, HoaFeesExpenseDependency, and HomeownersInsuranceExpenseDependency."""

    def setUp(self):
        """Set up test data for other expense tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

    def test_value_calculates_annual_childcare(self):
        """Test SnapDependentCareDeductionDependency.value() calculates annual childcare costs."""
        Expense.objects.create(screen=self.screen, type="childCare", amount=400, frequency="monthly")

        dep = spm.SnapDependentCareDeductionDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 4800)  # $400 * 12
        self.assertEqual(dep.field, "childcare_expenses")

    def test_value_returns_zero_when_no_hoa_fees(self):
        """Test HoaFeesExpenseDependency.value() returns 0 when no HOA fees exist."""
        dep = spm.HoaFeesExpenseDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)
        self.assertEqual(dep.field, "homeowners_association_fees")

    def test_value_calculates_annual_hoa_fees(self):
        """Test HoaFeesExpenseDependency.value() calculates annual HOA fees."""
        Expense.objects.create(screen=self.screen, type="hoa", amount=200, frequency="monthly")

        dep = spm.HoaFeesExpenseDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 2400)  # $200 * 12

    def test_value_returns_zero_when_no_homeowners_insurance(self):
        """Test HomeownersInsuranceExpenseDependency.value() returns 0 when no homeowners insurance exists."""
        dep = spm.HomeownersInsuranceExpenseDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)
        self.assertEqual(dep.field, "homeowners_insurance")

    def test_value_calculates_annual_homeowners_insurance_cost(self):
        """Test HomeownersInsuranceExpenseDependency.value() calculates annual homeowners insurance cost."""
        Expense.objects.create(screen=self.screen, type="homeownersInsurance", amount=150, frequency="monthly")

        dep = spm.HomeownersInsuranceExpenseDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 1800)  # $150 * 12


class TestSnapEmergencyAllotmentDependency(TestCase):
    """Tests for SnapEmergencyAllotmentDependency class used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for program-specific tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

    def test_value_returns_zero(self):
        """Test value() returns 0 for emergency allotment."""
        dep = spm.SnapEmergencyAllotmentDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)
        self.assertEqual(dep.field, "snap_emergency_allotment")
