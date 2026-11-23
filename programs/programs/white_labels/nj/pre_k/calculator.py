from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.util import DependencyError
from screener.models import HouseholdMember


class NjPreK(ProgramCalculator):
    """
    NJ Pre-K: free full-day preschool for 3- and 4-year-olds in New Jersey school districts that
    receive Preschool Education Aid. Rules and figures: program-ops
    `programs/white_labels/nj/pre_k/nj_pre_k_spec.md`.

    A child qualifies who is 3 or 4 on October 1 of this school year or the next. The school year
    turns over on July 1. There is no income test, and immigration status is handled by the
    program record.

    Every member needs a birth month: a household with any member missing one gets no result
    rather than an ineligible one. `birth_year_month` isn't a field `missing_fields()` reports,
    so declaring it as a dependency wouldn't do this; the calculator checks it itself.

    The value is per eligible child: the county's 2026-27 per-pupil rates for district, provider
    and Head Start seats, weighted by projected FY2027 statewide enrollment in each setting and
    rounded to the dollar. A county missing from the table raises, so a screen the table doesn't
    cover is reported rather than shown at 0.

    Data gaps (spec §5): district residency isn't checked, since the screener has no school
    district; district cutoffs later than October 1; the school year the family is applying for;
    and the day of birth, so every October birthday counts as already passed on October 1.
    """

    program_code = "nj_pre_k"

    min_age = 3
    max_age = 4

    # Age is measured on October 1, and the school year starts on July 1.
    age_cutoff = (10, 1)
    school_year_start = (7, 1)

    # County: (district rate, provider rate, Head Start rate), 2026-27 full-day per pupil.
    county_rates: dict[str, tuple[int, int, int]] = {
        "Atlantic County": (16_215, 18_226, 10_071),
        "Bergen County": (16_814, 18_899, 10_443),
        "Burlington County": (16_475, 18_517, 10_232),
        "Camden County": (16_339, 18_365, 10_148),
        "Cape May County": (15_774, 17_729, 9_797),
        "Cumberland County": (15_943, 17_919, 9_902),
        "Essex County": (17_125, 19_249, 10_636),
        "Gloucester County": (16_232, 18_245, 10_081),
        "Hudson County": (17_299, 19_444, 10_744),
        "Hunterdon County": (16_870, 18_961, 10_477),
        "Mercer County": (16_875, 18_967, 10_480),
        "Middlesex County": (16_806, 18_889, 10_438),
        "Monmouth County": (16_650, 18_715, 10_341),
        "Morris County": (17_028, 19_140, 10_576),
        "Ocean County": (16_190, 18_198, 10_055),
        "Passaic County": (16_550, 18_602, 10_279),
        "Salem County": (16_232, 18_245, 10_081),
        "Somerset County": (17_323, 19_471, 10_759),
        "Sussex County": (16_517, 18_564, 10_258),
        "Union County": (17_033, 19_145, 10_579),
        "Warren County": (16_160, 18_164, 10_037),
    }

    # Projected FY2027 enrollment: (district, provider, Head Start).
    setting_seats = (49_759, 26_149, 5_298)

    dependencies = ["county"]

    def eligible(self) -> Eligibility:
        if any(m.birth_year_month is None for m in self.screen.household_members.all()):
            raise DependencyError()

        return super().eligible()

    def member_eligible(self, e: MemberEligibility) -> None:
        birth_year_month = e.member.birth_year_month
        this_year = self._school_year()

        e.condition(
            self._is_age_eligible(birth_year_month, this_year) or self._is_age_eligible(birth_year_month, this_year + 1)
        )

    def member_value(self, member: HouseholdMember) -> int:
        rates = self.county_rates[self.screen.county]
        weighted = sum(Decimal(rate) * seats for rate, seats in zip(rates, self.setting_seats)) / sum(
            self.setting_seats
        )

        return int(weighted.quantize(Decimal(1), rounding=ROUND_HALF_UP))

    def _school_year(self) -> int:
        """The year the school year under way began: this year from July 1, else last year."""
        today = self.screen.get_reference_date()
        month, day = self.school_year_start

        return today.year if today >= date(today.year, month, day) else today.year - 1

    def _is_age_eligible(self, birth_year_month: date, school_year: int) -> bool:
        month, day = self.age_cutoff
        age = HouseholdMember.age_from_date(birth_year_month, date(school_year, month, day))

        return self.min_age <= age <= self.max_age
