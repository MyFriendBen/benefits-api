from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages
from typing import ClassVar


class WaUdp(ProgramCalculator):
    """Seattle Utility Discount Program — discounts on Seattle City Light and Seattle Public
    Utilities bills for income-qualified households in the SCL/SPU service area.

    Eligibility requires Seattle residency (ZIP + King County proxy) AND one of three
    financial pathways: SSI categorical, SNAP streamlined, or adult household income ≤ 70%
    Washington State Median Income.

    Income test covers adult (18+) members only; minor income is exempted per DPP III-428 §5.6.2.
    The annual and monthly SMI tests collapse to one check at the screener level since the limits
    are exactly proportional and the screener captures ongoing income rates, not a 1-month snapshot.

    Data gaps: account ownership and meter sharing (mixed-load exclusion) cannot be verified at
    screening. Calculator assumes neither disqualifying condition applies (inclusivity assumption).
    """

    amount = 732  # average annual savings per seattle.gov/human-services UDP page

    # 2026 70% WA State Median Income annual limits — WA DSHS, effective January 1, 2026
    SMI_70_ANNUAL: ClassVar[dict[int, int]] = {
        1: 51_228,
        2: 66_984,
        3: 82_740,
        4: 98_508,
        5: 114_264,
        6: 130_032,
        7: 132_984,
        8: 135_936,
        9: 138_900,
        10: 141_852,
    }
    SMI_70_PER_EXTRA_ANNUAL = 2_964  # +$2,964/year per person above HH=10

    SEATTLE_ZIP_CODES: ClassVar[frozenset[str]] = frozenset(
        [
            "98101",
            "98102",
            "98103",
            "98104",
            "98105",
            "98106",
            "98107",
            "98108",
            "98109",
            "98111",
            "98112",
            "98113",
            "98114",
            "98115",
            "98116",
            "98117",
            "98118",
            "98119",
            "98121",
            "98122",
            "98124",
            "98125",
            "98126",
            "98127",
            "98129",
            "98131",
            "98133",
            "98134",
            "98136",
            "98138",
            "98139",
            "98141",
            "98144",
            "98145",
            "98146",
            "98154",
            "98160",
            "98161",
            "98164",
            "98165",
            "98170",
            "98174",
            "98175",
            "98177",
            "98178",
            "98181",
            "98185",
            "98190",
            "98191",
            "98194",
            "98195",
            "98199",
        ]
    )

    dependencies: ClassVar[list[str]] = [
        "income_amount",
        "income_frequency",
        "household_size",
        "zipcode",
        "county",
    ]

    def _smi_limit(self) -> int:
        size = self.screen.household_size
        if size in self.SMI_70_ANNUAL:
            return self.SMI_70_ANNUAL[size]
        return self.SMI_70_ANNUAL[10] + (size - 10) * self.SMI_70_PER_EXTRA_ANNUAL

    def _adult_income_yearly(self) -> float:
        return sum(
            member.calc_gross_income("yearly", ["all"])
            for member in self.screen.household_members.all()
            if member.calc_age() is not None and member.calc_age() >= 18
        )

    def _has_ssi_recipient(self) -> bool:
        return any(member.calc_gross_income("yearly", ["sSI"]) > 0 for member in self.screen.household_members.all())

    def household_eligible(self, e: Eligibility) -> None:
        # Criterion 1: Seattle SCL/SPU service area (ZIP + county proxy)
        in_seattle = self.screen.zipcode in self.SEATTLE_ZIP_CODES and self.screen.county == "King County"
        e.condition(in_seattle, messages.location())

        # Financial pathway: SSI categorical (Criterion 4) OR SNAP streamlined (Criterion 5)
        # OR standard income test (Criteria 2+3)
        if self._has_ssi_recipient() or self.screen.has_benefit("wa_snap"):
            e.condition(True, messages.presumed_eligibility())
        else:
            adult_income = self._adult_income_yearly()
            income_limit = self._smi_limit()
            e.condition(adult_income <= income_limit, messages.income(adult_income, income_limit))
