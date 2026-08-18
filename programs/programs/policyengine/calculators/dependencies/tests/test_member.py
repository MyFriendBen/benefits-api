"""
Unit tests for member-level PolicyEngine dependencies used by TxSnap and TxLifeline.

These dependencies calculate individual member values used by PolicyEngine
to determine TX SNAP and Lifeline eligibility and benefit amounts.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense, IncomeStream
from programs.models import Program
from screener.tests.helpers import seed_program
from screener.serializers import _write_current_benefits
from programs.programs.policyengine.calculators.dependencies import member


class TestAgeDependency(TestCase):
    """Tests for AgeDependency and IsDisabledDependency classes used by TxSnap calculator."""

    def setUp(self):
        """Set up test data for basic member tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
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


class TestMeetsSsiDisabilityCriteriaDependency(TestCase):
    """Tests for MeetsSsiDisabilityCriteriaDependency, required by PolicyEngine frontier
    to classify a person as SSI-disabled (MFB-1102)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def _member(self, **kwargs):
        return HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40, **kwargs)

    def test_field_name(self):
        dep = member.MeetsSsiDisabilityCriteriaDependency(self.screen, self._member(), {})
        self.assertEqual(dep.field, "meets_ssi_disability_criteria")

    def test_true_when_disabled(self):
        dep = member.MeetsSsiDisabilityCriteriaDependency(self.screen, self._member(disabled=True), {})
        self.assertTrue(dep.value())

    def test_true_when_long_term_disability(self):
        dep = member.MeetsSsiDisabilityCriteriaDependency(self.screen, self._member(long_term_disability=True), {})
        self.assertTrue(dep.value())

    def test_true_when_visually_impaired(self):
        dep = member.MeetsSsiDisabilityCriteriaDependency(self.screen, self._member(visually_impaired=True), {})
        self.assertTrue(dep.value())

    def test_falsy_when_none_apply(self):
        dep = member.MeetsSsiDisabilityCriteriaDependency(self.screen, self._member(), {})
        self.assertFalse(dep.value())


class TestIsBlindDependency(TestCase):
    """Tests for IsBlindDependency, which maps the screener's visually_impaired flag
    to PolicyEngine's is_blind input (relied on by KsKanCare / KS Medicaid, MFB-1054)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def _member(self, **kwargs):
        return HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=50, **kwargs)

    def test_field_name(self):
        dep = member.IsBlindDependency(self.screen, self._member(), {})
        self.assertEqual(dep.field, "is_blind")

    def test_true_when_visually_impaired(self):
        dep = member.IsBlindDependency(self.screen, self._member(visually_impaired=True), {})
        self.assertTrue(dep.value())

    def test_false_when_not_visually_impaired(self):
        dep = member.IsBlindDependency(self.screen, self._member(visually_impaired=False), {})
        self.assertFalse(dep.value())


class TestMemberExpenseDependency(TestCase):
    """Tests for member-level expense dependency classes: SnapChildSupportDependency, PropertyTaxExpenseDependency, and MedicalExpenseDependency."""

    def setUp(self):
        """Set up test data for expense tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
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

    def test_value_head_gets_full_annual_medical_amount(self):
        """Test MedicalExpenseDependency.value() assigns full medical expenses to head."""
        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")

        dep = member.MedicalExpenseDependency(self.screen, self.head, {})
        # $200/month * 12
        self.assertEqual(dep.value(), 2400)
        self.assertEqual(dep.field, "other_medical_expenses")

    def test_value_non_head_returns_zero(self):
        """Test MedicalExpenseDependency.value() returns 0 for non-head members."""
        elderly_member = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=65)
        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")

        dep = member.MedicalExpenseDependency(self.screen, elderly_member, {})
        self.assertEqual(dep.value(), 0)


class TestHeatingExpensePersonDependency(TestCase):
    """Tests for HeatingExpensePersonDependency (used by MaHeap and other LIHEAP calculators)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="02108",
            county="Suffolk",
            household_size=2,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)
        self.spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=33)

    def test_field_name(self):
        dep = member.HeatingExpensePersonDependency(self.screen, self.head, {})
        self.assertEqual(dep.field, "heating_expense_person")

    def test_head_gets_full_annual_heating_and_cooling_amount(self):
        Expense.objects.create(screen=self.screen, type="heating", amount=100, frequency="monthly")
        Expense.objects.create(screen=self.screen, type="cooling", amount=50, frequency="monthly")

        dep = member.HeatingExpensePersonDependency(self.screen, self.head, {})
        # ($100 + $50) * 12
        self.assertEqual(dep.value(), 1800)

    def test_non_head_returns_zero(self):
        Expense.objects.create(screen=self.screen, type="heating", amount=100, frequency="monthly")

        dep = member.HeatingExpensePersonDependency(self.screen, self.spouse, {})
        self.assertEqual(dep.value(), 0)

    def test_head_returns_zero_when_no_expense(self):
        dep = member.HeatingExpensePersonDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestEmploymentIncomeDependency(TestCase):
    """Tests for EmploymentIncomeDependency class used by TxLifeline calculator."""

    def setUp(self):
        """Set up test data for employment income tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_wages_income(self):
        """Test value() calculates annual employment income from wages."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=3000,
            frequency="monthly",
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
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="selfEmployment",
            amount=1000,
            frequency="monthly",
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
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_self_employment_income(self):
        """Test value() calculates annual self-employment income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="selfEmployment",
            amount=4000,
            frequency="monthly",
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
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_rental_income(self):
        """Test value() calculates annual rental income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="rental",
            amount=1500,
            frequency="monthly",
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
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=65)

    def test_value_calculates_annual_pension_income(self):
        """Test value() calculates annual pension income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="pension",
            amount=2500,
            frequency="monthly",
        )

        dep = member.PensionIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 30000)  # $2500/month * 12
        self.assertEqual(dep.field, "taxable_pension_income")

    def test_value_includes_veteran_income(self):
        """Test value() includes veteran income as part of pension income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="veteran",
            amount=1000,
            frequency="monthly",
        )

        dep = member.PensionIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 12000)  # $1000/month * 12

    def test_value_combines_pension_and_veteran_income(self):
        """Test value() combines both pension and veteran income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="pension",
            amount=2000,
            frequency="monthly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="veteran",
            amount=500,
            frequency="monthly",
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
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)

    def test_value_calculates_annual_ss_retirement_income(self):
        """Test value() calculates annual social security retirement income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSRetirement",
            amount=1800,
            frequency="monthly",
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 21600)  # $1800/month * 12
        self.assertEqual(dep.field, "social_security")

    def test_value_calculates_annual_ss_disability_income(self):
        """Test value() calculates annual social security disability income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSDisability",
            amount=1500,
            frequency="monthly",
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 18000)  # $1500/month * 12

    def test_value_calculates_annual_ss_survivor_income(self):
        """Test value() calculates annual social security survivor income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSSurvivor",
            amount=1200,
            frequency="monthly",
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 14400)  # $1200/month * 12

    def test_value_calculates_annual_ss_dependent_income(self):
        """Test value() calculates annual social security dependent income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSDependent",
            amount=800,
            frequency="monthly",
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 9600)  # $800/month * 12

    def test_value_combines_all_social_security_types(self):
        """Test value() combines all types of social security income."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSRetirement",
            amount=1000,
            frequency="monthly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="sSDependent",
            amount=300,
            frequency="monthly",
        )

        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 15600)  # ($1000 + $300) * 12

    def test_value_returns_zero_when_no_social_security_income(self):
        """Test value() returns 0 when member has no social security income."""
        dep = member.SocialSecurityIncomeDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestPregnancyDependency(TestCase):
    """Tests for PregnancyDependency class used by WIC calculators."""

    def setUp(self):
        """Set up test data for pregnancy tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

        self.pregnant_member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, pregnant=True
        )

        self.non_pregnant_member = HouseholdMember.objects.create(
            screen=self.screen, relationship="spouse", age=28, pregnant=False
        )

    def test_value_returns_true_when_pregnant(self):
        """Test PregnancyDependency.value() returns True when member is pregnant."""
        dep = member.PregnancyDependency(self.screen, self.pregnant_member, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "is_pregnant")

    def test_value_returns_false_when_not_pregnant(self):
        """Test PregnancyDependency.value() returns False when member is not pregnant."""
        dep = member.PregnancyDependency(self.screen, self.non_pregnant_member, {})
        self.assertFalse(dep.value())

    def test_value_returns_false_when_pregnant_is_none(self):
        """Test PregnancyDependency.value() returns False when pregnant field is None."""
        member_none = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10, pregnant=None)

        dep = member.PregnancyDependency(self.screen, member_none, {})
        self.assertFalse(dep.value())


class TestExpectedChildrenPregnancyDependency(TestCase):
    """Tests for ExpectedChildrenPregnancyDependency class used by WIC calculators."""

    def setUp(self):
        """Set up test data for expected children pregnancy tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

        self.pregnant_member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, pregnant=True
        )

        self.non_pregnant_member = HouseholdMember.objects.create(
            screen=self.screen, relationship="spouse", age=28, pregnant=False
        )

    def test_value_returns_one_when_pregnant(self):
        """Test ExpectedChildrenPregnancyDependency.value() returns 1 when member is pregnant."""
        dep = member.ExpectedChildrenPregnancyDependency(self.screen, self.pregnant_member, {})
        self.assertEqual(dep.value(), 1)
        self.assertEqual(dep.field, "current_pregnancies")

    def test_value_returns_zero_when_not_pregnant(self):
        """Test ExpectedChildrenPregnancyDependency.value() returns 0 when member is not pregnant."""
        dep = member.ExpectedChildrenPregnancyDependency(self.screen, self.non_pregnant_member, {})
        self.assertEqual(dep.value(), 0)


