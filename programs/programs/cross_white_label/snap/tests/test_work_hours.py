"""
SNAP sends `weekly_hours_worked_before_lsr`, and every program on a screen agrees on it.

PolicyEngine removed this field's 40-hour default in 1.815.1. SNAP has to send it or every
adult reads as working zero hours and fails `meets_snap_general_work_requirements` (30 hrs)
and `meets_snap_abawd_work_requirements` (20 hrs) — both ANDed into `is_snap_eligible` for
the whole SPM unit, with no categorical-eligibility override. See MFB-1637.

The second half is the trap. One PolicyEngine request carries every program on the screen,
so two dependencies writing different values to one field and period raise `DependencyError`
in `update_unit` — raised from `pe_input()`, which runs outside `calc_pe_eligibility`'s
try/except, so the screen 500s instead of losing one program. MA is where that bites: TAFDC
and EAEDC approximate at the $15 state minimum wage while the base class uses the $7.25
federal floor.

`pe_input` takes calculator classes here, as the other payload tests do — `pe_period` is a
property needing a configured `Program.year`, and every calculator inherits the same
property object, so the conflict these tests are about resolves to one period key either way.
"""

from django.test import TestCase, override_settings

from benefits.tests.cache_override import LOCAL_CACHE
from integrations.clients.policyengine.registry import all_calculators
from programs.framework.pe_dependencies import member as member_dependency
from programs.framework.pe_dependencies.base import DependencyError
from programs.framework.pe_dependencies.payload import pe_input
from programs.programs.cross_white_label.snap.base import SNAP_HOURS_INPUT, Snap
from programs.programs.cross_white_label.snap.co import CoSnap
from programs.programs.cross_white_label.snap.il import IlSnap
from programs.programs.cross_white_label.snap.ks import KsSnap
from programs.programs.cross_white_label.snap.ma import MaSnap
from programs.programs.cross_white_label.snap.nc import NcSnap
from programs.programs.cross_white_label.snap.tx import TxSnap
from programs.programs.cross_white_label.snap.wa import WaFap, WaSnap
from programs.programs.cross_white_label.tanf.ma import MaTafdc
from programs.programs.white_labels.ma.eaedc.calculator import MaEaedc
from programs.programs.white_labels.tx.ccs.calculator import TxCcs
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel

HOURS_FIELD = "weekly_hours_worked_before_lsr"
BASE_HOURS = member_dependency.TotalHoursWorkedDependency
MA_HOURS = member_dependency.MaTotalHoursWorkedDependency

# Every SNAP row, and the hours class each has to send. MA is the exception: it swaps rather
# than adds, because MA TAFDC and EAEDC are on the same screen sending the MA variant.
SNAP_VARIANTS = {
    Snap: BASE_HOURS,
    CoSnap: BASE_HOURS,
    IlSnap: BASE_HOURS,
    KsSnap: BASE_HOURS,
    NcSnap: BASE_HOURS,
    TxSnap: BASE_HOURS,
    WaSnap: BASE_HOURS,
    WaFap: BASE_HOURS,
    MaSnap: MA_HOURS,
}


def hours_inputs(calculator) -> list[type]:
    """The distinct hours dependencies a calculator declares, base class and subclasses alike.

    Deduplicated because splatting composes: `MaMbta` splats MaSnap, MaTafdc and MaEaedc
    inputs and so names the MA class three times. Repeats are harmless — `update_unit` only
    raises when the values differ — so what matters is how many *different* classes appear."""
    declared = [dep for dep in calculator.pe_inputs if isinstance(dep, type) and issubclass(dep, BASE_HOURS)]
    return list(dict.fromkeys(declared))


@override_settings(CACHES=LOCAL_CACHE)
class TestSnapSendsWorkHours(TestCase):
    def test_the_shared_input_is_the_base_class(self):
        self.assertIs(SNAP_HOURS_INPUT, BASE_HOURS)

    def test_every_snap_variant_sends_hours(self):
        """Without it PolicyEngine reads zero hours and one adult zeroes the household."""
        for calculator in SNAP_VARIANTS:
            with self.subTest(calculator=calculator.__name__):
                self.assertEqual(len(hours_inputs(calculator)), 1)

    def test_every_snap_variant_sends_the_class_its_state_uses(self):
        for calculator, expected in SNAP_VARIANTS.items():
            with self.subTest(calculator=calculator.__name__):
                self.assertEqual(hours_inputs(calculator), [expected])

    def test_ma_swaps_the_base_class_out_rather_than_adding_to_it(self):
        """Declaring both would send two values for one field and 500 the screen."""
        self.assertNotIn(BASE_HOURS, MaSnap.pe_inputs)
        self.assertIn(MA_HOURS, MaSnap.pe_inputs)

    def test_ma_mbta_inherits_the_swap(self):
        """MaMbta splats MaSnap.pe_inputs alongside MaTafdc's and MaEaedc's, so leaving the
        base class in MaSnap would have put both classes on one calculator."""
        from programs.programs.white_labels.ma.mbta.calculator import MaMbta

        self.assertEqual(hours_inputs(MaMbta), [MA_HOURS])

    def test_ma_keeps_every_other_snap_input(self):
        """The swap is surgical: hours is the only input MA drops from the parent."""
        dropped = [dep for dep in Snap.pe_inputs if dep not in MaSnap.pe_inputs]

        self.assertEqual(dropped, [BASE_HOURS])


