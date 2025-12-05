"""
Unit tests for Screen and HouseholdMember model methods.
"""

from decimal import Decimal
from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream, Expense


class TestScreen(TestCase):
    """
    Tests for Screen model methods.
    """

    def setUp(self):
        """Set up test data for income calculation tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=2, completed=False
        )

        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_calc_gross_income_earned_yearly(self):
        """Test calc_gross_income with earned income types for yearly period."""
        # Add wages (earned income)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        result = self.screen.calc_gross_income("yearly", ["earned"])
        self.assertEqual(result, 24000)  # $2000/month * 12

    def test_calc_gross_income_unearned_yearly(self):
        """Test calc_gross_income with unearned income types for yearly period."""
        # Add alimony (unearned income)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="alimony", amount=500, frequency="monthly"
        )

        result = self.screen.calc_gross_income("yearly", ["unearned"])
        self.assertEqual(result, 6000)  # $500/month * 12

    def test_calc_gross_income_all_types(self):
        """Test calc_gross_income with 'all' income types."""
        # Add both earned and unearned
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="alimony", amount=500, frequency="monthly"
        )

        result = self.screen.calc_gross_income("yearly", ["all"])
        self.assertEqual(result, 30000)  # ($2000 + $500) * 12

    def test_calc_gross_income_with_exclude(self):
        """Test calc_gross_income with exclude parameter."""
        # Add cash assistance and other unearned income
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="cashAssistance", amount=300, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="alimony", amount=500, frequency="monthly"
        )

        # Exclude cash assistance
        result = self.screen.calc_gross_income("yearly", ["unearned"], exclude=["cashAssistance"])
        self.assertEqual(result, 6000)  # Only alimony: $500 * 12

    def test_calc_gross_income_zero_income(self):
        """Test calc_gross_income when household has no income."""
        result = self.screen.calc_gross_income("yearly", ["earned"])
        self.assertEqual(result, 0)

    def test_calc_gross_income_monthly_period(self):
        """Test calc_gross_income with monthly period."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )

        result = self.screen.calc_gross_income("monthly", ["earned"])
        self.assertEqual(result, 2000)

    def test_calc_gross_income_multiple_income_streams(self):
        """Test calc_gross_income with multiple income streams of same type."""
        # Add multiple wage income streams (e.g., two jobs)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=2000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=500, frequency="monthly"
        )

        result = self.screen.calc_gross_income("yearly", ["earned"])
        self.assertEqual(result, 30000)  # ($2000 + $500) * 12

    # Tests for Screen.calc_expenses() method

    def test_calc_expenses_single_type_yearly(self):
        """Test calc_expenses with single expense type for yearly period."""
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")

        result = self.screen.calc_expenses("yearly", ["rent"])
        self.assertEqual(result, 12000)  # $1000/month * 12

    def test_calc_expenses_multiple_types(self):
        """Test calc_expenses with multiple expense types."""
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")
        Expense.objects.create(screen=self.screen, type="mortgage", amount=500, frequency="monthly")

        result = self.screen.calc_expenses("yearly", ["rent", "mortgage"])
        self.assertEqual(result, 18000)  # ($1000 + $500) * 12

    def test_calc_expenses_zero_expenses(self):
        """Test calc_expenses when no matching expenses exist."""
        result = self.screen.calc_expenses("yearly", ["rent"])
        self.assertEqual(result, 0)

    def test_calc_expenses_monthly_period(self):
        """Test calc_expenses with monthly period."""
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")

        result = self.screen.calc_expenses("monthly", ["rent"])
        self.assertEqual(result, 1000)

    def test_calc_expenses_multiple_same_type(self):
        """Test calc_expenses with multiple expenses of same type."""
        # Multiple rent payments (e.g., shared housing)
        Expense.objects.create(screen=self.screen, type="rent", amount=800, frequency="monthly")
        Expense.objects.create(screen=self.screen, type="rent", amount=200, frequency="monthly")

        result = self.screen.calc_expenses("yearly", ["rent"])
        self.assertEqual(result, 12000)  # ($800 + $200) * 12

    def test_calc_expenses_different_frequencies(self):
        """Test calc_expenses with different frequency expenses."""
        # Monthly rent
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")
        # Yearly property tax
        Expense.objects.create(screen=self.screen, type="propertyTax", amount=3600, frequency="yearly")

        # Test both converted to yearly
        rent_result = self.screen.calc_expenses("yearly", ["rent"])
        self.assertEqual(rent_result, 12000)

        tax_result = self.screen.calc_expenses("yearly", ["propertyTax"])
        self.assertEqual(tax_result, 3600)

    # Tests for Screen.has_expense() method

    def test_has_expense_true(self):
        """Test has_expense returns True when expense exists."""
        Expense.objects.create(screen=self.screen, type="heating", amount=80, frequency="monthly")

        result = self.screen.has_expense(["heating"])
        self.assertTrue(result)

    def test_has_expense_false(self):
        """Test has_expense returns False when expense doesn't exist."""
        result = self.screen.has_expense(["heating"])
        self.assertFalse(result)

    def test_has_expense_multiple_types_any_match(self):
        """Test has_expense with multiple types returns True if any match."""
        Expense.objects.create(screen=self.screen, type="cooling", amount=60, frequency="monthly")

        result = self.screen.has_expense(["heating", "cooling"])
        self.assertTrue(result)

    def test_has_expense_multiple_types_no_match(self):
        """Test has_expense with multiple types returns False if none match."""
        Expense.objects.create(screen=self.screen, type="rent", amount=1000, frequency="monthly")

        result = self.screen.has_expense(["heating", "cooling"])
        self.assertFalse(result)

    def test_has_expense_zero_amount(self):
        """Test has_expense with zero amount expense."""
        Expense.objects.create(screen=self.screen, type="heating", amount=0, frequency="monthly")

        # Even with $0 amount, expense record exists
        result = self.screen.has_expense(["heating"])
        self.assertTrue(result)

    # Tests for Screen.num_adults() method

    def test_num_adults_default_age_19(self):
        """Test num_adults with default age_max=19."""
        # self.head already created in setUp (age 35)
        # Create additional members: 1 spouse and 1 child
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        result = self.screen.num_adults()
        self.assertEqual(result, 2)

    def test_num_adults_custom_age_18(self):
        """Test num_adults with custom age_max=18."""
        # self.head already created in setUp (age 35)
        # Create additional children
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=18)
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        result = self.screen.num_adults(age_max=18)
        self.assertEqual(result, 2)  # 35 and 18 both >= 18

    def test_num_adults_edge_case_age_boundary(self):
        """Test num_adults with member at exact age boundary."""
        # Update the existing head to age 19
        self.head.age = 19
        self.head.save()

        result = self.screen.num_adults()  # age_max=19
        self.assertEqual(result, 1)  # age >= 19

    def test_num_adults_no_members(self):
        """Test num_adults returns 0 when no household members."""
        # Delete the head created in setUp
        self.head.delete()

        result = self.screen.num_adults()
        self.assertEqual(result, 0)

    # Tests for Screen.has_benefit() method

    def test_has_benefit_returns_true_when_user_has_snap(self):
        """
        Test that has_benefit('tx_snap') returns True when user has SNAP.

        When screen.has_snap is True, has_benefit('tx_snap') should return True,
        indicating the user already receives this benefit and it should be filtered
        from eligibility results.
        """
        self.screen.has_snap = True
        self.screen.save()

        self.assertTrue(self.screen.has_benefit("tx_snap"))

    def test_has_benefit_returns_false_when_user_does_not_have_snap(self):
        """
        Test that has_benefit('tx_snap') returns False when user does not have SNAP.

        When screen.has_snap is False, has_benefit('tx_snap') should return False,
        indicating the user does not currently receive this benefit and it should
        appear in eligibility results.
        """
        self.screen.has_snap = False
        self.screen.save()

        self.assertFalse(self.screen.has_benefit("tx_snap"))

    def test_has_benefit_returns_true_for_ma_head_start_when_user_has_head_start(self):
        """
        Test that has_benefit('ma_head_start') returns True when user has Head Start.
        """
        self.screen.has_head_start = True
        self.screen.save()

        self.assertTrue(self.screen.has_benefit("ma_head_start"))

    def test_has_benefit_returns_false_for_ma_head_start_when_user_does_not_have_head_start(self):
        """
        Test that has_benefit('ma_head_start') returns False when user does not have Head Start.
        """
        self.screen.has_head_start = False
        self.screen.save()

        self.assertFalse(self.screen.has_benefit("ma_head_start"))

    # Tests for Screen.other_tax_unit_structure() method

    def test_other_tax_unit_structure_empty_when_all_in_primary_unit(self):
        """Test other_tax_unit_structure returns empty unit when all members in primary unit."""
        # Simple household: head only
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        result = self.screen.other_tax_unit_structure()

        self.assertIsNone(result["head"])
        self.assertIsNone(result["spouse"])
        self.assertEqual(result["dependents"], [])

    def test_other_tax_unit_structure_with_adult_child_high_income(self):
        """Test other_tax_unit_structure identifies adult child with high income as separate unit."""
        self.screen.household_size = 2
        self.screen.save()

        # Primary tax unit: head with moderate income
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=55)
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=3000, frequency="monthly"
        )

        # Adult child with high income (not a dependent)
        adult_child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=25, student=False, disabled=False
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult_child, type="wages", amount=4000, frequency="monthly"
        )

        result = self.screen.other_tax_unit_structure()

        # Adult child should be head of other tax unit
        self.assertEqual(result["head"], adult_child)
        self.assertIsNone(result["spouse"])
        self.assertEqual(result["dependents"], [])

    def test_other_tax_unit_structure_with_grandparents(self):
        """Test other_tax_unit_structure identifies grandparent couple as separate unit."""
        self.screen.household_size = 4
        self.screen.save()

        # Primary tax unit: young head with child
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)

        # Other tax unit: grandparent couple
        grandparent1 = HouseholdMember.objects.create(screen=self.screen, relationship="grandParent", age=65)

        grandparent2 = HouseholdMember.objects.create(screen=self.screen, relationship="grandParent", age=63)

        result = self.screen.other_tax_unit_structure()

        # Older grandparent should be head, younger should be spouse
        self.assertEqual(result["head"], grandparent1)
        self.assertEqual(result["spouse"], grandparent2)
        self.assertEqual(result["dependents"], [])

    def test_other_tax_unit_structure_with_parent_couple(self):
        """Test other_tax_unit_structure identifies parent couple as separate unit."""
        self.screen.household_size = 4
        self.screen.save()

        # Primary tax unit: young head with child
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)

        # Other tax unit: parent couple
        parent1 = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=60)

        parent2 = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=58)

        result = self.screen.other_tax_unit_structure()

        # Older parent should be head, younger should be spouse
        self.assertEqual(result["head"], parent1)
        self.assertEqual(result["spouse"], parent2)
        self.assertEqual(result["dependents"], [])

    def test_other_tax_unit_structure_head_selected_by_age(self):
        """Test other_tax_unit_structure selects oldest member as head when multiple candidates."""
        self.screen.household_size = 3
        self.screen.save()

        # Primary unit: head with child dependent
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)

        young_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        # Other unit members (not in primary tax unit due to age/income)
        adult1 = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=25, student=False, disabled=False
        )

        adult2 = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=28, student=False, disabled=False
        )

        # Give them high income so they're not dependents
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult1, type="wages", amount=3000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult2, type="wages", amount=3500, frequency="monthly"
        )

        self.screen.household_size = 4
        self.screen.save()

        result = self.screen.other_tax_unit_structure()

        # Adult2 (age 28) should be head of other unit
        self.assertEqual(result["head"], adult2)

    def test_other_tax_unit_structure_with_dependents(self):
        """Test other_tax_unit_structure identifies multiple non-primary-unit members."""
        self.screen.household_size = 5
        self.screen.save()

        # Primary unit: head with young child
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        child1 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=8)

        # Other unit: adult child (not dependent due to high income)
        adult_child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=25, student=False, disabled=False
        )

        # Give head moderate income
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )

        # Give adult child high income (not a dependent of head)
        # Need income > ($2000 * 12) / 2 = $12,000
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult_child, type="wages", amount=2000, frequency="monthly"
        )

        # Second adult child also not dependent
        adult_child2 = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=22, student=False, disabled=False
        )

        IncomeStream.objects.create(
            screen=self.screen, household_member=adult_child2, type="wages", amount=1500, frequency="monthly"
        )

        result = self.screen.other_tax_unit_structure()

        # Adult child should be head of other unit (older)
        self.assertEqual(result["head"], adult_child)
        # Second adult child should be in other unit (not spouse, so dependent)
        # Note: The actual behavior depends on relationship_map logic
        self.assertEqual(len(result["dependents"]), 1)
        self.assertIn(adult_child2, result["dependents"])


