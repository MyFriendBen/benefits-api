from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase


from programs.programs.white_labels.wa.wsos_grd.calculator import WaWsosGrd
from programs.framework.pe_dependencies import member


class TestWaWsosGrd(CustomCalculatorTestCase):
    """
    Unit tests for the WA WSOS Graduate Scholarship calculator.

    Covers the three screener-checkable gates (student, income <= 155% MFI for
    household size, household value), boundary cases against the 2026 published
    MFI table, and the linear extension for household sizes above the table.

    These map to the spec.md scenarios but call the calculator directly; the full
    end-to-end browser flow is exercised separately via Playwright.
    """

    calculator_class = WaWsosGrd
    program_code = "wa_wsos_grd"
    white_label_code = "wa"
    state_code = "WA"
    needs_program_row = False
    default_zipcode = "98101"
    default_county = "King"

    # --- Eligibility ---------------------------------------------------------

    def test_eligible_single_student_below_125_pct_mfi(self):
        """Scenario 1: WA student, 1-person household, $4k/mo wages -> well below 125% MFI ($90,500/yr)."""
        screen = self.make_screen()
        self.add_member(screen, student=True, monthly_income=4000, age=36)

        eligibility = self.make_calculator(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_ineligible_not_a_student(self):
        """Scenario 2: applicant is not a student -> per-member gate fails -> household ineligible."""
        screen = self.make_screen()
        self.add_member(screen, student=False, monthly_income=4000, age=36)

        eligibility = self.make_calculator(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_single_student_above_155_pct_mfi(self):
        """Scenario 3: 1-person student, $10k/mo = $120k/yr > 155% cap of $112,500."""
        screen = self.make_screen()
        self.add_member(screen, student=True, monthly_income=10000, age=36)

        eligibility = self.make_calculator(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_eligible_three_person_household_at_125_pct_mfi_boundary(self):
        """
        Scenario 4: 3-person student household at exactly the 125% MFI annualized
        from $12,208/mo ($146,496/yr) -> at or below 155% cap of $181,500. Eligible.
        """
        screen = self.make_screen(household_size=3, zipcode="98501", county="Thurston")
        self.add_member(screen, student=True, monthly_income=12208, age=36)
        self.add_member(screen, relationship="spouse", age=34, student=False)
        self.add_member(screen, relationship="child", age=3, student=False)

        eligibility = self.make_calculator(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_single_student_in_expanded_126_to_155_band(self):
        """
        Scenario 5: $8,500/mo = $102,000/yr. Above 125% cap ($90,500) but below 155%
        cap ($112,500) for 1-person household. Calculator returns eligible; UI surfaces
        the hardship caveat for the 126-155% MFI band.
        """
        screen = self.make_screen()
        self.add_member(screen, student=True, monthly_income=8500, age=36)

        eligibility = self.make_calculator(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_three_person_household_in_expanded_band(self):
        """
        Scenario 6: 3-person household, $13k/mo = $156k/yr. Above the 3-person
        125% MFI threshold ($146,500/yr) but below the 3-person 155% MFI cap
        ($181,500/yr), so this exercises the 126-155% expanded eligibility band.
        Eligible (UI surfaces the hardship caveat).
        """
        screen = self.make_screen(household_size=3, zipcode="98501", county="Thurston")
        self.add_member(screen, student=True, monthly_income=13000, age=36)
        self.add_member(screen, relationship="spouse", age=34, student=False)
        self.add_member(screen, relationship="child", age=3, student=False)

        eligibility = self.make_calculator(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_ineligible_three_person_household_above_155_pct_mfi(self):
        """Scenario 7: 3-person student household, $16k/mo = $192k/yr > 155% cap of $181,500."""
        screen = self.make_screen(household_size=3, zipcode="98501", county="Thurston")
        self.add_member(screen, student=True, monthly_income=16000, age=36)
        self.add_member(screen, relationship="spouse", age=34, student=False)
        self.add_member(screen, relationship="child", age=3, student=False)

        eligibility = self.make_calculator(screen).eligible()

        self.assertFalse(eligibility.eligible)

    # --- Value ---------------------------------------------------------------

    def test_value_is_25000_lump_sum(self):
        """Eligible household returns the published $25,000 lump-sum scholarship value."""
        screen = self.make_screen()
        self.add_member(screen, student=True, monthly_income=4000, age=36)

        calc = self.make_calculator(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 25_000)

    # --- MFI table boundaries ------------------------------------------------

    def test_income_limit_table_lookup(self):
        """All 6 published table sizes return the documented 155% MFI value verbatim."""
        for size, expected in WaWsosGrd.MFI_155_BY_SIZE.items():
            screen = self.make_screen(household_size=size)
            self.assertEqual(self.make_calculator(screen).income_limit_155(), expected)

    def test_income_limit_extension_above_table(self):
        """
        Sizes above the published table (1-6) extend by the documented per-person
        increment so a 7+ person household is not silently denied or crashed.
        """
        screen = self.make_screen(household_size=8)
        expected = WaWsosGrd.MFI_155_BY_SIZE[6] + 2 * WaWsosGrd.MFI_155_PER_EXTRA_PERSON_ABOVE_TABLE
        self.assertEqual(self.make_calculator(screen).income_limit_155(), expected)
