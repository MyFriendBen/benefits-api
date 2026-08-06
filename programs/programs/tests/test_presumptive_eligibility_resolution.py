"""
Pins the presumptive/categorical eligibility resolution for the calculators whose reads
were dead until this change and which have no test suite of their own.

Each of these calculators declares a `presumptive_eligibility` (or `categorically_eligible`)
list containing base program names — "snap", "tanf", "ssi", "wic". Those were read through
the exact-match `Screen.has_benefit()`, which never matches, because white labels ship
state-prefixed programs (co_snap, nc_tanf, tx_snap, …). So the presumptive branch was
unreachable in production for every one of them.

These tests exercise the resolution seam with real Program / CurrentBenefit rows rather
than the calculators' full `household_eligible()`, which would need the AMI and
income-limit integrations stubbed to say anything about this behavior. What's asserted is
exactly what was broken: does receiving the state's SNAP/TANF/WIC program satisfy the
calculator's declared presumptive list.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.programs.calc import Eligibility
from programs.programs.co.denver_sidewalk_rebate.calculator import DenverSidewalkRebate
from programs.programs.co.denver_trash_rebate.calculator import DenverTrashRebate
from programs.programs.co.energy_calculator.vehicle_exchange.calculator import EnergyCalculatorVehicleExchange
from programs.programs.co.weatherization_assistance.calculator import WeatherizationAssistance
from programs.programs.nc.nc_head_start.calculator import NCHeadStart
from programs.programs.nc.sun_bucks.calculator import SunBucks
from programs.programs.tx.wap.calculator import TxWap
from screener.models import Screen, WhiteLabel
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program


class PresumptiveEligibilityResolutionTests(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="80202", household_size=3, completed=False
        )

    def _receive(self, name_abbreviated: str, base_program: str) -> None:
        seed_program(self.white_label, name_abbreviated, base_program=base_program)
        _write_current_benefits(self.screen, [name_abbreviated])
        self.screen.invalidate_current_benefits_cache()

    def test_presumptive_lists_resolve_a_prefixed_snap_program(self):
        """One state SNAP program satisfies every calculator that lists "snap"."""
        self._receive("test_snap", "snap")

        for calculator, attr in (
            (WeatherizationAssistance, "presumptive_eligibility"),
            (DenverSidewalkRebate, "presumptive_eligibility"),
            (DenverTrashRebate, "presumptive_eligibility"),
            (NCHeadStart, "presumptive_eligibility"),
            (EnergyCalculatorVehicleExchange, "presumptive_eligibility"),
            (TxWap, "categorically_eligible"),
        ):
            with self.subTest(calculator=calculator.__name__):
                self.assertTrue(self.screen.has_benefit_from_list(getattr(calculator, attr)))

    def test_presumptive_lists_resolve_a_prefixed_tanf_program(self):
        self._receive("test_tanf", "tanf")

        for calculator, attr in (
            (WeatherizationAssistance, "presumptive_eligibility"),
            (DenverSidewalkRebate, "presumptive_eligibility"),
            (DenverTrashRebate, "presumptive_eligibility"),
            (NCHeadStart, "presumptive_eligibility"),
            (TxWap, "categorically_eligible"),
        ):
            with self.subTest(calculator=calculator.__name__):
                self.assertTrue(self.screen.has_benefit_from_list(getattr(calculator, attr)))

    def test_presumptive_lists_are_false_without_any_listed_benefit(self):
        """Receiving an unrelated program doesn't satisfy the lists."""
        self._receive("test_lifeline", "lifeline")

        for calculator, attr in (
            (WeatherizationAssistance, "presumptive_eligibility"),
            (DenverSidewalkRebate, "presumptive_eligibility"),
            (DenverTrashRebate, "presumptive_eligibility"),
            (NCHeadStart, "presumptive_eligibility"),
            (EnergyCalculatorVehicleExchange, "presumptive_eligibility"),
            (TxWap, "categorically_eligible"),
        ):
            with self.subTest(calculator=calculator.__name__):
                self.assertFalse(self.screen.has_benefit_from_list(getattr(calculator, attr)))

    def _sun_bucks_eligible(self, income: int = 10_000) -> bool:
        """Run SunBucks.household_eligible() against the real screen, stubbing only the
        FPL lookup and the income figure."""
        program = Mock()
        program.year.get_limit.return_value = 30_000
        self.screen.calc_gross_income = Mock(return_value=income)
        missing_deps = Mock()
        missing_deps.has.return_value = False

        e = Eligibility()
        SunBucks(self.screen, program, {}, missing_deps).household_eligible(e)
        return e.eligible

    def test_sun_bucks_excludes_a_snap_household(self):
        """NC SUN Bucks excludes SNAP/TANF households because they're auto-enrolled. The
        exclusion matched nothing before, so those households were shown the program."""
        self._receive("nc_snap", "snap")

        self.assertFalse(self._sun_bucks_eligible())

    def test_sun_bucks_excludes_a_tanf_household(self):
        self._receive("nc_tanf", "tanf")

        self.assertFalse(self._sun_bucks_eligible())

    def test_sun_bucks_allows_a_household_with_neither(self):
        self._receive("test_lifeline", "lifeline")

        self.assertTrue(self._sun_bucks_eligible())

    def test_wic_resolves_for_nurse_family_partnership(self):
        """CO/IL Nurse-Family Partnership treat WIC receipt as an income-test bypass. IL
        ships il_wic; CO's live program is co_wic (its bare "wic" row is retired)."""
        self._receive("il_wic", "wic")

        self.assertTrue(self.screen.has_base_benefit("wic"))
        self.assertFalse(self.screen.has_benefit("wic"))
