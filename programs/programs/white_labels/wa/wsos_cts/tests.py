from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase, add_income
from decimal import Decimal


from programs.programs.white_labels.wa.wsos_cts.calculator import WaWsosCts
from programs.framework.pe_dependencies import member


class TestWaWsosCts(CustomCalculatorTestCase):
    """Unit tests for WA WSOS Career & Technical Scholarship (CTS)."""

    calculator_class = WaWsosCts
    program_code = "wa_wsos_cts"
    white_label_code = "wa"
    state_code = "WA"
    needs_program_row = False
    default_zipcode = "98101"
    default_county = "King"

    def test_no_published_lump_sum_value(self):
        self.assertEqual(WaWsosCts.amount, 0)

    def test_dependencies(self):
        self.assertIn("income_amount", WaWsosCts.dependencies)
        self.assertIn("income_frequency", WaWsosCts.dependencies)
        self.assertIn("household_size", WaWsosCts.dependencies)

    # --- spec.md scenarios ---------------------------------------------------

    def test_scenario_1_eligible_student_below_mfi(self):
        """Scenario 1: student, $2,500/mo — under 1-person 125% MFI."""
        screen = self.make_screen()
        self.add_member(screen, age=24, student=True, monthly_income=2500)
        self.assertTrue(self.make_calculator(screen).eligible().eligible)

    def test_scenario_2_ineligible_not_a_student(self):
        """Scenario 2: not a student."""
        screen = self.make_screen()
        self.add_member(screen, age=36, student=False, monthly_income=3000)
        self.assertFalse(self.make_calculator(screen).eligible().eligible)

    def test_scenario_3_ineligible_income_above_mfi(self):
        """Scenario 3: student, $8,000/mo — above 125% MFI (no expanded path)."""
        screen = self.make_screen()
        self.add_member(screen, age=24, student=True, monthly_income=8000)
        self.assertFalse(self.make_calculator(screen).eligible().eligible)

    def test_scenario_4_three_person_at_exact_mfi_boundary(self):
        """Scenario 4: 3-person HH at exactly $146,500/yr — spec lists ~$12,208/mo (rounded); * 12 ≠ cap.

        Income streams store amounts to cents; `146500/12` is not representable as an exact annual sum in
        monthly form. Use a yearly wage of $146,500 so gross income equals the MFI cap and `<=` is tested.
        """
        screen = self.make_screen(household_size=3, zipcode="98501", county="Thurston")
        head = self.add_member(screen, age=31, student=True, monthly_income=0)
        add_income(head, Decimal("146500"), income_type="wages", frequency="yearly")
        self.add_member(screen, relationship="spouse", age=30, student=False)
        self.add_member(screen, relationship="child", age=3, student=False)
        self.assertTrue(self.make_calculator(screen).eligible().eligible)

    def test_scenario_4_three_person_one_cent_above_annual_mfi_ineligible(self):
        """Rejects income strictly above the cap (same 3p limit); would pass if ``<`` were used instead of ``<=``."""
        screen = self.make_screen(household_size=3, zipcode="98501", county="Thurston")
        head = self.add_member(screen, age=31, student=True, monthly_income=0)
        add_income(head, Decimal("146500.01"), income_type="wages", frequency="yearly")
        self.add_member(screen, relationship="spouse", age=30, student=False)
        self.add_member(screen, relationship="child", age=3, student=False)
        self.assertFalse(self.make_calculator(screen).eligible().eligible)

    def test_scenario_5_rji_candidate_still_cts_eligible(self):
        """Scenario 5: Whatcom, 2p, combined income under 2-person cap."""
        screen = self.make_screen(household_size=2, zipcode="98225", county="Whatcom")
        self.add_member(screen, age=23, student=True, monthly_income=3500)
        self.add_member(screen, relationship="parent", age=51, student=False, monthly_income=1500)
        self.assertTrue(self.make_calculator(screen).eligible().eligible)

    def test_scenario_6_four_person_above_mfi(self):
        """Scenario 6: student head $15k/mo only — over 4-person 125% MFI."""
        screen = self.make_screen(household_size=4, zipcode="98501", county="Thurston")
        self.add_member(screen, age=36, student=True, monthly_income=15000)
        self.add_member(screen, relationship="spouse", age=34, student=False)
        self.add_member(screen, relationship="child", age=7, student=False)
        self.add_member(screen, relationship="child", age=5, student=False)
        self.assertFalse(self.make_calculator(screen).eligible().eligible)

    def test_eligible_when_only_dependent_is_student(self):
        """Head not a student but a child is — base class requires one eligible member."""
        screen = self.make_screen(household_size=2)
        self.add_member(screen, age=40, student=False, monthly_income=4000)
        self.add_member(screen, relationship="child", age=18, student=True, monthly_income=0)
        self.assertTrue(self.make_calculator(screen).eligible().eligible)

    def test_income_slightly_above_limit_rejected(self):
        """Fractional excess above 125% cap must not pass (4p: $174,500.50 / year)."""
        screen = self.make_screen(household_size=4)
        self.add_member(screen, student=True, monthly_income=(174_500.50 / 12))
        self.add_member(screen, relationship="spouse", student=False, age=20)
        self.add_member(screen, relationship="child", age=10, student=False)
        self.add_member(screen, relationship="child", age=8, student=False)
        self.assertFalse(self.make_calculator(screen).eligible().eligible)

    def test_mfi_linear_extension_size_7(self):
        """Sizes above 6 extend by $28k per extra person (same rule as BaS)."""
        calc = self.make_calculator(self.make_screen(household_size=7))
        self.assertEqual(calc.income_limit_125(), 230_000 + 28_000)

    # --- Value ----------------------------------------------------------------

    def test_value_zero_when_eligible(self):
        screen = self.make_screen()
        self.add_member(screen, student=True, monthly_income=2500, age=20)
        calc = self.make_calculator(screen)
        e = calc.eligible()
        calc.value(e)
        self.assertEqual(e.value, 0)

    def test_mfi_table_matches_spec(self):
        self.assertEqual(
            WaWsosCts.MFI_125_BY_SIZE,
            {1: 90_500, 2: 118_000, 3: 146_500, 4: 174_500, 5: 202_000, 6: 230_000},
        )