class TestTaxUnitHeadDependency(TestCase):
    """Tests for TaxUnitHeadDependency class used by tax credit calculators."""

    def setUp(self):
        """Set up test data for tax unit head tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)
        self.spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=33)

    def test_value_returns_true_for_head_of_household(self):
        """Test TaxUnitHeadDependency.value() returns True for head of household."""
        dep = member.TaxUnitHeadDependency(self.screen, self.head, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "is_tax_unit_head")

    def test_value_returns_false_for_spouse(self):
        """Test TaxUnitHeadDependency.value() returns False for spouse."""
        dep = member.TaxUnitHeadDependency(self.screen, self.spouse, {})
        self.assertFalse(dep.value())


class TestTaxUnitSpouseDependency(TestCase):
    """Tests for TaxUnitSpouseDependency class used by tax credit calculators."""

    def setUp(self):
        """Set up test data for tax unit spouse tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)
        self.spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=33)

    def test_value_returns_true_for_spouse(self):
        """Test TaxUnitSpouseDependency.value() returns True for spouse."""
        dep = member.TaxUnitSpouseDependency(self.screen, self.spouse, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "is_tax_unit_spouse")

    def test_value_returns_false_for_head_of_household(self):
        """Test TaxUnitSpouseDependency.value() returns False for head of household."""
        dep = member.TaxUnitSpouseDependency(self.screen, self.head, {})
        self.assertFalse(dep.value())


