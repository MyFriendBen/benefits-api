from django.test import TestCase
from unittest.mock import Mock, patch

from integrations.clients.hud_income_limits import HudIncomeClientError
from programs.programs.tx import tx_calculators
from programs.programs.tx.hcv.calculator import TxHcv
from programs.programs.calc import ProgramCalculator, Eligibility


def make_member(
    age=40,
    relationship="headOfHousehold",
    disabled=False,
    student_full_time=False,
    earned=0,
    unearned=0,
):
    """A mock HouseholdMember. `earned`/`unearned` are ANNUAL dollar amounts."""
    member = Mock()
    member.age = age
    member.relationship = relationship
    member.disabled = disabled
    member.student = student_full_time
    member.student_full_time = student_full_time
    member.has_disability = Mock(return_value=disabled)

    def calc_gross_income(frequency, types):
        total = 0
        if "all" in types:
            total = earned + unearned
        else:
            if "earned" in types:
                total += earned
            if "unearned" in types:
                total += unearned
        return float(total)

    member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return member


def make_calculator(
    members=None,
    household_size=None,
    county="Harris",
    zipcode="77002",
    household_assets=0,
    has_section_8=False,
    reported_rent=0,
):
    if members is None:
        members = [make_member()]
    if household_size is None:
        household_size = len(members)

    screen = Mock()
    screen.household_size = household_size
    screen.county = county
    screen.zipcode = zipcode
    screen.household_assets = household_assets
    screen.household_members.all = Mock(return_value=members)
    screen.has_benefit = Mock(return_value=False)
    # Section 8 is matched via base_program ("section_8" → tx_hcv), not an exact name.
    screen.has_base_benefit = Mock(side_effect=lambda base: has_section_8 if base == "section_8" else False)
    screen.calc_expenses = Mock(return_value=reported_rent)
    head = next((m for m in members if m.relationship == "headOfHousehold"), members[0] if members else None)
    screen.get_head = Mock(return_value=head)

    program = Mock()
    program.year.period = "2026"

    missing_deps = Mock()
    missing_deps.has.return_value = False

    return TxHcv(screen, program, {}, missing_deps)


def patch_hud(il_ami=10_000_000, payment_standard=0, il_error=False):
    """Patch both HUD lookups the calculator uses."""

    def il_side_effect(*args, **kwargs):
        if il_error:
            raise HudIncomeClientError("test error")
        return il_ami

    return patch.multiple(
        "programs.programs.tx.hcv.calculator.hud_client",
        get_screen_il_ami=Mock(side_effect=il_side_effect),
        get_screen_payment_standard=Mock(return_value=payment_standard),
    )


class TestTxHcvClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TxHcv, ProgramCalculator))

    def test_is_registered_in_tx_calculators(self):
        self.assertIn("tx_hcv", tx_calculators)
        self.assertEqual(tx_calculators["tx_hcv"], TxHcv)

    def test_asset_limit_is_100k(self):
        self.assertEqual(TxHcv.asset_limit, 100_000)

    def test_min_head_age_is_18(self):
        self.assertEqual(TxHcv.min_head_age, 18)

    def test_ami_percent_is_50(self):
        self.assertEqual(TxHcv.ami_percent, "50%")

    def test_min_rent_is_25(self):
        self.assertEqual(TxHcv.min_rent_monthly, 25)

    def test_deductions(self):
        self.assertEqual(TxHcv.dependent_deduction_annual, 480)
        self.assertEqual(TxHcv.elderly_disabled_deduction_annual, 525)

    def test_bedroom_map_matches_spec(self):
        self.assertEqual(TxHcv.BEDROOM_MAP, {1: 0, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4})

    def test_dependencies(self):
        for field in (
            "income_amount",
            "household_size",
            "county",
            "zipcode",
            "household_assets",
            "age",
            "relationship",
        ):
            self.assertIn(field, TxHcv.dependencies)


