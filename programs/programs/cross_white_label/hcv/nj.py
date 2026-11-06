"""NJ Housing Choice Voucher (Section 8)."""

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.hcv.base import HousingChoiceVoucher


class NjHcv(HousingChoiceVoucher):
    """
    New Jersey's Housing Choice Voucher, as the Department of Community Affairs (DCA) runs it
    statewide. NJ inherits every federal rule and adds one: the head of household must be 18
    or older (DCA also takes an emancipated minor, which the screener can't record).

    The low-income (80%) route is offered with its special categories unevaluated, so every
    household at or below HUD's low-income limit can pass. Income limits are FY2026,
    read through the program's year; FMRs are FY2027.

    Values assume DCA applies HUD's HOTMA rules at calendar-2027 amounts from 2027-01-01:
    the asset limit, the student earnings cap and both deductions. MFB-2467 is confirming
    that with DCA. Minimum rent is $0 and DCA adds no deductions.

    Payment standards are HUD's FY2027 FMR by county, or the ZIP's Small Area FMR in the four
    mandatory-SAFMR metros (Bergen-Passaic, Jersey City, Monmouth-Ocean and the NJ counties of
    Philadelphia-Camden-Wilmington). This assumes DCA sets its standard at the FMR and uses
    SAFMRs in Hudson County, as HUD's 2024 designation requires.

    The spec is ``programs/cross_white_label/hcv/nj/hcv_nj_spec.md`` in program-ops.
    """

    program_code = "nj_hcv"

    net_assets_limit_amount = 109_797
    student_earnings_cap = 525
    dependent_deduction = 525
    elderly_disabled_deduction = 575
    minimum_rent = 0
    special_category_assumed = True
    payment_standard_year = 2027

    #: DCA plan §7.4, Subsidy Standards for Standard Issuance.
    subsidy_standards = (
        (0, 1, 1),
        (1, 1, 2),
        (2, 2, 4),
        (3, 4, 6),
        (4, 6, 8),
        (5, 8, 10),
        (6, 10, 12),
    )

    head_of_household_min_age = 18

    def household_eligible(self, e: Eligibility) -> None:
        super().household_eligible(e)

        head = self.screen.get_head()
        head_age = head.calc_age() if head is not None else None
        e.condition(head_age is None or head_age >= self.head_of_household_min_age)