class TestTaxUnitDependentDependency(TestCase):
    """Tests for TaxUnitDependentDependency class used by tax credit calculators."""

    def setUp(self):
        """Set up test data for tax unit dependent tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=3,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)
        self.child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

    def test_value_returns_true_for_child(self):
        """Test TaxUnitDependentDependency.value() returns True for child."""
        dep = member.TaxUnitDependentDependency(self.screen, self.child, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "is_tax_unit_dependent")

    def test_value_returns_false_for_head_of_household(self):
        """Test TaxUnitDependentDependency.value() returns False for head of household."""
        dep = member.TaxUnitDependentDependency(self.screen, self.head, {})
        self.assertFalse(dep.value())


class TestHeadStartDependency(TestCase):
    """Tests for HeadStart dependency class."""

    def setUp(self):
        """Set up test data for Head Start dependency tests."""
        self.white_label = WhiteLabel.objects.create(name="Massachusetts", code="ma", state_code="MA")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="02101",
            county="Boston",
            household_size=2,
            completed=False,
        )

        self.parent = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=30, has_income=True
        )

        self.child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4, has_income=False)

    def test_head_start_dependency_exists(self):
        """Test that HeadStart dependency class exists and has correct field."""
        self.assertTrue(hasattr(member, "HeadStart"))
        self.assertEqual(member.HeadStart.field, "head_start")

    def test_head_start_is_member_dependency(self):
        """Test that HeadStart inherits from Member dependency base class."""
        from programs.programs.policyengine.calculators.dependencies.base import Member

        self.assertTrue(issubclass(member.HeadStart, Member))

    def test_head_start_can_be_instantiated(self):
        """Test that HeadStart can be instantiated with screen and member."""
        dep = member.HeadStart(self.screen, self.child, {})
        self.assertIsNotNone(dep)
        self.assertEqual(dep.screen, self.screen)
        self.assertEqual(dep.member, self.child)

    def test_head_start_has_correct_field_name(self):
        """Test that HeadStart has the correct PolicyEngine field name for benefit value."""
        dep = member.HeadStart(self.screen, self.child, {})
        self.assertEqual(dep.field, "head_start")

    def test_head_start_has_correct_unit(self):
        """Test that HeadStart dependency has the correct unit field for PolicyEngine."""
        dep = member.HeadStart(self.screen, self.child, {})

        # Should be member-level (people) dependency
        self.assertEqual(dep.unit, "people")

    def test_head_start_works_with_different_ages(self):
        """Test that HeadStart can be instantiated with children of different ages."""
        # Test with age 3 (minimum eligible age for Head Start)
        child_3 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)
        dep_3 = member.HeadStart(self.screen, child_3, {})
        self.assertEqual(dep_3.member.age, 3)
        self.assertEqual(dep_3.field, "head_start")

        # Test with age 5 (maximum eligible age for Head Start)
        child_5 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)
        dep_5 = member.HeadStart(self.screen, child_5, {})
        self.assertEqual(dep_5.member.age, 5)

        # Test with age outside range (should still create dependency, PE determines eligibility)
        child_6 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=6)
        dep_6 = member.HeadStart(self.screen, child_6, {})
        self.assertEqual(dep_6.member.age, 6)

    def test_head_start_works_with_different_members(self):
        """Test that HeadStart value dependency can be created for different household members."""
        # Test with child (typical case)
        child_dep = member.HeadStart(self.screen, self.child, {})
        self.assertEqual(child_dep.member, self.child)
        self.assertEqual(child_dep.field, "head_start")

        # Test with parent (would not be eligible, but dependency should still work)
        parent_dep = member.HeadStart(self.screen, self.parent, {})
        self.assertEqual(parent_dep.member, self.parent)
        self.assertEqual(parent_dep.field, "head_start")

    def test_head_start_works_with_relationship_map(self):
        """Test that HeadStart dependency works with relationship_map parameter."""
        relationship_map = {self.parent.id: self.child.id}

        dep = member.HeadStart(self.screen, self.child, relationship_map)

        self.assertIsNotNone(dep)
        self.assertEqual(dep.member, self.child)
        self.assertEqual(dep.field, "head_start")


class TestPropertyTaxExpenseDependencyTaxFiling(TestCase):
    """Tests for PropertyTaxExpenseDependency head/spouse splitting logic for tax filing."""

    def setUp(self):
        """Set up test data for property tax dependency tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test_pt", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=45)

    def test_value_returns_full_amount_for_single_head(self):
        """Test PropertyTaxExpenseDependency.value() returns full amount for single head of household."""
        Expense.objects.create(screen=self.screen, type="propertyTax", amount=300, frequency="monthly")

        dep = member.PropertyTaxExpenseDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 3600)  # $300/month * 12

    def test_value_splits_between_head_and_spouse(self):
        """Test PropertyTaxExpenseDependency.value() splits evenly between head and spouse when married."""
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=42)
        Expense.objects.create(screen=self.screen, type="propertyTax", amount=400, frequency="monthly")

        head_dep = member.PropertyTaxExpenseDependency(self.screen, self.head, {})
        spouse_dep = member.PropertyTaxExpenseDependency(self.screen, spouse, {})

        # $400/month * 12 / 2 = $2400 each
        self.assertEqual(head_dep.value(), 2400)
        self.assertEqual(spouse_dep.value(), 2400)

    def test_value_returns_zero_for_non_head_non_spouse(self):
        """Test PropertyTaxExpenseDependency.value() returns 0 for children and other members."""
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=16)
        parent = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=75)
        Expense.objects.create(screen=self.screen, type="propertyTax", amount=500, frequency="monthly")

        child_dep = member.PropertyTaxExpenseDependency(self.screen, child, {})
        parent_dep = member.PropertyTaxExpenseDependency(self.screen, parent, {})

        self.assertEqual(child_dep.value(), 0)
        self.assertEqual(parent_dep.value(), 0)

    def test_value_full_amount_to_head_when_no_spouse(self):
        """Test PropertyTaxExpenseDependency.value() assigns full amount to head when no spouse."""
        # Add adult child but no spouse
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=25)
        Expense.objects.create(screen=self.screen, type="propertyTax", amount=600, frequency="monthly")

        head_dep = member.PropertyTaxExpenseDependency(self.screen, self.head, {})
        child_dep = member.PropertyTaxExpenseDependency(self.screen, adult_child, {})

        # Full amount to head, nothing to adult child
        self.assertEqual(head_dep.value(), 7200)  # $600 * 12
        self.assertEqual(child_dep.value(), 0)

    def test_value_returns_zero_when_no_property_tax(self):
        """Test PropertyTaxExpenseDependency.value() returns 0 when no property tax expense exists."""
        dep = member.PropertyTaxExpenseDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestRentDependency(TestCase):
    """Tests for RentDependency class used for tax calculations."""

    def setUp(self):
        """Set up test data for rent dependency tests."""
        self.white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="60601",
            county="Cook",
            household_size=1,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=70)

    def test_value_calculates_annual_rent_for_single_head(self):
        """Test RentDependency.value() returns full annual rent for single head of household."""
        Expense.objects.create(screen=self.screen, type="rent", amount=500, frequency="monthly")

        dep = member.RentDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 6000)  # $500/month * 12
        self.assertEqual(dep.field, "rent")

    def test_value_returns_zero_when_no_rent(self):
        """Test RentDependency.value() returns 0 when no rent expense exists."""
        dep = member.RentDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)

    def test_value_splits_rent_between_head_and_spouse(self):
        """Test RentDependency.value() splits rent evenly between head and spouse when married."""
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=68)
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")

        head_dep = member.RentDependency(self.screen, self.head, {})
        spouse_dep = member.RentDependency(self.screen, spouse, {})

        # $1000/month * 12 / 2 = $6000 each
        self.assertEqual(head_dep.value(), 6000)
        self.assertEqual(spouse_dep.value(), 6000)

    def test_value_returns_zero_for_non_head_non_spouse(self):
        """Test RentDependency.value() returns 0 for children and other household members."""
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=16)
        parent = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=75)
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")

        child_dep = member.RentDependency(self.screen, child, {})
        parent_dep = member.RentDependency(self.screen, parent, {})

        self.assertEqual(child_dep.value(), 0)
        self.assertEqual(parent_dep.value(), 0)

    def test_value_full_amount_to_head_when_no_spouse(self):
        """Test RentDependency.value() assigns full rent to head when there's no spouse."""
        # Add a child but no spouse
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
        Expense.objects.create(screen=self.screen, type="rent", amount=800, frequency="monthly")

        head_dep = member.RentDependency(self.screen, self.head, {})
        child_dep = member.RentDependency(self.screen, child, {})

        # Full amount to head, nothing to child
        self.assertEqual(head_dep.value(), 9600)  # $800 * 12
        self.assertEqual(child_dep.value(), 0)


class TestEarlyHeadStartDependency(TestCase):
    """Tests for EarlyHeadStart dependency class."""

    def setUp(self):
        """Set up test data for Early Head Start dependency tests."""
        self.white_label = WhiteLabel.objects.create(name="Massachusetts", code="ma_ehs", state_code="MA")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="02101",
            county="Boston",
            household_size=2,
            completed=False,
        )

        self.parent = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=30, has_income=True
        )

        self.child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=1, has_income=False)

    def test_early_head_start_dependency_exists(self):
        """Test that EarlyHeadStart dependency class exists and has correct field."""
        self.assertTrue(hasattr(member, "EarlyHeadStart"))
        self.assertEqual(member.EarlyHeadStart.field, "early_head_start")

    def test_early_head_start_is_member_dependency(self):
        """Test that EarlyHeadStart inherits from Member dependency base class."""
        from programs.programs.policyengine.calculators.dependencies.base import Member

        self.assertTrue(issubclass(member.EarlyHeadStart, Member))

    def test_early_head_start_can_be_instantiated(self):
        """Test that EarlyHeadStart can be instantiated with screen and member."""
        dep = member.EarlyHeadStart(self.screen, self.child, {})

        self.assertIsNotNone(dep)
        self.assertEqual(dep.member, self.child)

    def test_early_head_start_has_correct_field_name(self):
        """Test that EarlyHeadStart has the correct PolicyEngine field name for benefit value."""
        dep = member.EarlyHeadStart(self.screen, self.child, {})
        self.assertEqual(dep.field, "early_head_start")

    def test_early_head_start_works_with_different_ages(self):
        """Test that EarlyHeadStart can be instantiated with children of different ages."""
        # Test with infant (0 years)
        infant = HouseholdMember.objects.create(screen=self.screen, age=0, relationship="child")
        dep_infant = member.EarlyHeadStart(self.screen, infant, {})
        self.assertEqual(dep_infant.field, "early_head_start")

        # Test with 2 year old
        child_2 = HouseholdMember.objects.create(screen=self.screen, age=2, relationship="child")
        dep_2 = member.EarlyHeadStart(self.screen, child_2, {})
        self.assertEqual(dep_2.field, "early_head_start")

    def test_early_head_start_works_with_relationship_map(self):
        """Test that EarlyHeadStart dependency works with relationship_map parameter."""
        relationship_map = {self.parent.id: self.child.id}

        dep = member.EarlyHeadStart(self.screen, self.child, relationship_map)

        self.assertIsNotNone(dep)
        self.assertEqual(dep.member, self.child)
        self.assertEqual(dep.field, "early_head_start")


