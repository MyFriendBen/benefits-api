from programs.programs.calc import Eligibility

STATE_MEDICAID_OPTIONS = ("co_medicaid", "nc_medicaid", "il_medicaid", "ks_medicaid")


def medicaid_eligible(data: dict[str, Eligibility]):
    for name in STATE_MEDICAID_OPTIONS:
        if name in data:
            return data[name].eligible

    return False
