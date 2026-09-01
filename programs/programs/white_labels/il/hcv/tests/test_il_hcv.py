"""
Unit tests for the IL Housing Choice Voucher calculator.

Every scenario in `spec.md` has a test in `TestIlHcvSpecScenarios`, named for its
scenario number, asserting both eligibility and the exact benefit value. The
scenarios' HUD figures — the FY2026 Very Low Income limits and FMRs quoted in the
spec — are passed in rather than fetched, so the tests pin the calculator's
arithmetic without touching the HUD API.

Ages are stated as of the spec's reference date, 2026-08-29, and set directly on
the mock member rather than derived from a birth year, so the suite cannot drift
as birthdays pass.
"""

from django.test import TestCase
from unittest.mock import Mock, patch

from integrations.clients.hud_income_limits import HudIncomeClientError
from programs.framework.base import ProgramCalculator
from programs.programs.white_labels.il.hcv.calculator import IlHcv

EARNED_TYPES = frozenset(("wages", "selfEmployment"))

# FY2026 HUD figures the spec's scenarios quote, so a test reads like its scenario.
CHICAGO_VLI = {1: 42_550, 2: 48_600, 3: 54_700, 4: 60_750, 5: 65_650, 6: 70_500, 7: 75_350, 8: 80_200}
PEORIA_VLI = {1: 37_150, 2: 42_450, 3: 47_750, 4: 53_050, 5: 57_300, 6: 61_550, 7: 65_800, 8: 70_050}
CHICAGO_FMR = {0: 1_480, 1: 1_581, 2: 1_781, 3: 2_294, 4: 2_653}
PEORIA_FMR = {0: 758, 1: 818, 2: 1_039, 3: 1_346, 4: 1_449}


def make_member(
    age=40,
    relationship="headOfHousehold",
    income=None,
    disabled=False,
    student_full_time=False,
    pregnant=False,
):
    """
    A mock HouseholdMember. `income` maps an income type to an ANNUAL dollar amount,
    e.g. `{"wages": 36_450}`, and `calc_gross_income` reproduces the real model's
    earned/unearned/exclude semantics over it.
    """
    income = income or {}

    member = Mock()
    member.age = age
    member.relationship = relationship
    member.pregnant = pregnant
    member.disabled = disabled
    member.student = student_full_time
    member.student_full_time = student_full_time
    member.has_disability = Mock(return_value=disabled)

    def calc_gross_income(frequency, types, exclude=()):
        total = 0.0
        for income_type, annual in income.items():
            if income_type in exclude:
                continue
            matched = (
                "all" in types
                or income_type in types
                or ("earned" in types and income_type in EARNED_TYPES)
                or ("unearned" in types and income_type not in EARNED_TYPES)
            )
            if matched:
                total += annual if frequency == "yearly" else annual / 12
        return total

    member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return member


#: Distinguishes "not specified, derive it" from an explicit null household_size.
DERIVE = object()


def make_calculator(members=None, household_size=DERIVE, county="Cook", zipcode="60623", rent=0):
    if members is None:
        members = [make_member()]
    if household_size is DERIVE:
        household_size = len(members)

    screen = Mock()
    screen.household_size = household_size
    screen.county = county
    screen.zipcode = zipcode
    screen.household_members.all = Mock(return_value=members)
    screen.has_benefit = Mock(return_value=False)
    screen.has_base_benefit = Mock(return_value=False)
    # Only the `rent` expense type feeds the gross-rent proxy; `mortgage` is excluded.
    screen.calc_expenses = Mock(side_effect=lambda frequency, types: float(rent) if "rent" in types else 0.0)
    head = next((m for m in members if m.relationship == "headOfHousehold"), members[0] if members else None)
    screen.get_head = Mock(return_value=head)

    program = Mock()
    program.year.period = "2026"

    missing_deps = Mock()
    missing_deps.has.return_value = False

    return IlHcv(screen, program, {}, missing_deps)


