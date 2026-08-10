from screener.models import HouseholdMember
from .base import SpmUnit
from .receipt import TANF_INCOME_TYPE, screen_reports_snap, screen_reports_tanf


class ChildCareDependency(SpmUnit):
    field = "childcare_expenses"

    def value(self):
        return self.screen.calc_expenses("yearly", ["childCare"])


class SnapEarnedIncomeDependency(SpmUnit):
    field = "snap_earned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return self.screen.calc_gross_income("yearly", ["earned"])


class SnapUnearnedIncomeDependency(SpmUnit):
    field = "snap_unearned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return self.screen.calc_gross_income("yearly", ["unearned"])


class HousingCostDependency(SpmUnit):
    field = "housing_cost"

    def value(self):
        return int(self.screen.calc_expenses("yearly", ["rent", "mortgage", "subsidizedRent"]))


class SnapAssetsDependency(SpmUnit):
    field = "snap_assets"

    def value(self):
        assets = self.screen.household_assets or 0
        return int(assets)


class SnapGrossIncomeDependency(SpmUnit):
    field = "snap_gross_income"
    dependencies = (
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.screen.calc_gross_income("yearly", ["all"]))


class TakesUpSnapIfEligibleDependency(SpmUnit):
    """
    False for a household that does not report receiving SNAP, which zeroes PolicyEngine's
    simulated SNAP and switches off the categorical eligibility SNAP receipt confers
    (Head Start / Early Head Start, WIC's adjunct test).

    The Current Benefits tile is the only signal — the screener captures no SNAP amount —
    so an unticked tile is read as "not receiving" here, unlike SSI and TANF where a
    reported dollar amount can also stand in for the tile.

    ``takes_up_snap_if_eligible`` predates 1.779.3 but was ignored outside microsimulation
    until then; the gate is set to the release where it started applying through the API.
    """

    field = "takes_up_snap_if_eligible"
    min_pe_version = (1, 779, 3)

    def value(self):
        return screen_reports_snap(self.screen)


class ReceivesSnapDependency(SpmUnit):
    """
    Reported SNAP receipt, the signal that confers SNAP-based categorical eligibility on
    other programs. Separate from the take-up flag: this stays True even where PE computes
    the household's own SNAP entitlement as $0, which is the case a computed amount cannot
    express.
    """

    field = "receives_snap"
    min_pe_version = (1, 779, 3)

    def value(self):
        return screen_reports_snap(self.screen)


class HasHeatingCoolingExpenseDependency(SpmUnit):
    field = "has_heating_cooling_expense"

    def value(self):
        return self.screen.has_expense(["heating", "cooling"])


class HasPhoneExpenseDependency(SpmUnit):
    field = "has_phone_expense"

    def value(self):
        return self.screen.has_expense(["telephone"])


class UtilityExpenseDependency(SpmUnit):
    field = "utility_expense"

    def value(self):
        return int(self.screen.calc_expenses("yearly", ["otherUtilities", "heating", "cooling"]))


class HeatingCoolingExpenseDependency(SpmUnit):
    field = "heating_cooling_expense"

    def value(self):
        return self.screen.calc_expenses("yearly", ["heating", "cooling"])


class PhoneExpenseDependency(SpmUnit):
    field = "phone_expense"

    def value(self):
        return self.screen.calc_expenses("yearly", ["telephone"])


class PhoneCostDependency(SpmUnit):
    # PE's Lifeline formula reads phone_cost (distinct from phone_expense, which SNAP
    # uses for a yes/no utility check) to release the KS Lifeline state supplement:
    # min_(phone_cost, ks_supplement * MONTHS_IN_YEAR). Same underlying screener data
    # as PhoneExpenseDependency, just mapped to the field PE's Lifeline branch expects.
    # Without it PE treats phone_cost as $0 and the KS supplement always computes to $0.
    field = "phone_cost"

    def value(self):
        return self.screen.calc_expenses("yearly", ["telephone"])


class ElectricityExpenseDependency(SpmUnit):
    field = "electricity_expense"

    def value(self):
        return self.screen.calc_expenses("yearly", ["otherUtilities"])


class WaterExpenseDependency(SpmUnit):
    field = "water_expense"

    def value(self):
        return self.screen.calc_expenses("yearly", ["otherUtilities"])


class HoaFeesExpenseDependency(SpmUnit):
    field = "homeowners_association_fees"

    def value(self):
        return self.screen.calc_expenses("yearly", ["hoa"])


