from programs.programs.federal.pe.member import Wic
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
        # NOTE: that test's *reported*-enrollment branches, ``receives_snap`` / ``receives_tanf``, are
        # PE inputs nothing in our codebase populates. Today that is masked by the computed branch
        # firing anyway. Once income is supplied correctly, a household genuinely enrolled in SNAP or
        # TANF above 185% FPL is adjunct-eligible in real policy but would be denied here — so the
        # full fix has to send those inputs too, not just income (see the follow-up ticket).
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