def hud_mocks(income_limit=10_000_000, payment_standard=0):
    """The two HUD lookups the calculator makes, and a patcher over both. Returns
    the mocks so a test can assert on the call as well as stub it."""
    income_mock = Mock(return_value=income_limit)
    payment_mock = Mock(return_value=payment_standard)
    patcher = patch.multiple(
        "programs.programs.white_labels.il.hcv.calculator.hud_client",
        get_screen_il_ami=income_mock,
        get_screen_payment_standard=payment_mock,
    )
    return patcher, income_mock, payment_mock


def patch_hud(income_limit=10_000_000, payment_standard=0):
    return hud_mocks(income_limit, payment_standard)[0]


class TestIlHcvClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(IlHcv, ProgramCalculator))

    def test_program_code(self):
        self.assertEqual(IlHcv.program_code, "il_hcv")

    def test_registered_in_calculator_registry(self):
        from programs.programs import calculators

        self.assertIs(calculators["il_hcv"], IlHcv)

    def test_income_gate_is_very_low_income(self):
        self.assertEqual(IlHcv.ami_percent, "50%")

    def test_deductions_are_the_published_cy2026_values(self):
        self.assertEqual(IlHcv.dependent_deduction_annual, 500)
        self.assertEqual(IlHcv.elderly_disabled_deduction_annual, 550)

    def test_minimum_rent_is_modelled_at_zero(self):
        self.assertEqual(IlHcv.min_rent_monthly, 0)

    def test_bedroom_map_is_one_per_two_people(self):
        self.assertEqual(dict(IlHcv.BEDROOM_MAP), {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4})

    def test_workers_comp_is_the_type_level_exclusion(self):
        self.assertEqual(IlHcv.EXCLUDED_INCOME_TYPES, ("workersComp",))

    def test_no_asset_limit_is_declared(self):
        """Data gap 4: MFB applies no asset or property gate, so there is no limit
        to declare and `household_assets` is not a dependency."""
        self.assertFalse(hasattr(IlHcv, "asset_limit"))
        self.assertNotIn("household_assets", IlHcv.dependencies)

    def test_dependencies(self):
        self.assertEqual(
            IlHcv.dependencies,
            (
                "income_amount",
                "income_frequency",
                "household_size",
                "county",
                "zipcode",
                "age",
                "relationship",
            ),
        )


class TestIlHcvBedroomSize(TestCase):
    """The ⌈n/2⌉ voucher-size convention."""

    def _bedrooms(self, household_size, members=None):
        return make_calculator(members=members, household_size=household_size)._estimate_bedrooms()

    def test_one_person_is_1br(self):
        self.assertEqual(self._bedrooms(1), 1)

    def test_two_people_is_1br(self):
        self.assertEqual(self._bedrooms(2), 1)

    def test_three_people_is_2br(self):
        self.assertEqual(self._bedrooms(3), 2)

    def test_four_people_is_2br(self):
        self.assertEqual(self._bedrooms(4), 2)

    def test_five_people_is_3br(self):
        self.assertEqual(self._bedrooms(5), 3)

    def test_six_people_is_3br(self):
        self.assertEqual(self._bedrooms(6), 3)

    def test_seven_people_is_4br(self):
        self.assertEqual(self._bedrooms(7), 4)

    def test_eight_people_is_4br(self):
        self.assertEqual(self._bedrooms(8), 4)

    def test_over_eight_falls_to_4br(self):
        """4BR is the largest bedroom count HUD publishes an FMR for."""
        self.assertEqual(self._bedrooms(10), 4)

    def test_pregnant_single_person_counts_as_two(self):
        """24 CFR 982.402(b)(5). A no-op under this map — 1 and 2 both give 1BR — so
        the size, not the bedroom count, is what this asserts."""
        members = [make_member(pregnant=True)]
        calc = make_calculator(members=members, household_size=1)
        self.assertEqual(calc._effective_household_size(), 2)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_non_pregnant_single_person_stays_one(self):
        calc = make_calculator(members=[make_member()], household_size=1)
        self.assertEqual(calc._effective_household_size(), 1)


