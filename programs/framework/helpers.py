# medicaid_eligible() answers "is this household already Medicaid-eligible?", which a
# program reads to decide whether to surface itself. Sixteen callers across four
# families and three white labels, so it belongs to no single one.
#
# STATE_MEDICAID_OPTIONS is also spliced into screener/views.py's calculation order,
# so Medicaid resolves before the programs that gate on it. A state's Medicaid program
# must be listed here, or that gate reads False for it and the ordering reserves it
# no slot — both silent.
from programs.framework.base import Eligibility

STATE_MEDICAID_OPTIONS = ("co_medicaid", "nc_medicaid", "il_medicaid", "ks_medicaid")


def medicaid_eligible(data: dict[str, Eligibility]):
    for name in STATE_MEDICAID_OPTIONS:
        if name in data:
            return data[name].eligible

    return False