class HomeownersInsuranceExpenseDependency(SpmUnit):
    field = "homeowners_insurance"

    def value(self):
        return self.screen.calc_expenses("yearly", ["homeownersInsurance"])


class SnapEmergencyAllotmentDependency(SpmUnit):
    field = "snap_emergency_allotment"

    def value(self):
        return 0


class SnapIfTakesUp(SpmUnit):
    """
    PolicyEngine's would-be SNAP entitlement, independent of take-up. The SNAP program
    reads this rather than ``snap``, which ``takes_up_snap_if_eligible: False`` zeroes for
    every household that doesn't already receive it — precisely the households the
    program should be shown to.

    This replaced a ``snap: 1`` receipt sentinel. The sentinel pinned PE's computed SNAP
    to $1/mo for anyone who reported receiving it, polluting the income other programs
    read; ``ReceivesSnapDependency`` carries the same signal without touching the amount.
    """

    field = "snap_if_takes_up"
    min_pe_version = (1, 779, 3)


class Acp(SpmUnit):
    field = "acp"


class SchoolMealDailySubsidy(SpmUnit):
    field = "school_meal_daily_subsidy"


class SchoolMealNetSubsidy(SpmUnit):
    # Annual free/reduced-price school meal value: PolicyEngine multiplies the
    # per-child-per-day net subsidy (daily subsidy minus the full-price baseline)
    # by the number of K-12 children and the number of school days in the year.
    # PAID-tier households net to $0.
    field = "school_meal_net_subsidy"


class SchoolMealTier(SpmUnit):
    field = "school_meal_tier"


class Lifeline(SpmUnit):
    field = "lifeline"


class Tanf(SpmUnit):
    """
    The household's reported TANF amount, as PolicyEngine's ``tanf`` input.

    A positive ``tanf`` drives SNAP / Head Start / WIC categorical eligibility, and
    consumers that read the amount (spm_unit_benefits, tx_ceap_countable_income, HUD
    income) get the real figure. Otherwise None, so PE computes the benefit — whether that
    computed amount is then used depends on ``TakesUpTanfIfEligibleDependency``.

    The reported cash-assistance amount is the receipt signal on its own; a household that
    enters an amount without ticking the Current Benefits tile is still telling us they
    receive TANF, so this no longer requires the tile.
    """

    field = "tanf"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        reported_amount = self.screen.calc_gross_income("yearly", [TANF_INCOME_TYPE])
        return reported_amount if reported_amount > 0 else None


class TanfIfTakesUp(SpmUnit):
    """
    PolicyEngine's would-be TANF entitlement, independent of take-up — what the TANF
    program reads instead of the receipt-gated ``tanf``.

    Caveat: pinning a reported ``tanf`` amount drives this to 0, so it is a would-be read
    for non-recipients only. That is who the program is shown to — recipients are filtered
    out of results by ``already_has`` — but it means the two are not interchangeable.
    """

    field = "tanf_if_takes_up"
    min_pe_version = (1, 779, 3)


class ReceivesTanfDependency(SpmUnit):
    """
    Reported TANF receipt. Confers the categorical eligibility TANF carries (SNAP, Head
    Start, WIC's adjunct test) even where PE computes the household's own TANF as $0.

    PolicyEngine's ``is_tanf_enrolled`` defaults to this, so one boolean drives both
    cross-program categorical eligibility and TANF's own applicant-vs-recipient rules;
    there is no need to send ``is_tanf_enrolled`` separately.
    """

    field = "receives_tanf"
    min_pe_version = (1, 779, 3)
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return screen_reports_tanf(self.screen)


class TakesUpTanfIfEligibleDependency(SpmUnit):
    """
    False for a household that reports no TANF — neither the tile nor a cash-assistance
    income stream — so PE's simulated TANF stops counting as income and stops conferring
    categorical eligibility on other programs.
    """

    field = "takes_up_tanf_if_eligible"
    min_pe_version = (1, 779, 3)
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return screen_reports_tanf(self.screen)


class CoTanf(SpmUnit):
    field = "co_tanf"


class NcTanf(SpmUnit):
    field = "nc_tanf"


class IlTanf(SpmUnit):
    field = "il_tanf"


class MaTafdc(SpmUnit):
    field = "ma_tafdc"


