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
LATEST = (float("inf"),)


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
    - "frontier" -> LATEST (newest released model, supports gated inputs)
    - "current" / None / unparseable -> None (treat as the current default model)
    """
    if version == FRONTIER:
        return LATEST
    if not version or version == CURRENT:
        return None
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None
