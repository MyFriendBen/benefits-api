from programs.programs.federal.pe.member import (
    Wic,
    EarlyHeadStart,
)
import programs.programs.policyengine.calculators.dependencies as dependency
from screener.models import HouseholdMember


class MoWic(Wic):
    """
    Missouri WIC — federal ``Wic`` PE calculator + MO state code.

    Missouri has no WIC-specific rules of its own: income limits (185% FPL) and the
    categorical pathways (SNAP / Temporary Assistance / MO HealthNet) are federal, and
    PolicyEngine's WIC tree only branches on AK/HI vs. contiguous-US FPG tables. MO
    falls in the contiguous set, so the federal calculator applies as-is.

    Unlike CO/NC/MA — which override ``wic_categories`` with hardcoded per-category
    monthly amounts — this returns PolicyEngine's own computed benefit amount, the same
    approach ``TxWic`` takes. The federal base class's ``wic_categories`` are all zeros,
    so inheriting ``member_value`` unchanged would value every eligible member at $0 and
    the frontend's ``value > 0`` filter would drop the program from results entirely.
    """

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.MoStateCodeDependency,
        # PARTIAL income fix — makes wage-type income bind. See the gap note below.
        #
        # The federal ``Wic`` inputs carry only ``school_meal_countable_income``, the school-meals
        # variable. PolicyEngine's WIC tree never reads it: ``wic_countable_income`` sums its own
        # parameter list, ``gov.usda.wic.income.sources``. So with the federal inputs alone we
        # supply *none* of WIC's income sources and PE substitutes its own imputation — it computes
        # SSI/TANF for the household (both are in that sources list) and, seeing no earnings, also
        # satisfies the categorical test: ``meets_wic_categorical_eligibility`` fires when PE's own
        # *computed* snap/tanf benefit is > 0, or when it finds a member Medicaid-eligible
        # (``medicaid_enrolled`` reduces to ``is_medicaid_eligible`` — take-up defaults True). Per
        # ``is_wic_eligible``:
        #
        #     demographic_eligible & (meets_income_test | meets_categorical_test) & nutritional_risk
        #
        # the categorical (adjunct) branch then carries eligibility on its own, so WIC returns
        # eligible at any reported income — verified live at $108k/yr.
        #
        # Adjunct eligibility above 185% FPL is correct, not a bug: 42 USC 1786(d)(2)(A) makes
        # SNAP/TANF/Medicaid receipt its own pathway, and MO HealthNet for Pregnant Women reaches
        # 201% FPL (196% + 5% disregard, household includes the unborn child). Verified after this
        # fix: a pregnant applicant at ~190% FPL is still eligible via the Medicaid branch, and only
        # falls out at ~205% once both pathways fail. Expect the boundary at MO's Medicaid limit,
        # not at 185% — QA scenarios should assert that.
        #
        # NOTE: the categorical test's *reported*-enrollment inputs (``receives_snap`` /
        # ``receives_tanf``) are never populated by our code. That is a narrow gap, not a blocker:
        # PE computes snap/tanf/medicaid eligibility from the income we now send, so genuinely
        # eligible households still trip the branch. It only bites where PE's computed result
        # disagrees with reported enrollment (state rules PE doesn't model, or income risen since
        # enrollment). Tracked in the follow-up ticket.
        #
        # GAP: this bundle supplies only 5 of WIC's 24 income sources (employment, self-employment,
        # social_security, unemployment_compensation, rental); its other three fields
        # (taxable_pension_income, taxable_ira_distributions, long_term_capital_gains) are not in
        # WIC's list and are inert here — WIC wants pension_income and retirement_distributions.
        # Income the screener does collect but WIC still won't see includes veterans' benefits,
        # workers' comp, alimony, investment and pension income. Mapping those needs new dependency
        # classes, and the federal base class must be fixed for co/nc/ma/tx_wic, which changes
        # results for shipped programs. Both are tracked separately, not done here.
        *dependency.irs_gross_income,
    ]

    def member_value(self, member: HouseholdMember):
        """Return PolicyEngine's calculated WIC benefit for this member."""
        return self.get_member_variable(member.id)


class MoEarlyHeadStart(EarlyHeadStart):
    """Missouri Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + MO state code."""

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