class TestTxHcvHelpers(TestCase):
    def test_bedroom_size_single_is_0br(self):
        calc = make_calculator(members=[make_member()], household_size=1)
        self.assertEqual(calc._estimate_bedrooms(), 0)

    def test_bedroom_size_two_is_1br(self):
        calc = make_calculator(household_size=2)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_bedroom_size_four_is_2br(self):
        calc = make_calculator(household_size=4)
        self.assertEqual(calc._estimate_bedrooms(), 2)

    def test_bedroom_size_five_is_3br(self):
        calc = make_calculator(household_size=5)
        self.assertEqual(calc._estimate_bedrooms(), 3)

    def test_bedroom_size_seven_is_4br(self):
        calc = make_calculator(household_size=7)
        self.assertEqual(calc._estimate_bedrooms(), 4)

    def test_bedroom_size_over_8_caps_at_4br(self):
        calc = make_calculator(household_size=10)
        self.assertEqual(calc._estimate_bedrooms(), 4)

    def test_count_dependents_children_under_18(self):
        members = [
            make_member(age=35),
            make_member(age=9, relationship="child"),
            make_member(age=6, relationship="child"),
        ]
        self.assertEqual(make_calculator(members=members)._count_dependents(), 2)

    def test_count_dependents_excludes_head_and_spouse(self):
        members = [make_member(age=35), make_member(age=33, relationship="spouse")]
        self.assertEqual(make_calculator(members=members)._count_dependents(), 0)

    def test_count_dependents_excludes_foster_child(self):
        members = [make_member(age=35), make_member(age=10, relationship="fosterChild")]
        self.assertEqual(make_calculator(members=members)._count_dependents(), 0)

    def test_count_dependents_adult_disabled(self):
        members = [make_member(age=35), make_member(age=19, relationship="child", disabled=True)]
        self.assertEqual(make_calculator(members=members)._count_dependents(), 1)

    def test_count_dependents_adult_full_time_student(self):
        members = [make_member(age=35), make_member(age=20, relationship="child", student_full_time=True)]
        self.assertEqual(make_calculator(members=members)._count_dependents(), 1)

    def test_count_dependents_adult_non_disabled_non_student_excluded(self):
        members = [make_member(age=35), make_member(age=68, relationship="parent")]
        self.assertEqual(make_calculator(members=members)._count_dependents(), 0)

    def test_elderly_family_head_62_plus(self):
        self.assertTrue(make_calculator(members=[make_member(age=68)])._is_elderly_or_disabled_family())

    def test_elderly_family_spouse_62_plus(self):
        members = [make_member(age=50), make_member(age=63, relationship="spouse")]
        self.assertTrue(make_calculator(members=members)._is_elderly_or_disabled_family())

    def test_elderly_family_disabled_head(self):
        self.assertTrue(make_calculator(members=[make_member(age=40, disabled=True)])._is_elderly_or_disabled_family())

    def test_not_elderly_family(self):
        self.assertFalse(make_calculator(members=[make_member(age=35)])._is_elderly_or_disabled_family())

    def test_elderly_non_head_parent_does_not_trigger(self):
        """An elderly parent (not head/spouse) does not make an elderly family (Scenario 12)."""
        members = [make_member(age=35), make_member(age=68, relationship="parent")]
        self.assertFalse(make_calculator(members=members)._is_elderly_or_disabled_family())

    def test_head_age_ok_18(self):
        self.assertTrue(make_calculator(members=[make_member(age=18)])._head_age_ok())

    def test_head_age_not_ok_17(self):
        self.assertFalse(make_calculator(members=[make_member(age=17)])._head_age_ok())

    def test_head_age_unknown_does_not_block(self):
        self.assertTrue(make_calculator(members=[make_member(age=None)])._head_age_ok())

    def test_countable_income_excludes_minor_earned_income(self):
        """A minor's wages are excluded; their unearned income still counts (Scenario 23)."""
        members = [
            make_member(age=38, earned=12_000),
            make_member(age=16, relationship="child", earned=4_800, unearned=1_200),
        ]
        # head 12,000 + child unearned 1,200 (earned 4,800 excluded) = 13,200
        self.assertEqual(make_calculator(members=members)._countable_gross_income(), 13_200)

    def test_countable_income_excludes_all_foster_child_income(self):
        """A foster child's earned AND unearned income are both excluded (Scenario 24)."""
        members = [
            make_member(age=35, earned=14_400),
            make_member(age=10, relationship="fosterChild", earned=1_000, unearned=2_400),
        ]
        self.assertEqual(make_calculator(members=members)._countable_gross_income(), 14_400)


