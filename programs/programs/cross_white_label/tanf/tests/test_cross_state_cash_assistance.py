"""
Cross-state contract: non-TANF cash assistance reaches every TANF calculator's gates.

The screener offers two adjacent cash-assistance income types. ``cashAssistance`` is the
household's own TANF grant, which PolicyEngine deliberately excludes from TANF's own
unearned-income sources; ``cashAssistanceOther`` is cash aid from any other program —
General Assistance, another state's TANF, a local fund — and is ordinary countable income.

Before the split both arrived in one field, so a household reporting General Assistance had
it excluded from its own TANF calculation: a measured $200/month overstatement (MO, household
of 2, $234.09 returned where the spec says $34.09).

The states reach the new type by two different routes, which is exactly why this is asserted
per calculator rather than per route:

* KS, MO, TX and WA send ``NonTanfCashAssistanceIncomeDependency`` and let PolicyEngine sum
  its own source list.
* CO, IL, NC and MA compute countable unearned income themselves and pass a total, excluding
  only ``cashAssistance``. The new type falls into ``"unearned"`` automatically.

Asserted behaviourally rather than structurally — each calculator's own inputs are evaluated
against a household reporting the income — so a state that changes route still passes and a
state that loses the income fails.
"""

from django.test import TestCase

from integrations.clients.policyengine.registry import all_calculators
from programs.programs.cross_white_label.tanf.base import Tanf
from programs.programs.cross_white_label.tanf.ma import MaTafdc
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel

MONTHLY_AMOUNT = 400
ANNUAL_AMOUNT = MONTHLY_AMOUNT * 12


def _tanf_calculators() -> dict[str, type]:
    """Every registered TANF program. ``MaTafdc`` subclasses the generic PolicyEngine SPM
    calculator rather than ``Tanf``, so it is named explicitly; the bare ``tanf`` slug is the
    base contract rather than a shipped program."""
    registered = {
        slug: calc
        for slug, calc in all_calculators.items()
        if isinstance(calc, type) and issubclass(calc, Tanf) and calc is not Tanf
    }
    registered["ma_tafdc"] = MaTafdc
    return registered


class TanfCashAssistanceSplitTestCase(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="63101",
            county="Test County",
            household_size=2,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def _report(self, income_type: str) -> IncomeStream:
        return IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type=income_type,
            amount=MONTHLY_AMOUNT,
            frequency="monthly",
        )

    def _income_totals(self, calculator: type) -> dict[str, float]:
        """Every numeric value the calculator's inputs report, keyed by PolicyEngine field.

        Dependencies that need screen data this fixture does not carry (county lookups, tax
        units) are skipped rather than failed: this asserts where the money lands, not that
        every unrelated input is satisfiable.
        """
        totals = {}
        for dep in calculator.pe_inputs:
            field = getattr(dep, "field", None)
            if field is None:
                continue
            try:
                value = dep(self.screen, self.head, {}).value()
            except Exception:
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                totals[field] = totals.get(field, 0) + value
        return totals


class TestNonTanfCashAssistanceReachesEveryState(TanfCashAssistanceSplitTestCase):
    def test_every_tanf_calculator_counts_it(self):
        """The bug this ticket fixes. Each state must report the income under *some* field
        other than ``tanf`` — either the shared ``financial_assistance`` input or its own
        countable-unearned total."""
        for slug, calculator in sorted(_tanf_calculators().items()):
            with self.subTest(program=slug):
                IncomeStream.objects.all().delete()
                before = self._income_totals(calculator)

                self._report("cashAssistanceOther")
                after = self._income_totals(calculator)

                moved = {
                    field: after[field] - before.get(field, 0)
                    for field in after
                    if after[field] - before.get(field, 0) >= ANNUAL_AMOUNT
                }
                self.assertTrue(
                    moved,
                    f"{slug} does not count cashAssistanceOther anywhere: {before} -> {after}",
                )
                self.assertNotIn("tanf", moved, f"{slug} sends non-TANF cash aid as the household's own grant")

    def test_the_households_own_grant_stays_excluded_everywhere(self):
        """The other half of the contract, and the reason PR #1713's tile-based approach was
        reverted: a household re-reporting its own grant must not have it counted against
        itself at any gate, tile or no tile."""
        for slug, calculator in sorted(_tanf_calculators().items()):
            with self.subTest(program=slug):
                IncomeStream.objects.all().delete()
                before = self._income_totals(calculator)

                self._report("cashAssistance")
                after = self._income_totals(calculator)

                counted_against_itself = {
                    field: after[field] - before.get(field, 0)
                    for field in after
                    if field != "tanf" and after[field] - before.get(field, 0) > 0
                }
                self.assertFalse(
                    counted_against_itself,
                    f"{slug} counts the household's own TANF grant as income: {counted_against_itself}",
                )
