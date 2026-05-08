import math
from programs.programs.calc import ProgramCalculator, Eligibility
from programs.programs import messages


class WaLifeline(ProgramCalculator):
    """Lifeline is a federal program providing a monthly discount on phone or internet service.
    Eligible households qualify via income (≤135% FPL) or participation in a qualifying program
    (Medicaid/Apple Health, SNAP, SSI, TANF, Section 8, or WIC). One benefit per household;
    households already receiving Lifeline are excluded.

    Data gaps: Pell Grant, Veterans Pension/Survivors Benefit, BIA General Assistance,
    Tribal TANF, FDPIR, institutionalization status, and emancipated-minor exception.
    """

    fpl_percent = 1.35
    # Standard federal benefit: $9.25/month → stored as annual value ($9.25 × 12 = $111)
    amount = 111
    dependencies = [
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def _has_qualifying_program(self) -> bool:
        if self.screen.has_benefit("snap"):
            return True
        if self.screen.has_benefit("ssi"):
            return True
        if self.screen.has_benefit("tanf"):
            return True
        if self.screen.has_benefit("section_8"):
            return True
        if self.screen.has_benefit("wic"):
            return True
        if self.screen.has_benefit("medicaid"):
            return True
        # Also check member-level Medicaid (Apple Health insurance enrollment)
        for member in self.screen.household_members.all():
            if member.has_benefit("medicaid"):
                return True
        return False

    def household_eligible(self, e: Eligibility):
        e.condition(
            not self.screen.has_benefit("lifeline"),
            messages.must_not_have_benefit("Lifeline"),
        )

        program_eligible = self._has_qualifying_program()
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = math.ceil(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(
            program_eligible or gross_income <= income_limit,
            messages.income(gross_income, income_limit),
        )
