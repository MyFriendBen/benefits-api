"""NJ ACA Premium Tax Credit — the first state on the MFB federal base."""

from decimal import Decimal
from typing import Optional

from programs.programs.cross_white_label.aca.mfb_base import MfbAca
from screener.models import HouseholdMember

#: NJ DOBI, 2026 New Jersey Individual Health Benefits Plans and Rates. Ages 0–14 share one
#: factor and 64 and over another.
NJ_AGE_RATING_FACTORS: dict[int, Decimal] = {
    **{age: Decimal("0.765") for age in range(0, 15)},
    15: Decimal("0.833"),
    16: Decimal("0.859"),
    17: Decimal("0.885"),
    18: Decimal("0.913"),
    19: Decimal("0.941"),
    20: Decimal("0.970"),
    21: Decimal("1.000"),
    22: Decimal("1.000"),
    23: Decimal("1.000"),
    24: Decimal("1.000"),
    25: Decimal("1.004"),
    26: Decimal("1.024"),
    27: Decimal("1.048"),
    28: Decimal("1.087"),
    29: Decimal("1.119"),
    30: Decimal("1.135"),
    31: Decimal("1.159"),
    32: Decimal("1.183"),
    33: Decimal("1.198"),
    34: Decimal("1.214"),
    35: Decimal("1.222"),
    36: Decimal("1.230"),
    37: Decimal("1.238"),
    38: Decimal("1.246"),
    39: Decimal("1.262"),
    40: Decimal("1.278"),
    41: Decimal("1.302"),
    42: Decimal("1.325"),
    43: Decimal("1.357"),
    44: Decimal("1.397"),
    45: Decimal("1.444"),
    46: Decimal("1.500"),
    47: Decimal("1.563"),
    48: Decimal("1.635"),
    49: Decimal("1.706"),
    50: Decimal("1.786"),
    51: Decimal("1.865"),
    52: Decimal("1.952"),
    53: Decimal("2.040"),
    54: Decimal("2.135"),
    55: Decimal("2.230"),
    56: Decimal("2.333"),
    57: Decimal("2.437"),
    58: Decimal("2.548"),
    59: Decimal("2.603"),
    60: Decimal("2.714"),
    61: Decimal("2.810"),
    62: Decimal("2.873"),
    63: Decimal("2.952"),
}
NJ_AGE_RATING_FACTOR_64_AND_OVER = Decimal("3.000")


class NjAca(MfbAca):
    """
    NJ ACA Premium Tax Credit, through Get Covered New Jersey. Rules: program-ops
    ``programs/cross_white_label/aca/nj/aca_nj_spec.md``.

    The benchmark premium is DOBI's 2026 base rate for Oscar Silver Simple PCP Saver, the
    second-lowest Marketplace silver plan, times each member's age rating factor, with
    dependent children under 20 capped at three. NJ rates by age only and both of the lowest
    silver plans are sold in every county, so the county doesn't change it. 2026 rates stand
    in for 2027 until DOBI publishes them. Ages are as of the screening date.

    NJ FamilyCare's Medicaid and CHIP decide who NJ FamilyCare would cover. NJ Medicaid is a
    PolicyEngine program, so while its row is switched off this program is left out of
    results.
    """

    program_code = "nj_aca_ptc"

    medicaid_chip_program_codes = ("nj_medicaid", "nj_chip")
    gates_on = medicaid_chip_program_codes

    benchmark_base_rate = Decimal("426.25")
    max_rated_children = 3
    rated_child_max_age = 19

    def benchmark_premium(self, members: list[HouseholdMember]) -> Decimal:
        children: list[Decimal] = []
        total = Decimal(0)
        for member in members:
            age = member.calc_age()
            factor = self.age_rating_factor(age)
            if member.is_dependent() and age is not None and age <= self.rated_child_max_age:
                children.append(factor)
            else:
                total += factor

        total += sum(sorted(children, reverse=True)[: self.max_rated_children], Decimal(0))

        return self.benchmark_base_rate * total

    @staticmethod
    def age_rating_factor(age: Optional[int]) -> Decimal:
        if age is None:
            # `age` is a declared dependency, so a screen without one never reaches here.
            raise ValueError("an age rating factor needs an age")

        return NJ_AGE_RATING_FACTORS.get(age, NJ_AGE_RATING_FACTOR_64_AND_OVER)
