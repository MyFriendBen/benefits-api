"""
Unit tests for the WA SSI calculator.

The 15 reference scenarios in `programs/programs/wa/ssi/spec.md` are the source
of truth for expected eligibility and benefit values; the tests below mirror
those scenarios one-for-one, plus a handful of helper-level tests for the
income exclusion stack and deeming branches.
"""

from django.test import TestCase

from programs.models import Program
from programs.programs.wa.ssi.calculator import WaSsi
from programs.util import Dependencies
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel


class WaSsiTestCase(TestCase):
    """Shared fixtures and helpers."""

    @classmethod
    def setUpTestData(cls):
        cls.wa_white_label = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")
        cls.program = Program.objects.new_program(white_label="wa", name_abbreviated="wa_ssi")

    def _new_screen(self, *, household_size: int = 1, household_assets: int = 0, has_ssi: bool = False) -> Screen:
        return Screen.objects.create(
            agree_to_tos=True,
            zipcode="98101",
            county="King",
            household_size=household_size,
            household_assets=household_assets,
            white_label=self.wa_white_label,
            has_ssi=has_ssi,
            completed=False,
        )

    def _add_member(
        self,
        screen: Screen,
        *,
        relationship: str = "headOfHousehold",
        age: int = 70,
        disabled: bool = False,
        long_term_disability: bool = False,
        visually_impaired: bool = False,
    ) -> HouseholdMember:
        return HouseholdMember.objects.create(
            screen=screen,
            relationship=relationship,
            age=age,
            disabled=disabled,
            long_term_disability=long_term_disability,
            visually_impaired=visually_impaired,
            has_income=False,
        )

    def _add_income(
        self,
        screen: Screen,
        member: HouseholdMember,
        *,
        income_type: str,
        monthly_amount: float,
    ) -> IncomeStream:
        member.has_income = True
        member.save()
        return IncomeStream.objects.create(
            screen=screen,
            household_member=member,
            type=income_type,
            amount=monthly_amount,
            frequency="monthly",
        )

    def _calc(self, screen: Screen) -> WaSsi:
        return WaSsi(screen, self.program, {}, Dependencies())


class TestSpecScenarios(WaSsiTestCase):
    """One test per scenario in spec.md — eligibility + annualized value."""

    def _run(self, screen: Screen):
        calc = self._calc(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)
        return eligibility

    # ---------- eligible cases ----------

    def test_scenario_1_aged_no_income_no_resources(self):
        """Aged 65+, no income, no resources -> $11,928/year."""
        screen = self._new_screen()
        self._add_member(screen, age=70)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 11928)

    def test_scenario_2_long_term_disabled_under_65(self):
        """Disability path via long_term_disability flag -> $11,928/year."""
        screen = self._new_screen()
        self._add_member(screen, age=45, long_term_disability=True)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 11928)

    def test_scenario_3_visually_impaired_adult(self):
        """Blind path via visually_impaired flag -> $11,928/year."""
        screen = self._new_screen()
        self._add_member(screen, age=40, visually_impaired=True)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 11928)

    def test_scenario_6_eligible_aged_couple(self):
        """Both spouses aged 65+ -> couple FBR $17,892/year (per-member sum)."""
        screen = self._new_screen(household_size=2)
        self._add_member(screen, relationship="headOfHousehold", age=70)
        self._add_member(screen, relationship="spouse", age=68)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 17892)

    def test_scenario_9_disabled_child_parental_deeming_under_limits(self):
        """Disabled child + low-earning parents -> parent allocation absorbs deemed income, child gets full FBR."""
        screen = self._new_screen(household_size=3)
        head = self._add_member(screen, relationship="headOfHousehold", age=40)
        self._add_member(screen, relationship="spouse", age=38)
        self._add_member(screen, relationship="child", age=8, long_term_disability=True)
        self._add_income(screen, head, income_type="wages", monthly_amount=1500)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 11928)

    def test_scenario_10_general_disability_flag_only(self):
        """disabled=true alone (no long_term_disability) is enough -> $11,928/year."""
        screen = self._new_screen()
        self._add_member(screen, age=45, disabled=True, long_term_disability=False)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 11928)

    def test_scenario_11_partial_ss_retirement_reduces_benefit(self):
        """$500/mo SS Retirement reduces SSI to $514/mo -> $6,168/year."""
        screen = self._new_screen()
        head = self._add_member(screen, age=72)
        self._add_income(screen, head, income_type="sSRetirement", monthly_amount=500)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 6168)

    def test_scenario_12_partial_earned_wages_reduces_benefit(self):
        """$400/mo wages with $20+$65+1/2 exclusion -> $836.50/mo -> $10,038/year."""
        screen = self._new_screen()
        head = self._add_member(screen, age=45, long_term_disability=True)
        self._add_income(screen, head, income_type="wages", monthly_amount=400)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 10038)

    def test_scenario_15_eligible_aged_head_partial_spousal_deeming(self):
        """Aged head + ineligible spouse with $1,200/mo wages -> partial deeming -> $11,202/year."""
        screen = self._new_screen(household_size=2)
        self._add_member(screen, relationship="headOfHousehold", age=70)
        spouse = self._add_member(screen, relationship="spouse", age=60)
        self._add_income(screen, spouse, income_type="wages", monthly_amount=1200)

        eligibility = self._run(screen)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 11202)

    # ---------- ineligible cases ----------

    def test_scenario_4_unearned_income_above_fbr(self):
        """$1,200/mo SS Retirement (countable $1,180) > FBR $994 -> ineligible."""
        screen = self._new_screen()
        head = self._add_member(screen, age=68)
        self._add_income(screen, head, income_type="sSRetirement", monthly_amount=1200)

        eligibility = self._run(screen)

        self.assertFalse(eligibility.eligible)

    def test_scenario_5_resources_above_individual_limit(self):
        """$5,000 assets > $2,000 individual limit -> ineligible."""
        screen = self._new_screen(household_assets=5_000)
        self._add_member(screen, age=70)

        eligibility = self._run(screen)

        self.assertFalse(eligibility.eligible)

    def test_scenario_7_under_65_without_disability(self):
        """Adult fails all 3 categorical entry routes -> ineligible."""
        screen = self._new_screen()
        self._add_member(screen, age=35)

        eligibility = self._run(screen)

        self.assertFalse(eligibility.eligible)

    def test_scenario_8_already_receiving_ssi_via_has_ssi_flag(self):
        """has_ssi=True filters out duplicate enrollment."""
        screen = self._new_screen(has_ssi=True)
        head = self._add_member(screen, age=70)
        self._add_income(screen, head, income_type="sSI", monthly_amount=994)

        eligibility = self._run(screen)

        self.assertFalse(eligibility.eligible)

    def test_already_receiving_ssi_via_income_stream_alone(self):
        """sSI income stream alone (without has_ssi flag) also filters out duplicates."""
        screen = self._new_screen(has_ssi=False)
        head = self._add_member(screen, age=70)
        self._add_income(screen, head, income_type="sSI", monthly_amount=994)

        eligibility = self._run(screen)

        self.assertFalse(eligibility.eligible)

    def test_scenario_13_high_income_spouse_zeroes_ssi(self):
        """Ineligible spouse with $4,000/mo wages -> deemed countable exceeds couple FBR -> ineligible."""
        screen = self._new_screen(household_size=2)
        self._add_member(screen, relationship="headOfHousehold", age=60, long_term_disability=True)
        spouse = self._add_member(screen, relationship="spouse", age=58)
        self._add_income(screen, spouse, income_type="wages", monthly_amount=4000)

        eligibility = self._run(screen)

        self.assertFalse(eligibility.eligible)

    def test_scenario_14_above_sga_threshold(self):
        """Long-term disabled, $1,700/mo wages > $1,690 non-blind SGA -> ineligible."""
        screen = self._new_screen()
        head = self._add_member(screen, age=50, long_term_disability=True)
        self._add_income(screen, head, income_type="wages", monthly_amount=1700)

        eligibility = self._run(screen)

        self.assertFalse(eligibility.eligible)