class TestIlHcvAnnualIncome(TestCase):
    """24 CFR 5.609 — annual income is not raw gross income."""

    def _income(self, members):
        return make_calculator(members=members)._annual_income()

    def test_adult_earned_and_unearned_both_count(self):
        members = [make_member(income={"wages": 20_000, "pension": 5_000})]
        self.assertEqual(self._income(members), 25_000)

    def test_income_is_summed_across_members(self):
        members = [
            make_member(income={"wages": 30_375}),
            make_member(relationship="spouse", income={"wages": 30_375}),
        ]
        self.assertEqual(self._income(members), 60_750)

    def test_minor_earned_income_is_excluded(self):
        """§ 5.609(b)(3)."""
        members = [
            make_member(income={"wages": 55_000}),
            make_member(age=17, relationship="child", income={"wages": 9_000}),
        ]
        self.assertEqual(self._income(members), 55_000)

    def test_minor_unearned_income_still_counts(self):
        """§ 5.609(a)(1) counts unearned income received on behalf of a dependent
        under 18 — only the earned income is excluded."""
        members = [
            make_member(income={"wages": 30_000}),
            make_member(age=10, relationship="child", income={"childSupport": 2_400}),
        ]
        self.assertEqual(self._income(members), 32_400)

    def test_minor_head_of_household_income_counts_in_full(self):
        """§ 5.609(a)(1) counts the head's and spouse's income whatever their age."""
        members = [make_member(age=17, relationship="headOfHousehold", income={"wages": 12_000})]
        self.assertEqual(self._income(members), 12_000)

    def test_unknown_age_is_treated_as_an_adult(self):
        """An exclusion is never applied on a guess: an unknown age counts in full."""
        members = [
            make_member(income={"wages": 20_000}),
            make_member(age=None, relationship="child", income={"wages": 5_000}),
        ]
        self.assertEqual(self._income(members), 25_000)

    def test_dependent_full_time_student_earned_income_capped(self):
        """§ 5.609(b)(14): only the dependent-deduction amount of it counts."""
        members = [
            make_member(income={"wages": 30_000}),
            make_member(age=21, relationship="child", student_full_time=True, income={"wages": 5_000}),
        ]
        self.assertEqual(self._income(members), 30_500)

    def test_dependent_student_earning_under_the_cap_counts_in_full(self):
        members = [
            make_member(income={"wages": 30_000}),
            make_member(age=21, relationship="child", student_full_time=True, income={"wages": 300}),
        ]
        self.assertEqual(self._income(members), 30_300)

    def test_dependent_student_unearned_income_is_not_capped(self):
        """The cap reaches earned income only."""
        members = [
            make_member(income={"wages": 30_000}),
            make_member(age=21, relationship="child", student_full_time=True, income={"pension": 5_000}),
        ]
        self.assertEqual(self._income(members), 35_000)

    def test_head_who_is_a_full_time_student_is_not_capped(self):
        """The cap is for a *dependent* student; a head is never a dependent."""
        members = [make_member(age=21, student_full_time=True, income={"wages": 5_000})]
        self.assertEqual(self._income(members), 5_000)

    def test_workers_compensation_is_excluded_for_any_member(self):
        """§ 5.609(b)(5) is type-specific, not member-specific."""
        members = [
            make_member(income={"workersComp": 14_400}),
            make_member(relationship="spouse", income={"wages": 21_000, "workersComp": 3_000}),
        ]
        self.assertEqual(self._income(members), 21_000)

    def test_foster_child_income_is_excluded_entirely(self):
        """§ 5.609(b)(8), including the unearned income a minor exclusion would miss."""
        members = [
            make_member(income={"wages": 34_000}),
            make_member(age=16, relationship="fosterChild", income={"childSupport": 7_200}),
        ]
        self.assertEqual(self._income(members), 34_000)


