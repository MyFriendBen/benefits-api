"""
Helpers for checking that a translation keeps the ICU placeholders of its
source string.

The frontend passes values by name (values={{ subject }}), so a stored string
that renames {subject} to {sujeto}, or drops it, never renders the value.
"""

import re
from typing import Iterator, Optional

_NAME_ONLY_RE = re.compile(r"\s*(\w+)\s*$")
_ICU_RE = re.compile(r"\s*(\w+)\s*,\s*(?:plural|select|selectordinal)\s*,(.*)$", re.DOTALL)


def _top_level_groups(text: str) -> Iterator[str]:
    """Yield the contents of each outermost {...} group in `text`."""
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                yield text[start:i]


def extract_placeholders(text: str) -> set[str]:
    """
    Names of the ICU arguments in `text`.

    Picks up {name} and the argument of {name, plural|select|selectordinal, ...},
    and recurses into the branches of those, so branch keywords like `one {item}`
    are not mistaken for placeholders.
    """
    names: set[str] = set()
    for inner in _top_level_groups(text):
        icu = _ICU_RE.match(inner)
        if icu:
            names.add(icu.group(1))
            for branch in _top_level_groups(icu.group(2)):
                names |= extract_placeholders(branch)
            continue
        simple = _NAME_ONLY_RE.match(inner)
        if simple:
            names.add(simple.group(1))
    return names


def placeholder_diff(source_text: str, text: str) -> Optional[tuple[set[str], set[str]]]:
    """
    Compare the placeholders of `text` against `source_text`.

    Returns None when they match, otherwise (missing, extra): names the source
    has that `text` lacks, and names `text` has that the source lacks.
    """
    expected = extract_placeholders(source_text or "")
    found = extract_placeholders(text or "")
    if expected == found:
        return None
    return expected - found, found - expected
