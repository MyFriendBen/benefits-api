"""CO Property Tax/Rent/Heat Credit Rebate."""

from programs.programs.cross_white_label.cpcr.base import PropertyCreditRebate


class CoPropertyCreditRebate(PropertyCreditRebate):
    program_code = "cpcr"
