"""KS Early Head Start."""

from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
import programs.framework.pe_dependencies as dependency


class KsEarlyHeadStart(EarlyHeadStart):
    """
    Kansas Early Head Start (birth to age 3, and pregnant women). Thin wrapper on
    the federal ``EarlyHeadStart`` PE calculator that adds the KS state code; all
    eligibility and the per-individual value are computed by PolicyEngine's
    ``early_head_start`` variable with no KS-specific variance. Head Start (ages
    3-5) is a separate program (``KsHeadStart``).
    """

    program_code = "ks_early_head_start"

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