class TestCareWorkerEligibleDependency(TestCase):
    """Tests for CareWorkerEligibleDependency class used by Colorado Care Worker Tax Credit calculator."""

    def setUp(self):
        """Set up test data for care worker eligibility tests."""
        self.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="80202",
            county="Denver",
            household_size=2,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=35, is_care_worker=True
        )
        self.spouse = HouseholdMember.objects.create(
            screen=self.screen, relationship="spouse", age=33, is_care_worker=False
        )

    def test_value_returns_true_when_is_care_worker(self):
        """Test CareWorkerEligibleDependency.value() returns True when member is a care worker."""
        dep = member.CareWorkerEligibleDependency(self.screen, self.head, {})
        self.assertTrue(dep.value())
        self.assertEqual(dep.field, "co_care_worker_credit_eligible_care_worker")

    def test_value_returns_false_when_not_care_worker(self):
        """Test CareWorkerEligibleDependency.value() returns False when member is not a care worker."""
        dep = member.CareWorkerEligibleDependency(self.screen, self.spouse, {})
        self.assertFalse(dep.value())

    def test_value_returns_false_when_is_care_worker_is_none(self):
        """Test CareWorkerEligibleDependency.value() returns False when is_care_worker field is None."""
        member_none = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=10, is_care_worker=None
        )

        dep = member.CareWorkerEligibleDependency(self.screen, member_none, {})
        self.assertFalse(dep.value())

    def test_dependencies_includes_is_care_worker(self):
        """Test CareWorkerEligibleDependency.dependencies includes is_care_worker field."""
        dep = member.CareWorkerEligibleDependency(self.screen, self.head, {})
        self.assertIn("is_care_worker", dep.dependencies)


class TestChildcareAttendingDaysPerMonthDependency(TestCase):
    """Tests for ChildcareAttendingDaysPerMonthDependency class used by childcare subsidy calculators."""

    def setUp(self):
        """Set up test data for childcare attending days tests."""
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis",
            household_size=2,
            completed=False,
        )

        self.parent = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)
        self.child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)

    def test_value_returns_10_days(self):
        """Test ChildcareAttendingDaysPerMonthDependency.value() returns 10 days per month."""
        dep = member.ChildcareAttendingDaysPerMonthDependency(self.screen, self.child, {})
        self.assertEqual(dep.value(), 10)

    def test_field_name_is_correct(self):
        """Test that field name matches PolicyEngine's childcare_attending_days_per_month variable."""
        dep = member.ChildcareAttendingDaysPerMonthDependency(self.screen, self.child, {})
        self.assertEqual(dep.field, "childcare_attending_days_per_month")

    def test_is_member_level_dependency(self):
        """Test that ChildcareAttendingDaysPerMonthDependency is a member-level (per-child) dependency."""
        from programs.programs.policyengine.calculators.dependencies.base import Member

        self.assertTrue(issubclass(member.ChildcareAttendingDaysPerMonthDependency, Member))

    def test_value_same_for_all_children(self):
        """Test that all children get the same value of 10 days."""
        child2 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)

        dep1 = member.ChildcareAttendingDaysPerMonthDependency(self.screen, self.child, {})
        dep2 = member.ChildcareAttendingDaysPerMonthDependency(self.screen, child2, {})

        self.assertEqual(dep1.value(), 10)
        self.assertEqual(dep2.value(), 10)

    def test_works_with_relationship_map(self):
        """Test that dependency works correctly with relationship_map parameter."""
        relationship_map = {self.parent.id: self.child.id}

        dep = member.ChildcareAttendingDaysPerMonthDependency(self.screen, self.child, relationship_map)

        self.assertIsNotNone(dep)
        self.assertEqual(dep.value(), 10)

    def test_has_correct_unit(self):
        """Test that dependency has correct unit (people) for PolicyEngine."""
        dep = member.ChildcareAttendingDaysPerMonthDependency(self.screen, self.child, {})
        self.assertEqual(dep.unit, "people")


class TestIsMedicareEligibleDependency(TestCase):
    """Tests for IsMedicareEligibleDependency class used by IL MSP calculator.

    This dependency overrides PolicyEngine's is_medicare_eligible calculation
    when we know the user has Medicare selected, fixing the disabled under-65
    pathway issue (Test 13 in IL MSP QA).
    """

    def setUp(self):
        """Set up test data for Medicare eligibility tests."""
        from screener.models import Insurance

        self.white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="60601",
            county="Cook",
            household_size=1,
            completed=False,
        )

        # Member with Medicare
        self.member_with_medicare = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=55, disabled=True
        )
        Insurance.objects.create(household_member=self.member_with_medicare, medicare=True, none=False)

        # Member without Medicare (no insurance record)
        self.member_without_insurance = HouseholdMember.objects.create(
            screen=self.screen, relationship="spouse", age=68
        )

    def test_value_returns_true_when_member_has_medicare(self):
        """Test IsMedicareEligibleDependency.value() returns True when member has Medicare selected."""
        dep = member.IsMedicareEligibleDependency(self.screen, self.member_with_medicare, {})
        self.assertTrue(dep.value())

    def test_value_returns_none_when_member_has_no_insurance_record(self):
        """Test IsMedicareEligibleDependency.value() returns None when member has no insurance record."""
        dep = member.IsMedicareEligibleDependency(self.screen, self.member_without_insurance, {})
        self.assertIsNone(dep.value())

    def test_value_returns_none_when_member_has_other_insurance_only(self):
        """Test IsMedicareEligibleDependency.value() returns None when member has non-Medicare insurance."""
        from screener.models import Insurance

        member_with_medicaid = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=30)
        Insurance.objects.create(household_member=member_with_medicaid, medicaid=True, medicare=False, none=False)

        dep = member.IsMedicareEligibleDependency(self.screen, member_with_medicaid, {})
        self.assertIsNone(dep.value())

    def test_field_name_is_correct(self):
        """Test that field name matches PolicyEngine's is_medicare_eligible variable."""
        dep = member.IsMedicareEligibleDependency(self.screen, self.member_with_medicare, {})
        self.assertEqual(dep.field, "is_medicare_eligible")

    def test_is_member_level_dependency(self):
        """Test that IsMedicareEligibleDependency is a member-level dependency."""
        from programs.programs.policyengine.calculators.dependencies.base import Member

        self.assertTrue(issubclass(member.IsMedicareEligibleDependency, Member))

    def test_disabled_under_65_with_medicare_returns_true(self):
        """Test that disabled individual under 65 with Medicare returns True.

        This is the key fix for Test 13: disabled 55yo with Medicare should
        be eligible for MSP. Previously, PolicyEngine would calculate
        is_medicare_eligible=False because we don't send
        months_receiving_social_security_disability.
        """
        dep = member.IsMedicareEligibleDependency(self.screen, self.member_with_medicare, {})
        # Member is 55, disabled, and has Medicare - should return True
        self.assertEqual(self.member_with_medicare.age, 55)
        self.assertTrue(self.member_with_medicare.disabled)
        self.assertTrue(dep.value())


