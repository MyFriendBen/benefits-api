import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaSeniorDisabledPte(ProgramCalculator):
    """
    Washington Property Tax Exemption for Seniors and People with Disabilities.

    Reduces property taxes for qualifying homeowners who are age 61+, retired from
    regular gainful employment due to disability, or are disabled veterans. Income
    eligibility is county-specific per the WA DOR 2024-2026 income threshold table
    (RCW 84.36.381, WAC 458-16A-130).

    Benefit value is estimated using the household's reported annual property tax
    expense as a proxy — exact savings depend on county levies, assessed value, and
    tier, which the screener cannot determine.

    Data gaps (inclusivity assumptions applied per spec.md):
      - Homeownership / principal-residence occupancy: not collected; assumed met.
      - Disability-retirement pathway: long_term_disability used as proxy for
        "retired from regular gainful employment because of disability."
      - Disabled-veteran pathway: veteran + disability indicator used as proxy for
        VA service-connected disability rating of 40%+ or total disability rating.
      - Surviving spouse/domestic partner continuation: no screener field; omitted.
      - Cotenant income: household gross income used as conservative approximation.
    """

    # 2024-2026 WA DOR county income thresholds: (Threshold 1, Threshold 2, Threshold 3)
    # Eligibility requires income <= Threshold 3; tier affects benefit level.
    # Source: WA DOR Income Thresholds for Tax Years 2024-2026
    COUNTY_THRESHOLDS: dict[str, tuple[int, int, int]] = {
        "Adams County": (30_000, 35_000, 40_000),
        "Asotin County": (30_000, 35_000, 40_000),
        "Benton County": (35_000, 41_000, 48_000),
        "Chelan County": (35_000, 41_000, 48_000),
        "Clallam County": (30_000, 35_000, 40_000),
        "Clark County": (40_000, 48_000, 55_000),
        "Columbia County": (30_000, 35_000, 40_000),
        "Cowlitz County": (30_000, 35_000, 40_000),
        "Douglas County": (35_000, 41_000, 48_000),
        "Ferry County": (30_000, 35_000, 40_000),
        "Franklin County": (35_000, 41_000, 48_000),
        "Garfield County": (30_000, 35_000, 40_000),
        "Grant County": (30_000, 35_000, 40_000),
        "Grays Harbor County": (30_000, 35_000, 40_000),
        "Island County": (35_000, 41_000, 48_000),
        "Jefferson County": (35_000, 41_000, 48_000),
        "King County": (60_000, 72_000, 84_000),
        "Kitsap County": (40_000, 48_000, 55_000),
        "Kittitas County": (30_000, 35_000, 40_000),
        "Klickitat County": (30_000, 35_000, 40_000),
        "Lewis County": (30_000, 35_000, 40_000),
        "Lincoln County": (30_000, 35_000, 40_000),
        "Mason County": (30_000, 35_000, 40_000),
        "Okanogan County": (30_000, 35_000, 40_000),
        "Pacific County": (30_000, 35_000, 40_000),
        "Pend Oreille County": (30_000, 35_000, 40_000),
        "Pierce County": (45_000, 53_000, 62_000),
        "San Juan County": (40_000, 48_000, 55_000),
        "Skagit County": (35_000, 41_000, 48_000),
        "Skamania County": (30_000, 35_000, 40_000),
        "Snohomish County": (55_000, 65_000, 75_000),
        "Spokane County": (36_000, 43_000, 50_000),
        "Stevens County": (30_000, 35_000, 40_000),
        "Thurston County": (40_000, 48_000, 55_000),
        "Wahkiakum County": (30_000, 35_000, 40_000),
        "Walla Walla County": (30_000, 35_000, 40_000),
        "Whatcom County": (40_000, 48_000, 55_000),
        "Whitman County": (30_000, 35_000, 40_000),
        "Yakima County": (30_000, 35_000, 40_000),
    }

    # Fallback for counties not in the table (uses the minimum tier-3 threshold)
    default_threshold_3 = 40_000

    min_age = 61  # must be 61 or older by December 31 of the claim year (RCW 84.36.381(3)(a))

    dependencies = [
        "age",
        "income_amount",
        "income_frequency",
        "county",
    ]

    def _income_threshold_3(self) -> int:
        thresholds = self.COUNTY_THRESHOLDS.get(self.screen.county)
        if thresholds is None:
            return self.default_threshold_3
        return thresholds[2]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age pathway: 61+ by December 31 of claim year (RCW 84.36.381(3)(a))
        age_eligible = member.age is not None and member.age >= self.min_age

        # Disability-retirement pathway: long_term_disability as inclusivity proxy for
        # "retired from regular gainful employment because of disability" (RCW 84.36.381(3)(b))
        disability_eligible = bool(member.long_term_disability)

        # Disabled-veteran pathway: veteran + disability indicator as inclusivity proxy for
        # VA service-connected disability rating >=40% or total disability (RCW 84.36.381(3)(c))
        veteran_eligible = bool(member.veteran) and (bool(member.long_term_disability) or bool(member.disabled))

        e.condition(age_eligible or disability_eligible or veteran_eligible)

    def household_eligible(self, e: Eligibility):
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = self._income_threshold_3()
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def household_value(self) -> int:
        """Proxy for estimated annual savings using reported property tax expense."""
        return int(self.screen.calc_expenses("yearly", ["propertyTax"]))

    def member_value(self, member) -> int:
        return 0
