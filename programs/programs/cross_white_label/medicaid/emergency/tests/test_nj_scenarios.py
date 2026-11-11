"""
NJ's Emergency Medicaid (``NjEmergencyMedicaid``): one test per Test Scenario in the NJ spec
(program-ops ``programs/cross_white_label/medicaid/emergency/nj/emergency_nj_spec.md``).

Each scenario runs NJ Medicaid (``NjMedicaid``) against a recorded PolicyEngine response, then NJ's
Emergency Medicaid on that result, as the screener does. The spec is the source of truth: each
test asserts the spec's outcome. Where NJ Medicaid's PolicyEngine answer is known to differ, the
test is a strict ``xfail`` naming the discrepancy, so a cassette refresh shows when PolicyEngine's
fix lands. Nothing here works around them.

Household assets are $0 throughout: Scenario 8 states it, and NJ Medicaid tests assets only for
its aged, blind and disabled groups, which no other scenario reaches.
"""

from typing import Callable, Optional

import pytest

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.medicaid.emergency.nj import NjEmergencyMedicaid
from programs.programs.cross_white_label.medicaid.nj import NjMedicaid
from programs.programs.testing_fixtures.households import add_income, add_insurance
from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
)
from programs.util import Dependencies

YEAR = "2026"
EPISODE_COST = 8_265
NEWARK = ("07102", "Essex County")
CAMDEN = ("08102", "Camden County")

# Each scenario's Steps: (location, members), a member being
# (id, relationship, age, pregnant, monthly wages, monthly Social Security retirement, insurance).
Member = tuple[int, str, int, bool, int, int, str]
SCENARIOS: dict[int, tuple[tuple[str, str], list[Member]]] = {
    1: (NEWARK, [(1, "headOfHousehold", 35, False, 1_000, 0, "none")]),
    2: (NEWARK, [(1, "headOfHousehold", 19, False, 1_000, 0, "none")]),
    3: (NEWARK, [(1, "headOfHousehold", 18, False, 1_000, 0, "none")]),
    4: (NEWARK, [(1, "headOfHousehold", 40, False, 6_000, 0, "none")]),
    5: (
        NEWARK,
        [
            (1, "headOfHousehold", 30, False, 1_000, 0, "none"),
            (2, "child", 17, False, 0, 0, "medicaid"),
        ],
    ),
    6: (NEWARK, [(1, "headOfHousehold", 25, True, 2_500, 0, "none")]),
    7: (
        CAMDEN,
        [
            (1, "headOfHousehold", 40, False, 1_200, 0, "none"),
            (2, "spouse", 38, False, 0, 0, "none"),
        ],
    ),
    8: (CAMDEN, [(1, "headOfHousehold", 70, False, 0, 1_000, "none")]),
    9: (
        CAMDEN,
        [
            (1, "headOfHousehold", 30, False, 3_143, 0, "none"),
            (2, "spouse", 29, True, 0, 0, "none"),
        ],
    ),
}

# Each scenario's Expected outcome: the members eligible, each valued at the episode cost.
EXPECTED: dict[int, set[int]] = {
    1: {1},
    2: {1},
    3: set(),
    4: set(),
    5: {1},
    6: {1},
    7: {1, 2},
    8: {1},
    9: {2},
}

# Scenarios where NJ Medicaid's PolicyEngine answer is known to differ from the spec.
KNOWN_DISCREPANCIES: dict[int, str] = {}


class TestNjEmergencyMedicaidScenarios(PeIntegrationTestCase):
    """The NJ spec's Test Scenarios, with NJ Medicaid at PolicyEngine ``pe_version``."""

    pe_version = "2.94.7"
    pe_version_reason = (
        "Recorded at PolicyEngine current (2.94.7) on 2026-11-11 alongside NJ Medicaid's own scenarios, "
        "ahead of the suite pin. Moves back to PE_TEST_VERSION when the suite pin reaches it."
    )

    def run_scenario(self, number: int) -> Eligibility:
        (zipcode, county), members = SCENARIOS[number]
        screen = make_screen(
            screen_id=number,
            white_label_code="nj",
            state_code="NJ",
            household_size=len(members),
            zipcode=zipcode,
            county=county,
            household_assets=0,
        )
        for member_id, relationship, age, pregnant, wages, retirement, insurance in members:
            member = add_member(
                screen,
                member_id=member_id,
                relationship=relationship,
                age=age,
                pregnant=pregnant,
                disabled=False,
                student=False,
                visually_impaired=False,
                long_term_disability=False,
                was_in_foster_care=False,
                has_income=bool(wages or retirement),
            )
            add_insurance(member, none=insurance == "none", medicaid=insurance == "medicaid")
            if wages:
                add_income(member, wages, income_type="wages", frequency="monthly")
            if retirement:
                add_income(member, retirement, income_type="sSRetirement", frequency="monthly")

        nj_medicaid = calc_pe_program(screen, NjMedicaid, make_program("nj", "nj_medicaid", YEAR, "NJ"))
        program = make_program("nj", "nj_emergency_medicaid", YEAR, "NJ")
        return NjEmergencyMedicaid(screen, program, {"nj_medicaid": nj_medicaid}, Dependencies()).calc()

    def check(self, number: int) -> None:
        e = self.run_scenario(number)
        eligible = {member_e.member.id for member_e in e.eligible_members if member_e.eligible}
        self.assertEqual(eligible, EXPECTED[number])
        self.assertEqual(e.eligible, bool(EXPECTED[number]))
        self.assertEqual(e.value, EPISODE_COST * len(EXPECTED[number]))


def _scenario_test(number: int, reason: Optional[str]) -> Callable[[TestNjEmergencyMedicaidScenarios], None]:
    """One scenario's test, a strict xfail where NJ Medicaid's PolicyEngine answer is known to differ."""

    def test(self: TestNjEmergencyMedicaidScenarios) -> None:
        self.check(number)

    return pytest.mark.xfail(strict=True, reason=reason)(test) if reason else test


for _number in sorted(SCENARIOS):
    setattr(
        TestNjEmergencyMedicaidScenarios,
        f"test_scenario_{_number}",
        _scenario_test(_number, KNOWN_DISCREPANCIES.get(_number)),
    )
