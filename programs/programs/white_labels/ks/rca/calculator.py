from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.framework.pe_dependencies.receipt import (
    member_reports_ssi_amount,
    screen_reports_ssi_without_amount,
)
from programs.programs.cross_white_label.tanf.ks import KsTanf
from screener.models import HouseholdMember


def _ks_tanf_dependencies() -> list[str]:
    """The screener fields `ks_tanf` needs, read off its PolicyEngine inputs.

    RCA gates on `ks_tanf` strictly, so it must be uncalculable wherever TANF is.
    Derived rather than listed so the two cannot drift as KS TANF's inputs change.
    """
    fields = set()
    for pe_input in KsTanf.pe_inputs:
        fields.update(pe_input.dependencies)

    return sorted(fields)


class KsRca(ProgramCalculator):
    """
    Kansas Refugee Cash Assistance (RCA) — monthly cash for refugees and other
    ORR-eligible newcomers, administered by the Kansas Office for Refugees under the
    public/private model (45 CFR 400.56-400.63).

    Three criteria are evaluated:

    - ORR-eligible immigration status is carried by the program row's
      `legal_status_required` rather than by this calculator. The screener collects no
      per-member immigration status, so there is nothing here to test.
    - Ineligibility for TANF, which is both a strict `ks_tanf` eligibility gate and a
      reported-receipt check. Kansas routes refugee families with children to TANF, so
      in practice RCA reaches the households TANF cannot.
    - Non-receipt of SSI, at member scope. A member reporting SSI drops out of the RCA
      case and the rest of the household keeps its eligibility.

    Income is deliberately not tested. Kansas's RCA income standard is set by KSOR and
    approved by ORR in a state plan that is not published, so there is no threshold to
    apply; the administering agency makes that determination. The ORR eligibility
    window, the full-time-student exclusion and the voluntary-quit rule are likewise
    handled inclusively — the screener collects none of them. See spec.md Data Gaps.
    """

    program_code = "ks_rca"

    # Lowest Kansas TANF payment standard by RCA case size (Shared Living Arrangements,
    # Rural County), which holds statewide without depending on county tier. 45 CFR
    # 400.60(b) forbids an RCA payment below the comparable TANF amount for the size, so
    # this is a conservative floor rather than Kansas's actual RCA award.
    payment_standard = {1: 168, 2: 263, 3: 349, 4: 421, 5: 482, 6: 543, 7: 604, 8: 665}
    largest_tabulated_size = 4
    additional_person_amount = 61

    # `age` and `county` come from ks_tanf; the income fields are needed by both.
    dependencies = _ks_tanf_dependencies()

    def member_eligible(self, e: MemberEligibility):
        # SSI disqualifies on receipt, never on eligibility: 45 CFR 400.51(b)(1)(ii)
        # keeps RCA in payment until SSI cash assistance actually begins, so a member
        # awaiting an SSI determination stays in the case.
        e.condition(not self._member_receives_ssi(e.member))

    def _member_receives_ssi(self, member: HouseholdMember) -> bool:
        """Whether this member is the SSI recipient the screener can identify.

        A reported `sSI` amount names them directly. A ticked SSI tile with no amount
        names nobody, so it excludes only where `household_size` is 1 and there is no
        ambiguity left to preserve — MFB does not deny a member on a tile it cannot
        attribute to them.
        """
        if member_reports_ssi_amount(member):
            return True

        return self.screen.household_size == 1 and screen_reports_ssi_without_amount(self.screen)

    def household_eligible(self, e: Eligibility):
        # Ineligible for TANF. The gate is ineligibility rather than non-receipt, so it
        # reads the calculated `ks_tanf` result as well as the reported tile. The
        # dependency is strict: an absent result raises rather than being read as "not
        # TANF-eligible", which would offer RCA to a household whose TANF answer is
        # unknown.
        receives_tanf = self.screen.has_base_benefit("tanf")
        can_get_tanf = receives_tanf or self.program_eligible("ks_tanf")
        e.condition(not can_get_tanf)

    def household_value(self) -> int:
        return self.payment_standard.get(
            self._case_size(),
            self.payment_standard[self.largest_tabulated_size]
            + self.additional_person_amount * (self._case_size() - self.largest_tabulated_size),
        )

    def _case_size(self) -> int:
        """The RCA case: the household's members minus anyone excluded for SSI receipt.

        Composition is otherwise taken as MFB sees it. ORR splits a case around an adult
        child and around members living apart, but the screener records relationships
        only against the primary member, so the sub-units cannot be reconstructed
        (spec.md Data Gap 5).
        """
        return sum(1 for member in self.screen.household_members.all() if not self._member_receives_ssi(member))
