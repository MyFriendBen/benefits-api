"""
Tests for PolicyEngine's actual-receipt contract as a whole — the wiring that has to hold
across calculators rather than inside any one of them.

Three things can silently break it:

* A calculator that reads simulated SSI/TANF/SNAP without adopting the contract. It would
  keep conferring categorical eligibility, or counting income, off a benefit the household
  doesn't receive.
* One of the four programs left reading its receipt-gated field. Those read 0 for every
  non-recipient once the take-up flags go out, and the frontend drops programs valued at
  $0 — so the program would vanish from results for everyone not already on it.
* A contract input losing its min_pe_version. An unknown variable 400s the whole request,
  taking down every PolicyEngine program in it, not just the one that sent it.
"""

from django.test import TestCase

from programs.programs.federal.pe.spm import SNAP_BASE_INPUTS
from programs.framework.pe_dependencies import member, receipt_contract, spm
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.programs.cross_white_label.snap.base import Snap
from programs.programs.cross_white_label.tanf.base import Tanf
from programs.programs.cross_white_label.tanf.ks import KsTanf
from programs.programs.cross_white_label.wic.base import Wic
from programs.programs.cross_white_label.ssi.base import Ssi
from programs.programs.cross_white_label.msp.base import Msp
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.liheap.tx import TxCeap
from programs.programs.cross_white_label.medicaid.disability.il_aabd import IlAabd
from programs.programs.white_labels.co.andcs.calculator import AidToTheNeedyAndDisabled

# The amount inputs predate the contract; everything else arrived with it.
UNGATED_FIELDS = {"ssi", "tanf"}


class TestReceiptContractBundle(TestCase):
    def test_carries_receipt_and_take_up_for_all_three_benefits(self):
        self.assertEqual(
            {dep.field for dep in receipt_contract},
            {
                "ssi",
                "receives_ssi",
                "takes_up_ssi_if_eligible",
                "tanf",
                "receives_tanf",
                "takes_up_tanf_if_eligible",
                "receives_snap",
                "takes_up_snap_if_eligible",
            },
        )

    def test_snap_has_no_amount_input(self):
        """
        SNAP is receipt-only: the screener captures no SNAP dollar amount, so there is no
        `snap` input to send. PolicyEngine computes the amount and `receives_snap` carries
        the categorical signal. Should SNAP amount capture ever land, the amount input
        belongs in this bundle alongside ssi and tanf.
        """
        self.assertNotIn("snap", {dep.field for dep in receipt_contract})

    def test_every_new_field_is_version_gated(self):
        for dep in receipt_contract:
            expected = () if dep.field in UNGATED_FIELDS else (1, 779, 3)
            self.assertEqual(dep.min_pe_version, expected, f"{dep.field} carries the wrong version gate")

    def test_the_suppressing_half_is_the_gated_half(self):
        """
        The bundle's gating is deliberately mixed, and this is what makes that safe.

        Only the `ssi` and `tanf` *amount* inputs are ungated; every field that can suppress a
        benefit or assert receipt carries the floor. So below the floor we send amounts with no
        take-up flags, and there is no resolvable version at which we tell PolicyEngine to zero
        a benefit without also sending the evidence for it.

        Flooring the amounts too — the symmetric-looking alternative — would withhold reported
        SSI/TANF from older models, which loses information rather than tightening anything.
        """
        for dep in receipt_contract:
            suppresses_or_asserts_receipt = dep.field.startswith(("takes_up_", "receives_"))
            if suppresses_or_asserts_receipt:
                self.assertEqual(dep.min_pe_version, (1, 779, 3), f"{dep.field} must never outrun its floor")
            else:
                self.assertEqual(dep.field in UNGATED_FIELDS, True, f"{dep.field} is an unexpected ungated field")

    def test_would_be_outputs_are_version_gated(self):
        for dep in (member.SsiIfTakesUp, spm.SnapIfTakesUp, spm.TanfIfTakesUp):
            self.assertEqual(dep.min_pe_version, (1, 779, 3), dep.field)

    def test_wic_stays_on_the_ungated_output(self):
        """
        WIC is not switched to `wic_if_takes_up`, because for our payloads the two are the same
        number: `wic` is `wic_if_takes_up` gated on `takes_up_wic_if_eligible`, which defaults
        True and which we never send. `receives_wic` is measurably inert, so it is not wired
        either — there is no WIC suppression for a would-be output to route around.

        Staying ungated keeps WIC out of `_drop_unreadable_programs` below the version floor.
        """
        self.assertEqual(member.Wic.min_pe_version, ())
        sent_fields = {dep.field for dep in receipt_contract}
        self.assertNotIn("takes_up_wic_if_eligible", sent_fields)
        self.assertNotIn("receives_wic", sent_fields)


