from django.test import TestCase
from programs.programs.il.ccap.calculator import IlChildCareAssistanceProgram
from screener.models import Screen, HouseholdMember, IncomeStream, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.programs.calc import Eligibility
from programs.util import Dependencies


class TestIlChildCareAssistanceProgram(TestCase):
    """Test cases for Illinois Child Care Assistance Program calculator"""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests"""
        # Create white label for Illinois
        cls.il_white_label = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")

        # Create FPL year for testing
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")

        # Create program using the manager method
        cls.program = Program.objects.new_program(white_label="il", name_abbreviated="il_ccap")
        # Set the FPL year for the program
        cls.program.year = cls.fpl_year
        cls.program.save()

    def setUp(self):
        """Set up test fixtures for each test method"""

        # Basic eligible household: parent with child in Cook County
        self.eligible_screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )

        # Head of household with earned income (employed)
        self.parent = HouseholdMember.objects.create(
            screen=self.eligible_screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )

        # Add income below 225% FPL
        IncomeStream.objects.create(
            screen=self.eligible_screen,
            household_member=self.parent,
            type="wages",
            amount=2000,  # $2000/month = $24,000/year
            frequency="monthly",
        )

        # Eligible child (3 years old)
        self.child = HouseholdMember.objects.create(
            screen=self.eligible_screen,
            relationship="child",
            age=3,
            has_income=False,
        )

    def create_calculator(self, screen):
        """Helper method to create calculator instance with required dependencies"""
        data = {}
        missing_dependencies = Dependencies()
        return IlChildCareAssistanceProgram(screen, self.program, data, missing_dependencies)

    # County Group Tests
    def test_get_county_group_ia(self):
        """Test county group IA (highest rate counties)"""
        calc = self.create_calculator(self.eligible_screen)
        self.assertEqual(calc.get_county_group("Cook"), "GROUP_1A")
        self.assertEqual(calc.get_county_group("DuPage"), "GROUP_1A")
        self.assertEqual(calc.get_county_group("Lake"), "GROUP_1A")

    def test_get_county_group_ib(self):
        """Test county group IB (medium rate counties)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="61820",
            county="Champaign",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        calc = self.create_calculator(screen)
        self.assertEqual(calc.get_county_group("Champaign"), "GROUP_1B")
        self.assertEqual(calc.get_county_group("Peoria"), "GROUP_1B")
        self.assertEqual(calc.get_county_group("Will"), "GROUP_1B")

    def test_get_county_group_ii(self):
        """Test county group II (all other Illinois counties)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="62401",
            county="Effingham",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        calc = self.create_calculator(screen)
        self.assertEqual(calc.get_county_group("Effingham"), "GROUP_2")
        self.assertEqual(calc.get_county_group("Random County"), "GROUP_2")

    # Household Eligibility Tests
    def test_household_eligible_with_employed_parent(self):
        """Test household is eligible when parent is employed"""
        calc = self.create_calculator(self.eligible_screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)

    def test_household_eligible_with_student_parent(self):
        """Test household is eligible when parent is a student"""
        # Create new screen with student parent
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=True,
            has_income=False,
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)

    def test_household_ineligible_no_employment_or_school(self):
        """Test household is ineligible when parent is neither employed nor in school"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=False,
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    def test_household_ineligible_income_too_high(self):
        """Test household is ineligible when income exceeds 225% FPL"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        # Income well above 225% FPL
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=10000,  # $120,000/year - way above threshold
            frequency="monthly",
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    # Member Eligibility Tests
    def test_member_eligible_child_under_13(self):
        """Test child under 13 is eligible"""
        calc = self.create_calculator(self.eligible_screen)
        eligibility = calc.eligible()
        # Should have one eligible member (the 3-year-old child)
        self.assertTrue(eligibility.eligible)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 1)

    def test_member_ineligible_child_over_13(self):
        """Test child over 13 is not eligible (unless disabled)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # 14-year-old child (too old)
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=14, has_income=False)

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        # Household eligible but no eligible members
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 0)

    def test_member_eligible_disabled_child_under_19(self):
        """Test disabled child under 19 is eligible"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # 16-year-old with disability
        child = HouseholdMember.objects.create(
            screen=screen,
            relationship="child",
            age=16,
            has_income=False,
            disabled=True,
        )

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 1)

    def test_member_ineligible_wrong_relationship(self):
        """Test non-child household members are not eligible"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=3,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # Adult sibling (not eligible relationship)
        sibling = HouseholdMember.objects.create(screen=screen, relationship="sibling", age=25, has_income=False)

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        # No eligible members
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 0)

    def test_member_eligible_various_child_relationships(self):
        """Test various child relationships are eligible"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=5,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )

        # Various eligible child relationships
        child1 = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)
        child2 = HouseholdMember.objects.create(screen=screen, relationship="stepChild", age=5, has_income=False)
        child3 = HouseholdMember.objects.create(screen=screen, relationship="fosterChild", age=7, has_income=False)
        child4 = HouseholdMember.objects.create(screen=screen, relationship="grandChild", age=2, has_income=False)

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        self.assertTrue(eligibility.eligible)
        # All 4 children should be eligible
        eligible_count = sum(1 for m in eligibility.eligible_members if m.eligible)
        self.assertEqual(eligible_count, 4)

    # Value Calculation Tests
    def test_member_value_cook_county_infant(self):
        """Test benefit value for infant in Cook County (Group IA)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # Infant (1 year old)
        infant = HouseholdMember.objects.create(screen=screen, relationship="child", age=1, has_income=False)

        calc = self.create_calculator(screen)
        value = calc.member_value(infant)
        # $1474/month * 12 = $17,688/year
        self.assertEqual(value, 1474 * 12)

    def test_member_value_cook_county_preschool(self):
        """Test benefit value for preschooler in Cook County (Group IA)"""
        calc = self.create_calculator(self.eligible_screen)
        value = calc.member_value(self.child)
        # $1012/month * 12 = $12,144/year for 3-year-old
        self.assertEqual(value, 1012 * 12)

    def test_member_value_champaign_county_school_age(self):
        """Test benefit value for school-age child in Champaign County (Group IB)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="61820",
            county="Champaign",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # School-age child (8 years old)
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=8, has_income=False)

        calc = self.create_calculator(screen)
        value = calc.member_value(child)
        # $484/month * 12 = $5,808/year
        self.assertEqual(value, 484 * 12)

    def test_member_value_rural_county_twos(self):
        """Test benefit value for 2-year-old in rural county (Group II)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="62401",
            county="Effingham",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # 2-year-old
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=2, has_income=False)

        calc = self.create_calculator(screen)
        value = calc.member_value(child)
        # $1012/month * 12 = $12,144/year
        self.assertEqual(value, 1012 * 12)

    def test_member_value_too_old_returns_zero(self):
        """Test benefit value is 0 for children over 13 (non-disabled)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # 15-year-old (too old, not disabled)
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=15, has_income=False)

        calc = self.create_calculator(screen)
        value = calc.member_value(child)
        self.assertEqual(value, 0)

    def test_total_value_multiple_children(self):
        """Test total benefit value for household with multiple children"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=4,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )

        # Multiple children at different ages
        infant = HouseholdMember.objects.create(screen=screen, relationship="child", age=1, has_income=False)
        preschooler = HouseholdMember.objects.create(screen=screen, relationship="child", age=4, has_income=False)
        school_age = HouseholdMember.objects.create(screen=screen, relationship="child", age=8, has_income=False)

        calc = self.create_calculator(screen)
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
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        # Income at 100% FPL for family of 2 (approximately $1,580/month in 2025)
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=1500,
            frequency="monthly",
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 1)

    def test_copayment_just_above_100_percent_fpl(self):
        """Test copayment follows table for income just above 100% FPL"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        # $1,800/month - above 100% FPL, should use table
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=1800,
            frequency="monthly",
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        # $1800 falls in bracket ((1764, 2055), 37)
        self.assertEqual(copayment, 37)

    def test_copayment_mid_income_family_of_4(self):
        """Test copayment for mid-income family of 4"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=4,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        # $3,000/month income
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=3000,
            frequency="monthly",
        )
        child1 = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)
        child2 = HouseholdMember.objects.create(screen=screen, relationship="child", age=5, has_income=False)

        calc = self.create_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        # $3000 falls in bracket ((2780, 3174), 95)
        self.assertEqual(copayment, 95)

    def test_copayment_at_bracket_boundary_lower(self):
        """Test copayment at lower boundary of income bracket"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=3,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        # Exactly at bracket minimum: ((1985, 2312), 42)
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=1985,
            frequency="monthly",
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 42)

    def test_copayment_at_bracket_boundary_upper(self):
        """Test copayment at upper boundary of income bracket"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=3,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        # Exactly at bracket maximum: ((1985, 2312), 42)
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2312,
            frequency="monthly",
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 42)

    def test_copayment_highest_bracket(self):
        """Test copayment at highest income bracket"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=10,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        # At highest bracket for family of 10
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=13000,
            frequency="monthly",
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        copayment = calc.calculate_monthly_copayment()
        self.assertEqual(copayment, 836)

    def test_household_value_returns_negative_copayment(self):
        """Test household_value returns negative annual copayment"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        child = HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        calc = self.create_calculator(screen)
        household_value = calc.household_value()
        # $2000/month, family of 2: copayment = $37/month
        # household_value should be -$37 * 12 = -$444
        self.assertEqual(household_value, -37 * 12)

    def test_net_benefit_calculation(self):
        """Test that total value correctly calculates net benefit (subsidy - copayment)"""
        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="60601",
            county="Cook",
            household_size=2,
            white_label=self.il_white_label,
            completed=False,
        )
        parent = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=parent,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        # Infant in Cook County
        infant = HouseholdMember.objects.create(screen=screen, relationship="child", age=1, has_income=False)

        calc = self.create_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        # Subsidy: $1474 * 12 = $17,688
        # Copayment: $37 * 12 = $444
        # Net benefit: $17,688 - $444 = $17,244
        expected_net = (1474 * 12) - (37 * 12)
        self.assertEqual(eligibility.value, expected_net)