class TestHouseholdMember(TestCase):
    """
    Tests for HouseholdMember model methods.
    """

    def setUp(self):
        """Set up test data for household member tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
        )

        # Create head of household for tests that depend on it
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def test_has_disability_short_term_disability(self):
        """Test has_disability returns True for member with disabled=True."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=35, disabled=True, long_term_disability=False
        )

        result = member.has_disability()
        self.assertTrue(result)

    def test_has_disability_long_term_disability(self):
        """Test has_disability returns True for member with long_term_disability=True."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=35, disabled=False, long_term_disability=True
        )

        result = member.has_disability()
        self.assertTrue(result)

    def test_has_disability_both_disabilities(self):
        """Test has_disability returns True when both disability flags are True."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=35, disabled=True, long_term_disability=True
        )

        result = member.has_disability()
        self.assertTrue(result)

    def test_has_disability_no_disability(self):
        """Test has_disability returns False when no disabilities."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=35, disabled=False, long_term_disability=False
        )

        result = member.has_disability()
        self.assertFalse(result)

    # Tests for HouseholdMember.calc_gross_income() method

    def test_member_calc_gross_income_earned_yearly(self):
        """Test member calc_gross_income with earned income for yearly period."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add wages to specific member
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )

        result = head.calc_gross_income("yearly", ["earned"])
        self.assertEqual(result, 24000)  # $2000/month * 12

    def test_member_calc_gross_income_unearned_yearly(self):
        """Test member calc_gross_income with unearned income for yearly period."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add alimony to specific member
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="alimony", amount=500, frequency="monthly"
        )

        result = head.calc_gross_income("yearly", ["unearned"])
        self.assertEqual(result, 6000)  # $500/month * 12

    def test_member_calc_gross_income_all_types(self):
        """Test member calc_gross_income with 'all' income types."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add both earned and unearned to member
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="sSI", amount=800, frequency="monthly"
        )

        result = head.calc_gross_income("yearly", ["all"])
        self.assertEqual(result, 33600)  # ($2000 + $800) * 12

    def test_member_calc_gross_income_with_exclude(self):
        """Test member calc_gross_income with exclude parameter."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add cash assistance and other unearned income
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="cashAssistance", amount=300, frequency="monthly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="alimony", amount=500, frequency="monthly"
        )

        # Exclude cash assistance
        result = head.calc_gross_income("yearly", ["unearned"], exclude=["cashAssistance"])
        self.assertEqual(result, 6000)  # Only alimony: $500 * 12

    def test_member_calc_gross_income_zero_income(self):
        """Test member calc_gross_income when member has no income."""
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        result = head.calc_gross_income("yearly", ["earned"])
        self.assertEqual(result, 0)

    def test_member_calc_gross_income_monthly_period(self):
        """Test member calc_gross_income with monthly period."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )

        result = head.calc_gross_income("monthly", ["earned"])
        self.assertEqual(result, 2000)

    def test_member_calc_gross_income_only_counts_member_income(self):
        """Test member calc_gross_income only counts that member's income, not household."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add income to head
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )

        # Add another member with different income
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)
        IncomeStream.objects.create(
            screen=self.screen, household_member=spouse, type="wages", amount=1500, frequency="monthly"
        )

        # Head's income should only be $2000/month
        result = head.calc_gross_income("yearly", ["earned"])
        self.assertEqual(result, 24000)  # Only head's $2000 * 12

        # Spouse's income should only be $1500/month
        result = spouse.calc_gross_income("yearly", ["earned"])
        self.assertEqual(result, 18000)  # Only spouse's $1500 * 12

    # Tests for HouseholdMember.is_head() method

    def test_is_head_returns_true_for_head_of_household(self):
        """Test is_head returns True for member with headOfHousehold relationship."""
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        result = head.is_head()
        self.assertTrue(result)

    def test_is_head_returns_false_for_spouse(self):
        """Test is_head returns False for spouse."""
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)

        result = spouse.is_head()
        self.assertFalse(result)

    def test_is_head_returns_false_for_child(self):
        """Test is_head returns False for child."""
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        result = child.is_head()
        self.assertFalse(result)

    def test_is_head_returns_false_for_parent(self):
        """Test is_head returns False for parent."""
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        parent = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=65)

        result = parent.is_head()
        self.assertFalse(result)

    # Tests for HouseholdMember.is_spouse() method

    def test_is_spouse_returns_true_for_spouse_of_head(self):
        """Test is_spouse returns True for spouse of head of household."""
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)

        result = spouse.is_spouse()
        self.assertTrue(result)

    def test_is_spouse_returns_true_for_domestic_partner(self):
        """Test is_spouse returns True for domestic partner of head."""
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        partner = HouseholdMember.objects.create(screen=self.screen, relationship="domesticPartner", age=30)

        result = partner.is_spouse()
        self.assertTrue(result)

    def test_is_spouse_returns_false_for_head(self):
        """Test is_spouse returns False for head of household."""
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)

        result = head.is_spouse()
        self.assertFalse(result)

    def test_is_spouse_returns_false_for_child(self):
        """Test is_spouse returns False for child."""
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)

        self.screen.household_size = 3
        self.screen.save()

        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        result = child.is_spouse()
        self.assertFalse(result)

    def test_is_spouse_returns_false_when_no_spouse_exists(self):
        """Test is_spouse returns False for single head household."""
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # No spouse in household
        result = head.is_spouse()
        self.assertFalse(result)

    # Tests for HouseholdMember.is_dependent() method

    def test_is_dependent_returns_true_for_child_under_18_no_income(self):
        """Test is_dependent returns True for child under 18 with no income."""
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        result = child.is_dependent()
        self.assertTrue(result)

    def test_is_dependent_returns_true_for_student_under_23_no_income(self):
        """Test is_dependent returns True for student under 23 with no income."""
        student = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=21, student=True)

        result = student.is_dependent()
        self.assertTrue(result)

    def test_is_dependent_returns_true_for_disabled_member_low_income(self):
        """Test is_dependent returns True for disabled member with low income."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        # Add income to head
        IncomeStream.objects.create(
            screen=self.screen, household_member=head, type="wages", amount=4000, frequency="monthly"
        )

        # Disabled child with income less than half of household
        disabled_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=25, disabled=True)

        IncomeStream.objects.create(
            screen=self.screen, household_member=disabled_child, type="sSI", amount=800, frequency="monthly"
        )

        # $800*12 = $9,600 < ($4000+$800)*12 / 2 = $28,800
        result = disabled_child.is_dependent()
        self.assertTrue(result)

    def test_is_dependent_returns_false_for_head_of_household(self):
        """Test is_dependent returns False for head of household."""
        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

        result = head.is_dependent()
        self.assertFalse(result)

    def test_is_dependent_returns_false_for_spouse(self):
        """Test is_dependent returns False for spouse."""
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=30)

        result = spouse.is_dependent()
        self.assertFalse(result)

    def test_is_dependent_returns_false_for_adult_over_age_limit(self):
        """Test is_dependent returns False for adult over age limit (not student, not disabled)."""
        adult_child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=25, student=False, disabled=False
        )

        result = adult_child.is_dependent()
        self.assertFalse(result)

    def test_is_dependent_returns_false_for_child_with_high_income(self):
        """Test is_dependent returns False for child whose income exceeds 50% of household income."""
        self.screen.household_size = 2
        self.screen.save()

        # Use self.head from setUp
        # Head has low income
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1000, frequency="monthly"
        )

        # Child has high income (more than half)
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=17)

        IncomeStream.objects.create(
            screen=self.screen, household_member=child, type="wages", amount=2000, frequency="monthly"
        )

        # Child income $24,000 > household $36,000 / 2 = $18,000
        result = child.is_dependent()
        self.assertFalse(result)

    def test_is_dependent_edge_case_age_18_not_student(self):
        """Test is_dependent for member exactly age 18 (not student)."""
        member = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=18, student=False)

        # Age <= 18, so should be dependent
        result = member.is_dependent()
        self.assertTrue(result)

    def test_is_dependent_edge_case_age_19_not_student(self):
        """Test is_dependent returns False for member age 19 (not student, not disabled)."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=19, student=False, disabled=False
        )

        # Age > 18 and not student, so not dependent
        result = member.is_dependent()
        self.assertFalse(result)

    def test_is_dependent_edge_case_student_age_23(self):
        """Test is_dependent for student exactly age 23."""
        student = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=23, student=True)

        # Age <= 23 and student, so dependent
        result = student.is_dependent()
        self.assertTrue(result)

    def test_is_dependent_edge_case_student_age_24(self):
        """Test is_dependent returns False for student age 24."""
        student = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=24, student=True, disabled=False
        )

        # Age > 23, so not dependent (even though student)
        result = student.is_dependent()
        self.assertFalse(result)
