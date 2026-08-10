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
* A contract input losing its min_pe_version. Every field here landed in policyengine-us
  1.779.3, and an unknown variable 400s the whole request, taking down every PolicyEngine
  program in it, not just the one that sent it.
"""

from django.test import TestCase

from programs.programs.co.pe.member import AidToTheNeedyAndDisabled
from programs.programs.federal.pe.member import EarlyHeadStart, HeadStart, Medicaid, Msp, Ssi, Wic
from programs.programs.federal.pe.spm import SNAP_BASE_INPUTS, Lifeline, Snap, Tanf
from programs.programs.il.pe.member import IlAabd
from programs.programs.ks.pe.spm import KsTanf
from programs.programs.policyengine.calculators.dependencies import member, receipt_contract, spm
from programs.programs.tx.pe.spm import TxCeap

# The amount inputs predate the contract by years; everything else is a 1.779.3 field.
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

    def test_would_be_outputs_are_version_gated(self):
        for dep in (member.SsiIfTakesUp, member.WicIfTakesUp, spm.SnapIfTakesUp, spm.TanfIfTakesUp):
            self.assertEqual(dep.min_pe_version, (1, 779, 3), dep.field)


class TestProgramsReadWouldBeOutputs(TestCase):
    """
    The four programs the contract gates must report what the household *would* get, not
    the receipt-gated field the take-up flags zero out.
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

    def test_wic(self):
        self.assertEqual(Wic.pe_name, "wic_if_takes_up")
        self.assertIn(member.WicIfTakesUp, Wic.pe_outputs)


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


class TestRetiredSsiBridge(TestCase):
    """
    The reported-SSI bridge is gone: reported SSI is the `ssi` input, and suppression is the
    take-up flag. Verified against the live API that ssi_reported without use_reported_ssi
    moves nothing — not ssi, applicable_ssi, co_state_supplement, il_aabd_person or tx_ceap.
    """

    def test_dependencies_are_removed(self):
        for name in ("SsiReportedDependency", "UseReportedSsiDependency", "SsiAmountIfEligible"):
            self.assertFalse(hasattr(member, name), f"{name} should have been removed with the reported-SSI bridge")

    def test_snap_receipt_sentinel_is_removed(self):
        """The `snap: 1` sentinel pinned PolicyEngine's computed SNAP to $1/mo for anyone
        reporting receipt, polluting the income every other program in the request read."""
        self.assertFalse(hasattr(spm, "Snap"))
