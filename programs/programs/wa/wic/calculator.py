import math
import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaWic(ProgramCalculator):
    """
    WA Women, Infants, and Children (WIC) Nutrition Program.

    Provides food benefits (~$80/month per participant) to pregnant women, infants
    under 1, and children ages 1-4. Income must be at or below 185% FPL unless the
    household receives SNAP, Medicaid, or TANF (adjunctive eligibility).

    Pregnant women count as 1 participant plus 1 unborn child for both household
    size (income test) and benefit value calculation.

    Data gaps: nutritional risk assessment (low impact, procedural);
    postpartum/breastfeeding window (medium impact, approximated via infant presence).
    """

    max_child_age = 5
    fpl_percent = 1.85
    member_amount = 80 * 12

    dependencies = [
        "age",
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        is_pregnant = member.pregnant is True
        is_under_5 = member.age is not None and member.age < self.max_child_age
        e.condition(is_pregnant or is_under_5)

    def household_eligible(self, e: Eligibility):
        # SNAP and TANF are reported in the has-benefits step, so they resolve through
        # base_program (wa_snap / wa_tanf); the bare names were exact-match reads that
        # never hit, so adjunctive eligibility never fired and every household fell
        # through to the income test.
        #
        # Medicaid is NOT a has-benefits program in WA — Apple Health is collected as
        # insurance, so wa_apple_health_medicaid never enters current_benefits and
        # has_base_benefit("medicaid") would be False for every WA screen. Read it off
        # insurance instead, the way wa/wap does.
        #
        # Only the Medicaid leg is counted. Apple Health for Kids maps to the CHP+ field
        # and mixes Medicaid and CHIP coverage; whether CHIP confers WIC adjunctive
        # eligibility in WA is a policy question, not a naming one, so it stays out.
        adjunctive_eligible = (
            self.screen.has_base_benefit("snap")
            or self.screen.has_base_benefit("tanf")
            or self.screen.has_insurance_types(("wa_apple_health_medicaid",))
        )

        if adjunctive_eligible:
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            household_size = self._wic_household_size()
            income_limit = math.ceil(self.fpl_percent * self.program.year.get_limit(household_size))
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_value(self, member) -> int:
        if member.pregnant is True:
            return self.member_amount * 2
        return self.member_amount

    def _wic_household_size(self) -> int:
        """Add 1 per pregnant member to household size (unborn children count)."""
        size = self.screen.household_size
        for member in self.screen.household_members.all():
            if member.pregnant is True:
                size += 1
        return size
