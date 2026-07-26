from typing import Any, Optional
from .engines import Sim


class PolicyEngineClient:
    """
    Thin wrapper around an already-constructed Sim, per RFC 0003
    (rfcs/0003-program-calc-refactor/README.md). Does not construct or own
    a Sim -- wrapping an existing instance never triggers a second PE API
    call, since Sim.__init__ is the only place that call happens.

    Only get_spm_value casts to int: SPM-level PE values in this codebase
    are always currency (see DECISIONS.md D-009). get_member_value and
    get_household_value return the raw value uncast, since their real
    analogs (get_member_variable, get_member_dependency_value) are used for
    non-numeric values too (e.g. medicaid_category/chip_category strings
    used as dict keys) -- casting those would break on a value that was
    never meant to be numeric. get_spm_value also takes an optional period
    override (see DECISIONS.md D-013) -- SNAP's real value is monthly, not
    at self.period's annual period, so SnapCalculator needs to read at a
    different period than every other pure-pass-through program.
    """

    def __init__(self, sim: Sim, period: str):
        self.sim = sim
        self.period = period

    def get_member_value(self, member_id: int, variable: str) -> Any:
        return self.sim.value("people", str(member_id), variable, self.period)

    def get_spm_value(self, variable: str, period: Optional[str] = None) -> int:
        return int(self.sim.value("spm_units", "spm_unit", variable, period if period is not None else self.period))

    def get_household_value(self, category: str, sub_category: str, variable: str) -> Any:
        return self.sim.value(category, sub_category, variable, self.period)
