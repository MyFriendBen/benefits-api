from decimal import Decimal

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.white_labels.nj.anchor.calculator import NjAnchor
from programs.programs.white_labels.nj.income_tax import EXCLUDED_INCOME_TYPES, filers
from screener.models import HouseholdMember

# Stay NJ counts Social Security, which New Jersey gross income leaves out.
SOCIAL_SECURITY_TYPES = ("sSRetirement", "sSDisability", "sSSurvivor", "sSDependent")


class NjStayNj(ProgramCalculator):
    """
    Stay NJ: a New Jersey property tax credit for homeowners 65 or older, here the 2025 benefit
    paid in 2027. Rules and figures: program-ops `programs/white_labels/nj/staynj/nj_staynj_spec.md`.

    Eligible when the head or a spouse was 65 or older at the end of 2025, the household entered
    property tax, a mortgage, HOA fees or homeowners insurance and no rent, and the head's and
    spouse's 2025 income (NJ gross income plus Social Security) is 200,000 or less.

    Stay NJ pays what's left after ANCHOR and Senior Freeze: half the property tax, capped at
    6,500, less both. The FY2027 budget funds only two of the four quarterly payments and limits
    them by income tier, so the value is half the remainder, capped at the tier's payment limit.
    With no property tax entered, the county's average tax bill stands in, or the statewide
    average without a county. ANCHOR is the homeowner amount on ANCHOR's own income (no Social
    Security), whether or not the household passes ANCHOR's narrower ownership test. Senior
    Freeze is the county's average payment to recipients 65 or older, unless income is above
    the 2024 Senior Freeze limit.

    A household whose offsets use up half its tax gets 0, which hides the program: the PAS-1
    it would file is the one ANCHOR already shows it.

    Data gaps (spec §5): principal residence, full-year 2025 ownership, unit count, ownership
    itself, mobile homes, 2025 income, business and rental expenses, joint income shares,
    military disability pay, income losses, civil union partners entered as domestic partners,
    co-owners who aren't spouses, the 100% disabled-veteran exemption, and Social Security
    before Medicare Part B. Approximations (spec §7): the unindexed 6,500 cap, current tax and
    income for 2025's, county averages for the tax bill and Senior Freeze, ANCHOR under PILOT,
    ownership and unit shares, and the overall property tax relief ceiling.
    """

    program_code = "nj_staynj"

    # Ages and incomes are judged over 2025; the figures below are the FY2027 budget's for it.
    benefit_year = 2025
    min_age = 65

    income_limit = 200_000
    excluded_income_types = [t for t in EXCLUDED_INCOME_TYPES if t not in SOCIAL_SECURITY_TYPES]

    ownership_expenses = ["propertyTax", "mortgage", "hoa", "homeownersInsurance"]

    rate = Decimal("0.5")
    cap = 6_500
    funded_share = Decimal(2) / Decimal(4)

    # (income up to, payment limit on the two funded quarters)
    payment_limits = ((100_000, 3_250), (150_000, 2_500), (200_000, 2_000))

    senior_freeze_income_limit = 168_268

    # County: (2025 average residential property tax, average Senior Freeze payment 65+)
    county_averages: dict[str, tuple[int, int]] = {
        "Atlantic County": (7_301, 446),
        "Bergen County": (13_992, 988),
        "Burlington County": (8_179, 627),
        "Camden County": (7_734, 682),
        "Cape May County": (6_687, 456),
        "Cumberland County": (5_114, 479),
        "Essex County": (14_460, 1_161),
        "Gloucester County": (7_595, 579),
        "Hudson County": (10_610, 757),
        "Hunterdon County": (11_886, 810),
        "Mercer County": (10_058, 764),
        "Middlesex County": (9_623, 819),
        "Monmouth County": (11_830, 1_056),
        "Morris County": (12_259, 766),
        "Ocean County": (8_167, 688),
        "Passaic County": (11_670, 805),
        "Salem County": (6_842, 868),
        "Somerset County": (12_082, 866),
        "Sussex County": (9_052, 705),
        "Union County": (12_019, 858),
        "Warren County": (8_136, 682),
    }
    state_averages = (10_570, 779)

    dependencies = [
        "age",
        "relationship",
        "income_type",
        "income_amount",
        "income_frequency",
        "expense_type",
        "expense_amount",
        "expense_frequency",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        e.condition(any(self._is_senior(m) for m in filers(self.screen)), messages.older_than(self.min_age))
        e.condition(self._is_homeowner())

        income = self._income()
        e.condition(income <= self.income_limit, messages.income(income, self.income_limit))

    def household_value(self) -> int:
        tax = self._property_tax()
        half_tax = min(self.rate * tax, self.cap)
        remainder = max(Decimal(0), half_tax - self._anchor_amount(tax) - self._senior_freeze_amount())

        # Cents are dropped, as the API drops them from every value.
        return int(min(remainder * self.funded_share, self._payment_limit()))

    def _is_senior(self, member: HouseholdMember) -> bool:
        age = member.age_at_end_of_year(self.benefit_year)
        return age is not None and age >= self.min_age

    def _is_homeowner(self) -> bool:
        return (
            self.screen.calc_expenses("yearly", self.ownership_expenses) > 0
            and self.screen.calc_expenses("yearly", ["rent"]) == 0
        )

    def _income(self) -> float:
        return self._filer_income(self.excluded_income_types)

    def _anchor_income(self) -> float:
        return self._filer_income(NjAnchor.excluded_income_types)

    def _filer_income(self, excluded: list[str]) -> float:
        return sum(m.calc_gross_income("yearly", ["all"], exclude=excluded) for m in filers(self.screen))

    def _averages(self) -> tuple[int, int]:
        return self.county_averages.get(self.screen.county, self.state_averages)

    def _property_tax(self) -> Decimal:
        entered = self.screen.calc_expenses("yearly", ["propertyTax"])
        if entered > 0:
            return Decimal(str(entered))
        return Decimal(self._averages()[0])

    def _anchor_amount(self, tax: Decimal) -> Decimal:
        """The homeowner ANCHOR amount, computed as ANCHOR does, on the same property tax."""
        if self._anchor_income() <= NjAnchor.homeowner_cap_income:
            return min(tax, Decimal(NjAnchor.homeowner_cap_low))
        return min(tax, Decimal(NjAnchor.homeowner_cap_high))

    def _senior_freeze_amount(self) -> Decimal:
        if self._income() > self.senior_freeze_income_limit:
            return Decimal(0)
        return Decimal(self._averages()[1])

    def _payment_limit(self) -> int:
        income = self._income()
        for top, limit in self.payment_limits:
            if income <= top:
                return limit
        return 0