class TestProgramsReadWouldBeOutputs(TestCase):
    """
    A program the contract gates must report what the household *would* get, not the
    receipt-gated field its take-up flag zeroes out.

    That means `*_if_takes_up` for SNAP, TANF and SSI. WIC is the exception: we send no WIC
    take-up flag, so its plain output is already the would-be value.
    """

    def test_snap(self):
        self.assertEqual(Snap.pe_name, "snap_if_takes_up")
        self.assertEqual(Snap.pe_outputs, [spm.SnapIfTakesUp])

    def test_tanf(self):
        self.assertEqual(Tanf.pe_name, "tanf_if_takes_up")
        self.assertEqual(Tanf.pe_outputs, [spm.TanfIfTakesUp])

    def test_ssi(self):
        self.assertEqual(Ssi.pe_name, "ssi_if_takes_up")
        self.assertEqual(Ssi.pe_outputs, [member.SsiIfTakesUp])

    def test_wic_reads_the_ungated_output(self):
        """The exception: `wic` is already the would-be value, since `takes_up_wic_if_eligible`
        is never sent and holds at its True default. See
        `test_wic_stays_on_the_ungated_output`."""
        self.assertEqual(Wic.pe_name, "wic")
        self.assertIn(member.Wic, Wic.pe_outputs)


class TestAdoptingCalculators(TestCase):
    """
    Every calculator whose eligibility or income reads SSI, TANF or SNAP sends the contract.

    PE requests are a single shared payload, so in practice these inputs reach every program
    in a request regardless of which one declared them. Declaring them on each consumer is
    what keeps that from depending on which programs a white label happens to enable.
    """

    def _assert_adopts(self, calculator, inputs=None):
        pe_inputs = inputs if inputs is not None else calculator.pe_inputs
        for dep in receipt_contract:
            self.assertIn(dep, pe_inputs, f"{getattr(calculator, '__name__', calculator)} is missing {dep.field}")

    def test_snap_all_states(self):
        """All 8 SNAP variants are XxSnap(Snap) sharing SNAP_BASE_INPUTS, so this covers
        CO / IL / KS / MA / NC / TX / WA and the federal calculator at once."""
        self._assert_adopts(Snap, SNAP_BASE_INPUTS)
        self._assert_adopts(Snap)

    def test_head_start_and_early_head_start(self):
        self._assert_adopts(HeadStart)
        self._assert_adopts(EarlyHeadStart)

    def test_wic(self):
        """WIC's adjunct test reads SNAP/TANF receipt."""
        self._assert_adopts(Wic)

    def test_medicaid_and_msp(self):
        """medicaid_category and msp_category both have SSI-recipient pathways."""
        self._assert_adopts(Medicaid)
        self._assert_adopts(Msp)

    def test_lifeline(self):
        self._assert_adopts(Lifeline)

    def test_ssi_and_tanf_themselves(self):
        self._assert_adopts(Ssi)
        self._assert_adopts(Tanf)

    def test_state_programs_that_read_ssi_or_tanf(self):
        self._assert_adopts(IlAabd)  # counts SSI as unearned income
        self._assert_adopts(TxCeap)  # counts SSI via applicable_ssi
        self._assert_adopts(AidToTheNeedyAndDisabled)  # tops up SSI
        self._assert_adopts(KsTanf)  # excludes SSI recipients from the assistance unit


class TestSupersededSsiInputsStayAbsent(TestCase):
    """
    Reported SSI travels as the `ssi` amount and suppression as the take-up flag, so the
    separate `ssi_reported` / `use_reported_ssi` channel must not come back. Measured against
    the live API, `ssi_reported` without `use_reported_ssi` moves nothing — not `ssi`,
    `applicable_ssi`, `co_state_supplement`, `il_aabd_person` or `tx_ceap` — so re-adding it
    would read as a working input while doing nothing.
    """

    def test_reported_ssi_dependencies_are_absent(self):
        for name in ("SsiReportedDependency", "UseReportedSsiDependency", "SsiAmountIfEligible"):
            self.assertFalse(hasattr(member, name), f"{name} duplicates the `ssi` input and must stay absent")

    def test_snap_receipt_sentinel_is_absent(self):
        """A `snap: 1` input pins PolicyEngine's computed SNAP to $1/mo for anyone reporting
        receipt, polluting the income every other program in the request reads. `receives_snap`
        carries that signal without a dollar value."""
        self.assertFalse(hasattr(spm, "Snap"))
