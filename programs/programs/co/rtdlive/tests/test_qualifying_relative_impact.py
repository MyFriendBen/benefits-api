"""Tests for CO RTD LiVE after the qualifying-relative fix (MFB-722)."""

from django.test import TestCase
from unittest.mock import Mock

from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream
from programs.programs.co.rtdlive.calculator import RtdLive
from programs.programs.calc import MemberEligibility

# 2024 FPL values (48 contiguous states), mocked for deterministic tests
FPL_2024 = {1: 15060, 2: 20440, 3: 25820, 4: 31200}

DENVER_ZIP = "80204"  # eligible county
EL_PASO_ZIP = "80951"  # not in RtdLive.eligible_counties


def _make_program():
    mock_program = Mock()
    mock_program.year.as_dict.return_value = FPL_2024
    return mock_program


def _make_missing_deps():
    mock = Mock()
    mock.has.return_value = False
    return mock


class TestRtdLiveQualifyingRelativeImpact(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(
            name="Colorado", code="co", state_code="CO"
        )

    def _make_screen(self, zipcode: str) -> Screen:
        return Screen.objects.create(
            white_label=self.white_label,
            completed=False,
            last_tax_filing_year="2024",
            zipcode=zipcode,
        )

    def _make_calculator(self, screen: Screen) -> RtdLive:
        return RtdLive(screen, _make_program(), {}, _make_missing_deps())

    def test_eligible_when_household_income_is_low(self):
        """Parents $30k + adult child $0 → combined $30k < 3-person 2.5×FPL ($64,550) → eligible."""
        screen = self._make_screen(DENVER_ZIP)
        head = HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=40
        )
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=15000, frequency="yearly"
        )
        spouse = HouseholdMember.objects.create(screen=screen, relationship="spouse", age=38)
        IncomeStream.objects.create(
            screen=screen, household_member=spouse, type="wages", amount=15000, frequency="yearly"
        )
        adult_child = HouseholdMember.objects.create(
            screen=screen, relationship="child", age=25, student=False
        )

        self.assertTrue(adult_child.is_in_tax_unit())

        calc = self._make_calculator(screen)
        e = MemberEligibility(adult_child)
        calc.member_eligible(e)

        self.assertTrue(e.eligible)

    def test_ineligible_when_household_income_is_high(self):
        """Post-fix behavior change: adult dependent with high-earning parents loses eligibility.

        Before fix: split into secondary unit, evaluated on own $0 → eligible.
        After fix: joins main unit, evaluated on combined $80k > $64,550 → not eligible.
        """
        screen = self._make_screen(DENVER_ZIP)
        head = HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=40
        )
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=40000, frequency="yearly"
        )
        spouse = HouseholdMember.objects.create(screen=screen, relationship="spouse", age=38)
        IncomeStream.objects.create(
            screen=screen, household_member=spouse, type="wages", amount=40000, frequency="yearly"
        )
        adult_child = HouseholdMember.objects.create(
            screen=screen, relationship="child", age=25, student=False
        )

        self.assertTrue(adult_child.is_in_tax_unit())

        calc = self._make_calculator(screen)
        e = MemberEligibility(adult_child)
        calc.member_eligible(e)

        self.assertFalse(e.eligible)

    def test_non_dependent_adult_evaluated_on_own_income(self):
        """Adult child earning $10k is above threshold → splits into secondary unit → eligible on own income."""
        screen = self._make_screen(DENVER_ZIP)
        head = HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=40
        )
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=40000, frequency="yearly"
        )
        spouse = HouseholdMember.objects.create(screen=screen, relationship="spouse", age=38)
        IncomeStream.objects.create(
            screen=screen, household_member=spouse, type="wages", amount=40000, frequency="yearly"
        )
        adult_child = HouseholdMember.objects.create(
            screen=screen, relationship="child", age=25, student=False
        )
        IncomeStream.objects.create(
            screen=screen, household_member=adult_child, type="wages", amount=10000, frequency="yearly"
        )

        self.assertFalse(adult_child.is_in_tax_unit())

        calc = self._make_calculator(screen)
        e = MemberEligibility(adult_child)
        calc.member_eligible(e)

        self.assertTrue(e.eligible)

    def test_county_gate_blocks_ineligible_county(self):
        """Households outside eligible counties are ineligible regardless of dependency status."""
        screen = self._make_screen(EL_PASO_ZIP)
        head = HouseholdMember.objects.create(
            screen=screen, relationship="headOfHousehold", age=40
        )
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=15000, frequency="yearly"
        )
        spouse = HouseholdMember.objects.create(screen=screen, relationship="spouse", age=38)
        IncomeStream.objects.create(
            screen=screen, household_member=spouse, type="wages", amount=15000, frequency="yearly"
        )
        HouseholdMember.objects.create(
            screen=screen, relationship="child", age=25, student=False
        )

        calc = self._make_calculator(screen)
        result = calc.eligible()

        self.assertFalse(result.eligible)
