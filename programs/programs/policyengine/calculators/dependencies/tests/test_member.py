"""
Unit tests for member-level PolicyEngine dependencies used by TxSnap and TxLifeline.

These dependencies calculate individual member values used by PolicyEngine
to determine TX SNAP and Lifeline eligibility and benefit amounts.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense, IncomeStream
from programs.programs.policyengine.calculators.dependencies import member


class TestAgeDependency(TestCase):
    """Tests for AgeDependency and IsDisabledDependency classes used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for basic member tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
        )

        self.head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=35, disabled=True
        )

    def test_value_returns_member_age(self):
        """Test AgeDependency.value() returns the household member's age."""
        dep = member.AgeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 35)
        self.assertEqual(dep.field, "age")

    def test_value_returns_true_when_member_disabled(self):
        """Test IsDisabledDependency.value() returns True when household member is disabled."""
        dep = member.IsDisabledDependency(self.screen, self.head, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "is_disabled")


class TestMemberExpenseDependency(TestCase):
    """Tests for member-level expense dependency classes: SnapChildSupportDependency, PropertyTaxExpenseDependency, and MedicalExpenseDependency."""

    def setUp(self):
        """Set up test data for expense tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_per_person(self):
        """Test SnapChildSupportDependency.value() calculates annual child support divided by household size."""
        Expense.objects.create(screen=self.screen, type="childSupport", amount=500, frequency="monthly")

        dep = member.SnapChildSupportDependency(self.screen, self.head, {})
        # $500/month * 12 / household_size(2)
        self.assertEqual(dep.value(), 3000)
        self.assertEqual(dep.field, "child_support_expense")

    def test_value_returns_zero_when_no_expense(self):
        """Test SnapChildSupportDependency.value() returns 0 when no child support expense exists."""
        dep = member.SnapChildSupportDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)

    def test_value_returns_zero_when_no_property_tax_expense(self):
        """Test PropertyTaxExpenseDependency.value() returns 0 when member has no property tax expense."""
        dep = member.PropertyTaxExpenseDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)
        self.assertEqual(dep.field, "real_estate_taxes")

    def test_value_calculates_annual_per_adult(self):
        """Test PropertyTaxExpenseDependency.value() calculates annual property tax divided by number of adults."""
        Expense.objects.create(screen=self.screen, type="propertyTax", amount=300, frequency="monthly")

        # Add second adult to test per-adult division
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)

        dep = member.PropertyTaxExpenseDependency(self.screen, self.head, {})
        # $300/month * 12 / 2 adults
        self.assertEqual(dep.value(), 1800)

    def test_value_calculates_annual_for_elderly_member(self):
        """Test MedicalExpenseDependency.value() calculates annual medical expenses for elderly member."""
        elderly_member = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=65)

        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")

        dep = member.MedicalExpenseDependency(self.screen, elderly_member, {})
        # $200/month * 12 / 1 elderly or disabled member
        self.assertEqual(dep.value(), 2400)
        self.assertEqual(dep.field, "medical_out_of_pocket_expenses")

    def test_value_returns_zero_for_non_elderly_non_disabled(self):
        """Test MedicalExpenseDependency.value() returns 0 for non-elderly, non-disabled member."""
        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")

        dep = member.MedicalExpenseDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestSnapIneligibleStudentDependency(TestCase):
    """Tests for SnapIneligibleStudentDependency class used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for student eligibility tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        # Need head of household for relationship_map
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=45)

    def test_value_evaluates_adult_student(self):
        """Test value() evaluates adult student eligibility based on helper logic."""
        student = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=20, student=True)

        dep = member.SnapIneligibleStudentDependency(self.screen, student, {})
        # Result depends on snap_ineligible_student helper logic
        self.assertIsNotNone(dep.value())
        self.assertEqual(dep.field, "is_snap_ineligible_student")

    def test_value_returns_false_for_young_student(self):
        """Test value() returns False for student under 18."""
        young_student = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=16, student=True)

        dep = member.SnapIneligibleStudentDependency(self.screen, young_student, {})
        # Students under 18 are eligible
        self.assertFalse(dep.value())

    def test_value_returns_false_for_disabled_student(self):
        """Test value() returns False for disabled student."""
        disabled_student = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=20, student=True, disabled=True
        )

        dep = member.SnapIneligibleStudentDependency(self.screen, disabled_student, {})
        # Disabled students are eligible
        self.assertFalse(dep.value())


