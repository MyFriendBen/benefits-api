# Medicaid-specific: the only consumer group is the state Medicaid calculators.
# Relocates alongside the Medicaid family in MFB-1676; framework/ holds only what
# every calculator needs regardless of white label or engine.
from programs.framework.base import Eligibility

STATE_MEDICAID_OPTIONS = ("co_medicaid", "nc_medicaid", "il_medicaid", "ks_medicaid")


def medicaid_eligible(data: dict[str, Eligibility]):
    for name in STATE_MEDICAID_OPTIONS:
        if name in data:
            return data[name].eligible

    return False
