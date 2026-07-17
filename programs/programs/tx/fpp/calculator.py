from typing import ClassVar

from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
import programs.programs.messages as messages


class TxFpp(ProgramCalculator):
    """
    Texas Family Planning Program (FPP).

    State-funded HHSC program offering free or low-cost reproductive and preventive
    health care to Texans through age 64. Migrated from a PolicyEngine calculator to
    a custom calculator (MFB-1088) so the §4140 adjunctive income bypass — which
    depends on MFB enrollment flags PolicyEngine cannot see — can be enforced directly.

    Eligibility (FPP Policy Manual):
    - Age 64 or younger. No minimum age; HHSC states only "64 or younger" (§4130).
    - Household income at or below 250% of the Federal Poverty Level (§4130), OR
      adjunctive income eligibility via enrollment in SNAP, WIC, or CHIP — applicant
      or their child (§4140). CHIP Perinatal, the 4th §4140 program, is not collected
      by the screener and is tracked as a data gap.
      The income test uses a *countable* income that mirrors PolicyEngine's
      gov.states.tx.fpp countable-income model at the version we serve (policyengine-us
      1.768.1) — see ``_countable_income``. It is NOT a flat gross-income total; PE is
      treated as the source of truth (not independently verified against 1 TAC §382.109
      / the FPP Policy Manual). If PE changes its FPP countable-income logic, re-sync.
    - Not enrolled in (full) Medicaid (§4100). FPP serves those who earn too much for
      regular Medicaid. Emergency Medicaid recipients are classified as underinsured
      and remain eligible, so they are NOT excluded. Other coverage (employer, private,
      CHIP) does not disqualify; the §4200 exception for insured clients with a
      confidentiality concern or an annual deductible > 5% of income is surfaced in the
      program description rather than enforced here.

    Texas residency is handled automatically by the TX white label.

    Benefit value:
    - $266.84/year per eligible participant — the average annual benefit value from the
      TX HHS Women's Health Programs Report FY2024 (total expenditures $78,705,897 ÷
      294,954 clients served). Mirrors PolicyEngine's gov.states.tx.fpp.annual_benefit
      parameter. The household total scales with the number of eligible members.
    """

    max_age = 64
    fpl_percent = 2.5
    member_amount = 266.84

    # Earnings of members below this age are exempt from countable income — mirrors
    # PolicyEngine (1 TAC §382.109(3)(A); FPP Policy Manual 4140 treats 18-year-olds as
    # adults). PE is treated as the source of truth here; not independently verified.
    child_age_threshold = 18

    # Monthly disregard applied to child support *received* before it counts as income —
    # only the amount above this counts. $75/month per the Texas FPP Policy Manual
    # (Definition of Income, Rev 24-2), mirroring PolicyEngine's
    # gov.states.tx.fpp.income.child_support_disregard (unchanged since 2016-07-01).
    child_support_received_disregard_monthly = 75

    dependencies: ClassVar[list[str]] = [
        "age",
        "insurance",
        "income_type",
        "income_amount",
        "income_frequency",
        "household_size",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age 64 or younger (no minimum age — HHS FPP states only "64 or younger").
        e.condition(member.age is not None and member.age <= self.max_age)

        # §4100: only (full) Medicaid disqualifies. Emergency Medicaid is a separate
        # insurance flag and is intentionally not matched here, so those recipients
        # (classified as underinsured) remain eligible.
        e.condition(not member.insurance.has_insurance_types(("medicaid",)))

    def household_eligible(self, e: Eligibility):
        # §4140 adjunctive income eligibility: enrollment in SNAP, WIC, or CHIP
        # (applicant or their child) bypasses the 250% FPL income test.
        #
        # SNAP/WIC enrollment lives in the CurrentBenefit join table under their
        # TX-scoped names (tx_snap, tx_wic — the "already have this" tiles flagged
        # in migration 0142), read via has_benefit(). CHIP is NOT a current-benefits
        # tile: tx_chip is a PolicyEngine eligibility program, never written to the
        # join table, so has_benefit("tx_chip") is always False. CHIP enrollment is
        # captured as a per-member insurance question, so it is read from member
        # insurance (matches any household member — "applicant or their child"),
        # mirroring the sibling Healthy Texas Women calculator.
        #
        # Do NOT read the legacy Screen.has_snap/has_wic/has_chp boolean columns:
        # the join-table migration (MFB-720) dropped them from the serializer write
        # contract, so they are never populated and are permanently False.
        presumptive_eligibility = (
            self.screen.has_benefit("tx_snap")
            or self.screen.has_benefit("tx_wic")
            or self.screen.has_insurance_types(("chp",))
        )

        if presumptive_eligibility:
            e.condition(True, messages.presumed_eligibility())
            return

        countable_income = self._countable_income()
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(countable_income <= income_limit, messages.income(countable_income, income_limit))

    def _countable_income(self) -> int:
        """TX FPP countable income, mirroring PolicyEngine's gov.states.tx.fpp
        (``tx_fpp_countable_income``) at the version we serve (policyengine-us 1.768.1).

        Differs from a flat gross-income total in three ways (PE treated as source of
        truth; not independently verified against 1 TAC §382.109 / the FPP Policy Manual):
          - earnings of members under ``child_age_threshold`` are exempt,
          - child support *paid* is deducted,
          - child support *received* counts only above a monthly disregard.

        The dependent-care deduction PE added in 1.771.2 (frontier) is intentionally NOT
        applied — it is absent from the 1.768.1 model we serve.
        """
        # Earned income counts only for adults (under-18 earnings are exempt). Members
        # with no recorded age are not counted as adults.
        adult_earned = sum(
            member.calc_gross_income("yearly", ["earned"])
            for member in self.screen.household_members.all()
            if member.age is not None and member.age >= self.child_age_threshold
        )

        # Unearned income counts for all ages. Child support received is pulled out of
        # the unearned bucket and re-added net of its (annualized) disregard.
        unearned = self.screen.calc_gross_income("yearly", ["unearned"], exclude=["childSupport"])
        child_support_received = self.screen.calc_gross_income("yearly", ["childSupport"])
        countable_child_support = max(
            0, child_support_received - self.child_support_received_disregard_monthly * 12
        )

        # Child support paid is deducted.
        child_support_paid = self.screen.calc_expenses("yearly", ["childSupport"])

        return int(max(0, adult_earned + unearned + countable_child_support - child_support_paid))
