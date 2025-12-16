from django.test import TestCase
from programs.programs.nc.nc_head_start.calculator import NCHeadStart
from screener.models import Screen, HouseholdMember, IncomeStream, Expense, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies
from unittest.mock import patch
from datetime import datetime


class TestNCHeadStart(TestCase):
    """
    Test cases for NC Head Start Program Calculator

    These tests verify:
    - Location eligibility (county has market rates)
    - Presumptive eligibility (SNAP, TANF, SSI)
    - Income eligibility (130% FPL)
    - Housing cost adjustment (rent > 30% of income)
    - Age eligibility (0-5, 6-17 with disability, pregnant)
    - Value calculation (estimated annual savings by county and age)
    """

    # 2025 Market rates from Google Sheet for 4-star child care centers
    MARKET_RATES_DATA = {
        "Alamance County": {
            "infant": 956,  # 0-1 years
            "toddler": 942,  # 2 years
            "preschool": 844,  # 3-5 years
            "school_age": 718,  # 6-12 years
            "teen_disabled": 323,  # 12-17 with disabilities
        },
        "Alexander County": {
            "infant": 726,
            "toddler": 682,
            "preschool": 634,
            "school_age": 585,
            "teen_disabled": 263,
        },
        "Bertie County": {
            "infant": 827,
            "toddler": 769,
            "preschool": 750,
            "school_age": 595,
            "teen_disabled": 268,
        },
        "Durham County": {
            "infant": 1401,
            "toddler": 1259,
            "preschool": 1167,
            "school_age": 845,
            "teen_disabled": 380,
        },
    }

    @classmethod
    def setUpTestData(cls):
        """Set up data for the entire TestCase - runs once for all tests"""
        # Create white label for North Carolina
        cls.nc_white_label = WhiteLabel.objects.create(name="North Carolina", code="nc", state_code="NC")

        # Create FPL year for testing
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")

        # Create the NC Head Start program
        cls.program = Program.objects.new_program(white_label="nc", name_abbreviated="nc_head_start")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def setUp(self):
        """Set up data for each individual test - runs before each test method"""
        # This will be overridden in each test
        pass

    def create_household_member(
        self,
        screen,
        relationship="child",
        age=4,
        pregnant=False,
        disabled=False,
        has_income=False,
        insurance_type=None,
        birth_year=None,
        birth_month=None,
    ):
        """Helper method to create household members"""
        # Calculate birth_year_month from age if not provided
        if birth_year and birth_month:
            birth_year_month = datetime(year=birth_year, month=birth_month, day=1).date()
        else:
            current_year = datetime.now().year
            birth_year_month = datetime(year=current_year - age, month=1, day=1).date()

        member = HouseholdMember.objects.create(
            screen=screen,
            relationship=relationship,
            age=age,
            pregnant=pregnant,
            disabled=disabled,
            has_income=has_income,
            birth_year_month=birth_year_month,
        )

        return member

    def add_income(self, screen, member, income_type, amount, frequency="monthly"):
        """Helper method to add income to a household member"""
        return IncomeStream.objects.create(
            screen=screen, household_member=member, type=income_type, amount=amount, frequency=frequency
        )

    def add_expense(self, screen, member, expense_type, amount, frequency="monthly"):
        """Helper method to add expenses to a household member"""
        return Expense.objects.create(
            screen=screen, household_member=member, type=expense_type, amount=amount, frequency=frequency
        )

    # ============================================================================
    # TEST CASE 1: Pregnant with SSI (Presumptive Eligibility)
    # ============================================================================
    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_case_1_pregnant_with_ssi_eligible(self, mock_fetch):
        """
        Test Case 1: Bertie County, HH=2
        Person 1: Jan 2000, pregnant, no insurance, Wages $2,220/month (125% FPL)
        Person 2: Spouse, Jan 2000, Medicaid, SSI $393/month

        Expected: ELIGIBLE
        - Household receives SSI (presumptive eligibility) so income check is skipped
        - Infant rate (pregnant person): $827/month
        - Estimated savings: $827/month × 12 = $9,924/year
        """
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27805",
            county="Bertie County",
            household_size=2,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
            has_ssi=True,  # Household receives SSI - presumptive eligibility
        )

        # Person 1: Pregnant person with wages
        person1 = self.create_household_member(
            screen=screen,
            relationship="headOfHousehold",
            age=25,
            pregnant=True,
            has_income=True,
            birth_year=2000,
            birth_month=1,
        )
        self.add_income(screen, person1, "wages", 2220, "monthly")

        # Person 2: Spouse with SSI
        person2 = self.create_household_member(
            screen=screen, relationship="spouse", age=25, has_income=True, birth_year=2000, birth_month=1
        )
        self.add_income(screen, person2, "ssi", 393, "monthly")

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Should be eligible due to SSI (presumptive eligibility)
        self.assertTrue(eligibility.eligible, "Should be eligible due to SSI presumptive eligibility")
        # Value should be infant rate * 12 months = $827 * 12 = $9,924
        self.assertEqual(eligibility.value, 827 * 12, "Estimated value should be $9,924 (infant rate × 12)")

    # ============================================================================
    # TEST CASE 2: Over Income Without Presumptive Eligibility
    # ============================================================================
    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_case_2_over_income_not_eligible(self, mock_fetch):
        """
        Test Case 2: Bertie County, HH=2
        Person 1: Jan 2000, pregnant, no insurance, Wages $2,330/month (132% FPL)
        Person 2: Spouse, Jan 2000, Medicaid, no income

        Expected: NOT ELIGIBLE
        - Income is above 130% FPL ($2,330 × 12 = $27,960 > 130% FPL for HH of 2)
        - No presumptive eligibility (no SNAP/TANF/SSI)
        - No housing cost adjustment to reduce income
        """
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27805",
            county="Bertie County",
            household_size=2,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
            has_ssi=False,
            has_snap=False,
            has_tanf=False,
        )

        # Person 1: Pregnant person with wages above 130% FPL
        person1 = self.create_household_member(
            screen=screen,
            relationship="headOfHousehold",
            age=25,
            pregnant=True,
            has_income=True,
            birth_year=2000,
            birth_month=1,
        )
        self.add_income(screen, person1, "wages", 2330, "monthly")

        # Person 2: Spouse with no income
        person2 = self.create_household_member(
            screen=screen, relationship="spouse", age=25, has_income=False, birth_year=2000, birth_month=1
        )

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Should NOT be eligible - income too high (132% FPL > 130% FPL)
        self.assertFalse(
            eligibility.eligible, "Should NOT be eligible - income exceeds 130% FPL without housing adjustment"
        )

    # ============================================================================
    # TEST CASE 3: Over Income with Low Rent (Not Enough Adjustment)
    # ============================================================================
    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_case_3_over_income_low_rent_not_eligible(self, mock_fetch):
        """
        Test Case 3: Durham County, HH=3
        Person 1: Jan 2000, no insurance, Wages $3,500/month + Child Support $1,000/month
        Person 2: Child, Jan 2019, Medicaid, no income
        Person 3: Child, Jan 2022, Medicaid, no income
        Expenses: Rent $1,100/month

        Expected: NOT ELIGIBLE
        - Countable income: $3,500/month (child support NOT counted)
        - Gross annual: $3,500 × 12 = $42,000
        - 130% FPL for HH of 3: $26,650 × 1.3 = $34,645
        - 30% of gross income: $3,500 × 0.3 = $1,050/month
        - Rent: $1,100/month exceeds $1,050 by only $50/month
        - Housing adjustment: $50 × 12 = $600/year
        - Adjusted income: $42,000 - $600 = $41,400 (still > $34,645)
        - Result: NOT ELIGIBLE
        """
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27706",
            county="Durham County",
            household_size=3,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
        )

        # Person 1: Parent with wages and child support
        person1 = self.create_household_member(
            screen=screen, relationship="headOfHousehold", age=25, has_income=True, birth_year=2000, birth_month=1
        )
        self.add_income(screen, person1, "wages", 3500, "monthly")
        # Child support is NOT a countable income type
        self.add_income(screen, person1, "childSupport", 1000, "monthly")
        self.add_expense(screen, person1, "rent", 1100, "monthly")

        # Person 2: Child born Jan 2019 (age 6) - not eligible (too old, no disability)
        person2 = self.create_household_member(
            screen=screen, relationship="child", age=6, birth_year=2019, birth_month=1
        )

        # Person 3: Child born Jan 2022 (age 3) - eligible
        person3 = self.create_household_member(
            screen=screen, relationship="child", age=3, birth_year=2022, birth_month=1
        )

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Should NOT be eligible - rent adjustment not enough
        self.assertFalse(
            eligibility.eligible,
            "Should NOT be eligible - rent adjustment of $50/month not enough to bring income below 130% FPL",
        )

    # ============================================================================
    # TEST CASE 4: Over Income with High Rent (Housing Cost Adjustment)
    # ============================================================================
    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_case_4_over_income_high_rent_eligible(self, mock_fetch):
        """
        Test Case 4: Durham County, HH=3
        Person 1: Jan 2000, no insurance, Wages $3,500/month + Child Support $1,000/month
        Person 2: Child, Jan 2019, Medicaid, no income
        Person 3: Child, Jan 2022, Medicaid, no income
        Expenses: Rent $2,000/month

        Expected: ELIGIBLE
        - Countable income: $3,500/month (child support NOT counted)
        - Gross annual: $3,500 × 12 = $42,000 (157% FPL)
        - 130% FPL for HH of 3: $26,650 × 1.3 = $34,645
        - 30% of gross income: $3,500 × 0.3 = $1,050/month
        - Rent: $2,000/month exceeds $1,050 by $950/month
        - Housing adjustment: $950 × 12 = $11,400/year
        - Adjusted income: $42,000 - $11,400 = $30,600 (114% FPL) - ELIGIBLE!

        Eligible children:
        - Person 2 (age 6): NOT eligible (school-age, no disability)
        - Person 3 (age 3): ELIGIBLE (preschool age)

        Value calculation:
        - Only Person 3 is eligible: preschool rate = $1,000/month
        - Estimated savings: $1,000 × 12 = $12,000/year
        """
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27706",
            county="Durham County",
            household_size=3,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
        )

        # Person 1: Parent with wages and child support
        person1 = self.create_household_member(
            screen=screen, relationship="headOfHousehold", age=25, has_income=True, birth_year=2000, birth_month=1
        )
        self.add_income(screen, person1, "wages", 3500, "monthly")
        self.add_income(screen, person1, "childSupport", 1000, "monthly")  # Not counted
        self.add_expense(screen, person1, "rent", 2000, "monthly")

        # Person 2: Child born Jan 2019 (age 6) - not eligible (too old, no disability)
        person2 = self.create_household_member(
            screen=screen, relationship="child", age=6, birth_year=2019, birth_month=1
        )

        # Person 3: Child born Jan 2022 (age 3) - eligible
        person3 = self.create_household_member(
            screen=screen, relationship="child", age=3, birth_year=2022, birth_month=1
        )

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Should be ELIGIBLE due to housing cost adjustment
        self.assertTrue(
            eligibility.eligible, "Should be ELIGIBLE - housing cost adjustment brings income below 130% FPL"
        )

        # Should have 1 eligible child (the 3-year-old) - parent doesn't count since not pregnant
        eligible_children = [m for m in eligibility.eligible_members if m.member.relationship == "child" and m.eligible]
        self.assertEqual(len(eligible_children), 1, "Should have 1 eligible child (3-year-old)")

        # Value should be preschool rate * 12
        # Durham County preschool rate: $1,167/month (1000 in MARKET_RATES_DATA)
        self.assertEqual(eligibility.value, 1167 * 12, "Estimated value should be $14,004 (preschool rate × 12)")

    # ============================================================================
    # ADDITIONAL TESTS: Age Eligibility
    # ============================================================================
    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_child_age_0_to_5_eligible(self, mock_fetch):
        """Test that children aged 0-5 are eligible"""
        mock_fetch.return_value = self.MARKET_RATES_DATA

        # Test various ages 0-5
        ages_to_test = {
            0: "infant",
            1: "infant",
            2: "toddler",
            3: "preschool",
            4: "preschool",
            5: "preschool",
        }

        for age, age_category in ages_to_test.items():
            with self.subTest(age=age):
                screen = Screen.objects.create(
                    agree_to_tos=True,
                    zipcode="27706",
                    county="Durham County",
                    household_size=1,
                    household_assets=0,
                    white_label=self.nc_white_label,
                    completed=False,
                )

                child = self.create_household_member(
                    screen=screen, relationship="child", age=age, birth_year=2025 - age, birth_month=1
                )

                calculator = NCHeadStart(screen, self.program, {}, Dependencies())
                eligibility = calculator.calc()

                # Check that child is eligible
                self.assertTrue(len(eligibility.eligible_members) > 0, f"Child age {age} should be eligible")

    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_pregnant_member_eligible(self, mock_fetch):
        """Test that pregnant household member is eligible regardless of age"""
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27706",
            county="Durham County",
            household_size=1,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
        )

        # Pregnant 25-year-old (outside normal age range for Head Start)
        pregnant_person = self.create_household_member(
            screen=screen, relationship="headOfHousehold", age=25, pregnant=True, birth_year=2000, birth_month=1
        )

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Should have 1 eligible member (the pregnant person using infant rate)
        self.assertEqual(len(eligibility.eligible_members), 1, "Pregnant person should be eligible (uses infant rate)")

    # ============================================================================
    # ADDITIONAL TESTS: County Market Rate Data
    # ============================================================================
    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_multiple_children_different_ages(self, mock_fetch):
        """Test value calculation with multiple children at different ages"""
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27806",
            county="Alamance County",
            household_size=3,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
        )

        # Parent
        parent = self.create_household_member(screen=screen, relationship="headOfHousehold", age=30)

        # Create multiple children at different ages
        # Child 1: age 1 (infant rate: $956/month)
        child1 = self.create_household_member(
            screen=screen, relationship="child", age=1, birth_year=2024, birth_month=1
        )

        # Child 2: age 2 (toddler rate: $942/month)
        child2 = self.create_household_member(
            screen=screen, relationship="child", age=2, birth_year=2023, birth_month=1
        )

        # Child 3: age 4 (preschool rate: $844/month)
        child3 = self.create_household_member(
            screen=screen, relationship="child", age=4, birth_year=2021, birth_month=1
        )

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Expected value: (956 + 942 + 844) * 12 = 2742 * 12 = $32,904
        expected_value = (956 + 942 + 844) * 12

        eligible_children = [m for m in eligibility.eligible_members if m.member.relationship == "child"]
        self.assertEqual(len(eligible_children), 3, "Should have 3 eligible children")
        self.assertEqual(eligibility.value, expected_value, f"Estimated value should be ${expected_value}")

    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_ineligible_county(self, mock_fetch):
        """Test household in county without Head Start market rates"""
        # Mock with limited counties (exclude the test county)
        mock_fetch.return_value = {
            "Alamance County": self.MARKET_RATES_DATA["Alamance County"],
            "Alexander County": self.MARKET_RATES_DATA["Alexander County"],
        }

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27701",
            county="Wake County",  # Not in market rates
            household_size=2,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
        )

        # Parent
        parent = self.create_household_member(screen=screen, relationship="headOfHousehold", age=30)

        # Eligible child
        child = self.create_household_member(screen=screen, relationship="child", age=4, birth_year=2021, birth_month=1)

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Should NOT be eligible - county not in market rates
        self.assertFalse(eligibility.eligible, "Should NOT be eligible - county not in market rates")

    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_countable_income_types_only(self, mock_fetch):
        """Test that only specific income types are counted"""
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27806",
            county="Alamance County",
            household_size=2,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
        )

        # Parent with income
        parent = self.create_household_member(screen=screen, relationship="headOfHousehold", age=30, has_income=True)

        # Add countable income (wages) - $2,000/month = $24,000/year
        self.add_income(screen, parent, "wages", 2000, "monthly")

        # Add non-countable income (child support) - should be ignored
        self.add_income(screen, parent, "childSupport", 1000, "monthly")

        # Child
        child = self.create_household_member(screen=screen, relationship="child", age=4, birth_year=2021, birth_month=1)

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())
        eligibility = calculator.calc()

        # Should be eligible because only wages count ($2,000 × 12 = $24,000)
        # 130% FPL for HH of 2: $21,150 × 1.3 = $27,495
        # $24,000 < $27,495, so ELIGIBLE
        # Child support is NOT counted
        self.assertTrue(
            eligibility.eligible, "Should be eligible - only wages ($2,000/month) are counted, child support ignored"
        )

    @patch("programs.programs.nc.nc_head_start.calculator.NcHeadStartMarketRatesCache.fetch")
    def test_member_value_returns_zero(self, mock_fetch):
        """Test that member_value returns 0 (all value at household level)"""
        mock_fetch.return_value = self.MARKET_RATES_DATA

        screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="27806",
            county="Alamance County",
            household_size=2,
            household_assets=0,
            white_label=self.nc_white_label,
            completed=False,
        )

        # Parent
        parent = self.create_household_member(screen=screen, relationship="headOfHousehold", age=30)

        # Child
        child = self.create_household_member(screen=screen, relationship="child", age=4, birth_year=2021, birth_month=1)

        calculator = NCHeadStart(screen, self.program, {}, Dependencies())

        # member_value should return 0 to avoid double-counting
        self.assertEqual(
            calculator.member_value(child), 0, "member_value should return 0 (value calculated at household level)"
        )
