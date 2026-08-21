"""KS Lifeline."""

from programs.programs.cross_white_label.lifeline.base import Lifeline
import programs.framework.pe_dependencies as dependency


class KsLifeline(Lifeline):
    """
    Kansas Lifeline Phone and Internet Discount calculator.

    Uses PolicyEngine's federal ``lifeline`` calculator with the KS state branch.
    Kansas layers a state supplement ($7.77/month, phone service only) on top of
    the federal benefit ($9.25/month), for a combined $17.02/month ($204.24/year).

    The KS supplement is released by PE only up to the household's ``phone_cost``
    (``min_(phone_cost, ks_supplement * MONTHS_IN_YEAR)`` in PE's ``lifeline.py``).
    ``phone_cost`` is supplied via the base ``Lifeline.pe_inputs`` (PhoneCostDependency),
    so without it every KS household would silently receive only the federal-only
    $111/year instead of $204.24/year. Mirrors the TxLifeline / WaLifeline pattern,
    adding the KS state code so PE resolves the KS supplement parameters.
    """

    program_code = "ks_lifeline"

    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
