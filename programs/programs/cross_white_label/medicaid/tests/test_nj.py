"""
NJ FamilyCare (Medicaid) (``NjMedicaid``): one eligibility test and one value test per Test
Scenario in the NJ spec (program-ops ``programs/cross_white_label/medicaid/nj/medicaid_nj_spec.md``).

``NjMedicaid`` takes eligibility from PolicyEngine, so every answer comes from a recorded
PolicyEngine response. Each test asserts the spec's outcome. Where PolicyEngine's eligibility is
known to differ, the test is a strict ``xfail`` naming the discrepancy: it fails loudly once
PolicyEngine's answer changes, so a cassette refresh shows which upstream fix has landed. Nothing
here works around them.

- Eligibility: the members the spec finds eligible, and no others.
- Value: each eligible member's annual value against the spec's §7 figure × 12, from the member's
  spending group. A value test is an expected failure only where PolicyEngine turns away a member
  the spec finds eligible.
"""

from typing import Callable
from unittest.mock import Mock

import pytest

import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.medicaid.federal_base import FederalMedicaid
from programs.programs.cross_white_label.medicaid.nj import NjMedicaid
from programs.programs.cross_white_label.medicaid.tests.nj_scenarios import SCENARIOS
from programs.programs.testing_fixtures.households import add_income, add_insurance
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
)
from django.test import SimpleTestCase

YEAR = "2026"

# The spec's §7 monthly figures (MACStats Exhibit 22, FY 2023 ÷ 12, rounded).
CHILD, NEW_ADULT, OTHER_ADULT, DISABLED, AGED = 350, 604, 613, 3_224, 2_388

# Each scenario's Expected outcome by member id: the monthly figure §7 gives each eligible member.
# A member not listed is ineligible.
EXPECTED: dict[int, dict[int, int]] = {
    1: {1: OTHER_ADULT, 2: OTHER_ADULT, 3: CHILD},
    2: {1: NEW_ADULT},
    3: {1: OTHER_ADULT, 2: CHILD},
    4: {1: OTHER_ADULT, 2: OTHER_ADULT, 3: CHILD},
    5: {2: CHILD},
    6: {1: OTHER_ADULT, 2: CHILD},
    7: {1: OTHER_ADULT, 2: CHILD},
    8: {2: CHILD},
    9: {1: OTHER_ADULT, 2: CHILD},
    10: {1: OTHER_ADULT, 2: CHILD},
    11: {1: OTHER_ADULT},
    12: {},
    13: {2: OTHER_ADULT},
    14: {},
    15: {},
    16: {1: OTHER_ADULT},
    17: {2: CHILD},
    18: {},
    19: {2: CHILD},
    20: {},
    21: {},
    22: {2: CHILD},
    23: {},
    24: {1: NEW_ADULT},
    25: {},
    26: {1: NEW_ADULT, 2: OTHER_ADULT},
    27: {2: OTHER_ADULT},
    28: {1: NEW_ADULT},
    29: {1: CHILD},
    30: {1: NEW_ADULT},
    31: {},
    32: {1: DISABLED},
    33: {1: NEW_ADULT, 2: CHILD},
    34: {2: CHILD},
    35: {2: NEW_ADULT},
    36: {1: NEW_ADULT, 2: NEW_ADULT},
    37: {1: DISABLED},
    38: {1: DISABLED},
    39: {1: AGED},
    40: {1: AGED},
    41: {},
    42: {1: AGED},
    43: {},
    44: {1: AGED},
    45: {1: AGED, 2: AGED},
    46: {},
    47: {1: AGED},
    48: {},
    49: {1: AGED, 2: AGED},
    50: {},
    51: {2: CHILD},
    52: {},
    53: {},
    54: {2: CHILD},
    55: {1: NEW_ADULT, 2: CHILD},
    56: {1: OTHER_ADULT, 2: CHILD},
    57: {1: OTHER_ADULT, 2: CHILD},
    58: {2: CHILD},
    59: {1: OTHER_ADULT, 2: CHILD},
    60: {1: OTHER_ADULT, 2: CHILD},
    61: {2: CHILD},
    62: {2: CHILD},
    63: {2: CHILD},
    64: {2: CHILD},
    65: {3: CHILD},
    66: {1: NEW_ADULT},
    67: {2: OTHER_ADULT},
    68: {1: DISABLED, 2: CHILD},
    69: {1: OTHER_ADULT, 2: CHILD},
    70: {1: OTHER_ADULT, 2: CHILD},
    71: {1: NEW_ADULT, 2: NEW_ADULT},
    72: {2: DISABLED},
}

_CHILD_COVERAGE = (
    "PolicyEngine does not apply the adult group's child-coverage condition (42 CFR 435.119(c)), so a "
    "parent or caretaker whose child has no coverage is admitted as an expansion adult"
)
_FILER_WITH_18_YEAR_OLD = (
    "PolicyEngine counts a tax-filing parent living with an 18-year-old as a household of 3, so the parent "
    "is admitted below the expansion limit"
)
_OTHER_MEMBERS_PREGNANCY = (
    "PolicyEngine counts another member's pregnancy as one person, not herself plus her expected child"
)
_ASSETS_AT_LIMIT = "PolicyEngine denies aged/disabled assets exactly at the limit, which the rule allows"

KNOWN_ELIGIBILITY_DISCREPANCIES: dict[int, str] = {
    **{n: _CHILD_COVERAGE for n in (5, 8, 34, 35, 54, 58, 61, 62, 63, 64, 65, 67, 72)},
    22: _FILER_WITH_18_YEAR_OLD,
    26: _OTHER_MEMBERS_PREGNANCY,
    47: _ASSETS_AT_LIMIT,
    49: _ASSETS_AT_LIMIT,
}