class TestSgaExemptions(WaSsiTestCase):
    """SGA only applies on the non-blind disability path; aged and blind are exempt."""

    def test_blind_applicant_above_non_blind_sga_still_eligible(self):
        """Visually impaired + $1,700/mo wages stays eligible (blind path is SGA-exempt)."""
        screen = self._new_screen()
        head = self._add_member(screen, age=40, visually_impaired=True)
        self._add_income(screen, head, income_type="wages", monthly_amount=1700)

        calc = self._calc(screen)
        eligibility = calc.eligible()

        self.assertTrue(eligibility.eligible)

    def test_aged_applicant_high_earned_income_within_fbr_still_eligible(self):
        """Aged 65+ skip the SGA test entirely; only the FBR income test applies."""
        screen = self._new_screen()
        head = self._add_member(screen, age=70)
        # $400 wages -> $157.50 countable, well below FBR
        self._add_income(screen, head, income_type="wages", monthly_amount=400)

        calc = self._calc(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, 10038)


class TestCountableIncomeHelper(WaSsiTestCase):
    """Direct tests for the $20 + $65 + 1/2 exclusion stack."""

    def setUp(self):
        screen = self._new_screen()
        self._add_member(screen, age=70)
        self.calc = self._calc(screen)

    def test_no_income_returns_zero(self):
        self.assertEqual(self.calc._countable_income(0, 0), 0)

    def test_unearned_only_applies_general_exclusion(self):
        # $500 unearned - $20 general = $480 countable
        self.assertEqual(self.calc._countable_income(0, 500), 480)

    def test_earned_only_applies_general_then_earned_then_half(self):
        # $400 earned - $20 (general spillover) - $65 earned = $315; * 0.5 = $157.50
        self.assertAlmostEqual(self.calc._countable_income(400, 0), 157.5)

    def test_general_exclusion_spills_from_unearned_to_earned(self):
        # $5 unearned consumes $5 of the $20 general; remaining $15 spills to earned.
        # $400 earned - $15 - $65 = $320; * 0.5 = $160. Unearned: $5 - $5 = $0.
        self.assertAlmostEqual(self.calc._countable_income(400, 5), 160)

    def test_earned_exclusion_floors_at_zero(self):
        # $30 earned, $0 unearned: $30 - $20 (general) = $10; - $65 (earned) floors at $0.
        self.assertEqual(self.calc._countable_income(30, 0), 0)


class TestResourceLimits(WaSsiTestCase):
    """Couple resource limit applies whenever a spouse is in the household."""

    def test_individual_limit_at_boundary_passes(self):
        screen = self._new_screen(household_assets=2_000)
        self._add_member(screen, age=70)

        eligibility = self._calc(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_couple_limit_applied_when_spouse_present(self):
        # $2,500 > individual $2,000 but <= couple $3,000
        screen = self._new_screen(household_size=2, household_assets=2_500)
        self._add_member(screen, relationship="headOfHousehold", age=70)
        self._add_member(screen, relationship="spouse", age=68)

        eligibility = self._calc(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_couple_limit_just_above_fails(self):
        screen = self._new_screen(household_size=2, household_assets=3_500)
        self._add_member(screen, relationship="headOfHousehold", age=70)
        self._add_member(screen, relationship="spouse", age=68)

        eligibility = self._calc(screen).eligible()

        self.assertFalse(eligibility.eligible)