class TestTxHcvEligibility(TestCase):
    def test_eligible_when_income_at_or_below_limit(self):
        calc = make_calculator(members=[make_member(age=35, earned=21_600)])
        with patch_hud(il_ami=46_800):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_ineligible_when_income_above_limit(self):
        calc = make_calculator(members=[make_member(age=35, earned=75_000)])
        with patch_hud(il_ami=47_050):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)

    def test_income_exactly_at_limit_is_eligible(self):
        calc = make_calculator(members=[make_member(age=35, earned=47_050)])
        with patch_hud(il_ami=47_050):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_has_section_8_is_ineligible(self):
        calc = make_calculator(members=[make_member(age=35, earned=10_000)], has_section_8=True)
        with patch_hud(il_ami=46_800):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)

    def test_section_8_check_uses_base_benefit_not_exact_name(self):
        """Section 8 is the HCV program via base_program ("section_8" → tx_hcv);
        the gate must call has_base_benefit, not the dead has_benefit("section_8")."""
        calc = make_calculator(members=[make_member(age=35, earned=10_000)])
        # Exact-name has_benefit is always False; only has_base_benefit("section_8") is True.
        calc.screen.has_benefit = Mock(return_value=False)
        calc.screen.has_base_benefit = Mock(side_effect=lambda base: base == "section_8")
        with patch_hud(il_ami=46_800):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)
            calc.screen.has_base_benefit.assert_any_call("section_8")

    def test_assets_above_100k_ineligible(self):
        calc = make_calculator(members=[make_member(age=35, earned=14_400)], household_assets=150_000)
        with patch_hud(il_ami=46_800):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)

    def test_assets_exactly_100k_eligible(self):
        calc = make_calculator(members=[make_member(age=35, earned=14_400)], household_assets=100_000)
        with patch_hud(il_ami=46_800):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_none_assets_treated_as_zero(self):
        calc = make_calculator(members=[make_member(age=35, earned=14_400)], household_assets=None)
        with patch_hud(il_ami=46_800):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_head_under_18_ineligible(self):
        calc = make_calculator(members=[make_member(age=17, earned=14_400)])
        with patch_hud(il_ami=46_800):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)

    def test_hud_error_makes_ineligible(self):
        calc = make_calculator(members=[make_member(age=35, earned=14_400)])
        with patch_hud(il_error=True):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)


class TestTxHcvBenefitValue(TestCase):
    def test_zero_income_uses_minimum_rent_floor(self):
        """Scenario 14 mechanic: TTP floors at the $25 minimum rent, not $0."""
        calc = make_calculator(members=[make_member(age=30, earned=0)], household_size=1)
        with patch_hud(payment_standard=773):
            # TTP = max(0, 0, 25) = 25; HAP = 773 - 25 = 748; annual = 8976
            self.assertEqual(calc.household_value(), 8976)

    def test_reported_rent_below_payment_standard_caps_gross_rent(self):
        """Scenario 19 mechanic: HAP uses min(payment standard, reported rent)."""
        calc = make_calculator(members=[make_member(age=35, earned=18_000)], household_size=1, reported_rent=600)
        with patch_hud(payment_standard=821):
            # TTP = 450; gross rent = min(821, 600) = 600; HAP = 150; annual = 1800
            self.assertEqual(calc.household_value(), 1800)

    def test_ttp_exceeds_payment_standard_floors_at_zero(self):
        """Scenario 4 mechanic: negative HAP floors at $0."""
        members = [
            make_member(age=68, unearned=24_000),
            make_member(age=65, relationship="spouse", unearned=12_000),
        ]
        calc = make_calculator(members=members, household_size=2)
        with patch_hud(payment_standard=870):
            self.assertEqual(calc.household_value(), 0)

    def test_hud_error_returns_zero_value(self):
        calc = make_calculator(members=[make_member(age=35, earned=14_400)], household_size=1)
        with patch.multiple(
            "programs.programs.tx.hcv.calculator.hud_client",
            get_screen_payment_standard=Mock(side_effect=HudIncomeClientError("boom")),
        ):
            self.assertEqual(calc.household_value(), 0)

    def test_unexpected_error_returns_zero_value(self):
        calc = make_calculator(members=[make_member(age=35, earned=14_400)], household_size=1)
        with patch.multiple(
            "programs.programs.tx.hcv.calculator.hud_client",
            get_screen_payment_standard=Mock(side_effect=KeyError("unexpected")),
        ):
            self.assertEqual(calc.household_value(), 0)


