"""Lifeline."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class Lifeline(PolicyEngineSpmCalulator):
    program_code = "lifeline"
    pe_name = "lifeline"
    pe_inputs = [
        dependency.spm.BroadbandCostDependency,
        # phone_cost gates PE's state Lifeline supplements (e.g. KS: the supplement is
        # released only up to phone_cost). Sent for all states that inherit Lifeline so
        # a phone-service supplement is never silently zeroed out; states without such a
        # supplement (TX, WA) are unaffected since their value doesn't depend on it.
        dependency.spm.PhoneCostDependency,
        *dependency.irs_gross_income,
        # Categorically eligible off SNAP / TANF / SSI receipt.
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.spm.Lifeline]