class TestIsMedicaidEligibleDependency(TestCase):
    """Tests for IsMedicaidEligibleDependency class used by IL MSP calculator.

    This dependency overrides PolicyEngine's is_medicaid_eligible calculation
    when we know the user has Medicaid selected, enforcing the QI exclusion:
    QI is only available to Medicare beneficiaries who are NOT eligible for Medicaid.
    """

    def setUp(self):
        """Set up test data for Medicaid eligibility tests."""
        from screener.models import Insurance

        self.white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="60601",
            county="Cook",
            household_size=1,
            completed=False,
        )

        # Member with Medicaid
        self.member_with_medicaid = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=68
        )
        Insurance.objects.create(household_member=self.member_with_medicaid, medicaid=True, medicare=True, none=False)

        # Member without any insurance record
        self.member_without_insurance = HouseholdMember.objects.create(
            screen=self.screen, relationship="spouse", age=70
        )

    def test_value_returns_true_when_member_has_medicaid(self):
        """Test IsMedicaidEligibleDependency.value() returns True when member has Medicaid selected."""
        dep = member.IsMedicaidEligibleDependency(self.screen, self.member_with_medicaid, {})
        self.assertTrue(dep.value())

    def test_value_returns_none_when_member_has_no_insurance_record(self):
        """Test IsMedicaidEligibleDependency.value() returns None when member has no insurance record."""
        dep = member.IsMedicaidEligibleDependency(self.screen, self.member_without_insurance, {})
        self.assertIsNone(dep.value())

    def test_value_returns_none_when_member_has_other_insurance_only(self):
        """Test IsMedicaidEligibleDependency.value() returns None when member has Medicare but not Medicaid."""
        from screener.models import Insurance

        member_with_medicare_only = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=66)
        Insurance.objects.create(household_member=member_with_medicare_only, medicare=True, medicaid=False, none=False)

        dep = member.IsMedicaidEligibleDependency(self.screen, member_with_medicare_only, {})
        self.assertIsNone(dep.value())

    def test_field_name_is_correct(self):
        """Test that field name matches PolicyEngine's is_medicaid_eligible variable."""
        dep = member.IsMedicaidEligibleDependency(self.screen, self.member_with_medicaid, {})
        self.assertEqual(dep.field, "is_medicaid_eligible")

    def test_is_member_level_dependency(self):
        """Test that IsMedicaidEligibleDependency is a member-level dependency."""
        from programs.programs.policyengine.calculators.dependencies.base import Member

        self.assertTrue(issubclass(member.IsMedicaidEligibleDependency, Member))

    def test_member_with_medicaid_is_excluded_from_qi(self):
        """Test that a member with Medicaid returns True, enforcing the QI exclusion.

        QI (Qualified Individual) is only available to Medicare beneficiaries who are
        NOT eligible for Medicaid. By returning True here, PolicyEngine will correctly
        exclude this member from QI even if they haven't provided full income/asset data.
        """
        dep = member.IsMedicaidEligibleDependency(self.screen, self.member_with_medicaid, {})
        # Member has both Medicare and Medicaid — Medicaid dependency returns True,
        # which causes PolicyEngine to exclude them from QI.
        self.assertTrue(dep.value())


class TestFosterCareDependency(TestCase):
    """Tests for FosterCareDependency which maps fosterChild relationship to was_in_foster_care."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)
        self.foster_child = HouseholdMember.objects.create(screen=self.screen, relationship="fosterChild", age=4)
        self.biological_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)

    def test_field_name(self):
        """FosterCareDependency maps to the was_in_foster_care PE variable."""
        dep = member.FosterCareDependency(self.screen, self.foster_child, {})
        self.assertEqual(dep.field, "was_in_foster_care")

    def test_value_returns_true_for_foster_child(self):
        """Returns True when the member's relationship is fosterChild."""
        dep = member.FosterCareDependency(self.screen, self.foster_child, {})
        self.assertTrue(dep.value())

    def test_value_returns_none_for_biological_child(self):
        """Returns None for a child with a non-foster relationship (let PE calculate)."""
        dep = member.FosterCareDependency(self.screen, self.biological_child, {})
        self.assertIsNone(dep.value())

    def test_value_returns_none_for_head_of_household(self):
        """Returns None for the head of household (not a foster child)."""
        dep = member.FosterCareDependency(self.screen, self.head, {})
        self.assertIsNone(dep.value())


class TestEmploymentIncomeBeforeLsrDependency(TestCase):
    """Tests for EmploymentIncomeBeforeLsrDependency used by WaTanf calculator."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="98101",
            county="King",
            household_size=2,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_field_name(self):
        dep = member.EmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.field, "employment_income_before_lsr")

    def test_value_calculates_annual_wages(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=800, frequency="monthly"
        )
        dep = member.EmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 9600)  # $800/month * 12

    def test_value_returns_zero_when_no_wages(self):
        dep = member.EmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)

    def test_value_excludes_self_employment(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="selfEmployment", amount=500, frequency="monthly"
        )
        dep = member.EmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestSelfEmploymentIncomeBeforeLsrDependency(TestCase):
    """Tests for SelfEmploymentIncomeBeforeLsrDependency used by WaTanf calculator."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="98101",
            county="King",
            household_size=2,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_field_name(self):
        dep = member.SelfEmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.field, "self_employment_income_before_lsr")

    def test_value_calculates_annual_self_employment(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="selfEmployment", amount=600, frequency="monthly"
        )
        dep = member.SelfEmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 7200)  # $600/month * 12

    def test_value_returns_zero_when_no_self_employment(self):
        dep = member.SelfEmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)

    def test_value_excludes_wages(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1000, frequency="monthly"
        )
        dep = member.SelfEmploymentIncomeBeforeLsrDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)


class TestPartTimeCollegeStudentDependency(TestCase):
    """Tests for PartTimeCollegeStudentDependency (PE input: is_part_time_college_student).

    True only when the member is enrolled (student=True) AND is not full-time
    (student_full_time=False).
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def _dep(self, **kwargs):
        m = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, **kwargs)
        return member.PartTimeCollegeStudentDependency(self.screen, m, {})

    def test_field_name(self):
        self.assertEqual(self._dep(student=False).field, "is_part_time_college_student")

    def test_true_when_student_and_not_full_time(self):
        self.assertTrue(self._dep(student=True, student_full_time=False).value())

    def test_false_when_student_and_full_time(self):
        self.assertFalse(self._dep(student=True, student_full_time=True).value())

    def test_false_when_student_full_time_is_none(self):
        # Unknown enrollment status → not treated as part-time
        self.assertFalse(self._dep(student=True, student_full_time=None).value())

    def test_false_when_not_a_student(self):
        self.assertFalse(self._dep(student=False, student_full_time=False).value())


class TestSnapWorkExceptionDependency(TestCase):
    """Tests for SnapWorkExceptionDependency (PE input: meets_snap_work_exception).

    PE's Exception 4: weekly_hours_worked_before_lsr >= 20 OR is_federal_work_study_participant.
    MFB overrides the whole expression directly from the two self-reported screener flags,
    avoiding the lossy income-approximated hours proxy.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def _dep(self, **kwargs):
        m = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, **kwargs)
        return member.SnapWorkExceptionDependency(self.screen, m, {})

    def test_field_name(self):
        self.assertEqual(self._dep().field, "meets_snap_work_exception")

    def test_true_when_works_20_plus_hrs(self):
        self.assertTrue(self._dep(student_works_20_plus_hrs=True).value())

    def test_true_when_has_work_study(self):
        self.assertTrue(self._dep(student_has_work_study=True).value())

    def test_true_when_both_flags_set(self):
        self.assertTrue(self._dep(student_works_20_plus_hrs=True, student_has_work_study=True).value())

    def test_false_when_neither_flag_set(self):
        self.assertFalse(self._dep(student_works_20_plus_hrs=False, student_has_work_study=False).value())

    def test_false_when_both_flags_none(self):
        self.assertFalse(self._dep(student_works_20_plus_hrs=None, student_has_work_study=None).value())