class TestTxHcvScenarios(TestCase):
    """One test per acceptance-criteria scenario in spec.md.

    `il_ami` is the scenario's stated Very Low Income (50% AMI) limit;
    `payment_standard` is the scenario's stated FMR/SAFMR payment standard.
    """

    def _assert_scenario(self, members, il_ami, payment_standard, expected_value, **calc_kwargs):
        calc = make_calculator(members=members, **calc_kwargs)
        with patch_hud(il_ami=il_ami, payment_standard=payment_standard):
            e = calc.calc()
            self.assertTrue(e.eligible, "expected eligible")
            self.assertEqual(e.value, expected_value)

    def _assert_ineligible(self, members, il_ami, payment_standard=0, **calc_kwargs):
        calc = make_calculator(members=members, **calc_kwargs)
        with patch_hud(il_ami=il_ami, payment_standard=payment_standard):
            e = calc.calc()
            self.assertFalse(e.eligible)

    def test_scenario_1_single_mother_two_children_harris(self):
        members = [
            make_member(age=35, relationship="headOfHousehold", earned=21_600),
            make_member(age=9, relationship="child"),
            make_member(age=6, relationship="child"),
        ]
        self._assert_scenario(members, il_ami=46_800, payment_standard=1573, expected_value=12_684, county="Harris")

    def test_scenario_2_single_adult_el_paso(self):
        members = [make_member(age=18, earned=23_400)]
        self._assert_scenario(members, il_ami=29_300, payment_standard=821, expected_value=2_832, county="El Paso")

    def test_scenario_3_family_of_four_multi_earner_dallas(self):
        members = [
            make_member(age=40, earned=42_000),
            make_member(age=37, relationship="spouse", earned=13_800),
            make_member(age=8, relationship="child"),
            make_member(age=5, relationship="child"),
        ]
        self._assert_scenario(members, il_ami=60_550, payment_standard=2900, expected_value=18_348, county="Dallas")

    def test_scenario_4_elderly_couple_bexar_zero_hap(self):
        members = [
            make_member(age=68, unearned=24_000),
            make_member(age=65, relationship="spouse", unearned=12_000),
        ]
        # Eligible for the voucher, but $0 net benefit.
        calc = make_calculator(members=members, county="Bexar", zipcode="78207")
        with patch_hud(il_ami=40_250, payment_standard=870):
            e = calc.calc()
            self.assertTrue(e.eligible)
            self.assertEqual(e.value, 0)

    def test_scenario_5_income_above_limit_travis(self):
        members = [make_member(age=35, earned=75_000)]
        self._assert_ineligible(members, il_ami=47_050, county="Travis")

    def test_scenario_6_head_exactly_18_tarrant(self):
        members = [make_member(age=18, earned=10_800)]
        self._assert_scenario(members, il_ami=40_000, payment_standard=1680, expected_value=16_920, county="Tarrant")

    def test_scenario_7_head_17_el_paso_ineligible(self):
        members = [make_member(age=17, earned=14_400)]
        self._assert_ineligible(members, il_ami=29_300, county="El Paso")

    def test_scenario_8_adult_45_lubbock(self):
        members = [make_member(age=45, earned=14_400)]
        self._assert_scenario(members, il_ami=29_300, payment_standard=818, expected_value=5_496, county="Lubbock")

    def test_scenario_9_single_adult_midland(self):
        members = [make_member(age=35, earned=14_400)]
        self._assert_scenario(members, il_ami=35_000, payment_standard=1424, expected_value=12_768, county="Midland")

    def test_scenario_10_already_receiving_section8_harris(self):
        members = [make_member(age=40, earned=0)]
        self._assert_ineligible(members, il_ami=46_800, has_section_8=True, county="Harris")

    def test_scenario_11_already_receiving_section8_dallas(self):
        members = [
            make_member(age=38, earned=21_600),
            make_member(age=11, relationship="child"),
            make_member(age=8, relationship="child"),
        ]
        self._assert_ineligible(members, il_ami=60_550, has_section_8=True, county="Dallas")

    def test_scenario_12_mixed_generation_hidalgo(self):
        members = [
            make_member(age=35, earned=16_800),
            make_member(age=68, relationship="parent", unearned=9_000),
            make_member(age=7, relationship="child"),
        ]
        self._assert_scenario(members, il_ami=37_700, payment_standard=1060, expected_value=5_124, county="Hidalgo")

    def test_scenario_13_two_working_adults_two_children_collin(self):
        members = [
            make_member(age=35, earned=16_800),
            make_member(age=32, relationship="spouse", earned=14_400),
            make_member(age=8, relationship="child"),
            make_member(age=4, relationship="child"),
        ]
        self._assert_scenario(members, il_ami=60_550, payment_standard=2580, expected_value=21_888, county="Collin")

    def test_scenario_14_zero_income_cameron(self):
        members = [make_member(age=30, earned=0)]
        self._assert_scenario(members, il_ami=20_000, payment_standard=773, expected_value=8_976, county="Cameron")

    def test_scenario_15_full_time_student_lubbock(self):
        members = [make_member(age=22, earned=9_600, student_full_time=True)]
        self._assert_scenario(members, il_ami=29_300, payment_standard=818, expected_value=6_936, county="Lubbock")

    def test_scenario_16_household_of_five_mclennan(self):
        members = [
            make_member(age=41, earned=24_000),
            make_member(age=38, relationship="spouse"),
            make_member(age=10, relationship="child"),
            make_member(age=8, relationship="child"),
            make_member(age=4, relationship="child"),
        ]
        self._assert_scenario(members, il_ami=48_800, payment_standard=1599, expected_value=12_420, county="McLennan")

    def test_scenario_17_between_50_and_80_ami_travis_ineligible(self):
        members = [make_member(age=35, earned=55_000)]
        self._assert_ineligible(members, il_ami=47_050, county="Travis")

    def test_scenario_18_family_of_seven_mclennan_4br(self):
        members = [
            make_member(age=41, earned=27_600),
            make_member(age=38, relationship="spouse"),
            make_member(age=14, relationship="child"),
            make_member(age=12, relationship="child"),
            make_member(age=10, relationship="child"),
            make_member(age=8, relationship="child"),
            make_member(age=4, relationship="child"),
        ]
        self._assert_scenario(members, il_ami=55_000, payment_standard=1644, expected_value=12_168, county="McLennan")

    def test_scenario_19_reported_rent_el_paso(self):
        members = [make_member(age=35, earned=18_000)]
        self._assert_scenario(
            members, il_ami=29_300, payment_standard=821, expected_value=1_800, county="El Paso", reported_rent=600
        )

    def test_scenario_20_assets_over_limit_harris_ineligible(self):
        members = [make_member(age=35, earned=14_400)]
        self._assert_ineligible(members, il_ami=46_800, household_assets=150_000, county="Harris")

    def test_scenario_21_elderly_head_disabled_adult_dependent_bexar(self):
        members = [
            make_member(age=63, earned=16_800),
            make_member(age=19, relationship="child", disabled=True),
        ]
        self._assert_scenario(
            members, il_ami=40_250, payment_standard=870, expected_value=5_700, county="Bexar", zipcode="78207"
        )

    def test_scenario_22_foster_child_excluded_from_dependent_deduction_harris(self):
        members = [
            make_member(age=35, earned=14_400),
            make_member(age=10, relationship="fosterChild"),
        ]
        self._assert_scenario(members, il_ami=41_600, payment_standard=1323, expected_value=11_556, county="Harris")

    def test_scenario_23_teen_wages_excluded_el_paso(self):
        members = [
            make_member(age=38, earned=12_000),
            make_member(age=16, relationship="child", earned=4_800),
        ]
        self._assert_scenario(members, il_ami=33_500, payment_standard=1013, expected_value=8_700, county="El Paso")

    def test_scenario_24_foster_child_unearned_income_excluded_harris(self):
        members = [
            make_member(age=35, earned=14_400),
            make_member(age=10, relationship="fosterChild", unearned=2_400),
        ]
        self._assert_scenario(members, il_ami=41_600, payment_standard=1323, expected_value=11_556, county="Harris")


