"""WIC."""

from screener.models import HouseholdMember
from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class Wic(PolicyEngineMembersCalculator):
    """
    Federal WIC. PolicyEngine decides it with::

        demographic_eligible & (meets_income_test | meets_categorical_test) & nutritional_risk

    The only income input here used to be ``school_meal_countable_income``, which WIC's
    tree never reads — ``wic_countable_income`` sums its own parameter list,
    ``gov.usda.wic.income.sources``. Supplying none of those sources let PE substitute an
    imputation, and because that imputation also satisfied the categorical branch, WIC came
    back eligible at any reported income (measured: eligible at $150k/yr). ``wic_income`` is
    that source list, as far as the screener collects it.

    ``financial_assistance`` carries the screener's ``cashAssistanceOther`` type (non-TANF cash
    aid). It is added to hold WIC harmless, not to fix an undercount: ``gov.usda.wic.income``
    lists both ``tanf`` and ``financial_assistance``, so before the cash-assistance split this
    money already counted here via the ``tanf`` input. Adding it keeps ``wic_countable_income``
    unchanged now that the money arrives in a different field — measured, the total is identical
    either way. The real WIC change in the split is narrower: adjunctive eligibility no longer
    triggers on non-TANF cash aid, because that is no longer read as TANF receipt.

    Adjunctive eligibility above 185% FPL is correct, not a bug: 42 U.S.C. § 1786(d)(2)(A)
    makes SNAP/TANF/Medicaid receipt its own pathway, and the 185% figure attaches only to
    the income-test pathway. The practical boundary is the state's Medicaid limit — in MO,
    ~201% FPL via MO HealthNet for Pregnant Women — so QA scenarios asserting a hard 185%
    cutoff will flag correct behavior as a bug.

    Nutritional risk has no screener field and defaults True in PE, so the third term is
    always satisfied.

    The base ``wic_categories`` are all zeros; state subclasses either override them with
    per-category amounts (CO/IL/MA/NC) or override ``member_value`` to return PE's own
    computed benefit (MO/TX).
    """

    program_code = "wic"

    wic_categories = {
        "NONE": 0,
        "INFANT": 0,
        "CHILD": 0,
        "PREGNANT": 0,
        "POSTPARTUM": 0,
        "BREASTFEEDING": 0,
    }
    pe_name = "wic"
    pe_inputs = [
        dependency.member.PregnancyDependency,
        dependency.member.ExpectedChildrenPregnancyDependency,
        dependency.member.AgeDependency,
        *dependency.wic_income,
        # WIC's adjunct test reads SNAP/TANF receipt.
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.member.Wic, dependency.member.WicCategory]

    def member_value(self, member: HouseholdMember):
        if self.get_member_variable(member.id) <= 0:
            return 0

        wic_category = self.get_member_dependency_value(dependency.member.WicCategory, member.id)
        return self.wic_categories[wic_category] * 12
