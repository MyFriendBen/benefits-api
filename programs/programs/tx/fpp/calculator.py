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
    dependencies: ClassVar[list[str]] = [
        "age",
        "insurance",
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
        # SNAP/WIC enrollment lives in the CurrentBenefit join table, read via
        # has_base_benefit() against the cross-white-label `base_program` grouping
        # (tx_snap → "snap", tx_wic → "wic"). CHIP is collected as a per-member
        # insurance question, not a current benefit, so it is read from member
        # insurance (matches any household member — "applicant or their child").
        #
        # Do NOT read the legacy Screen.has_snap/has_wic/has_chp boolean columns:
        # the join-table migration (MFB-720) dropped them from the serializer write
        # contract, so they are never populated and are permanently False.
        adjunctive_eligible = (
            self.screen.has_base_benefit("snap")
            or self.screen.has_base_benefit("wic")
            or self.screen.has_insurance_types(("chp",))
        )

        if adjunctive_eligible:
            e.condition(True, messages.presumed_eligibility())
            return

        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
