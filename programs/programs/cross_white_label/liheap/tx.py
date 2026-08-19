"""TxCeap."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class TxCeap(PolicyEngineSpmCalulator):
    """
    Texas Comprehensive Energy Assistance Program (CEAP) — the state's LIHEAP
    implementation. Helps low-income Texas households pay home heating and cooling
    costs. Households are eligible at or below 150% FPL, or categorically via
    TANF/SNAP/SSI receipt (42 U.S.C. § 8624(b)(2)(A)). The benefit is a tiered
    annual utility-assistance amount (1,800 / 1,500 / 1,200 by FPG bracket per
    10 TAC § 6.309(e)), capped by the household's reported energy expenses.
    """

    program_code = "tx_liheap"

    pe_name = "tx_ceap"
    pe_inputs = [
        dependency.household.TxStateCodeDependency,
        *dependency.irs_gross_income,
        # tx_ceap counts SSI via applicable_ssi, which follows the `ssi` input: the
        # household's reported amount where they report one, and PolicyEngine's own
        # simulated SSI otherwise. The take-up flag suppresses that simulated value for
        # anyone reporting no SSI, keeping a modelled benefit out of their FPG tier.
        *dependency.receipt_contract,
        # tx_ceap caps the payment at electricity_expense + gas_expense; route the
        # screener's energy expenses into electricity_expense so the cap is non-zero.
        dependency.spm.TxCeapEnergyExpenseDependency,
    ]
    pe_outputs = [dependency.spm.TxCeap]