class TestTxHcvNeverRaises(TestCase):
    """A HUD lookup that raises must never propagate out of the calculator and
    break the eligibility run. calc() must finish and fall back to the safe guess
    (income gate we can't evaluate -> not eligible; value we can't compute -> $0),
    for BOTH the typed HudIncomeClientError and any unexpected exception.
    """

    def _calc(self):
        return make_calculator(members=[make_member(age=35, earned=12_000)], household_size=1)

    def test_calc_finishes_when_income_lookup_raises_hud_error(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.tx.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=HudIncomeClientError("HUD unavailable")),
            get_screen_payment_standard=Mock(return_value=1000),
        ):
            e = calc.calc()  # must not raise
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_calc_finishes_when_income_lookup_raises_unexpected_exception(self):
        """A non-HudIncomeClientError from the HUD layer must still be swallowed."""
        calc = self._calc()
        with patch.multiple(
            "programs.programs.tx.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=ValueError("unexpected boom")),
            get_screen_payment_standard=Mock(return_value=1000),
        ):
            e = calc.calc()  # must not raise, despite a non-typed exception
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_calc_finishes_when_payment_standard_raises_hud_error(self):
        calc = self._calc()  # income-eligible below
        with patch.multiple(
            "programs.programs.tx.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=40_000),
            get_screen_payment_standard=Mock(side_effect=HudIncomeClientError("no FMR")),
        ):
            e = calc.calc()  # must not raise
        self.assertTrue(e.eligible)  # eligibility resolved before the value lookup
        self.assertEqual(e.value, 0)  # value degrades to $0

    def test_calc_finishes_when_payment_standard_raises_unexpected_exception(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.tx.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=40_000),
            get_screen_payment_standard=Mock(side_effect=KeyError("unexpected")),
        ):
            e = calc.calc()  # must not raise, despite a non-typed exception
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)