class CoTanfCountableGrossIncomeDependency(SpmUnit):
    field = "co_tanf_countable_gross_earned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.screen.calc_gross_income("yearly", ["earned"]))


class CoTanfCountableGrossUnearnedIncomeDependency(SpmUnit):
    field = "co_tanf_countable_gross_unearned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.screen.calc_gross_income("yearly", ["unearned"], exclude=["cashAssistance"]))


class NcTanfCountableEarnedIncomeDependency(SpmUnit):
    field = "nc_tanf_countable_earned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.screen.calc_gross_income("yearly", ["earned"]))


class NcTanfCountableGrossUnearnedIncomeDependency(SpmUnit):
    field = "nc_tanf_countable_gross_unearned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(
            self.screen.calc_gross_income(
                "yearly", ["unearned"], exclude=["sSI", "gifts", "cashAssistance", "cOSDisability"]
            )
        )


class IlTanfCountableEarnedIncomeDependency(SpmUnit):
    field = "il_tanf_countable_gross_earned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.screen.calc_gross_income("yearly", ["earned"]))


class IlTanfCountableGrossUnearnedIncomeDependency(SpmUnit):
    field = "il_tanf_countable_unearned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.screen.calc_gross_income("yearly", ["unearned"], exclude=["cashAssistance"]))


class TxTanf(SpmUnit):
    field = "tx_tanf"


class KsTanf(SpmUnit):
    field = "ks_tanf"


class PreSubsidyChildcareExpensesDependency(SpmUnit):
    field = "spm_unit_pre_subsidy_childcare_expenses"

    def value(self):
        return self.screen.calc_expenses("yearly", ["childCare", "dependentCare"])


class NcScca(SpmUnit):
    field = "nc_scca_maximum_payment"


class NcSccaCountableIncomeDependency(SpmUnit):
    field = "nc_scca_countable_income"
    income_types = [
        "wages",
        "selfEmployment",
        "pension",
        "veteran",
        "unemployment",
        "sSDisability",
        "workersComp",
        "sSRetirement",
        "deferredComp",
        "rental",
        "childSupport",
        "alimony",
        "investment",
        "sSSurvivor",
        "sSDependent",
        "boarder",
    ]

    def value(self):
        return self.screen.calc_gross_income("yearly", self.income_types)


class BroadbandCostDependency(SpmUnit):
    # PE's Lifeline benefit is capped at the household's phone + broadband spend
    # (min_(phone_cost + broadband_cost, max_amount)). A blank internet expense means
    # "not reported," not "$0 spent" — sending 0 would let PE cap the benefit to $0 and,
    # via MFB's value>0 rule, hide an eligible household. So: send the reported internet
    # cost when we have one (PE legitimately caps the discount at actual spend), otherwise
    # fall back to a value above the benefit ceiling so an eligible household still sees
    # the full benefit they'd receive once enrolled in service. NO_DATA_FALLBACK keeps the
    # prior hardcoded behavior for the no-data case (strict improvement: no regression when
    # the field is blank, real data used when it's present).
    field = "broadband_cost"
    NO_DATA_FALLBACK = 500

    def value(self):
        if self.screen.has_expense(["internet"]):
            return int(self.screen.calc_expenses("yearly", ["internet"]))
        return self.NO_DATA_FALLBACK


class SchoolMealCountableIncomeDependency(SpmUnit):
    """
    Feeds PE's ``school_meal_countable_income``, which only ``school_meal_fpg_ratio``
    reads. Our Wic and CommoditySupplementalFoodProgram classes also send this field,
    but PE's WIC and CSFP trees never read it, so changes here move school meals alone.

    The tier still honors ``meets_school_meal_categorical_eligibility``, so households
    categorically eligible through SNAP/TANF keep free meals regardless of this total.
    """

    field = "school_meal_countable_income"
    income_types = [
        "wages",
        "selfEmployment",
        "rental",
        "pension",
        "veteran",
        "sSDisability",
        "sSSurvivor",
        "sSRetirement",
        "sSDependent",
        # Counts on the application-income path. Only offered on the CO white label,
        # so it contributes nothing to the other states that inherit this list.
        "nurturingFutures",
    ]

    def value(self):
        return self.screen.calc_gross_income("yearly", self.income_types)


class AssetsDependency(SpmUnit):
    field = "spm_unit_assets"

    def value(self):
        assets = self.screen.household_assets or 0
        return int(assets)


class MaEaedc(SpmUnit):
    field = "ma_eaedc"


