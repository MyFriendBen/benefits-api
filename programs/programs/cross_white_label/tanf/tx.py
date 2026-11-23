"""TX TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class TxTanf(Tanf):
    """
    Texas Temporary Assistance for Needy Families (TANF) calculator.

    Uses PolicyEngine-calculated benefit amounts for TX-specific TANF eligibility
    and benefit values. Inherits from federal TANF calculator and adds TX state
    code dependency and person-level income inputs.

    Income is provided at the person level (via irs_gross_income) so PolicyEngine
    can compute tx_tanf_countable_earned_income correctly — applying the $120 work
    expense deduction and 1/3 earned income disregard per § 372.409. Passing gross
    income directly as tx_tanf_countable_earned_income (the previous approach) bypassed
    these deductions and caused households with gross wages between ~$188-$402/month
    to be incorrectly denied for a family of 3 with 1 parent.
    """

    program_code = "tx_tanf"

    pe_name = "tx_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.TxStateCodeDependency,
        dependency.member.TaxUnitDependentDependency,
        *dependency.irs_gross_income,
        # Non-TANF cash aid is not in the taxable set, so irs_gross_income alone drops it
        # from every gate. Sent here for when PolicyEngine reads it, but inert today:
        # unlike the federal list, TX's own `gov.states.tx.tanf.income.sources.unearned`
        # omits `financial_assistance`, so `tx_tanf_countable_unearned_income` stays 0 and
        # the grant is still overstated by the reported amount. Supplying TX's unearned
        # total ourselves would fix that at the cost of counting `sSI`, `veteran`, `rental`
        # and `boarder` income that TX deliberately excludes, so the fix belongs upstream.
        dependency.member.NonTanfCashAssistanceIncomeDependency,
    ]

    pe_outputs = [dependency.spm.TxTanf]
