"""MA CCDF."""

from programs.programs.cross_white_label.ccdf.base import Ccdf
from screener.models import HouseholdMember


class MaCcdf(Ccdf):
    program_code = "ma_ccdf"
    cost_by_age = (
        # cost, age
        (23_191, 2),
        (21_125, 3),
        (16_572, 4.5),
        (12_632, 14),
    )

    def child_care_cost(self, member: HouseholdMember):
        age = member.fraction_age()

        for [cost, age_limit] in self.cost_by_age:
            if age < age_limit:
                return cost

        return 0
