from programs.programs.cross_white_label.ccdf.il import IlChildCareAssistanceProgram
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase


class TestIlChildCareAssistanceProgram(CustomCalculatorTestCase):
    """Test cases for Illinois Child Care Assistance Program calculator"""

    calculator_class = IlChildCareAssistanceProgram
    program_code = "il_ccap"
    white_label_code = "il"
    state_code = "IL"

    def setUp(self):
        super().setUp()

        # Basic eligible household: employed parent, one 3-year-old, income below 225% FPL
        self.eligible_screen = self.make_screen(zipcode="60601", county="Cook")
        self.parent = self.add_member(self.eligible_screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(self.parent, 2000)
        self.child = self.add_member(self.eligible_screen, "child", 3)

    # County Group Tests
    def test_get_county_group_ia(self):
        """Test county group IA (highest rate counties)"""
        calc = self.make_calculator(self.eligible_screen)
        self.assertEqual(calc.get_county_group("Cook"), "GROUP_1A")
        self.assertEqual(calc.get_county_group("DuPage"), "GROUP_1A")
        self.assertEqual(calc.get_county_group("Lake"), "GROUP_1A")

    def test_get_county_group_ib(self):
        """Test county group IB (medium rate counties)"""
        screen = self.make_screen(zipcode="61820", county="Champaign", household_size=2)
        calc = self.make_calculator(screen)
        self.assertEqual(calc.get_county_group("Champaign"), "GROUP_1B")
        self.assertEqual(calc.get_county_group("Peoria"), "GROUP_1B")
        self.assertEqual(calc.get_county_group("Will"), "GROUP_1B")

    def test_get_county_group_ii(self):
        """Test county group II (all other Illinois counties)"""
        screen = self.make_screen(zipcode="62401", county="Effingham", household_size=2)
        calc = self.make_calculator(screen)
        self.assertEqual(calc.get_county_group("Effingham"), "GROUP_2")
        self.assertEqual(calc.get_county_group("Random County"), "GROUP_2")

    # Household Eligibility Tests
    def test_household_eligible_with_employed_parent(self):
        """Test household is eligible when parent is employed"""
        calc = self.make_calculator(self.eligible_screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)

    def test_household_eligible_with_student_parent(self):
        """Test household is eligible when parent is a student"""
        # Create new screen with student parent
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=True, has_income=False)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)

    def test_household_ineligible_no_employment_or_school(self):
        """Test household is ineligible when parent is neither employed nor in school"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=False)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    def test_household_ineligible_income_too_high(self):
        """Test household is ineligible when income exceeds 225% FPL"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        # Income well above 225% FPL
        self.add_income(parent, 10000)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    # Member Eligibility Tests
    def test_member_eligible_child_under_13(self):
        """Test child under 13 is eligible"""
        calc = self.make_calculator(self.eligible_screen)
        eligibility = calc.eligible()
        # Should have one eligible member (the 3-year-old child)
        self.assertTrue(eligibility.eligible)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 1)

    def test_member_ineligible_child_over_13(self):
        """Test child over 13 is not eligible (unless disabled)"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # 14-year-old child (too old)
        child = self.add_member(screen, "child", 14, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        # Household eligible but no eligible members
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 0)

    def test_member_eligible_disabled_child_under_19(self):
        """Test disabled child under 19 is eligible"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # 16-year-old with disability
        child = self.add_member(screen, "child", 16, has_income=False, disabled=True)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 1)

    def test_member_ineligible_wrong_relationship(self):
        """Test non-child household members are not eligible"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=3)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # Adult sibling (not eligible relationship)
        sibling = self.add_member(screen, "sibling", 25, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        # No eligible members
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 0)

    def test_member_eligible_various_child_relationships(self):
        """Test various child relationships are eligible"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=5)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)

        # Various eligible child relationships
        child1 = self.add_member(screen, "child", 3, has_income=False)
        child2 = self.add_member(screen, "stepChild", 5, has_income=False)
        child3 = self.add_member(screen, "fosterChild", 7, has_income=False)
        child4 = self.add_member(screen, "grandChild", 2, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)
        # All 4 children should be eligible
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 4)

    # Value Calculation Tests
    def test_member_value_cook_county_infant(self):
        """Test benefit value for infant in Cook County (Group IA)"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # Infant (1 year old)
        infant = self.add_member(screen, "child", 1, has_income=False)

        calc = self.make_calculator(screen)
        value = calc.member_value(infant)
        # $1474/month * 12 = $17,688/year
        self.assertEqual(value, 1474 * 12)

    def test_member_value_cook_county_preschool(self):
        """Test benefit value for preschooler in Cook County (Group IA)"""
        calc = self.make_calculator(self.eligible_screen)
        value = calc.member_value(self.child)
        # $1012/month * 12 = $12,144/year for 3-year-old
        self.assertEqual(value, 1012 * 12)

    def test_member_value_champaign_county_school_age(self):
        """Test benefit value for school-age child in Champaign County (Group IB)"""
        screen = self.make_screen(zipcode="61820", county="Champaign", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # School-age child (8 years old)
        child = self.add_member(screen, "child", 8, has_income=False)

        calc = self.make_calculator(screen)
        value = calc.member_value(child)
        # $484/month * 12 = $5,808/year
        self.assertEqual(value, 484 * 12)

    def test_member_value_rural_county_twos(self):
        """Test benefit value for 2-year-old in rural county (Group II)"""
        screen = self.make_screen(zipcode="62401", county="Effingham", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # 2-year-old
        child = self.add_member(screen, "child", 2, has_income=False)

        calc = self.make_calculator(screen)
        value = calc.member_value(child)
        # $1012/month * 12 = $12,144/year
        self.assertEqual(value, 1012 * 12)

    def test_member_value_too_old_returns_zero(self):
        """Test benefit value is 0 for children over 13 (non-disabled)"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # 15-year-old (too old, not disabled)
        child = self.add_member(screen, "child", 15, has_income=False)

        calc = self.make_calculator(screen)
        value = calc.member_value(child)
        self.assertEqual(value, 0)

    def test_total_value_multiple_children(self):
        """Test total benefit value for household with multiple children"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=4)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)

        # Multiple children at different ages
        infant = self.add_member(screen, "child", 1, has_income=False)
        preschooler = self.add_member(screen, "child", 4, has_income=False)
        school_age = self.add_member(screen, "child", 8, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)  # Calculate values for eligible members

        # Calculate expected total (subsidy - copayment)
        # Subsidy:
        # Infant: $1474 * 12 = $17,688
        # Preschooler: $1012 * 12 = $12,144
        # School-age: $506 * 12 = $6,072
        # Total subsidy: $35,904
        # Copayment: $2000/month income, family of 4 falls in bracket ((0, 2384), 1) = $1/month * 12 = $12/year
        # Net benefit: $35,904 - $12 = $35,892
        expected_subsidy = (1474 * 12) + (1012 * 12) + (506 * 12)
        expected_copayment = 1 * 12
        expected_net = expected_subsidy - expected_copayment

        self.assertTrue(eligibility.eligible)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 3)
        self.assertEqual(eligibility.value, expected_net)

    # Copayment Calculation Tests
    def test_copayment_at_100_percent_fpl(self):
        """Test copayment is $1/month for families at or below 100% FPL"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        # Income at 100% FPL for family of 2 (approximately $1,580/month in 2025)
        self.add_income(parent, 1500)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 1)

    def test_copayment_just_above_100_percent_fpl(self):
        """Test copayment follows table for income just above 100% FPL"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        # $1,800/month - above 100% FPL, should use table
        self.add_income(parent, 1800)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        # $1800 falls in bracket ((1764, 2055), 37)
        self.assertEqual(copayment, 37)

    def test_copayment_mid_income_family_of_4(self):
        """Test copayment for mid-income family of 4"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=4)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        # $3,000/month income
        self.add_income(parent, 3000)
        child1 = self.add_member(screen, "child", 3, has_income=False)
        child2 = self.add_member(screen, "child", 5, has_income=False)

        calc = self.make_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        # $3000 falls in bracket ((2780, 3174), 95)
        self.assertEqual(copayment, 95)

    def test_copayment_at_bracket_boundary_lower(self):
        """Test copayment at lower boundary of income bracket"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=3)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        # Exactly at bracket minimum: ((1985, 2312), 42)
        self.add_income(parent, 1985)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 42)

    def test_copayment_at_bracket_boundary_upper(self):
        """Test copayment at upper boundary of income bracket"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=3)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        # Exactly at bracket maximum: ((1985, 2312), 42)
        self.add_income(parent, 2312)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 42)

    def test_copayment_highest_bracket(self):
        """Test copayment at highest income bracket"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=10)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        # At highest bracket for family of 10
        self.add_income(parent, 13000)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 836)

    def test_household_value_returns_negative_copayment(self):
        """Test household_value returns negative annual copayment"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        child = self.add_member(screen, "child", 3, has_income=False)

        calc = self.make_calculator(screen)
        household_value = calc.household_value()
        # $2000/month, family of 2: copayment = $37/month
        # household_value should be -$37 * 12 = -$444
        self.assertEqual(household_value, -37 * 12)

    def test_net_benefit_calculation(self):
        """Test that total value correctly calculates net benefit (subsidy - copayment)"""
        screen = self.make_screen(zipcode="60601", county="Cook", household_size=2)
        parent = self.add_member(screen, "headOfHousehold", 30, student=False, has_income=True)
        self.add_income(parent, 2000)
        # Infant in Cook County
        infant = self.add_member(screen, "child", 1, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        # Subsidy: $1474 * 12 = $17,688
        # Copayment: $37 * 12 = $444
        # Net benefit: $17,688 - $444 = $17,244
        expected_net = (1474 * 12) - (37 * 12)
        self.assertEqual(eligibility.value, expected_net)
