"""Presumptive-eligibility lists resolve a state-prefixed program name.

A calculator declares base program names ("snap", "tanf", "wic") in its
``presumptive_eligibility`` or ``categorically_eligible`` list, and a household
receives a state's program (``co_snap``, ``nc_tanf``). These pin that the prefixed
name satisfies the unprefixed list, across every calculator that declares one —
the seam itself, not any one program's rules.
"""

from programs.programs.white_labels.co.dsr.calculator import DenverSidewalkRebate
from programs.programs.white_labels.co.dtr.calculator import DenverTrashRebate
from programs.programs.white_labels.cesn.energy_vec.calculator import EnergyCalculatorVehicleExchange
from programs.programs.cross_white_label.weatherization.co import WeatherizationAssistance
from programs.programs.cross_white_label.head_start.nc import NCHeadStart
from programs.programs.white_labels.nc.sunbucks.calculator import SunBucks
from programs.programs.cross_white_label.weatherization.tx import TxWap
from programs.programs.testing.current_benefit_fixtures import ReceivesBenefitTestCase


class PresumptiveEligibilityResolutionTests(ReceivesBenefitTestCase):
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
