"""MO Medicare Savings Program."""

from programs.programs.cross_white_label.msp.base import Msp
from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency


class MoMsp(Msp):
    """
    Missouri Medicare Savings Program (QMB / SLMB / QI) — federal ``Msp`` plus the MO state
    code and Medicaid inputs, mirroring ``KsMsp`` / ``TxMsp`` / ``IlMsp``.

    The income tiers are the federal floor in Missouri, so the state code is the only
    MO-keyed input. It resolves the MSP asset-test-applies parameter, which is ``true`` for
    MO — without it the resource test would silently not apply and over-resourced
    households would show as eligible.

    Missouri rules PolicyEngine does not model are recorded in the MO MSP spec.
    """

    program_code = "mo_medicare_savings"

    pe_inputs = [
        *Msp.pe_inputs,
        dependency.household.MoStateCodeDependency,
        *Medicaid.pe_inputs,
    ]