class TestIlHcvDependents(TestCase):
    def _count(self, members):
        return make_calculator(members=members)._count_dependents()

    def test_minor_children_count(self):
        members = [make_member(), make_member(age=12, relationship="child"), make_member(age=7, relationship="child")]
        self.assertEqual(self._count(members), 2)

    def test_head_spouse_and_domestic_partner_never_count(self):
        members = [
            make_member(age=17),
            make_member(age=17, relationship="spouse"),
            make_member(age=17, relationship="domesticPartner"),
        ]
        self.assertEqual(self._count(members), 0)

    def test_adult_full_time_student_counts(self):
        members = [make_member(), make_member(age=19, relationship="child", student_full_time=True)]
        self.assertEqual(self._count(members), 1)

    def test_adult_with_a_disability_counts(self):
        members = [make_member(), make_member(age=22, relationship="child", disabled=True)]
        self.assertEqual(self._count(members), 1)

    def test_adult_who_is_neither_student_nor_disabled_does_not_count(self):
        members = [make_member(), make_member(age=68, relationship="parent")]
        self.assertEqual(self._count(members), 0)

    def test_foster_child_counts_departing_from_the_federal_text(self):
        """MFB convention: `fosterChild` conflates foster placement with kinship care,
        and a kinship-care child is an ordinary dependent, so the deduction is kept."""
        members = [make_member(), make_member(age=16, relationship="fosterChild")]
        self.assertEqual(self._count(members), 1)


class TestIlHcvElderlyOrDisabledFamily(TestCase):
    def _is_elderly_or_disabled(self, members):
        return make_calculator(members=members)._is_elderly_or_disabled_family()

    def test_sole_member_62_qualifies(self):
        self.assertTrue(self._is_elderly_or_disabled([make_member(age=62)]))

    def test_head_61_does_not(self):
        self.assertFalse(self._is_elderly_or_disabled([make_member(age=61)]))

    def test_spouse_62_qualifies(self):
        members = [make_member(age=50), make_member(age=63, relationship="spouse")]
        self.assertTrue(self._is_elderly_or_disabled(members))

    def test_head_with_a_disability_qualifies(self):
        self.assertTrue(self._is_elderly_or_disabled([make_member(age=45, disabled=True)]))

    def test_elderly_non_head_member_does_not_qualify_the_family(self):
        members = [make_member(age=35), make_member(age=70, relationship="parent")]
        self.assertFalse(self._is_elderly_or_disabled(members))

    def test_child_with_a_disability_does_not_qualify_the_family(self):
        members = [make_member(age=35), make_member(age=10, relationship="child", disabled=True)]
        self.assertFalse(self._is_elderly_or_disabled(members))

    def test_unknown_head_age_without_disability_does_not_qualify(self):
        self.assertFalse(self._is_elderly_or_disabled([make_member(age=None)]))


