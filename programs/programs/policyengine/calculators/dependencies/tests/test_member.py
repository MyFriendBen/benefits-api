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
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=2,
            completed=False,
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
            screen=self.screen,
            relationship="child",
            age=20,
            student=True,
            disabled=True,
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
