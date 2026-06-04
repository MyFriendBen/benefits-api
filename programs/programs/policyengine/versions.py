"""
Single source of truth for what a valid PolicyEngine model-version string is and
what each form means. Imported by:
  - configuration.models.PolicyEngineConfig (validates the pinned config value)
  - screener.views (validates the ?pe_version= override)
  - programs.programs.policyengine.policy_engine (parses the resolved version for
    input gating)

Two kinds of version string:
  - an exact package version, e.g. "1.715.2" (MAJOR.MINOR.PATCH) — the only form
    allowed in the DB config, since it's an immutable contract.
  - a floating alias, "current" or "frontier" — allowed ONLY on the test-only
    ?pe_version= override, never in the config (PolicyEngine repoints these when it
    promotes a release, so storing one would let our served version move under us).
"""

import re
from typing import Optional

# Exact MAJOR.MINOR.PATCH. The shape (not a hardcoded list) means new PolicyEngine
# releases need no code change.
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

# PolicyEngine's floating model aliases.
CURRENT = "current"
FRONTIER = "frontier"
ALIASES = (CURRENT, FRONTIER)

# Sentinel tuple meaning "newest released model" — compares greater than any real
# version, so it satisfies any min_pe_version floor.
NEWEST_VERSION = (float("inf"),)


def is_valid_version_number(value: str) -> bool:
    """True if value is an exact MAJOR.MINOR.PATCH version (no aliases)."""
    return bool(VERSION_RE.match(value))


def is_valid_override(value: str) -> bool:
    """True if value is acceptable on the ?pe_version= override: an alias or an
    exact version number."""
    return value in ALIASES or is_valid_version_number(value)


def to_comparable_pe_version(version: Optional[str]) -> Optional[tuple]:
    """Turn a given PE version into a comparable tuple for PE API input gating:
    - "1.715.2"  -> (1, 715, 2)
    - "frontier" -> NEWEST_VERSION (newest released model, supports gated inputs)
    - "current" / None / unparseable -> None (treat as the current default model)
    """
    if version == FRONTIER:
        return NEWEST_VERSION
    if not version or version == CURRENT:
        return None
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def determine_pe_version(pe_version_override: Optional[str] = None) -> Optional[str]:
    """Determine the PolicyEngine version string to send: per-request override
    (test-only, passed down as a url param) wins, then the global DB PolicyEngineConfig
    pin, else None (omit the field, i.e. PolicyEngine's default version). The override
    may be a floating alias ("frontier"/"current"); the config value must be an exact
    MAJOR.MINOR.PATCH version (enforced on the model)."""
    if pe_version_override:
        return pe_version_override

    # Deferred to keep this module import-light (avoids pulling the configuration model
    # layer at import time); there is no import cycle.
    from configuration.models import PolicyEngineConfig

    # Read-only accessor: must not write a row on the eligibility hot path.
    return PolicyEngineConfig.current_version() or None


def version_supports(comparable_version: Optional[tuple], min_pe_version: tuple, max_pe_version: tuple) -> bool:
    """Whether a request at comparable_version may send an input that exists in the
    version window [min_pe_version, max_pe_version] (each bound optional, from a
    dependency's min_pe_version/max_pe_version). Ungated inputs (both empty) are always
    sent. comparable_version is the output of to_comparable_pe_version().

    comparable_version is None for an unknown/current/unpinned request. We treat that
    asymmetrically: it FAILS any min floor (don't send a not-yet-existing variable to
    the current model) but SATISFIES any max ceiling (a variable that still exists on
    the current model should keep being sent until we pin a version past its removal)."""
    if min_pe_version:
        if comparable_version is None or comparable_version < min_pe_version:
            return False
    if max_pe_version:
        if comparable_version is not None and comparable_version > max_pe_version:
            return False
    return True
