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


class TestMortgageDependency(TestCase):
    """Tests for MortgageDependency class used by IL AABD calculator."""

    def setUp(self):
        """Set up test data for mortgage dependency tests."""
        self.white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60601", county="Cook", household_size=1, completed=False
        )

    def test_value_calculates_annual_mortgage(self):
        """Test MortgageDependency.value() calculates annual mortgage expense."""
        Expense.objects.create(screen=self.screen, type="mortgage", amount=1200, frequency="monthly")

        dep = spm.MortgageDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 14400)  # $1200/month * 12
        self.assertEqual(dep.field, "mortgage_payments")

    def test_value_returns_zero_when_no_mortgage(self):
        """Test MortgageDependency.value() returns 0 when no mortgage expense exists."""
        dep = spm.MortgageDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)


class TestOtherExpenseDependency(TestCase):
    """Tests for other expense dependency classes: ChildCareDependency, HoaFeesExpenseDependency, and HomeownersInsuranceExpenseDependency."""

    def setUp(self):
        """Set up test data for other expense tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

    def test_value_calculates_annual_childcare(self):
        """Test ChildCareDependency.value() calculates annual childcare costs."""
        Expense.objects.create(screen=self.screen, type="childCare", amount=400, frequency="monthly")

        dep = spm.ChildCareDependency(self.screen, None, {})
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


class TestBroadbandCostDependency(TestCase):
    """Tests for BroadbandCostDependency class used by TxLifeline calculator."""

    def setUp(self):
        """Set up test data for broadband cost tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

    def test_value_returns_fixed_broadband_cost(self):
        """Test value() returns hardcoded broadband cost of 500."""
        dep = spm.BroadbandCostDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 500)
        self.assertEqual(dep.field, "broadband_cost")

    def test_value_returns_constant_regardless_of_household_data(self):
        """Test value() returns 500 regardless of household characteristics."""
        # Test with different household size
        self.screen.household_size = 5
        self.screen.save()

        dep = spm.BroadbandCostDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 500)


