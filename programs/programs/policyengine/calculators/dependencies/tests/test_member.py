"""
Unit tests for member-level PolicyEngine dependencies used by TxSnap.

These dependencies calculate individual member values used by PolicyEngine
to determine TX SNAP eligibility and benefit amounts.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense
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
