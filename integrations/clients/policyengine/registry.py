"""
The PolicyEngine calculators, discovered rather than listed.

This was sixty lines of imports and dict merges, one block per state per
PolicyEngine entity. Each calculator now declares its own ``name_abbreviated``
and `programs.framework.registry.build` finds it, so adding a program touches
one file instead of a calculator plus a state dict plus this module — the third
of which was easy to forget, and forgetting it meant the program silently
returned no value.

Entity type is read off the base class the calculator inherits, not off which
dict it was listed in. Those two disagreed: ``il_aca`` and ``nc_aca`` sat in the
member dict while subclassing ``PolicyEngineTaxUnitCalulator``. Nothing broke,
because the per-entity dicts have no runtime consumer — ``pe_category`` on the
class is what the request payload keys off, and that was correct. Deriving the
split from the class makes the two impossible to disagree.
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
