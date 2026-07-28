from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages


class KsPromiseAct(ProgramCalculator):
    """
    Kansas Promise Scholarship Act.

    A last-dollar scholarship covering tuition, required fees, and required
    books/materials for students in KBOR-designated high-demand fields at Kansas
    community colleges, technical colleges, Washburn Institute of Technology, and
    certain qualifying private institutions (K.S.A. 74-32,271 et seq.).

    Only one criterion is screenable:
      - Household income at or below a size-tiered limit (K.S.A. 74-32,274):
          * family of 1-2: $100,000
          * family of 3:   $150,000
          * family of 4+:  $150,000 + $4,800 per member beyond 3
        The statute measures FAFSA adjusted gross income; the screener uses gross
        income (pre-deductions), which may be higher — so this is a conservative
        screen-out, and the description tells near-limit households to apply anyway.

    Kansas residency is enforced by white-label routing, and US citizenship is
    enforced via the program config's legal_status_required, so neither is checked
    here.

    Data gaps handled as inclusivity assumptions (see spec.md): qualifying
    educational history (recent KS graduate / GED, 3+ years KS residency, military
    dependent, or foster-care pathway) and enrollment in a KBOR-approved program at
    an eligible institution are not captured by the screener, so all households are
    assumed to satisfy them.

    Benefit value is a fixed $3,960/year estimate — the statewide average
    in-district tuition + required fees across Kansas community colleges at
    full-time enrollment ($132/credit hour x 30 credit hours/year, KBOR Community
    College Data Book 2026). Because this is a last-dollar award, a student with
    other non-repayable aid receives less; the screener cannot see other aid,
    prior Promise Act receipt, or the lifetime cap ($20,000 / 68 credit hours), so
    the estimate is the maximum a student with no other assistance would receive.
    """

    # Size-tiered income limits (K.S.A. 74-32,274).
    small_household_limit = 100_000  # family of 1-2
    base_household_limit = 150_000  # family of 3
    per_member_addition = 4_800  # each member beyond 3

    # Fixed estimated annual benefit (statewide CC tuition + fees, full-time).
    amount = 3_960

    dependencies = [
        "income_amount",
        "income_frequency",
        "household_size",
    ]

    def household_eligible(self, e: Eligibility):
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = self._income_limit()
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def _income_limit(self) -> int:
        household_size = self.screen.household_size if self.screen.household_size is not None else 1

        if household_size <= 2:
            return self.small_household_limit

        return self.base_household_limit + self.per_member_addition * (household_size - 3)
