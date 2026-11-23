"""CO CSFP."""

from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram
from screener.models import HouseholdMember


class EveryDayEats(CommoditySupplementalFoodProgram):
    program_code = "ede"
    amount = 600

    def member_value(self, member: HouseholdMember):
        ede_eligible = self.get_member_variable(member.id) > 0

        if ede_eligible:
            return self.amount

        return 0
