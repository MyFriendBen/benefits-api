# STATE_MEDICAID_OPTIONS is spliced into `screener.views.CALC_ORDER`, so a state's
# Medicaid program resolves before the programs that gate on it, and it is the set of
# member-level auto-eligible benefits for CO's lwcr.
#
# A state's Medicaid program must be listed here or the calculation order reserves it no
# slot, and the programs gating on it raise DependencyError instead of being calculated.
# The gate itself is per-calculator: see `ProgramCalculator.medicaid_eligible`, which
# names the program it depends on.
STATE_MEDICAID_OPTIONS = ("co_medicaid", "nc_medicaid", "il_medicaid", "ks_medicaid")
