from unittest.mock import MagicMock

from django.test import SimpleTestCase

from programs.programs.calc import Eligibility
from programs.programs.co.energy_calculator.utility_bill_pay.calculator import (
    EnergyCalculatorUtilityBillPay,
)
from programs.programs.co.utility_bill_pay.calculator import UtilityBillPay


class TestEnergyCalculatorUtilityBillPayPresumptiveMedicaid(SimpleTestCase):
    """
    CESN does not collect health insurance, so the base member-level Medicaid
    check never fires for CESN. CESN collects Medicaid at the household level via
    the "already has benefits" step, so the CESN UBP calculator adds "medicaid" to
    the household-level `presumptive_eligibility` tuple. These tests exercise that
    household-level branch directly (calling household_eligible) rather than the
    full calc() pipeline, which needs a Program row + dependency wiring.
    """

    def _build_calculator(self, has_benefit_names):
        """
        Build an EnergyCalculatorUtilityBillPay with a stubbed screen.

        - screen.has_benefit returns True only for names in `has_benefit_names`
          (the household-level "already has benefits" signal).
        - household_members is empty so the member-level insurance branch is a
          no-op (mirrors CESN, which never collects insurance).
        - the utility-provider check the CESN subclass adds is forced True so we
          isolate the presumptive logic.
        """
        screen = MagicMock()
        screen.has_benefit.side_effect = lambda name: name in has_benefit_names
        screen.household_members.all.return_value = []
        screen.energy_calculator.has_utility_provider.return_value = True

        calculator = EnergyCalculatorUtilityBillPay(
            screen=screen,
            program=MagicMock(),
            data={},
            missing_dependencies=MagicMock(),
        )
        return calculator

    def test_medicaid_in_household_presumptive_tuple(self):
        # The CESN subclass extends the base household-level tuple with "medicaid".
        self.assertIn("medicaid", EnergyCalculatorUtilityBillPay.presumptive_eligibility)
        for benefit in UtilityBillPay.presumptive_eligibility:
            self.assertIn(benefit, EnergyCalculatorUtilityBillPay.presumptive_eligibility)

    def test_base_co_ubp_does_not_include_medicaid(self):
        # The plain `co` white label must be unaffected: base stays member-level only.
        self.assertNotIn("medicaid", UtilityBillPay.presumptive_eligibility)

    def test_household_with_medicaid_is_presumptively_eligible(self):
        calculator = self._build_calculator(has_benefit_names={"medicaid"})

        e = Eligibility()
        calculator.household_eligible(e)

        # Presumed eligible via household Medicaid; income/expense test is skipped.
        self.assertTrue(e.eligible)

    def test_household_without_medicaid_is_not_presumptively_eligible(self):
        # No presumptive benefit and no household members -> falls through to the
        # income/expense path, which fails with an empty stubbed screen.
        calculator = self._build_calculator(has_benefit_names=set())

        e = Eligibility()
        calculator.household_eligible(e)

        self.assertFalse(e.eligible)