class TestSnapJobTrainingStudentDependency(TestCase):
    """Tests for SnapJobTrainingStudentDependency
    (PE input: is_snap_employment_training_or_work_incentive_student).

    Maps student_job_training_program → PE's Exception 3 / WIOA field, which PE
    now models (shipped after MFB-640). Closes the NC job-training regression.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def _dep(self, **kwargs):
        m = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, **kwargs)
        return member.SnapJobTrainingStudentDependency(self.screen, m, {})

    def test_field_name(self):
        self.assertEqual(self._dep().field, "is_snap_employment_training_or_work_incentive_student")

    def test_true_when_in_job_training(self):
        self.assertTrue(self._dep(student_job_training_program=True).value())

    def test_false_when_not_in_job_training(self):
        self.assertFalse(self._dep(student_job_training_program=False).value())

    def test_false_when_job_training_is_none(self):
        self.assertFalse(self._dep(student_job_training_program=None).value())


class TestFullTimeCollegeStudentDependencyFixed(TestCase):
    """Tests for the corrected FullTimeCollegeStudentDependency (PE input: is_full_time_college_student).

    Previously returned `student or False`, which treated every student as full-time.
    Now returns `student and student_full_time`, correctly distinguishing full-time
    from part-time enrolment.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def _dep(self, **kwargs):
        m = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, **kwargs)
        return member.FullTimeCollegeStudentDependency(self.screen, m, {})

    def test_field_name(self):
        self.assertEqual(self._dep(student=False).field, "is_full_time_college_student")

    def test_true_when_student_and_full_time(self):
        self.assertTrue(self._dep(student=True, student_full_time=True).value())

    def test_false_when_student_and_part_time(self):
        # Key regression test: old code returned True here; must now return False
        self.assertFalse(self._dep(student=True, student_full_time=False).value())

    def test_false_when_student_full_time_is_none(self):
        # Unknown → conservative: not treated as full-time
        self.assertFalse(self._dep(student=True, student_full_time=None).value())

    def test_false_when_not_a_student(self):
        self.assertFalse(self._dep(student=False, student_full_time=True).value())


class TestIsIncapableOfSelfCareDependency(TestCase):
    """Tests for IsIncapableOfSelfCareDependency, PolicyEngine's
    `is_incapable_of_self_care` person input used by the federal CDCC to mark a
    qualifying individual of any age. Inferred from the same disability signals as
    is_disabled (disabled OR long_term_disability OR visually_impaired)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def _dep(self, **kwargs):
        m = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40, **kwargs)
        return member.IsIncapableOfSelfCareDependency(self.screen, m, {})

    def test_field_name(self):
        self.assertEqual(self._dep().field, "is_incapable_of_self_care")

    def test_true_when_disabled(self):
        self.assertTrue(self._dep(disabled=True).value())

    def test_true_when_long_term_disability(self):
        self.assertTrue(self._dep(long_term_disability=True).value())

    def test_true_when_visually_impaired(self):
        self.assertTrue(self._dep(visually_impaired=True).value())

    def test_false_when_no_disability_signal(self):
        self.assertFalse(self._dep(disabled=False, long_term_disability=False, visually_impaired=False).value())


class TestCareExpensesDependency(TestCase):
    """Tests for CareExpensesDependency, PolicyEngine's `care_expenses` person input
    used by the federal CDCC. Our screener captures a single household-level
    `dependentCare` expense with no per-member attribution, so it is split evenly
    across members who are incapable of self-care; members who are not get 0."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            completed=False,
        )

    def test_field_name(self):
        m = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        self.assertEqual(member.CareExpensesDependency(self.screen, m, {}).field, "care_expenses")

    def test_zero_when_member_not_incapable(self):
        Expense.objects.create(screen=self.screen, type="dependentCare", amount=500, frequency="monthly")
        m = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        self.assertEqual(member.CareExpensesDependency(self.screen, m, {}).value(), 0)

    def test_full_amount_when_single_incapable_member(self):
        Expense.objects.create(screen=self.screen, type="dependentCare", amount=500, frequency="monthly")
        disabled = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=40, disabled=True
        )
        # $500/mo → $6,000/yr, single incapable member gets the whole amount.
        self.assertEqual(member.CareExpensesDependency(self.screen, disabled, {}).value(), 6000)

    def test_split_evenly_across_incapable_members(self):
        Expense.objects.create(screen=self.screen, type="dependentCare", amount=500, frequency="monthly")
        d1 = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40, disabled=True)
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=38, long_term_disability=True)
        # $6,000/yr split across 2 incapable members → $3,000 each.
        self.assertEqual(member.CareExpensesDependency(self.screen, d1, {}).value(), 3000)


