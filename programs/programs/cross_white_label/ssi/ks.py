"""KS SSI."""

from programs.programs.cross_white_label.ssi.base import Ssi
import programs.framework.pe_dependencies as dependency


class KsSsi(Ssi):
    """
    Kansas Supplemental Security Income — federal SSI applied to KS residents.

    A thin wrapper around the federal ``Ssi`` PolicyEngine calculator that adds the
    KS state code so PolicyEngine can apply state-specific SSI handling. Kansas pays
    no general SSI state supplement (the KS supplement, SSPP, is tracked as its own
    program), so the output is the federal Federal Benefit Rate (FBR) minus
    PolicyEngine's countable income. The FBR is sourced from PolicyEngine's
    parameters at calculation time, so the value tracks SSA COLA updates year over
    year.
    """

    program_code = "ks_ssi"

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.KsStateCodeDependency,
    ]