# Scenarios whose value test fails because PolicyEngine turns away a member the spec values. A
# discrepancy that only admits an extra member leaves the expected members' values right.
KNOWN_VALUE_DISCREPANCIES: dict[int, str] = {
    26: _OTHER_MEMBERS_PREGNANCY,
    47: _ASSETS_AT_LIMIT,
    49: _ASSETS_AT_LIMIT,
}


class TestNjMedicaidClass(SimpleTestCase):
    """What the NJ class adds to the federal base, and that it adds nothing else."""

    def test_program_code(self) -> None:
        self.assertEqual(NjMedicaid.program_code, "nj_medicaid")

    def test_is_the_federal_base_with_nj_location_inputs(self) -> None:
        self.assertTrue(issubclass(NjMedicaid, FederalMedicaid))
        self.assertFalse(NjMedicaid._abstract)
        self.assertEqual(
            NjMedicaid.pe_inputs,
            [
                *FederalMedicaid.pe_inputs,
                dependency.household.NjStateCodeDependency,
                dependency.household.NjCountyDependency,
            ],
        )

    def test_values_by_macstats_exhibit_22(self) -> None:
        self.assertEqual(
            NjMedicaid.group_spend_per_fye_enrollee,
            {"child": 4_203, "new_adult": 7_248, "other_adult": 7_351, "disabled": 38_688, "aged": 28_650},
        )

    def test_pregnant_member_in_a_child_group_takes_the_other_adult_figure(self) -> None:
        calculator = NjMedicaid.__new__(NjMedicaid)
        member = Mock(pregnant=True, calc_age=Mock(return_value=17))
        self.assertEqual(calculator.spending_group("OLDER_CHILD", member), "other_adult")
        self.assertEqual(calculator.spending_group("SSI_RECIPIENT", member), "disabled")
        member.pregnant = False
        self.assertEqual(calculator.spending_group("OLDER_CHILD", member), "child")


class TestNjMedicaidScenarios(PeIntegrationTestCase):
    """The NJ spec's Test Scenarios, at PolicyEngine ``PE_TEST_VERSION``."""

    def member_values(self, number: int) -> dict[int, float]:
        """Each member's annual value from PolicyEngine for one scenario's household."""
        scenario = next(s for s in SCENARIOS if s["number"] == number)
        screen = make_screen(
            screen_id=number,
            white_label_code="nj",
            state_code="NJ",
            household_size=scenario["household_size"],
            zipcode=scenario["zipcode"],
            county=scenario["county"],
            household_assets=scenario["assets"],
        )
        for spec_member in scenario["members"]:
            member = add_member(
                screen,
                member_id=spec_member["id"],
                relationship=spec_member["relationship"],
                age=spec_member["age"],
                pregnant=spec_member["pregnant"],
                disabled=spec_member["disabled"],
                student=False,
                visually_impaired=False,
                long_term_disability=False,
                was_in_foster_care=False,
                has_income=bool(spec_member["incomes"]),
            )
            insurance = spec_member["insurance"]
            add_insurance(
                member, none=insurance == "none", medicaid=insurance == "medicaid", medicare=insurance == "medicare"
            )
            for income_type, amount, frequency in spec_member["incomes"]:
                add_income(member, amount, income_type=income_type, frequency=frequency)

        eligibility = calc_pe_program(screen, NjMedicaid, make_program("nj", "nj_medicaid", year=YEAR))
        return {me.member.id: me.value for me in eligibility.eligible_members}

    def check_eligibility(self, number: int) -> None:
        """Assert the members PolicyEngine finds eligible are exactly the ones the scenario expects."""
        values = self.member_values(number)
        eligible = {member_id for member_id, value in values.items() if value > 0}
        self.assertEqual(
            eligible, set(EXPECTED[number]), next(s for s in SCENARIOS if s["number"] == number)["expected"]
        )

    def check_value(self, number: int) -> None:
        """Assert each expected member's annual value is the spec's §7 monthly figure × 12."""
        values = self.member_values(number)
        expected = {member_id: monthly * 12 for member_id, monthly in EXPECTED[number].items()}
        actual = {member_id: round(values.get(member_id, 0)) for member_id in expected}
        self.assertEqual(actual, expected, next(s for s in SCENARIOS if s["number"] == number)["expected"])


def _eligibility_test(number: int) -> Callable[[TestNjMedicaidScenarios], None]:
    """One scenario's eligibility test, a strict xfail where PolicyEngine is known to answer differently."""

    def test(self: TestNjMedicaidScenarios) -> None:
        self.check_eligibility(number)

    reason = KNOWN_ELIGIBILITY_DISCREPANCIES.get(number)
    return pytest.mark.xfail(strict=True, reason=reason)(test) if reason else test


def _value_test(number: int) -> Callable[[TestNjMedicaidScenarios], None]:
    """One scenario's value test, a strict xfail where PolicyEngine turns away a member the spec values."""

    def test(self: TestNjMedicaidScenarios) -> None:
        self.check_value(number)

    reason = KNOWN_VALUE_DISCREPANCIES.get(number)
    return pytest.mark.xfail(strict=True, reason=reason)(test) if reason else test


for _number in sorted(EXPECTED):
    setattr(TestNjMedicaidScenarios, f"test_scenario_{_number:02d}_eligibility", _eligibility_test(_number))
    if EXPECTED[_number]:
        setattr(TestNjMedicaidScenarios, f"test_scenario_{_number:02d}_value", _value_test(_number))