class TestSsiReceiptDependencies(TestCase):
    """
    Tests for the SSI half of the actual-receipt contract.

    ``ssi`` and ``receives_ssi`` are person-level, and a reported amount is the only per-member
    SSI signal the screener captures, so receipt is read from the amount alone. The
    household-scoped Current Benefits tile names no recipient, and PolicyEngine treats
    ``receives_ssi`` as conclusive (measured: it alone flips ``medicaid_category`` to
    SSI_RECIPIENT with no demographic or income test), so a tile is never attributed to a
    guessed member. It still holds take-up at PolicyEngine's default so a real recipient is not
    zeroed. SSDI (``sSDisability``) is a different program and must never be folded in.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Test County",
            household_size=2,
            completed=False,
        )
        # Aged head, working-age non-disabled spouse, young child: only the head could be
        # an SSI recipient, so attribution is observable.
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)
        self.spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=40)
        self.child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)

    def _report_ssi(self, household_member, monthly):
        IncomeStream.objects.create(
            screen=self.screen, household_member=household_member, type="sSI", amount=monthly, frequency="monthly"
        )

    def _tick_ssi_tile(self, name_abbreviated="ssi"):
        seed_program(self.white_label, name_abbreviated)
        Program.objects.filter(white_label=self.white_label, name_abbreviated=name_abbreviated).update(
            base_program="ssi"
        )
        _write_current_benefits(self.screen, [name_abbreviated])

    def test_field_names(self):
        self.assertEqual(member.Ssi(self.screen, self.head, {}).field, "ssi")
        self.assertEqual(member.ReceivesSsiDependency(self.screen, self.head, {}).field, "receives_ssi")
        self.assertEqual(
            member.TakesUpSsiIfEligibleDependency(self.screen, self.head, {}).field, "takes_up_ssi_if_eligible"
        )
        self.assertEqual(member.SsiIfTakesUp(self.screen, self.head, {}).field, "ssi_if_takes_up")

    def test_new_fields_are_version_gated(self):
        self.assertEqual(member.ReceivesSsiDependency.min_pe_version, (1, 779, 3))
        self.assertEqual(member.TakesUpSsiIfEligibleDependency.min_pe_version, (1, 779, 3))
        self.assertEqual(member.SsiIfTakesUp.min_pe_version, (1, 779, 3))
        self.assertEqual(member.Ssi.min_pe_version, ())

    def test_sends_the_reported_amount_annualized(self):
        self._report_ssi(self.head, 943)

        self.assertEqual(member.Ssi(self.screen, self.head, {}).value(), 11316)
        self.assertTrue(member.ReceivesSsiDependency(self.screen, self.head, {}).value())
        self.assertTrue(member.TakesUpSsiIfEligibleDependency(self.screen, self.head, {}).value())

    def test_no_reported_ssi_lowers_take_up(self):
        """
        Lowering take-up is what keeps PolicyEngine from counting the SSI it simulates for a
        non-reporter as income they receive — load-bearing for IL AABD, which that phantom
        income blocks outright, and for SNAP's income test.
        """
        self.assertIsNone(member.Ssi(self.screen, self.head, {}).value())
        self.assertFalse(member.ReceivesSsiDependency(self.screen, self.head, {}).value())
        self.assertFalse(member.TakesUpSsiIfEligibleDependency(self.screen, self.head, {}).value())

    def test_receipt_is_scoped_to_the_reporting_member(self):
        """A spouse's SSI is not this member's — ``ssi`` is person-level."""
        self._report_ssi(self.spouse, 943)

        self.assertIsNone(member.Ssi(self.screen, self.head, {}).value())
        self.assertFalse(member.ReceivesSsiDependency(self.screen, self.head, {}).value())
        self.assertFalse(member.TakesUpSsiIfEligibleDependency(self.screen, self.head, {}).value())
        self.assertTrue(member.ReceivesSsiDependency(self.screen, self.spouse, {}).value())

    def test_tile_without_an_amount_asserts_nobody_receives_ssi(self):
        """
        A ticked tile is household-scoped, so it names no recipient. With an aged head, a
        working-age spouse and a child all equally unexcluded by the data we hold, crediting any
        of them is a guess — and PolicyEngine would treat it as conclusive, handing that member
        the SSI-recipient Medicaid pathway with no demographic or income test (measured at
        $15,167 for the spouse, $10,222 for the child).
        """
        self._tick_ssi_tile()

        for household_member in (self.head, self.spouse, self.child):
            self.assertFalse(member.ReceivesSsiDependency(self.screen, household_member, {}).value())

    def test_tile_without_an_amount_leaves_take_up_alone(self):
        """
        The tile is not discarded, though: somebody here receives SSI, so lowering take-up would
        zero the simulated SSI of whoever that is. The whole household keeps PolicyEngine's
        default instead — unknown stays unknown rather than becoming a denial.
        """
        self._tick_ssi_tile()

        for household_member in (self.head, self.spouse, self.child):
            self.assertTrue(member.TakesUpSsiIfEligibleDependency(self.screen, household_member, {}).value())

    def test_a_reported_amount_explains_the_tile_for_the_rest_of_the_household(self):
        """Once a member accounts for the household's SSI, members reporting nothing are
        suppressed normally — otherwise one SSI recipient would shield every relative's
        simulated SSI from suppression."""
        self._tick_ssi_tile()
        self._report_ssi(self.head, 943)

        self.assertTrue(member.TakesUpSsiIfEligibleDependency(self.screen, self.head, {}).value())
        self.assertTrue(member.ReceivesSsiDependency(self.screen, self.head, {}).value())
        self.assertFalse(member.TakesUpSsiIfEligibleDependency(self.screen, self.spouse, {}).value())
        self.assertFalse(member.ReceivesSsiDependency(self.screen, self.spouse, {}).value())

    def test_tile_resolves_a_white_label_prefixed_ssi_program(self):
        """White labels ship ks_ssi / mo_ssi / tx_ssi, so the tile has to resolve by
        base_program rather than the bare name for take-up to be held at the default."""
        self._tick_ssi_tile("ks_ssi")

        self.assertTrue(member.TakesUpSsiIfEligibleDependency(self.screen, self.head, {}).value())

    def test_ssdi_and_other_income_are_not_ssi(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSDisability", amount=1000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=500, frequency="monthly"
        )

        self.assertIsNone(member.Ssi(self.screen, self.head, {}).value())
        self.assertFalse(member.ReceivesSsiDependency(self.screen, self.head, {}).value())
        self.assertFalse(member.TakesUpSsiIfEligibleDependency(self.screen, self.head, {}).value())


class TestWicDependency(TestCase):
    """
    The WIC program's output stays on the ungated ``wic``.

    ``wic`` is ``wic_if_takes_up`` gated on ``takes_up_wic_if_eligible``, which defaults True and
    which we never send, so the two are the same number for every payload we submit. Staying
    ungated keeps WIC out of the version floor and so out of ``_drop_unreadable_programs``.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="65101", county="Test County", household_size=1, completed=False
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=29)

    def test_field_name(self):
        self.assertEqual(member.Wic(self.screen, self.head, {}).field, "wic")

    def test_not_version_gated(self):
        self.assertEqual(member.Wic.min_pe_version, ())