@override_settings(CACHES=LOCAL_CACHE)
class TestOneHoursClassPerState(TestCase):
    """Nothing may put two hours classes on one screen. Grouping by the state prefix of
    `program_code` is the closest static stand-in for a white label's program set."""

    def test_no_calculator_declares_two_different_hours_classes(self):
        for code, calculator in all_calculators.items():
            with self.subTest(program=code):
                self.assertLessEqual(len(hours_inputs(calculator)), 1)

    def test_calculators_in_a_state_agree_on_the_class(self):
        by_state: dict[str, dict[str, type]] = {}
        for code, calculator in all_calculators.items():
            declared = hours_inputs(calculator)
            if not declared:
                continue
            state = code.split("_")[0]
            by_state.setdefault(state, {})[code] = declared[0]

        # MA (SNAP, TAFDC, EAEDC, MBTA) and TX (SNAP, CCS) are the states with more than one
        # hours-sending program today; the assertion is on whatever the registry holds, so a
        # new one is covered on arrival.
        self.assertIn("ma", by_state)
        self.assertIn("tx", by_state)

        for state, per_program in by_state.items():
            with self.subTest(state=state):
                self.assertEqual(
                    len(set(per_program.values())),
                    1,
                    f"{state} programs disagree on the hours class: {per_program}",
                )


@override_settings(CACHES=LOCAL_CACHE)
class HoursPayloadTestBase(TestCase):
    state_code = "TS"
    white_label_code = "test"
    zipcode = "78701"
    county = "Test County"

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(
            name=self.white_label_code, code=self.white_label_code, state_code=self.state_code
        )
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode=self.zipcode,
            county=self.county,
            household_size=3,
            household_assets=0,
            completed=False,
        )
        # A part-time earner, an adult reporting nothing, and a young child: the three cases
        # the floor treats differently.
        self.earner = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=34, disabled=False, student=False
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.earner,
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        self.no_income_adult = HouseholdMember.objects.create(
            screen=self.screen, relationship="spouse", age=31, disabled=False, student=False
        )
        self.child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=8, disabled=False, student=False
        )

    def hours_sent(self, calculators):
        """{member id: the one hours value in the payload}, asserting there is only one."""
        people = pe_input(self.screen, calculators)["household"]["people"]

        sent = {}
        for member_obj in (self.earner, self.no_income_adult, self.child):
            periods = people[str(member_obj.id)][HOURS_FIELD]
            self.assertEqual(len(periods), 1, f"{HOURS_FIELD} written at more than one period")
            sent[member_obj.id] = next(iter(periods.values()))
        return sent


class TestSnapHoursPayload(HoursPayloadTestBase):
    def test_snap_writes_hours_for_every_member(self):
        sent = self.hours_sent([TxSnap])

        # $2,000/mo at the $7.25 federal floor over 4 weeks — above the assumed 40.
        self.assertAlmostEqual(sent[self.earner.id], 2000 / 7.25 / 4)
        self.assertEqual(sent[self.no_income_adult.id], 40)
        self.assertEqual(sent[self.child.id], 0)


class TestMaHoursPayload(HoursPayloadTestBase):
    """MA SNAP, TAFDC and EAEDC on one screen — the DependencyError case."""

    state_code = "MA"
    white_label_code = "ma"
    zipcode = "02101"
    county = "Suffolk County"

    def test_snap_alongside_tafdc_and_eaedc_builds_one_payload(self):
        sent = self.hours_sent([MaSnap, MaTafdc, MaEaedc])

        # $2,000/mo at the $15 MA minimum wage is 33.3 hours, under the floor.
        self.assertEqual(sent[self.earner.id], 40)
        self.assertEqual(sent[self.no_income_adult.id], 40)
        self.assertEqual(sent[self.child.id], 0)

    def test_program_order_does_not_change_the_result(self):
        self.assertEqual(
            self.hours_sent([MaSnap, MaTafdc, MaEaedc]),
            self.hours_sent([MaEaedc, MaTafdc, MaSnap]),
        )

    def test_snap_on_its_own_sends_the_ma_approximation(self):
        """A screen where TAFDC and EAEDC are gated out still gets MA's wage, so SNAP
        results do not depend on which sibling programs happened to run."""
        self.assertEqual(hours_inputs(MaSnap), [MA_HOURS])

    def test_the_base_class_would_have_conflicted(self):
        """Guards the reason for the swap: this is the 500 MaSnap exists to avoid. The
        earner's $2,000/mo reads 68.9 hours federally against MA's floored 40."""
        with self.assertRaises(DependencyError):
            pe_input(self.screen, [TxSnap, MaTafdc])


class TestTxHoursPayload(HoursPayloadTestBase):
    """TX CCS already sent the base class, so TX SNAP joining it is a no-op for the payload."""

    state_code = "TX"
    white_label_code = "tx"
    county = "Travis County"

    def test_snap_alongside_ccs_builds_one_payload(self):
        self.assertEqual(self.hours_sent([TxSnap, TxCcs]), self.hours_sent([TxCcs]))