class TestEmploymentIncomeDependency(TestCase):
    """Tests for EmploymentIncomeDependency class used by TxLifeline calculator."""

    def setUp(self):
        """Set up test data for employment income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_wages_income(self):
        """Test value() calculates annual employment income from wages."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=3000, frequency="monthly"
        )

        dep = member.EmploymentIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 36000)  # $3000/month * 12
        self.assertEqual(dep.field, "employment_income")

    def test_value_returns_zero_when_no_employment_income(self):
        """Test value() returns 0 when member has no employment income."""
        dep = member.EmploymentIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)

    def test_value_only_includes_wages_income_type(self):
        """Test value() only includes wages income type, not other types."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="selfEmployment", amount=1000, frequency="monthly"
        )

        dep = member.EmploymentIncomeDependency(self.screen, self.head, {})
        # Should only include wages, not self-employment
        self.assertEqual(dep.value(), 24000)


class TestSelfEmploymentIncomeDependency(TestCase):
    """Tests for SelfEmploymentIncomeDependency class used by TxLifeline calculator."""

    def setUp(self):
        """Set up test data for self-employment income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_self_employment_income(self):
        """Test value() calculates annual self-employment income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="selfEmployment", amount=4000, frequency="monthly"
        )

        dep = member.SelfEmploymentIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 48000)  # $4000/month * 12
        self.assertEqual(dep.field, "self_employment_income")

    def test_value_returns_zero_when_no_self_employment_income(self):
        """Test value() returns 0 when member has no self-employment income."""
        dep = member.SelfEmploymentIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestRentalIncomeDependency(TestCase):
    """Tests for RentalIncomeDependency class used by TxLifeline calculator."""

    def setUp(self):
        """Set up test data for rental income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_rental_income(self):
        """Test value() calculates annual rental income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="rental", amount=1500, frequency="monthly"
        )

        dep = member.RentalIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 18000)  # $1500/month * 12
        self.assertEqual(dep.field, "rental_income")

    def test_value_returns_zero_when_no_rental_income(self):
        """Test value() returns 0 when member has no rental income."""
        dep = member.RentalIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestPensionIncomeDependency(TestCase):
    """Tests for PensionIncomeDependency class used by TxLifeline calculator."""

    def setUp(self):
        """Set up test data for pension income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=65)

    def test_value_calculates_annual_pension_income(self):
        """Test value() calculates annual pension income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="pension", amount=2500, frequency="monthly"
        )

        dep = member.PensionIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 30000)  # $2500/month * 12
        self.assertEqual(dep.field, "taxable_pension_income")

    def test_value_includes_veteran_income(self):
        """Test value() includes veteran income as part of pension income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="veteran", amount=1000, frequency="monthly"
        )

        dep = member.PensionIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 12000)  # $1000/month * 12

    def test_value_combines_pension_and_veteran_income(self):
        """Test value() combines both pension and veteran income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="pension", amount=2000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="veteran", amount=500, frequency="monthly"
        )

        dep = member.PensionIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 30000)  # ($2000 + $500) * 12

    def test_value_returns_zero_when_no_pension_income(self):
        """Test value() returns 0 when member has no pension or veteran income."""
        dep = member.PensionIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestSocialSecurityIncomeDependency(TestCase):
    """Tests for SocialSecurityIncomeDependency class used by TxLifeline calculator."""

    def setUp(self):
        """Set up test data for social security income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)

    def test_value_calculates_annual_ss_retirement_income(self):
        """Test value() calculates annual social security retirement income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSRetirement", amount=1800, frequency="monthly"
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 21600)  # $1800/month * 12
        self.assertEqual(dep.field, "social_security")

    def test_value_calculates_annual_ss_disability_income(self):
        """Test value() calculates annual social security disability income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSDisability", amount=1500, frequency="monthly"
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 18000)  # $1500/month * 12

    def test_value_calculates_annual_ss_survivor_income(self):
        """Test value() calculates annual social security survivor income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSSurvivor", amount=1200, frequency="monthly"
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 14400)  # $1200/month * 12

    def test_value_calculates_annual_ss_dependent_income(self):
        """Test value() calculates annual social security dependent income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSDependent", amount=800, frequency="monthly"
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 9600)  # $800/month * 12

    def test_value_combines_all_social_security_types(self):
        """Test value() combines all types of social security income."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSRetirement", amount=1000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSDependent", amount=300, frequency="monthly"
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 15600)  # ($1000 + $300) * 12

    def test_value_returns_zero_when_no_social_security_income(self):
        """Test value() returns 0 when member has no social security income."""
        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)
