"""
The PolicyEngine calculators, keyed by the ``Program`` row each one backs.

Assembled by `programs.framework.registry.build`, which walks the package and
reads the ``program_code`` every calculator declares. Adding a program means
writing the calculator; nothing here needs editing.

Entity type is read off the base class a calculator inherits, so the member, spm
and tax-unit groupings cannot disagree with the classes themselves. ``pe_category``
on the class is what the request payload keys off; these groupings exist for
callers that need one entity's calculators.
"""

from programs.framework.pe_base import (
    PolicyEngineCalulator,
    PolicyEngineMembersCalculator,
    PolicyEngineSpmCalulator,
    PolicyEngineTaxUnitCalulator,
)
from programs.framework.registry import build

#: Every PolicyEngine calculator, keyed by the ``Program.name_abbreviated`` it answers to.
all_calculators: dict[str, type[PolicyEngineCalulator]] = build("programs.programs", PolicyEngineCalulator)


def _of_entity(entity):
    return {key: cls for key, cls in all_calculators.items() if issubclass(cls, entity)}


all_member_calculators: dict[str, type[PolicyEngineMembersCalculator]] = _of_entity(PolicyEngineMembersCalculator)
all_spm_unit_calculators: dict[str, type[PolicyEngineSpmCalulator]] = _of_entity(PolicyEngineSpmCalulator)
all_tax_unit_calculators: dict[str, type[PolicyEngineTaxUnitCalulator]] = _of_entity(PolicyEngineTaxUnitCalulator)

all_pe_programs = all_calculators.keys()