class TestSchoolMealCountableIncomeDependency(TestCase):
    """Tests for SchoolMealCountableIncomeDependency class used by WIC calculators."""

    def setUp(self):
        """Set up test data for school meal countable income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_income_from_specified_types(self):
        """Test value() calculates annual income from specific income types used for school meal eligibility."""
        # Add wages income (included in school meal countable income)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        # Add self-employment income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="selfEmployment", amount=500, frequency="monthly"
        )

        dep = spm.SchoolMealCountableIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 30000)  # ($2000 + $500) * 12
        self.assertEqual(dep.field, "school_meal_countable_income")

    def test_value_includes_social_security_income_types(self):
        """Test value() includes various social security income types in calculation."""
        # Add SS Retirement income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSRetirement", amount=1500, frequency="monthly"
        )

        # Add SS Disability income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSDisability", amount=1000, frequency="monthly"
        )

        # Add SS Survivor income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSSurvivor", amount=800, frequency="monthly"
        )

        # Add SS Dependent income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSDependent", amount=400, frequency="monthly"
        )

        dep = spm.SchoolMealCountableIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 44400)  # ($1500 + $1000 + $800 + $400) * 12

    def test_value_includes_rental_and_pension_income(self):
        """Test value() includes rental, pension, and veteran income types."""
        # Add rental income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="rental", amount=1200, frequency="monthly"
        )

        # Add pension income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="pension", amount=2000, frequency="monthly"
        )

        # Add veteran income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="veteran", amount=800, frequency="monthly"
        )

        dep = spm.SchoolMealCountableIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 48000)  # ($1200 + $2000 + $800) * 12

    def test_value_excludes_non_specified_income_types(self):
        """Test value() excludes income types not in the specified list."""
        # Add wages income (included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        # Add alimony income (NOT included in school meal countable income)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="alimony", amount=500, frequency="monthly"
        )

        # Add unemployment income (NOT included)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="unemployment", amount=300, frequency="monthly"
        )

        dep = spm.SchoolMealCountableIncomeDependency(self.screen, None, {})
        # Should only include wages, not alimony or unemployment
        self.assertEqual(dep.value(), 24000)  # $2000 * 12

    def test_value_returns_zero_when_no_countable_income(self):
        """Test value() returns 0 when household has no school meal countable income."""
        dep = spm.SchoolMealCountableIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)

    def test_value_aggregates_income_across_multiple_household_members(self):
        """Test value() aggregates countable income across all household members."""
        # Head has wages
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        # Spouse has self-employment
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=32)
        IncomeStream.objects.create(
            screen=self.screen, household_member=spouse, type="selfEmployment", amount=1500, frequency="monthly"
        )

        dep = spm.SchoolMealCountableIncomeDependency(self.screen, None, {})
        # Should include income from both members
        self.assertEqual(dep.value(), 42000)  # ($2000 + $1500) * 12

    def test_value_uses_screen_calc_gross_income_method(self):
        """Test value() uses Screen.calc_gross_income() method with correct parameters."""
        # Add multiple income types
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=3000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSRetirement", amount=1000, frequency="monthly"
        )

        dep = spm.SchoolMealCountableIncomeDependency(self.screen, None, {})

        # Verify it calls calc_gross_income with the correct income_types list
        expected_income_types = [
            "wages",
            "selfEmployment",
            "rental",
            "pension",
            "veteran",
            "sSDisability",
            "sSSurvivor",
            "sSRetirement",
            "sSDependent",
        ]

        # The dependency should have these income types
        self.assertEqual(dep.income_types, expected_income_types)

        # And the value should match what calc_gross_income returns
        self.assertEqual(dep.value(), 48000)  # ($3000 + $1000) * 12


class TestTxTanfDependencies(TestCase):
    """Tests for TX TANF income dependencies used by TxTanf calculator."""

    def setUp(self):
        """Set up test data for TX TANF dependency tests."""
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Travis", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add earned income
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1500, frequency="monthly"
        )

        # Add unearned income
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="childSupport", amount=300, frequency="monthly"
        )

        # Add cash assistance (should be excluded from unearned income)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="cashAssistance", amount=200, frequency="monthly"
        )

    def test_tx_tanf_countable_earned_income_dependency(self):
        """Test TxTanfCountableEarnedIncomeDependency.value() calculates total annual earned income."""
        dep = spm.TxTanfCountableEarnedIncomeDependency(self.screen, None, {})

        # Should calculate annual earned income
        self.assertEqual(dep.value(), 18000)  # $1500/month * 12
        self.assertEqual(dep.field, "tx_tanf_countable_earned_income")

        # Verify dependencies are set
        self.assertIn("income_type", dep.dependencies)
        self.assertIn("income_amount", dep.dependencies)
        self.assertIn("income_frequency", dep.dependencies)

    def test_tx_tanf_countable_unearned_income_dependency(self):
        """Test TxTanfCountableUnearnedIncomeDependency.value() excludes cash assistance."""
        dep = spm.TxTanfCountableUnearnedIncomeDependency(self.screen, None, {})

        # Should calculate annual unearned income, excluding cash assistance
        # $300/month * 12 = $3600 (cash assistance should be excluded)
        self.assertEqual(dep.value(), 3600)
        self.assertEqual(dep.field, "tx_tanf_countable_unearned_income")

        # Verify dependencies are set
        self.assertIn("income_type", dep.dependencies)
        self.assertIn("income_amount", dep.dependencies)
        self.assertIn("income_frequency", dep.dependencies)

    def test_tx_tanf_output_dependency(self):
        """Test TxTanf output dependency has correct field."""
        dep = spm.TxTanf(self.screen, None, {})
        self.assertEqual(dep.field, "tx_tanf")

    def test_tx_tanf_earned_income_with_no_earned_income(self):
        """Test TxTanfCountableEarnedIncomeDependency.value() returns 0 when no earned income."""
        # Remove earned income
        IncomeStream.objects.filter(screen=self.screen, type="wages").delete()

        dep = spm.TxTanfCountableEarnedIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)

    def test_tx_tanf_unearned_income_with_no_unearned_income(self):
        """Test TxTanfCountableUnearnedIncomeDependency.value() returns 0 when no unearned income."""
        # Remove all income
        IncomeStream.objects.filter(screen=self.screen).delete()

        dep = spm.TxTanfCountableUnearnedIncomeDependency(self.screen, None, {})
        self.assertEqual(dep.value(), 0)

    def test_tx_tanf_multi_member_income_aggregation(self):
        """Test TX TANF dependencies aggregate earned/unearned income across multiple household members."""
        # Remove existing income streams
        IncomeStream.objects.filter(screen=self.screen).delete()

        # Create additional household members
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=32)
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        # Add earned income streams for multiple members
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1500, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=spouse, type="selfEmployment", amount=800, frequency="monthly"
        )

        # Add unearned income streams for multiple members
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="childSupport", amount=300, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=spouse, type="sSRetirement", amount=500, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=child, type="sSSurvivor", amount=200, frequency="monthly"
        )

        # Add cash assistance (should be excluded from unearned income)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="cashAssistance", amount=150, frequency="monthly"
        )

        # Test earned income aggregation
        earned_dep = spm.TxTanfCountableEarnedIncomeDependency(self.screen, None, {})
        # $1500 (head wages) + $800 (spouse self-employment) = $2300/month * 12 = $27,600
        self.assertEqual(earned_dep.value(), 27600)

        # Test unearned income aggregation (excluding cash assistance)
        unearned_dep = spm.TxTanfCountableUnearnedIncomeDependency(self.screen, None, {})
        # $300 (head child support) + $500 (spouse SS retirement) + $200 (child SS survivor) = $1000/month * 12 = $12,000
        # Cash assistance of $150/month should be excluded
        self.assertEqual(unearned_dep.value(), 12000)
