"""NJ FamilyCare CHIP — the first state on the MFB CHIP base."""

from decimal import Decimal

from programs.programs.cross_white_label.medicaid.chip.mfb_base import MfbChip, round_half_up
from screener.models import HouseholdMember

#: Section 7: MFB's 2026 silver-plan benchmark, the second-lowest monthly base rate among NJ's
#: Marketplace individual silver plans (NJ DOBI 2026 rates).
BENCHMARK_SILVER_BASE_RATE = Decimal("426.25")

#: NJ DOBI's 2026 age rating factors for children. Ages 0-14 share one factor.
CHILD_AGE_FACTORS = {15: Decimal("0.833"), 16: Decimal("0.859"), 17: Decimal("0.885"), 18: Decimal("0.913")}
YOUNG_CHILD_AGE_FACTOR = Decimal("0.765")


class NjChip(MfbChip):
    """
    NJ FamilyCare CHIP. Rules: program-ops
    ``programs/cross_white_label/medicaid/chip/nj/chip_nj_spec.md``.

    Children under 19 above Medicaid's 142% (194% for an infant or a pregnant child) up to
    350% of poverty, and pregnant women above 194% up to 200% (NJ's pregnancy ceiling is below
    the children's). A pregnant member counts as herself plus her expected child in everyone's
    family size (NJ-13-0018, CS15).

    Stricter than the base: Medicare coverage bars every route, and current NJ FamilyCare
    (CHIP) coverage bars the children's route (NJ-22-0033, CS20). NJ elects the lawfully
    residing option, which the program record's ``legal_status_required`` carries. NJ's FCEP
    election is unresolved, so NJ has no FCEP program.

    Value: an estimated private-coverage replacement cost per child, the benchmark silver base
    rate times DOBI's age factor, rounded to the dollar. Pregnancy coverage has no estimate.
    Data gaps beyond the base's: Medicare eligibility without enrolment, NJ's limited-benefit
    policies, and the fraud-termination bar.
    """

    program_code = "nj_chip"

    poverty_guideline_table = "48-state"
    pregnant_member_count_for_others = "herself_plus_expected"

    chip_income_limit_fpl = 350
    medicaid_child_income_limit_under_1_fpl = 194
    medicaid_child_income_limit_1_to_5_fpl = 142
    medicaid_child_income_limit_6_to_18_fpl = 142
    pregnant_women_option = True
    medicaid_pregnancy_income_limit_fpl = 194
    nj_pregnancy_income_limit_fpl = 200

    other_coverage_types = ("employer", "private", "medicare")
    child_route_other_coverage_types = ("chp",)

    @property
    def pregnant_income_limit_fpl(self) -> int:
        return self.nj_pregnancy_income_limit_fpl

    def child_monthly_value(self, member: HouseholdMember) -> int:
        factor = CHILD_AGE_FACTORS.get(member.calc_age(), YOUNG_CHILD_AGE_FACTOR)
        return round_half_up(BENCHMARK_SILVER_BASE_RATE * factor)
