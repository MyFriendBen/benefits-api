from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase, add_income
from programs.programs.white_labels.co.upk.calculator import UniversalPreschool


class TestCoUniversalPreschool(CustomCalculatorTestCase):
    """Test cases for Colorado Universal Preschool Program calculator"""

    calculator_class = UniversalPreschool
    program_code = "upk"
    white_label_code = "co"
    state_code = "CO"

    def test_member_value_3yo_foster_child_income_270_fpl_returns_10_hours(self):
        """Test 3-year-old foster child with HH income 270% FPL or less returns 10 hours"""

        screen = self.make_screen(household_size=2, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=True)

        # Add income below 270% FPL
        add_income(parent, 4500, income_type="wages", frequency="monthly")  # 54,000/yearly

        # Eligible child (3 years old and foster child)
        child = self.add_member(screen, relationship="fosterChild", age=3, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_10_hr)

    def test_member_value_3yo_income_100_fpl_returns_10_hours(self):
        """Test 3-year-old child with HH income ≤100% FPL returns 10 hours"""

        screen = self.make_screen(household_size=2, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=True)

        # Add income below 100% FPL
        add_income(parent, 1700, income_type="wages", frequency="monthly")  # 20,400/yearly

        # Eligible child (3 years old)
        child = self.add_member(screen, relationship="child", age=3, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_10_hr)

    def test_member_value_4yo_foster_income_270_fpl_returns_30_hours(self):
        """Test 4-year-old foster child with HH income 270% FPL or less returns 30 hours"""

        screen = self.make_screen(household_size=3, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=True)

        # Add income below 270% FPL
        add_income(parent, 5600, income_type="wages", frequency="monthly")  # 67,200 yearly

        # Eligible child (4 years old and foster child)
        child = self.add_member(screen, relationship="fosterChild", age=4, has_income=False)

        spouse = self.add_member(screen, relationship="spouse", age=21, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_30_hr)

    def test_member_value_4yo_income_100_fpl_returns_30_hours(self):
        """Test 4-year-old child with HH income 100% FPL or less returns 30 hours"""

        screen = self.make_screen(household_size=2, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=True)

        # Add income below 100% FPL
        add_income(parent, 1700, income_type="wages", frequency="monthly")  # 20,400 yearly

        # Eligible child (4 years old)
        child = self.add_member(screen, relationship="child", age=4, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_30_hr)

    def test_member_value_4yo_non_qualifying_returns_15_hours(self):
        """Test 4-year-old child with HH income above 270% FPL returns 15 hours"""

        screen = self.make_screen(household_size=2, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=True)

        # Add income above 270% FPL
        add_income(parent, 5000, income_type="wages", frequency="monthly")  # 60,000 yearly
        # Eligible child (4 years old)
        child = self.add_member(screen, relationship="child", age=4, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        value = calc.member_value(child)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(value, UniversalPreschool.amount_15_hr)

    # Eligibility Tests
    def test_eligibility_3yo_above_270_fpl_not_eligible(self):
        """Test 3-year-old child with HH income above 270% FPL is not eligible"""
        screen = self.make_screen(household_size=2, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=True)

        add_income(parent, 5000, income_type="wages", frequency="monthly")  # 60,000

        child = self.add_member(screen, relationship="child", age=3, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    def test_age_2_not_eligible(self):
        """Test 2-year-old is not eligible (below minimum age)"""

        screen = self.make_screen(household_size=2, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=True)

        # Too young for preschool
        child = self.add_member(screen, relationship="fosterChild", age=2, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)

    def test_age_5_not_eligible(self):
        """Test 5-year-old is not eligible (above maximum age)"""
        screen = self.make_screen(household_size=2, zipcode="80016", county="Elbert County")

        parent = self.add_member(screen, relationship="headOfHousehold", age=32, has_income=False)

        child = self.add_member(screen, relationship="child", age=5, has_income=False)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        self.assertFalse(eligibility.eligible)