class TestSsiCountableResourcesDependency(TestCase):
    """
    Tests for SsiCountableResourcesDependency. SSI's resource limit is a hard cutoff, and
    the screener collects assets only at the household level — so this splits the household
    total evenly across adults (19+) to approximate a per-person figure, and attributes
    nothing to children.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Test County",
            household_size=3,
            household_assets=6000,
            completed=False,
        )

    def test_field_name(self):
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)
        self.assertEqual(member.SsiCountableResourcesDependency(self.screen, head, {}).field, "ssi_countable_resources")

    def test_single_adult_gets_all_household_assets(self):
        screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Test County",
            household_size=1,
            household_assets=1500,
            completed=False,
        )
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=67)
        self.assertEqual(member.SsiCountableResourcesDependency(screen, head, {}).value(), 1500)

    def test_assets_split_evenly_across_adults(self):
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=65)
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
        # $6,000 across 2 adults (the 10-year-old is not counted) -> $3,000 each.
        self.assertEqual(member.SsiCountableResourcesDependency(self.screen, head, {}).value(), 3000)

    def test_children_are_attributed_no_resources(self):
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
        self.assertEqual(member.SsiCountableResourcesDependency(self.screen, child, {}).value(), 0)

    def test_age_19_counts_as_an_adult(self):
        """num_adults() uses age_max=19, so 19 is the boundary — 18 gets nothing, 19 gets a share."""
        eighteen = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=18)
        nineteen = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19)
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)

        self.assertEqual(member.SsiCountableResourcesDependency(self.screen, eighteen, {}).value(), 0)
        # $6,000 across the 19-year-old and the 67-year-old -> $3,000 each.
        self.assertEqual(member.SsiCountableResourcesDependency(self.screen, nineteen, {}).value(), 3000)

    def test_value_is_an_int(self):
        """PolicyEngine gets an int; an uneven split must not leak a Decimal."""
        # $6,001 across 3 adults divides to Decimal('2000.333...'), so this exercises the
        # int() truncation. An evenly divisible amount would pass whether or not the cast
        # is there.
        self.screen.household_assets = 6001
        self.screen.save()
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=65)
        HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=88)

        value = member.SsiCountableResourcesDependency(self.screen, head, {}).value()
        self.assertIsInstance(value, int)
        self.assertEqual(value, 2000)


class TestSsiEarnedAndUnearnedIncomeDependencies(TestCase):
    """
    Tests for SsiEarnedIncomeDependency / SsiUnearnedIncomeDependency. SSI applies a
    different exclusion to each ($20 general, then $65 + half of remaining earned), so the
    two must stay split — collapsing them would understate the benefit.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Test County",
            household_size=1,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=67)

    def test_field_names(self):
        self.assertEqual(member.SsiEarnedIncomeDependency(self.screen, self.head, {}).field, "ssi_earned_income")
        self.assertEqual(member.SsiUnearnedIncomeDependency(self.screen, self.head, {}).field, "ssi_unearned_income")

    def test_earned_covers_wages_and_self_employment_only(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="selfEmployment", amount=500, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSA", amount=800, frequency="monthly"
        )

        self.assertEqual(member.SsiEarnedIncomeDependency(self.screen, self.head, {}).value(), 18000)

    def test_unearned_covers_everything_that_is_not_earned(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSA", amount=800, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="pension", amount=200, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1000, frequency="monthly"
        )

        self.assertEqual(member.SsiUnearnedIncomeDependency(self.screen, self.head, {}).value(), 12000)

    def test_the_two_partition_all_income_without_overlap(self):
        """Every income stream lands in exactly one bucket — nothing double-counted, nothing dropped."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSA", amount=800, frequency="monthly"
        )

        earned = member.SsiEarnedIncomeDependency(self.screen, self.head, {}).value()
        unearned = member.SsiUnearnedIncomeDependency(self.screen, self.head, {}).value()

        self.assertEqual(earned + unearned, self.head.calc_gross_income("yearly", ["all"]))

    def test_both_return_zero_with_no_income(self):
        self.assertEqual(member.SsiEarnedIncomeDependency(self.screen, self.head, {}).value(), 0)
        self.assertEqual(member.SsiUnearnedIncomeDependency(self.screen, self.head, {}).value(), 0)

    def test_nurturing_futures_is_excluded_from_unearned(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="pension", amount=200, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="nurturingFutures", amount=600, frequency="monthly"
        )

        self.assertEqual(member.SsiUnearnedIncomeDependency(self.screen, self.head, {}).value(), 2400)

    def test_nurturing_futures_is_the_one_break_in_the_partition(self):
        """
        The earned/unearned split otherwise covers every income stream. Nurturing Futures
        is deliberately in neither bucket, so it is the sole gap against total income.
        """
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="nurturingFutures", amount=600, frequency="monthly"
        )

        earned = member.SsiEarnedIncomeDependency(self.screen, self.head, {}).value()
        unearned = member.SsiUnearnedIncomeDependency(self.screen, self.head, {}).value()

        self.assertEqual(earned + unearned, self.head.calc_gross_income("yearly", ["all"]) - 7200)


class TestHasEsiDependency(TestCase):
    """
    Tests for HasEsiDependency, which maps the screener's employer-insurance checkbox to
    PolicyEngine's ``has_esi``.

    This is the statutory employer-coverage disqualifier for the ACA Premium Tax Credit
    (26 U.S.C. 36B(c)(2)(C)). PolicyEngine only applies it if we send the field, so the
    False case matters as much as the True case: a member with *some other* coverage must
    not be scored as having job-based coverage.
    """

    def setUp(self):
        from screener.models import Insurance

        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="64108",
            county="Jackson County",
            household_size=1,
            completed=False,
        )

        self.with_employer = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=self.with_employer, employer=True, none=False)

        self.uninsured = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=38)
        Insurance.objects.create(household_member=self.uninsured, none=True)

        self.with_medicaid = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
        Insurance.objects.create(household_member=self.with_medicaid, medicaid=True, none=False)

        # No Insurance row at all — has_insurance_types() short-circuits to False.
        self.no_insurance_record = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=7)

    def test_value_true_when_member_has_employer_coverage(self):
        self.assertTrue(member.HasEsiDependency(self.screen, self.with_employer, {}).value())

    def test_value_false_when_member_is_uninsured(self):
        self.assertFalse(member.HasEsiDependency(self.screen, self.uninsured, {}).value())

    def test_value_false_for_non_employer_coverage(self):
        """Medicaid is not employer-sponsored — it must not trip the ESI disqualifier."""
        self.assertFalse(member.HasEsiDependency(self.screen, self.with_medicaid, {}).value())

    def test_value_false_when_no_insurance_record_exists(self):
        self.assertFalse(member.HasEsiDependency(self.screen, self.no_insurance_record, {}).value())

    def test_returns_bool_not_none(self):
        """False must be sent, not None — the field is safe to send unconditionally."""
        for household_member in (self.with_employer, self.uninsured, self.no_insurance_record):
            self.assertIsInstance(member.HasEsiDependency(self.screen, household_member, {}).value(), bool)

    def test_field_name_matches_policyengine_variable(self):
        self.assertEqual(member.HasEsiDependency.field, "has_esi")

    def test_is_member_level_dependency(self):
        from programs.programs.policyengine.calculators.dependencies.base import Member

        self.assertTrue(issubclass(member.HasEsiDependency, Member))


class TestChildSupportReceivedDependency(TestCase):
    """Child support *received*, sent to PolicyEngine as income (a WIC income source).

    The pairing with ``SnapChildSupportDependency`` is the thing worth guarding: that one
    sends child support *paid*, as an expense, under a different PE field. A household can
    report both, and collapsing them would count a payer's outflow as their income.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_value_calculates_annual_child_support_received(self):
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="childSupport",
            amount=400,
            frequency="monthly",
        )

        dep = member.ChildSupportReceivedDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 4800)  # $400/month * 12

    def test_value_returns_zero_when_none_reported(self):
        dep = member.ChildSupportReceivedDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 0)

    def test_value_excludes_other_income_types(self):
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="childSupport",
            amount=400,
            frequency="monthly",
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="alimony",
            amount=300,
            frequency="monthly",
        )

        dep = member.ChildSupportReceivedDependency(self.screen, self.head, {})
        self.assertEqual(dep.value(), 4800)

    def test_field_name_matches_policyengine_variable(self):
        self.assertEqual(member.ChildSupportReceivedDependency.field, "child_support_received")

    def test_is_distinct_from_the_child_support_paid_expense(self):
        """Received income and paid expense are separate PE fields, and both can be
        non-zero for the same household."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="childSupport",
            amount=400,
            frequency="monthly",
        )
        Expense.objects.create(screen=self.screen, type="childSupport", amount=500, frequency="monthly")

        received = member.ChildSupportReceivedDependency(self.screen, self.head, {})
        paid = member.SnapChildSupportDependency(self.screen, self.head, {})

        self.assertNotEqual(received.field, paid.field)
        self.assertEqual(received.value(), 4800)
        self.assertEqual(paid.value(), 3000)  # $500/month * 12 / household_size(2)
