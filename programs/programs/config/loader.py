"""
Loads config-layer JSON (schemas/config_layer.schema.json, Phase 1) into a
frozen ConfigLayer object, per DECISIONS.md D-011: parsed once, in memory,
at whatever module's import time performs registration (see
factories/calculator_factory.py) -- no DB table.

additional_inputs/state_dependency are bare dependency-class name strings in
the JSON (e.g. "CoStateCodeDependency"); resolve_dependency_class() resolves
them against the four existing dependency modules
(policyengine/calculators/dependencies/{household,member,spm,tax}.py).

The schema carries no pe_outputs field (checked directly against
config_layer.schema.json) -- build_output_dependency() derives a minimal
output-only dependency class from pe_entity + pe_name instead, mirroring
dependency.spm.Snap's shape (a plain unit subclass with `field` set) without
reusing Snap itself, since Snap's real value() encodes SNAP-specific
already-reported-benefit logic this generic derivation has no reason to
copy.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from programs.programs.policyengine.calculators.dependencies import household, member, spm, tax
from programs.programs.policyengine.calculators.dependencies.base import (
    Household,
    Member,
    PolicyEngineScreenInput,
    SpmUnit,
    TaxUnit,
)


class ConfigLoadError(Exception):
    """Malformed config-layer JSON or an invalid extends/federal_config pairing."""


class UnknownDependencyClassError(ConfigLoadError):
    """additional_inputs/state_dependency names a class that doesn't exist."""


class UnsupportedPeEntityError(ConfigLoadError):
    """pe_entity is 'family'/'marital_unit' -- no base dependency class exists
    for either yet (dependencies/base.py only defines Household/TaxUnit/
    SpmUnit/Member). Not needed by SNAP/TANF; flagged as a known gap in
    ROADMAP.md, not fixed here."""


_ENTITY_BASE_CLASS: dict[str, type[PolicyEngineScreenInput]] = {
    "spm_unit": SpmUnit,
    "tax_unit": TaxUnit,
    "person": Member,
    "household": Household,
}


def _build_dependency_registry() -> dict[str, type[PolicyEngineScreenInput]]:
    registry: dict[str, type[PolicyEngineScreenInput]] = {}
    for module in (household, member, spm, tax):
        for name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and issubclass(obj, PolicyEngineScreenInput)
                and obj is not PolicyEngineScreenInput
            ):
                registry[name] = obj
    return registry


# Built once, at import time of this module. This is a name->class lookup
# over four already-explicitly-imported dependency modules -- not calculator
# auto-discovery (D-001 is unaffected; nothing here scans directories or
# discovers program/calculator registrations).
_DEPENDENCY_REGISTRY = _build_dependency_registry()


def resolve_dependency_class(name: str) -> type[PolicyEngineScreenInput]:
    try:
        return _DEPENDENCY_REGISTRY[name]
    except KeyError:
        raise UnknownDependencyClassError(name) from None


@functools.lru_cache(maxsize=None)
def build_output_dependency(pe_entity: str, pe_name: str) -> type[PolicyEngineScreenInput]:
    """A pure pass-through program's output dependency is always just "the
    field named pe_name, on the entity's own unit" -- derived rather than
    configured, since the config schema carries no pe_outputs field."""
    base_cls = _ENTITY_BASE_CLASS.get(pe_entity)
    if base_cls is None:
        raise UnsupportedPeEntityError(pe_entity)
    class_name = f"_Output_{pe_entity}_{pe_name}"
    return type(class_name, (base_cls,), {"field": pe_name})


@dataclass(frozen=True)
class ConfigLayer:
    """Immutable once loaded -- a new, deliberate hardening this phase
    introduces (see plan Context: existing calculators are ordinary mutable
    ProgramCalculator subclasses; there is no precedent for immutability,
    only for the attribute-access style this mirrors)."""

    program: str
    state: str
    pe_name: str
    pe_entity: str
    pe_period_month: Optional[str]
    pe_inputs: list[type[PolicyEngineScreenInput]] = field(default_factory=list)
    pe_outputs: list[type[PolicyEngineScreenInput]] = field(default_factory=list)


def load_config_layer(config: dict, *, federal_config: Optional[dict] = None) -> ConfigLayer:
    extends = config["extends"]

    if extends is not None:
        if federal_config is None:
            raise ConfigLoadError(
                f"{config['program']}/{config['state']}: extends={extends!r} but no federal_config given"
            )
        if federal_config.get("extends") is not None:
            # D-006: chains are capped at one level.
            raise ConfigLoadError(
                "federal_config itself has a non-null extends -- chains beyond one level are not supported"
            )
        if federal_config["program"] != extends:
            raise ConfigLoadError(
                f"federal_config.program={federal_config['program']!r} does not match extends={extends!r}"
            )
        base_inputs = [resolve_dependency_class(n) for n in federal_config["additional_inputs"]]
    else:
        if federal_config is not None:
            raise ConfigLoadError("federal_config given but extends is null")
        base_inputs = []

    own_inputs = [resolve_dependency_class(n) for n in config["additional_inputs"]]
    state_dep = [resolve_dependency_class(config["state_dependency"])] if config["state_dependency"] else []

    return ConfigLayer(
        program=config["program"],
        state=config["state"],
        pe_name=config["pe_name"],
        pe_entity=config["pe_entity"],
        pe_period_month=config["pe_period_month"],
        pe_inputs=[*base_inputs, *own_inputs, *state_dep],
        pe_outputs=[build_output_dependency(config["pe_entity"], config["pe_name"])],
    )


def load_config_layer_from_file(path: str | Path, *, federal_path: Optional[str | Path] = None) -> ConfigLayer:
    config = json.loads(Path(path).read_text())
    federal_config = json.loads(Path(federal_path).read_text()) if federal_path is not None else None
    return load_config_layer(config, federal_config=federal_config)