# NOTE: PE has an open issue to calculate this: https://github.com/PolicyEngine/policyengine-us/issues/5768
class MaEaedcLivingArangementDependency(SpmUnit):
    field = "ma_eaedc_living_arrangement"

    def value(self):
        return "A"


class MaEaedcNonFinancialCriteria(SpmUnit):
    field = "ma_eaedc_non_financial_eligible"

    elderly_min_age = 65
    caretaker_min_age = 18
    disabled_dependent_income_limit = 1_500 * 12
    dependent_max_age = 18

    # NOTE: copying logic from PE minus the not SSI eligible requirement
    # https://github.com/PolicyEngine/policyengine-us/blob/master/policyengine_us/variables/gov/states/ma/dta/tcap/eaedc/eligibility/non_financial/ma_eaedc_non_financial_eligible.py
    def value(self):
        for member in self.members.all():
            if any(
                [
                    self._elderly(member),
                    self._disabled_head_or_spouse(member),
                    self._disabled_dependent(member),
                    self._caretaker_family(member),
                ]
            ):
                return True

        return False

    def _elderly(self, member: HouseholdMember) -> bool:
        if not (member.is_head() or member.is_spouse()):
            return False

        if not member.age >= self.elderly_min_age:
            return False

        return True

    def _disabled_head_or_spouse(self, member: HouseholdMember) -> bool:
        if not (member.is_head() or member.is_spouse()):
            return False

        if not (member.disabled or member.long_term_disability):
            return False

        return True

    def _disabled_dependent(self, member: HouseholdMember) -> bool:
        if not member.is_dependent():
            return False

        if not (member.disabled or member.long_term_disability):
            return False

        # meets TCAP income eligibility
        earned_income = member.calc_gross_income("yearly", ["earned"])
        if not earned_income <= self.disabled_dependent_income_limit:
            return False

        return True

    def _caretaker_family(self, member: HouseholdMember) -> bool:
        if not (member.is_head() or member.is_spouse()):
            return False

        if not member.age >= self.caretaker_min_age:
            return False

        for other_member in self.members.all():
            if (
                other_member.is_dependent()
                and other_member.age < self.dependent_max_age
                and other_member.relationship == "fosterChild"
            ):
                return True

        return False


class MaEaedc(SpmUnit):
    field = "ma_eaedc"


class CashAssetsDependency(SpmUnit):
    field = "spm_unit_cash_assets"

    def value(self):
        assets = self.screen.household_assets or 0
        return int(assets)


class IlLiheapIncomeEligible(SpmUnit):
    field = "il_liheap_income_eligible"


class IlLiheap(SpmUnit):
    field = "il_liheap"


class MaLiheap(SpmUnit):
    field = "ma_liheap"


class MaLiheapReceivesHousingAssistance(SpmUnit):
    field = "receives_housing_assistance"

    # Fixed to True: produces a conservative benefit estimate (subsidized payment
    # table has lower amounts than non-subsidized) and keeps the household eligible
    # via the (is_subsidized & ~heat_in_rent) branch of ma_liheap_eligible_subsidized_housing.
    def value(self):
        return True


class MaLiheapHeatExpenseIncludedInRent(SpmUnit):
    field = "heat_expense_included_in_rent"

    # Fixed to False: required for MA LIHEAP calculation; False produces conservative benefit estimate
    def value(self):
        return False


class MortgageDependency(SpmUnit):
    field = "mortgage_payments"

    def value(self):
        return int(self.screen.calc_expenses("yearly", ["mortgage"]))


class TxCeap(SpmUnit):
    field = "tx_ceap"


class TxCeapEnergyExpenseDependency(SpmUnit):
    """
    PolicyEngine's tx_ceap caps the benefit at electricity_expense + gas_expense.
    Our screener captures home energy as heating/cooling/otherUtilities expenses,
    so we route their total into electricity_expense (PE's gas_expense is left at
    its 0 default) to reflect the household's reported energy burden in the cap.
    """

    field = "electricity_expense"

    def value(self):
        return self.screen.calc_expenses("yearly", ["heating", "cooling", "otherUtilities"])


class TxCcs(SpmUnit):
    field = "tx_ccs"


class WaTanf(SpmUnit):
    field = "wa_tanf"


class WaShowAllCashAssistanceProgramsDependency(SpmUnit):
    field = "wa_show_all_cash_assistance_programs"

    def value(self):
        return True