class TestIlHcvTotalTenantPayment(TestCase):
    """24 CFR 5.628(a) — the highest of three prongs, rounded half-up."""

    def _ttp(self, annual_income, annual_adjusted):
        calc = make_calculator()
        return calc._total_tenant_payment(annual_income, calc._adjusted_income(annual_adjusted))

    def test_thirty_percent_prong_governs(self):
        # No dependents and not elderly, so adjusted == income: $36,450/40 = $911.25.
        self.assertEqual(self._ttp(36_450, 36_450), 911)

    def test_ten_percent_prong_governs_when_deductions_dominate(self):
        members = [
            make_member(age=47, disabled=True, income={"sSDisability": 6_060}),
            *[make_member(age=age, relationship="child") for age in (17, 15, 13, 11, 8, 7, 5)],
        ]
        calc = make_calculator(members=members, county="Peoria", zipcode="61604")
        income = calc._annual_income()
        adjusted = calc._adjusted_income(income)
        # 7 dependents + elderly/disabled → $4,050 of deductions, adjusted $2,010.
        self.assertEqual(adjusted, 2_010)
        # 30% of monthly adjusted is $50.25; 10% of monthly income is $50.50.
        self.assertEqual(calc._total_tenant_payment(income, adjusted), 51)

    def test_rounds_half_up_not_half_even(self):
        """$1,188.50 must round to $1,189. Python's `round()` gives 1188, and so does
        a float `0.3 * (47540 / 12)`, which lands at 1188.4999999999998."""
        self.assertEqual(self._ttp(50_040, 47_540), 1_189)

    def test_rounds_a_half_dollar_up_at_a_second_value(self):
        self.assertEqual(self._ttp(30_500, 29_500), 738)

    def test_rounds_below_a_half_dollar_down(self):
        # $35,450/40 = $886.25.
        self.assertEqual(self._ttp(36_450, 35_450), 886)

    def test_zero_income_gives_a_zero_payment_under_the_modelled_minimum_rent(self):
        self.assertEqual(self._ttp(0, 0), 0)

    def test_deductions_never_drive_adjusted_income_negative(self):
        calc = make_calculator(members=[make_member(age=70)])
        # $0 income less the $550 elderly deduction floors at $0, not −$550.
        self.assertEqual(calc._adjusted_income(0), 0)


class TestIlHcvGrossRentProxy(TestCase):
    def test_reported_rent_is_used_when_present(self):
        calc = make_calculator(rent=1_500)
        self.assertEqual(calc._gross_rent_proxy(1_781), 1_500)

    def test_falls_back_to_the_payment_standard_with_no_rent(self):
        calc = make_calculator(rent=0)
        self.assertEqual(calc._gross_rent_proxy(1_781), 1_781)

    def test_mortgage_is_not_a_rent_proxy(self):
        """24 CFR 982.4: gross rent is rent to owner plus the utility allowance. An
        owner household falls back to the payment standard."""
        calc = make_calculator()
        calc.screen.calc_expenses = Mock(side_effect=lambda frequency, types: 2_000.0 if "mortgage" in types else 0.0)
        self.assertEqual(calc._gross_rent_proxy(1_781), 1_781)
        calc.screen.calc_expenses.assert_called_with("monthly", ["rent"])


class TestIlHcvIncomeGate(TestCase):
    def test_income_at_the_limit_is_eligible(self):
        """The regulation phrases the test as "does not exceed", so it is inclusive."""
        calc = make_calculator(members=[make_member(income={"wages": 42_550})], household_size=1)
        with patch_hud(income_limit=CHICAGO_VLI[1], payment_standard=CHICAGO_FMR[1]):
            self.assertTrue(calc.eligible().eligible)

    def test_one_dollar_over_the_limit_is_not_eligible(self):
        calc = make_calculator(members=[make_member(income={"wages": 42_551})], household_size=1)
        with patch_hud(income_limit=CHICAGO_VLI[1]):
            self.assertFalse(calc.eligible().eligible)

    def test_the_limit_is_looked_up_for_the_household_size_and_county(self):
        calc = make_calculator(members=[make_member(income={"wages": 18_000})], county="Peoria", zipcode="61604")
        patcher, income_mock, _ = hud_mocks(income_limit=PEORIA_VLI[1], payment_standard=PEORIA_FMR[1])
        with patcher:
            calc.eligible()
        income_mock.assert_called_once_with(calc.screen, "50%", "2026")

    def test_null_household_size_passes_the_gate_inclusively(self):
        """Committed treatment: a null size is not compared against a limit. Normally
        unreachable — `household_size` is a declared dependency."""
        calc = make_calculator(members=[make_member(income={"wages": 500_000})], household_size=None)
        patcher, income_mock, _ = hud_mocks(income_limit=CHICAGO_VLI[4])
        with patcher:
            self.assertTrue(calc.eligible().eligible)
        income_mock.assert_not_called()

    def test_no_asset_gate_is_applied(self):
        """Data gap 4: a household reporting assets far above the § 5.618 threshold is
        still eligible, because `household_assets` is not HUD's net family assets."""
        calc = make_calculator(members=[make_member(income={"wages": 18_000})], household_size=1)
        calc.screen.household_assets = 500_000
        with patch_hud(income_limit=CHICAGO_VLI[1], payment_standard=CHICAGO_FMR[1]):
            self.assertTrue(calc.eligible().eligible)

    def test_a_head_under_18_is_not_gated(self):
        """Data gap 5: the rule turns on legal capacity to lease, which no numeric age
        gate can substitute for, so it is assumed met."""
        calc = make_calculator(members=[make_member(age=17, income={"wages": 12_000})], household_size=1)
        with patch_hud(income_limit=CHICAGO_VLI[1], payment_standard=CHICAGO_FMR[1]):
            self.assertTrue(calc.eligible().eligible)


