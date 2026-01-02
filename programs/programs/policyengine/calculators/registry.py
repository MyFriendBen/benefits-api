"""
Registry of all PolicyEngine calculators.

This module aggregates all state-specific and federal calculators into unified
dictionaries. It's separated from __init__.py to avoid circular imports when
importing base classes.

Import from this module when you need access to the calculator dictionaries:
    from programs.programs.policyengine.calculators.registry import all_calculators
"""

from .base import (
    PolicyEngineCalulator,
    PolicyEngineMembersCalculator,
    PolicyEngineSpmCalulator,
    PolicyEngineTaxUnitCalulator,
)
from programs.programs.co.pe import (
    co_member_calculators,
    co_spm_calculators,
    co_tax_unit_calculators,
)
from programs.programs.federal.pe import (
    federal_member_calculators,
    federal_spm_unit_calculators,
    federal_tax_unit_calculators,
)
from programs.programs.il.pe import (
    il_member_calculators,
    il_spm_calculators,
    il_tax_unit_calculators,
)
from programs.programs.ma.pe import (
    ma_member_calculators,
    ma_spm_calculators,
    ma_tax_unit_calculators,
)
from programs.programs.nc.pe import nc_member_calculators, nc_spm_calculators
from programs.programs.tx.pe import (
    tx_member_calculators,
    tx_spm_calculators,
    tx_tax_unit_calculators,
)


all_member_calculators: dict[str, type[PolicyEngineMembersCalculator]] = {
    **co_member_calculators,
    **federal_member_calculators,
    **il_member_calculators,
    **ma_member_calculators,
    **nc_member_calculators,
    **tx_member_calculators,
}

all_spm_unit_calculators: dict[str, type[PolicyEngineSpmCalulator]] = {
    **co_spm_calculators,
    **federal_spm_unit_calculators,
    **il_spm_calculators,
    **ma_spm_calculators,
    **nc_spm_calculators,
    **tx_spm_calculators,
}

all_tax_unit_calculators: dict[str, type[PolicyEngineTaxUnitCalulator]] = {
    **co_tax_unit_calculators,
    **federal_tax_unit_calculators,
    **il_tax_unit_calculators,
    **ma_tax_unit_calculators,
    **tx_tax_unit_calculators,
}

all_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **all_member_calculators,
    **all_spm_unit_calculators,
    **all_tax_unit_calculators,
}

all_pe_programs = all_calculators.keys()
