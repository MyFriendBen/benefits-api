from screener.models import HouseholdMember
from .base import SpmUnit
from .receipt import TANF_INCOME_TYPE, screen_reports_snap, screen_reports_tanf, member_reports_ssi_amount, screen_reports_ssi_without_amount


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
    PolicyEngine's ``takes_up_snap_if_eligible`` spm_unit input, default True. False stops
    PolicyEngine counting the SNAP it simulates for the household as income they receive, and
    withdraws the categorical eligibility SNAP receipt confers (Head Start / Early Head Start,
    WIC's adjunct test).

    Lowered for a household that does not report receiving SNAP. The tile is the only signal,
    so an unticked one reads as "not receiving" — unlike SSI and TANF, where a reported amount
    can stand in for it.

    The gate is the release where this field started applying through the API, not the one that
    introduced it.
    """

    field = "takes_up_snap_if_eligible"
    min_pe_version = (1, 779, 3)

    def value(self):
        return screen_reports_snap(self.screen)


class ReceivesSnapDependency(SpmUnit):
    """
    PolicyEngine's ``receives_snap`` spm_unit input: the household is a reported SNAP recipient.

    Confers SNAP-based categorical eligibility on other programs even where PolicyEngine
    computes the household's own SNAP as $0 — the case a computed amount cannot express.
    spm_unit-scoped, matching the household scope of the tile it reads, so unlike SSI it needs
    no attribution to a member.
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
    PolicyEngine's ``snap_if_takes_up`` spm_unit output: the SNAP the household would get if it
    took the program up, regardless of reported take-up.

    What the SNAP program reads, since the plain ``snap`` output is gated on
    ``takes_up_snap_if_eligible`` and so reads 0 for exactly the non-recipients the program
    should be recommended to.
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
    The household's reported TANF amount, as PolicyEngine's ``tanf`` input; None when none is
    reported, leaving PolicyEngine to compute it.

    A positive value drives SNAP / Head Start / WIC categorical eligibility and gives the
    consumers that read the amount (spm_unit_benefits, tx_ceap_countable_income, HUD income)
    the real figure. The amount is itself the receipt signal, so this does not require the tile.
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
    PolicyEngine's ``tanf_if_takes_up`` spm_unit output: the TANF the household would get if it
    took the program up, summed across the state programs, regardless of reported take-up.

    What the TANF program reads, since the plain ``tanf`` output is gated on
    ``takes_up_tanf_if_eligible`` and so reads 0 for exactly the non-recipients the program
    should be recommended to.
    """

    field = "tanf_if_takes_up"
    min_pe_version = (1, 779, 3)


class ReceivesTanfDependency(SpmUnit):
    """
    PolicyEngine's ``receives_tanf`` spm_unit input: the household is a reported TANF recipient.

    Confers the categorical eligibility TANF carries (SNAP, Head Start, WIC's adjunct test) even
    where PolicyEngine computes the household's own TANF as $0 — the case a reported amount
    cannot express. spm_unit-scoped, matching the household scope of the signals it reads, so
    unlike SSI it needs no attribution to a member.

    ``is_tanf_enrolled`` defaults to this, so it need not be sent separately.
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
    PolicyEngine's ``takes_up_tanf_if_eligible`` spm_unit input, default True. False stops
    PolicyEngine counting the TANF it simulates for the household as income they receive, and
    withdraws the categorical eligibility that receipt confers.

    Lowered for a household reporting no TANF by either signal — the tile or a cash-assistance
    amount.
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


class MoTanf(SpmUnit):
    field = "mo_tanf"


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


class CashAssetsExcludingSsiHouseholdsDependency(CashAssetsDependency):
    """
    The household's liquid assets, or nothing when a member's resources are excluded from
    the program's resource test.

    Programs that exclude an SSI recipient's resources (TANF, per 13 CSR 40-2.310(1)(F) and
    the equivalent state rules) need to know which share of the household's assets belongs
    to that member. ``Screen.household_assets`` is a single figure with no ownership
    breakdown, so that share is unknowable — and attributing it per person only invents the
    answer. Reporting no countable figure says what is true: for this household we cannot
    establish countable resources, so the test should not be the thing that denies them.

    That is the treatment the specs commit to — do not deny on the aggregate alone when a
    member's resources are excluded — and it is deliberately inclusive: a household with an
    excluded member passes the resource test whatever the reported total. Counting the
    remaining members' assets exactly needs an input PolicyEngine does not offer (MFB-1696).

    Receipt is read from both signals the screener carries, since either establishes that
    somebody's resources are excluded even when neither identifies whose: a per-member SSI
    amount, or the household-level SSI tile with no amount attached.
    """

    dependencies = (
        "household_assets",
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        if screen_reports_ssi_without_amount(self.screen):
            return 0

        if any(member_reports_ssi_amount(m) for m in self.screen.household_members.all()):
            return 0

        return super().value()


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