class TestIlHcvSpecScenarios(TestCase):
    """One test per Test Scenario in spec.md, asserting eligibility and value."""

    def _assert_eligible(self, members, income_limit, payment_standard, expected_value, **kwargs):
        calc = make_calculator(members=members, **kwargs)
        with patch_hud(income_limit=income_limit, payment_standard=payment_standard):
            e = calc.calc()
        self.assertTrue(e.eligible, "expected eligible")
        self.assertEqual(e.value, expected_value)

    def _assert_ineligible(self, members, income_limit, **kwargs):
        calc = make_calculator(members=members, **kwargs)
        with patch_hud(income_limit=income_limit):
            e = calc.calc()
        self.assertFalse(e.eligible)

    def _cook_family_of_four(self, head_income=36_450, spouse_income=0):
        return [
            make_member(age=36, income={"wages": head_income}),
            make_member(age=35, relationship="spouse", income={"wages": spouse_income} if spouse_income else None),
            make_member(age=12, relationship="child"),
            make_member(age=7, relationship="child"),
        ]

    def test_scenario_1_cook_family_at_the_extremely_low_income_limit(self):
        self._assert_eligible(
            self._cook_family_of_four(),
            income_limit=CHICAGO_VLI[4],
            payment_standard=CHICAGO_FMR[2],
            expected_value=10_740,
            rent=1_900,
        )

    def test_scenario_2_two_earners_exactly_at_the_income_limit(self):
        # $2,531.25/month each — the mock takes annual amounts, so ×12.
        self._assert_eligible(
            self._cook_family_of_four(head_income=30_375, spouse_income=30_375),
            income_limit=CHICAGO_VLI[4],
            payment_standard=CHICAGO_FMR[2],
            expected_value=3_444,
            rent=1_900,
        )

    def test_scenario_3_cook_family_one_dollar_over_the_modelled_gate(self):
        self._assert_ineligible(
            self._cook_family_of_four(head_income=60_751),
            income_limit=CHICAGO_VLI[4],
            rent=1_900,
        )

    def test_scenario_4_single_adult_in_peoria(self):
        self._assert_eligible(
            [make_member(age=30, income={"wages": 18_000})],
            income_limit=PEORIA_VLI[1],
            payment_standard=PEORIA_FMR[1],
            expected_value=4_416,
            county="Peoria",
            zipcode="61604",
            rent=900,
        )

    def test_scenario_5_single_adult_over_peorias_modelled_gate(self):
        """The same $40,000 is inside Chicago's $42,550 limit — the county-specific
        lookup is what this pins."""
        self._assert_ineligible(
            [make_member(age=30, income={"wages": 40_000})],
            income_limit=PEORIA_VLI[1],
            county="Peoria",
            zipcode="61604",
            rent=900,
        )

    def test_scenario_6_five_person_cook_household(self):
        members = [
            make_member(age=38, income={"wages": 39_400}),
            make_member(age=37, relationship="spouse"),
            make_member(age=13, relationship="child"),
            make_member(age=10, relationship="child"),
            make_member(age=7, relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=CHICAGO_VLI[5],
            payment_standard=CHICAGO_FMR[3],
            expected_value=16_152,
            rent=2_400,
        )

    def test_scenario_7_seven_person_household_with_an_adult_full_time_student(self):
        members = [
            make_member(age=41, income={"wages": 50_040}),
            make_member(age=40, relationship="spouse"),
            make_member(age=19, relationship="child", student_full_time=True),
            make_member(age=14, relationship="child"),
            make_member(age=12, relationship="child"),
            make_member(age=9, relationship="child"),
            make_member(age=6, relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=CHICAGO_VLI[7],
            payment_standard=CHICAGO_FMR[4],
            expected_value=17_568,
            rent=2_800,
        )

    def test_scenario_8_rent_below_the_payment_standard(self):
        self._assert_eligible(
            self._cook_family_of_four(),
            income_limit=CHICAGO_VLI[4],
            payment_standard=CHICAGO_FMR[2],
            expected_value=7_368,
            rent=1_500,
        )

    def test_scenario_9_rent_below_the_households_own_tenant_payment(self):
        """The computed payment is $0; the value floors at $1 so the results page does
        not drop a household that genuinely qualifies (spec amended 2026-09-01)."""
        self._assert_eligible(
            self._cook_family_of_four(head_income=60_750),
            income_limit=CHICAGO_VLI[4],
            payment_standard=CHICAGO_FMR[2],
            expected_value=1,
            rent=1_200,
        )

    def test_scenario_10_elderly_single_adult_in_cook_with_income(self):
        self._assert_eligible(
            [make_member(age=70, income={"wages": 18_000})],
            income_limit=CHICAGO_VLI[1],
            payment_standard=CHICAGO_FMR[1],
            expected_value=13_740,
            rent=1_700,
        )

    def test_scenario_11_elderly_single_adult_in_peoria_with_no_income(self):
        self._assert_eligible(
            [make_member(age=70)],
            income_limit=PEORIA_VLI[1],
            payment_standard=PEORIA_FMR[1],
            expected_value=9_816,
            county="Peoria",
            zipcode="61604",
            rent=900,
        )

    def test_scenario_12_cook_family_with_a_working_17_year_old(self):
        members = [
            make_member(age=36, income={"wages": 55_000}),
            make_member(age=35, relationship="spouse"),
            make_member(age=17, relationship="child", income={"wages": 9_000}),
            make_member(age=7, relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=CHICAGO_VLI[4],
            payment_standard=CHICAGO_FMR[2],
            expected_value=5_172,
            rent=1_900,
        )

    def test_scenario_12_counting_the_minors_wages_would_flip_eligibility(self):
        """The raw gross of $64,000 exceeds the $60,750 limit — the exclusion is an
        eligibility rule here, not only a value one."""
        members = [
            make_member(age=36, income={"wages": 55_000}),
            make_member(age=35, relationship="spouse"),
            make_member(age=17, relationship="child", income={"wages": 9_000}),
            make_member(age=7, relationship="child"),
        ]
        calc = make_calculator(members=members, rent=1_900)
        raw_gross = sum(m.calc_gross_income("yearly", ["all"]) for m in members)
        self.assertEqual(raw_gross, 64_000)
        self.assertGreater(raw_gross, CHICAGO_VLI[4])
        self.assertEqual(calc._annual_income(), 55_000)
        with patch_hud(income_limit=CHICAGO_VLI[4], payment_standard=CHICAGO_FMR[2]):
            self.assertTrue(calc.eligible().eligible)

    def test_scenario_13_dependent_full_time_student_earning_above_the_cap(self):
        members = [
            make_member(age=46, income={"wages": 30_000}),
            make_member(age=21, relationship="child", student_full_time=True, income={"wages": 5_000}),
            make_member(age=14, relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=CHICAGO_VLI[3],
            payment_standard=CHICAGO_FMR[2],
            expected_value=12_516,
            rent=1_900,
        )

    def test_scenario_14_both_deductions_reached_through_disability(self):
        members = [
            make_member(age=45, disabled=True, income={"wages": 24_000}),
            make_member(age=22, relationship="child", disabled=True),
        ]
        self._assert_eligible(
            members,
            income_limit=CHICAGO_VLI[2],
            payment_standard=CHICAGO_FMR[1],
            expected_value=12_084,
            rent=1_700,
        )

    def test_scenario_15_second_income_is_workers_compensation(self):
        members = [
            make_member(age=38, income={"workersComp": 14_400}),
            make_member(age=35, relationship="spouse", income={"wages": 21_000}),
            make_member(age=13, relationship="child"),
            make_member(age=8, relationship="child"),
        ]
        self._assert_eligible(
            members,
            income_limit=CHICAGO_VLI[4],
            payment_standard=CHICAGO_FMR[2],
            expected_value=15_372,
            rent=1_900,
        )

    def test_scenario_16_foster_child_receiving_unearned_income(self):
        members = [
            make_member(age=41, income={"wages": 34_000}),
            make_member(age=39, relationship="spouse"),
            make_member(age=15, relationship="child"),
            make_member(age=11, relationship="child"),
            make_member(age=16, relationship="fosterChild", income={"childSupport": 7_200}),
        ]
        self._assert_eligible(
            members,
            income_limit=CHICAGO_VLI[5],
            payment_standard=CHICAGO_FMR[3],
            expected_value=17_772,
            rent=2_400,
        )

    def test_scenario_17_eight_person_peoria_household_on_the_ten_percent_prong(self):
        members = [
            make_member(age=47, disabled=True, income={"sSDisability": 6_060}),
            *[make_member(age=age, relationship="child") for age in (17, 15, 13, 11, 8, 7, 5)],
        ]
        self._assert_eligible(
            members,
            income_limit=PEORIA_VLI[8],
            payment_standard=PEORIA_FMR[4],
            expected_value=16_776,
            county="Peoria",
            zipcode="61604",
            rent=1_600,
        )


class TestIlHcvNeverRaises(TestCase):
    """A HUD lookup that raises must never propagate out and break the eligibility
    run. `calc()` finishes and falls back to the safe guess: an income gate we cannot
    evaluate is not eligible, a value we cannot compute is $0 — unfloored, because
    that is a value MFB could not compute rather than one that came out at zero."""

    def _calc(self):
        return make_calculator(members=[make_member(age=35, income={"wages": 12_000})], household_size=1)

    def test_income_lookup_hud_error(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.il.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=HudIncomeClientError("HUD unavailable")),
            get_screen_payment_standard=Mock(return_value=1_581),
        ):
            e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_income_lookup_unexpected_exception(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.il.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(side_effect=ValueError("unexpected boom")),
            get_screen_payment_standard=Mock(return_value=1_581),
        ):
            e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_hud_error_degrades_to_zero(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.il.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=CHICAGO_VLI[1]),
            get_screen_payment_standard=Mock(side_effect=HudIncomeClientError("no FMR")),
        ):
            e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_payment_standard_unexpected_exception_degrades_to_zero(self):
        calc = self._calc()
        with patch.multiple(
            "programs.programs.white_labels.il.hcv.calculator.hud_client",
            get_screen_il_ami=Mock(return_value=CHICAGO_VLI[1]),
            get_screen_payment_standard=Mock(side_effect=KeyError("unexpected")),
        ):
            e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_unconfigured_program_year_is_not_eligible(self):
        calc = self._calc()
        calc.program.year = None
        e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)
