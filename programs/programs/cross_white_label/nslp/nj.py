"""NJ National School Lunch Program."""

from decimal import Decimal
from typing import Optional

from programs.programs.cross_white_label.nslp.mfb_base import REDUCED_PRICE, NationalSchoolLunchProgram
from screener.models import HouseholdMember

# New Jersey Expanded Income Eligibility: free lunch above the federal reduced-price limit.
NJEIE = "njeie"


class NjNslp(NationalSchoolLunchProgram):
    """
    New Jersey National School Lunch Program. Inherits every federal rule from
    ``NationalSchoolLunchProgram``; NJ adds a route and its own payments.

    - A student 18 or younger the federal income limits leave out eats free where household
      income is at or below NJ's expanded limit, about 224% of the poverty line (Form 427,
      SY 2026-27). Income is compared at the reported frequency, as the federal limits are.
    - NJ pays 8 cents on every lunch, plus 40 cents on a reduced-price lunch so a student 18
      or younger eats it free, and 4.31 dollars on an expanded-band lunch. A student 19 or 20
      at the reduced-price tier pays the reduced-price charge, so that lunch is worth less.
    - The school year is the 180-day minimum.

    A free, reduced-price (18 or younger) or expanded-band lunch is worth 4.84 dollars, 871 a
    year; a reduced-price lunch at 19 or 20 is worth 4.44, 799 a year. Values are rounded to
    whole dollars from 871.20 and 799.20.

    Medicaid direct certification is not evaluated: the screener can't see the income Medicaid
    used, and testing ours repeats the federal income limit.

    The spec is ``programs/cross_white_label/nslp/nj/nslp_nj_spec.md`` in program-ops.
    """

    program_code = "nj_nslp"

    school_days = 180

    max_student_age = 18

    # FY 2027 Reimbursement Rate Breakdown, public schools.
    state_lunch_rate = Decimal("0.08")
    state_reduced_price_payment = Decimal("0.40")
    njeie_rate = Decimal("4.31")

    # Form 427, SY 2026-27, NJEIE annual limits by household size.
    njeie_limits = {
        1: 35_751,
        2: 48_474,
        3: 61_197,
        4: 73_920,
        5: 86_644,
        6: 99_367,
        7: 112_090,
        8: 124_813,
        9: 137_536,
        10: 150_260,
        11: 162_983,
        12: 175_706,
        13: 188_429,
        14: 201_152,
        15: 213_876,
        16: 226_599,
    }
    njeie_additional_member = 12_724

    def _state_tier(self, member: HouseholdMember) -> Optional[str]:
        if self._is_student(member) and self._income_within(self._njeie_limit()):
            return NJEIE

        return None

    def _is_student(self, member: HouseholdMember) -> bool:
        age = member.calc_age()
        return age is not None and age <= self.max_student_age

    def _njeie_limit(self) -> int:
        size = self.screen.household_size
        largest = max(self.njeie_limits)
        if size <= largest:
            return self.njeie_limits[size]

        return self.njeie_limits[largest] + (size - largest) * self.njeie_additional_member

    def _widest_income_limit(self) -> int:
        return self._njeie_limit()

    def lunch_rate(self, member: HouseholdMember, tier: str) -> Decimal:
        if tier == NJEIE:
            return self.section_4_rate + self.state_lunch_rate + self.njeie_rate

        rate = super().lunch_rate(member, tier) + self.state_lunch_rate
        if tier == REDUCED_PRICE and self._is_student(member):
            rate += self.state_reduced_price_payment

        return rate
