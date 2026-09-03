from decimal import Decimal

from programs.framework.base import MemberEligibility
from programs.programs.cross_white_label.nslp.wa import WaNslp
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import HouseholdMember, Screen
from screener.tests.helpers import seed_program
from screener.serializers import _write_current_benefits


class TestWaNslp(CustomCalculatorTestCase):
    calculator_class = WaNslp
    program_code = "wa_nslp"
    white_label_code = "wa"
    state_code = "WA"

    def test_eligible_by_income_below_free_tier(self):
        """Spec / validation: HH 3, one school-age child, income below reduced cap."""
        screen = self.make_screen(household_size=3, zipcode="98101", county="King County")
        self.add_income(self.add_member(screen, "headOfHousehold", 36, has_income=True), 2000, frequency="monthly")
        self.add_member(screen, "spouse", 34)
        self.add_member(screen, "child", 7)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_ineligible_monthly_income_cents_over_reduced_cap(self):
        """HH3 monthly cap $4,109 — cents must not be truncated (CodeRabbit / Decimal)."""
        screen = self.make_screen(zipcode="98103", county="King County", household_size=3)
        head = self.add_member(screen, "headOfHousehold", 39, has_income=True)
        self.add_income(head, Decimal("4109.99"), frequency="monthly")
        self.add_member(screen, "spouse", 37)
        self.add_member(screen, "child", 12)

        result = self.calculate(screen)
        self.assertFalse(result.eligible)

    def test_medicaid_does_not_confer_categorical_eligibility(self):
        """Medicaid must NOT be a categorical pathway (spec: Medicaid alone must not
        create categorical eligibility). A school-age child is present, so the only
        thing that could make this over-income HH3 eligible is wrongly treating
        Medicaid as presumptive — it stays ineligible because Medicaid isn't in
        `presumptive_eligibility`. ($4,110/mo > $4,109 monthly reduced-price cap.)"""
        seed_program(self.white_label, "wa_medicaid")
        screen = self.make_screen(
            zipcode="98103",
            county="King County",
            household_size=3,
            has_benefits="true",
        )
        _write_current_benefits(screen, ["wa_medicaid"])
        head = self.add_member(screen, "headOfHousehold", 39, has_income=True)
        self.add_income(head, 4110, frequency="monthly")
        self.add_member(screen, "spouse", 37)
        self.add_member(screen, "child", 12)

        result = self.calculate(screen)
        self.assertFalse(result.eligible)

    def test_eligible_at_reduced_monthly_cap_exact(self):
        """Regression: frequency-matched monthly must not always annualize (+$5 error)."""
        screen = self.make_screen(household_size=3, zipcode="98103", county="King County")
        head = self.add_member(screen, "headOfHousehold", 39, has_income=True)
        self.add_income(head, 4109, frequency="monthly")
        self.add_member(screen, "spouse", 37)
        self.add_member(screen, "child", 12)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_eligible_snap_categorical_high_income(self):
        seed_program(self.white_label, "wa_snap")
        screen = self.make_screen(
            household_size=3,
            zipcode="99201",
            county="Spokane County",
            has_benefits="true",
        )
        _write_current_benefits(screen, ["wa_snap"])
        head = self.add_member(screen, "headOfHousehold", 40, has_income=True)
        self.add_income(head, 7000, frequency="monthly")
        self.add_member(screen, "spouse", 39)
        self.add_member(screen, "child", 10)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_eligible_tanf_categorical(self):
        seed_program(self.white_label, "wa_tanf")
        screen = self.make_screen(household_size=3, zipcode="98901", county="Yakima County", has_benefits="true")
        _write_current_benefits(screen, ["wa_tanf"])
        head = self.add_member(screen, "headOfHousehold", 36, has_income=True)
        self.add_income(head, 5500, frequency="monthly")
        self.add_member(screen, "spouse", 35)
        self.add_member(screen, "child", 9)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_ineligible_snap_but_no_school_age_child(self):
        seed_program(self.white_label, "wa_snap")
        screen = self.make_screen(zipcode="98103", county="King County", household_size=2)
        _write_current_benefits(screen, ["wa_snap"])
        head = self.add_member(screen, "headOfHousehold", 40, has_income=True)
        self.add_income(head, 1800, frequency="monthly")
        self.add_member(screen, "child", 3)

        result = self.calculate(screen)
        self.assertFalse(result.eligible)

    def test_eligible_head_start_categorical_high_income(self):
        seed_program(self.white_label, "wa_head_start")
        screen = self.make_screen(
            household_size=3,
            zipcode="98402",
            county="Pierce County",
            has_benefits="true",
        )
        _write_current_benefits(screen, ["wa_head_start"])
        head = self.add_member(screen, "headOfHousehold", 33, has_income=True)
        self.add_income(head, 5000, frequency="monthly")
        self.add_member(screen, "spouse", 32)
        self.add_member(screen, "child", 5)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_snap_categorical_uses_presumed_eligibility_pass_message_not_income(self):
        seed_program(self.white_label, "wa_snap")
        screen = self.make_screen(
            household_size=3,
            zipcode="99201",
            county="Spokane County",
            has_benefits="true",
        )
        _write_current_benefits(screen, ["wa_snap"])
        head = self.add_member(screen, "headOfHousehold", 40, has_income=True)
        self.add_income(head, 7000, frequency="monthly")
        self.add_member(screen, "spouse", 39)
        self.add_member(screen, "child", 10)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertTrue(any("Presumed eligibility" in str(m) for m in result.pass_messages))
        self.assertFalse(any("Household makes" in str(m) for m in result.pass_messages))

    def test_eligible_foster_child_categorical(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", 35, has_income=True)
        self.add_income(head, 8000, frequency="monthly")
        self.add_member(screen, "spouse", 34)
        self.add_member(screen, "fosterChild", 12)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_two_school_age_children_value_scales(self):
        screen = self.make_screen(zipcode="99201", county="Spokane County", household_size=6)
        head = self.add_member(screen, "headOfHousehold", 40, has_income=True)
        self.add_income(head, 2400, frequency="monthly")
        spouse = self.add_member(screen, "spouse", 38, has_income=True)
        self.add_income(spouse, 800, frequency="monthly")
        self.add_member(screen, "child", 15)
        self.add_member(screen, "child", 11)
        self.add_member(screen, "child", 6)
        self.add_member(screen, "child", 2)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828 * 3)

    def test_mixed_frequency_uses_annual_limit(self):
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", 39, has_income=True)
        self.add_income(head, 2000, frequency="monthly")
        self.add_income(head, 500, frequency="yearly")
        self.add_member(screen, "spouse", 37)
        self.add_member(screen, "child", 12)

        calc = self.make_calculator(screen)
        self.assertTrue(calc._income_at_or_below_reduced_cap())

    def test_member_eligible_false_for_head(self):
        calc = self.make_calculator(self.make_screen(household_size=3))
        e = MemberEligibility(HouseholdMember(relationship="headOfHousehold", age=30))
        calc.member_eligible(e)
        self.assertFalse(e.eligible)

    def test_grandchild_counts(self):
        screen = self.make_screen(household_size=3)
        self.add_income(self.add_member(screen, "headOfHousehold", 55, has_income=True), 2500, frequency="monthly")
        self.add_member(screen, "spouse", 54)
        self.add_member(screen, "grandChild", 10)

        result = self.calculate(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)
