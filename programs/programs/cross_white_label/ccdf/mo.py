"""Missouri Child Care Subsidy (DESE)."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages
from screener.models import EARNED_INCOME_TYPES, HouseholdMember

# DESE's Income Limits and Sliding Fee Chart, by Eligibility Unit size: the monthly
# chart maximum. Each is round(1.5 x FPL / 12) on the **2025** guidelines, so these are
# transcribed rather than derived from `program.year`, which is pinned to 2026 and would
# raise every ceiling $39-$466 above the chart DESE publishes.
CHART_MAXIMUM: dict[int, int] = {
    1: 1_956,
    2: 2_644,
    3: 3_331,
    4: 4_019,
    5: 4_706,
    6: 5_394,
    7: 6_081,
    8: 6_769,
    9: 7_456,
    10: 8_144,
    11: 8_831,
    12: 9_519,
    13: 10_206,
    14: 10_894,
    15: 11_581,
    16: 12_269,
    17: 12_956,
    18: 13_644,
    19: 14_331,
    20: 15_019,
}

# The chart's 85% State Median Income row. The ceiling is min(chart maximum, 85% SMI):
# the chart binds at sizes 1-16 and SMI at 17-20, so the SMI limb is unreachable from a
# screener capped at eight members but is the operative Missouri test.
SMI_85_PERCENT: dict[int, Decimal] = {
    1: Decimal("4023.26"),
    2: Decimal("5261.22"),
    3: Decimal("6499.10"),
    4: Decimal("7737.05"),
    5: Decimal("8975.01"),
    6: Decimal("10212.89"),
    7: Decimal("10445.01"),
    8: Decimal("10677.13"),
    9: Decimal("10909.25"),
    10: Decimal("11141.38"),
    11: Decimal("11373.50"),
    12: Decimal("11605.62"),
    13: Decimal("11837.67"),
    14: Decimal("12069.79"),
    15: Decimal("12301.91"),
    16: Decimal("12534.03"),
    17: Decimal("12766.15"),
    18: Decimal("12998.27"),
    19: Decimal("13230.39"),
    20: Decimal("13462.44"),
}

MAX_UNIT_SIZE = max(CHART_MAXIMUM)

# The daily sliding fee per child in care, (full unit, half unit), for the seven daily
# bands in ascending order. The part-unit column is omitted: the committed care pattern
# is Full day or the school-age half day, so it is never selected.
DAILY_FEES: tuple[tuple[Decimal, Decimal], ...] = (
    (Decimal("0.50"), Decimal("0.35")),
    (Decimal("0.75"), Decimal("0.50")),
    (Decimal("1.00"), Decimal("0.65")),
    (Decimal("2.00"), Decimal("1.30")),
    (Decimal("3.00"), Decimal("1.95")),
    (Decimal("4.00"), Decimal("2.60")),
    (Decimal("5.00"), Decimal("3.25")),
)

# Each size's band upper bounds on monthly adjusted gross income: the `$1.00 per year`
# band first, then the first six daily bands of DAILY_FEES. The `$5.00` band's top is
# that size's CHART_MAXIMUM, so it is not restated. A band's floor is one dollar above
# the previous band's top, and the comparison is inclusive at the top.
FEE_BAND_TOPS: dict[int, tuple[int, ...]] = {
    1: (417, 500, 583, 667, 750, 834, 917),
    2: (545, 654, 763, 872, 981, 1_090, 1_199),
    3: (674, 808, 943, 1_078, 1_212, 1_347, 1_482),
    4: (802, 962, 1_122, 1_283, 1_443, 1_604, 1_764),
    5: (930, 1_116, 1_302, 1_488, 1_674, 1_860, 2_046),
    6: (1_058, 1_270, 1_482, 1_693, 1_905, 2_117, 2_328),
    7: (1_082, 1_299, 1_515, 1_732, 1_948, 2_165, 2_381),
    8: (1_106, 1_328, 1_549, 1_770, 1_991, 2_213, 2_434),
    9: (1_130, 1_356, 1_582, 1_808, 2_034, 2_261, 2_487),
    10: (1_154, 1_385, 1_616, 1_847, 2_078, 2_309, 2_539),
    11: (1_179, 1_414, 1_650, 1_886, 2_121, 2_357, 2_593),
    12: (1_203, 1_443, 1_684, 1_924, 2_165, 2_405, 2_646),
    13: (1_227, 1_472, 1_717, 1_962, 2_208, 2_453, 2_698),
    14: (1_251, 1_501, 1_751, 2_001, 2_251, 2_501, 2_751),
    15: (1_275, 1_529, 1_784, 2_039, 2_294, 2_549, 2_804),
    16: (1_299, 1_559, 1_818, 2_078, 2_338, 2_598, 2_857),
    17: (1_323, 1_587, 1_852, 2_116, 2_381, 2_646, 2_910),
    18: (1_347, 1_616, 1_885, 2_155, 2_424, 2_694, 2_963),
    19: (1_371, 1_645, 1_919, 2_193, 2_467, 2_742, 3_016),
    20: (1_395, 1_674, 1_953, 2_232, 2_511, 2_790, 3_068),
}

INFANT = "infant"
PRESCHOOL = "preschool"
SCHOOL_AGE = "school_age"

# DESE's "Daytime Rates 2025" workbook, Licensed Center row of each grouping, plain
# (unenhanced) rates. School age carries both the full-day and the half-day cell, the
# latter pricing the before-and-after-school unit.
REGION_1 = 1
REGION_2 = 2
REGION_3 = 3
REGION_4 = 4
REGION_5 = 5

DAILY_RATES: dict[int, dict[str, Decimal]] = {
    REGION_1: {INFANT: Decimal("96.00"), PRESCHOOL: Decimal("50.00"), SCHOOL_AGE: Decimal("36.00")},
    REGION_2: {INFANT: Decimal("71.60"), PRESCHOOL: Decimal("37.00"), SCHOOL_AGE: Decimal("34.00")},
    REGION_3: {INFANT: Decimal("79.00"), PRESCHOOL: Decimal("40.00"), SCHOOL_AGE: Decimal("46.54")},
    REGION_4: {INFANT: Decimal("58.50"), PRESCHOOL: Decimal("32.50"), SCHOOL_AGE: Decimal("30.00")},
    REGION_5: {INFANT: Decimal("58.50"), PRESCHOOL: Decimal("31.00"), SCHOOL_AGE: Decimal("30.02")},
}

SCHOOL_AGE_HALF_DAY_RATES: dict[int, Decimal] = {
    REGION_1: Decimal("27.00"),
    REGION_2: Decimal("25.50"),
    REGION_3: Decimal("34.905"),
    REGION_4: Decimal("22.50"),
    REGION_5: Decimal("22.515"),
}

# The workbook's "Breakdown Of Counties" sheet, in DESE's spellings. Region 5 is also
# the default for an unmatched county, though all 115 of MFB's county strings match.
COUNTY_REGIONS: dict[int, tuple[str, ...]] = {
    REGION_1: ("Clay", "Jackson", "Jefferson", "Platte", "St Charles", "St Louis", "St Louis City"),
    REGION_2: (
        "Andrew",
        "Bates",
        "Bollinger",
        "Caldwell",
        "Callaway",
        "Clinton",
        "Cooper",
        "Dallas",
        "Franklin",
        "Howard",
        "Lafayette",
        "Lincoln",
        "Moniteau",
        "Osage",
        "Polk",
        "Warren",
        "Webster",
    ),
    REGION_3: (
        "Boone",
        "Buchanan",
        "Cape Girardeau",
        "Cass",
        "Christian",
        "Cole",
        "Greene",
        "Jasper",
        "Newton",
        "Ray",
    ),
    REGION_4: (
        "Adair",
        "Audrain",
        "Butler",
        "Dunklin",
        "Howell",
        "Johnson",
        "Laclede",
        "Marion",
        "Mississippi",
        "Nodaway",
        "Pettis",
        "Phelps",
        "Pulaski",
        "Ralls",
        "Randolph",
        "Schuyler",
        "Scott",
        "St Francois",
        "Stoddard",
        "Stone",
        "Taney",
        "Vernon",
    ),
    REGION_5: (
        "Atchison",
        "Barry",
        "Barton",
        "Benton",
        "Camden",
        "Carroll",
        "Carter",
        "Cedar",
        "Chariton",
        "Clark",
        "Crawford",
        "Dade",
        "Daviess",
        "Dekalb",
        "Dent",
        "Douglas",
        "Gasconade",
        "Gentry",
        "Grundy",
        "Harrison",
        "Henry",
        "Hickory",
        "Holt",
        "Iron",
        "Knox",
        "Lawrence",
        "Lewis",
        "Linn",
        "Livingston",
        "Macon",
        "Madison",
        "Maries",
        "McDonald",
        "Mercer",
        "Miller",
        "Monroe",
        "Montgomery",
        "Morgan",
        "New Madrid",
        "Oregon",
        "Ozark",
        "Pemiscot",
        "Perry",
        "Pike",
        "Putnam",
        "Reynolds",
        "Ripley",
        "Sainte Genevieve",
        "Saline",
        "Scotland",
        "Shannon",
        "Shelby",
        "St Clair",
        "Sullivan",
        "Texas",
        "Washington",
        "Wayne",
        "Worth",
        "Wright",
    ),
}
DEFAULT_REGION = REGION_5


def normalize_county(county: str) -> str:
    """
    Reduce an MFB or a DESE county string to one comparable form.

    A rule about the class of difference, not an exception list: an exception list
    naming the three obvious spellings leaves St. Louis and St. Charles County -- both
    Region 1 -- unmatched on the period alone. The order matters: `Ste ` is replaced
    before the casefold, or the cased literal never fires on `Ste. Genevieve County`.
    """
    county = county.removesuffix(" County").replace(".", "")
    if county.startswith("Ste "):
        county = "Sainte " + county.removeprefix("Ste ")
    return county.casefold()


REGION_BY_COUNTY: dict[str, int] = {
    normalize_county(county): region for region, counties in COUNTY_REGIONS.items() for county in counties
}


class MoChildCareSubsidy(ProgramCalculator):
    """
    Missouri Child Care Subsidy (5 CSR 25-200 and DESE's May 2026 Manual), the state's
    CCDF subsidy.

    Pays a contracted provider for the care of a child under 13 -- or under 18 with a
    special need -- in an Eligibility Unit whose Missouri adjusted gross income is at or
    under the lower of DESE's published chart maximum and 85% of State Median Income.

    A plain ``ProgramCalculator``: PolicyEngine models ``mo_ccs``, but Discovery kept
    this program custom and the estimate below is MFB's own.

    The value is an **MFB-owned estimate of the state's payment to the provider**, not
    a payment to the household: per eligible child, the Licensed Center Daytime rate for
    the household's county grouping and the child's age category, less the daily sliding
    fee, over 21 care days a month. The 21 days, the provider type, the Full day
    category and the school-age before-and-after-school pattern are all committed proxy
    assumptions -- Missouri sets each of them per authorization.

    Data gaps, inclusive by design: the qualifying-activity test (valid need) cannot
    screen a household out, because three of its eight pathways are wholly unobservable,
    so it is not implemented; and the $1,000,000 net-worth test cannot fail from the
    gross ``household_assets`` alone, because the screener collects no debts. The
    Protective Services route and the homelessness fee waiver are unobservable and
    never applied, in the narrowing direction.
    """

    program_code = "mo_ccs"

    # `household_assets` is deliberately absent: the net-worth test can never fail from
    # screener data, and declaring it would drop the program from results over a field
    # the calculator never screens on. `household_size` is absent because the
    # Eligibility Unit is counted from the member roster, which it never consults.
    # `county` is declared so a null county withholds the program rather than pricing
    # it at a guessed grouping.
    dependencies = ["age", "relationship", "county", "income_amount", "income_frequency"]

    BASE_AGE_LIMIT = 13
    SPECIAL_NEEDS_AGE_LIMIT = 18
    # Missouri's under-18 child-earnings exclusion. School attendance is imputed from
    # age alone, because `student` records post-secondary enrolment rather than K-12.
    CHILD_EARNINGS_AGE_LIMIT = 18

    PRESCHOOL_MIN_AGE = 2
    SCHOOL_AGE_MIN_AGE = 5

    CARE_DAYS_PER_MONTH = 21
    # Manual 7.9's five full-time school-year days, spread evenly over the eight months
    # September through April.
    SCHOOL_YEAR_FULL_DAYS_PER_MONTH = Decimal(5) / Decimal(8)
    SCHOOL_YEAR_MONTHS = (9, 10, 11, 12, 1, 2, 3, 4)

    # `relatedOther` is included because `relationship` is head-relative: when a
    # caregiver relative heads the household, it is the child who carries it.
    child_relationships = (
        "child",
        "stepChild",
        "fosterChild",
        "grandChild",
        "sisterOrBrother",
        "stepSisterOrBrother",
        "relatedOther",
    )

    def member_eligible(self, e: MemberEligibility):
        e.condition(self.is_eligible_child(e.member))

    def household_eligible(self, e: Eligibility):
        # Criterion 7. Criteria 5 (valid need) and 8 (net worth) have no condition here:
        # neither can screen a household out on the data the screener collects.
        income = self.adjusted_monthly_income()
        limit = self.income_limit()
        e.condition(income <= limit, messages.income(int(income), int(limit)))

    def is_eligible_child(self, member: HouseholdMember) -> bool:
        """Criteria 4 and 6. Also the set the value sums over, so the two cannot drift."""
        if member.relationship not in self.child_relationships:
            return False

        # Month-granular: the boundary falls on the first of the birth month.
        age = member.calc_age()
        if age is None:
            return False

        if age < self.BASE_AGE_LIMIT:
            return True

        # The special-needs extension runs to under 18, where `.050(11)` caps the
        # status itself. The 18-but-under-19 limbs need K-12 attendance or Protective
        # Services status, neither observable, so they are not asserted.
        return age < self.SPECIAL_NEEDS_AGE_LIMIT and self.has_special_needs(member)

    def eligible_children(self) -> list[HouseholdMember]:
        return [member for member in self.screen.household_members.all() if self.is_eligible_child(member)]

    def has_special_needs(self, member: HouseholdMember) -> bool:
        """
        The observable subset of `.050(11)`'s special-needs status: the child's own SSI
        receipt, or a self-reported disability or delay.

        SSI is read off the child's own income streams, never `has_benefit`, which is
        household-level and would confer status on every child in a household where
        anyone receives it.
        """
        return bool(member.has_disability()) or self.receives_ssi(member)

    @staticmethod
    def receives_ssi(member: HouseholdMember) -> bool:
        return any(stream.type == "sSI" for stream in member.income_streams.all())

    def unit_size(self) -> int:
        """
        The Eligibility Unit, counted from the member roster: everyone living in the
        household, with no `.050(17)` composition rule removing a member on the facts
        MFB can establish. Above the published range the size-20 row applies.
        """
        return min(max(self.screen.household_members.count(), 1), MAX_UNIT_SIZE)

    def counted_streams(self) -> list:
        """
        The Eligibility Unit's income streams after the two Missouri exclusions MFB can
        identify: SSI payments, and the earnings of a child under 18.

        `calc_gross_income` cannot express the second, which turns on the earner rather
        than the income type.
        """
        streams = []
        for member in self.screen.household_members.all():
            age = member.calc_age()
            excludes_earnings = age is not None and age < self.CHILD_EARNINGS_AGE_LIMIT
            for stream in member.income_streams.all():
                if stream.type == "sSI":
                    continue
                if excludes_earnings and stream.type in EARNED_INCOME_TYPES:
                    continue
                streams.append(stream)
        return streams

    def adjusted_monthly_income(self) -> Decimal:
        """
        Missouri adjusted gross monthly income, quantised to the cent: counted income
        less the reported `medical` expense.

        The whole `medical` amount is deducted, though Manual 5.7 allows only health
        coverage premiums and nursing care -- the screener's one field cannot tell them
        apart, and ignoring the deduction would overstate income.
        """
        income = sum((stream.monthly() for stream in self.counted_streams()), Decimal(0))

        # `Expense.missing_fields` does not require `frequency`, and `monthly()` raises
        # on a null one, so such an expense is skipped rather than failing the response.
        deduction = sum(
            (
                Decimal(expense.monthly())
                for expense in self.screen.expenses.all()
                if expense.type == "medical" and expense.frequency
            ),
            Decimal(0),
        )

        # Quantised for the same reason as `ks_ccap`: `_hour_to_month` multiplies by the
        # float-derived `Decimal(4.35)`, so an hourly figure lands a fraction of a cent
        # off every published bound.
        return (income - deduction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def income_limit(self) -> Decimal:
        size = self.unit_size()
        return min(Decimal(CHART_MAXIMUM[size]), SMI_85_PERCENT[size])

    def only_income_is_temporary_assistance(self) -> bool:
        """
        Manual 9.1's categorical limb of the `$1`-a-year fee. `cashAssistance` is the
        TANF-specific option, so the mapping is exact.

        Read over the counted streams, so an excluded SSI payment or child's earnings
        does not stop TANF from being the unit's only income.
        """
        streams = [stream for stream in self.counted_streams() if stream.amount]
        return bool(streams) and all(stream.type == "cashAssistance" for stream in streams)

    def pays_annual_fee(self) -> bool:
        """Fee precedence rule 2: `$1` a year, once per household."""
        if self.only_income_is_temporary_assistance():
            return True
        return self.adjusted_monthly_income() <= FEE_BAND_TOPS[self.unit_size()][0]

    def daily_fees(self) -> tuple[Decimal, Decimal]:
        """Fee precedence rule 3: the chart's (full unit, half unit) daily fee."""
        income = self.adjusted_monthly_income()
        daily_band_tops = FEE_BAND_TOPS[self.unit_size()][1:]
        for top, fees in zip(daily_band_tops, DAILY_FEES):
            if income <= top:
                return fees
        return DAILY_FEES[-1]

    def region(self) -> int:
        """
        DESE's geographic grouping, keyed on the household's county.

        Missouri keys the rate on the provider's location; MFB observes only the
        family's and uses it as a proxy.
        """
        return REGION_BY_COUNTY.get(normalize_county(self.screen.county), DEFAULT_REGION)

    def reference_date(self) -> date:
        return self.screen.get_reference_date()

    def age_category(self, member: HouseholdMember) -> str:
        """
        Infant (under 2), Preschool (2 through 4) or School age (5 and over). DESE's
        published endpoints overlap at 2 and at 5; both resolve upward, at 5 because
        `.050(37)` defines School Age as at least five.
        """
        age = member.calc_age()
        if age < self.PRESCHOOL_MIN_AGE:
            return INFANT
        if age < self.SCHOOL_AGE_MIN_AGE or self.held_at_preschool(member):
            return PRESCHOOL
        return SCHOOL_AGE

    def held_at_preschool(self, member: HouseholdMember) -> bool:
        """
        The school-year hold: a child not yet 5 before August 1 keeps the Preschool rate
        for that school year, August 1 through July 31.

        Read off `birth_year_month`, not `calc_age`, which is 5 on both sides of the
        July/August edge. Only a five-year-old can be held -- anyone 6 at the reference
        date was already 5 on the August 1 that opened their school year.
        """
        if member.calc_age() != self.SCHOOL_AGE_MIN_AGE:
            return False

        birth_year_month: Optional[date] = member.birth_year_month
        if birth_year_month is None:
            # Undeterminable, so applied: Preschool out-pays the school-age pattern in
            # every grouping.
            return True

        today = self.reference_date()
        school_year_start = today.year if today.month >= 8 else today.year - 1
        age_on_july_31 = HouseholdMember.age_from_date(birth_year_month, date(school_year_start, 7, 31))
        return age_on_july_31 < self.SCHOOL_AGE_MIN_AGE

    def in_school_year(self) -> bool:
        """MFB's committed September-through-April window for Manual 7.9."""
        return self.reference_date().month in self.SCHOOL_YEAR_MONTHS

    def child_monthly_value(self, member: HouseholdMember, full_fee: Decimal, half_fee: Decimal) -> Decimal:
        """
        One child's monthly payment. A school-age child in the school year is authorized
        before-and-after-school care, priced at the half-day rate for 21 days, plus five
        full-time days spread over the eight school-year months; everyone else draws the
        full-day rate for 21 days.

        The `max(0, ...)` clamps are unreachable under the published rates and fees.
        """
        region = self.region()
        category = self.age_category(member)
        full_rate = DAILY_RATES[region][category]

        if category == SCHOOL_AGE and self.in_school_year():
            half_rate = SCHOOL_AGE_HALF_DAY_RATES[region]
            return (
                max(half_rate - half_fee, Decimal(0)) * self.CARE_DAYS_PER_MONTH
                + max(full_rate - full_fee, Decimal(0)) * self.SCHOOL_YEAR_FULL_DAYS_PER_MONTH
            )

        return max(full_rate - full_fee, Decimal(0)) * self.CARE_DAYS_PER_MONTH

    def household_value(self) -> int:
        """
        The whole annual figure, returned here with no member values, because the
        `$1`-a-year fee is one household obligation and cannot be split across members.

        Fee precedence, in a fixed order: (1) a child with special needs pays no fee;
        otherwise (2) where the unit's only income is Temporary Assistance or its income
        is in the chart's `$1.00 per year` band, the household owes `$1` a year once;
        otherwise (3) each child in care pays the chart's daily fee.
        """
        waived = []
        charged = []
        for child in self.eligible_children():
            (waived if self.has_special_needs(child) else charged).append(child)

        monthly = sum((self.child_monthly_value(child, Decimal(0), Decimal(0)) for child in waived), Decimal(0))
        annual_fee = Decimal(0)

        if charged:
            if self.pays_annual_fee():
                full_fee, half_fee = Decimal(0), Decimal(0)
                annual_fee = Decimal(1)
            else:
                full_fee, half_fee = self.daily_fees()

            monthly += sum((self.child_monthly_value(child, full_fee, half_fee) for child in charged), Decimal(0))

        # Truncated here rather than left to `screener/views.py`, which truncates only
        # the payload's `estimated_value` -- the results card reads `household_value`
        # and rounds it on display. No visibility floor: an eligible household always
        # has a child, and no published fee reaches its rate.
        return int(monthly * 12 - annual_fee)
