"""
Guard: every ZIP/county pair in a program spec is one the white label's crosswalk produces.

Specs feed the api-qa harness and the test suite, and screen creation rejects a ZIP or
county the crosswalk can't produce (see `test_location_validation_api`). A spec that
says `Sedgwick` where KS stores `Sedgwick County` describes a screen that 400s before
eligibility runs. This is stricter than the API: the county must belong to the stated
ZIP, not just to the white label.

A ZIP outside the crosswalk is allowed only in a scenario that expects the rejection,
i.e. its section says "400 on `zipcode`".

Recognized forms (county backticked or not, `Location` label optional):
    ZIP `67202`, county `Sedgwick County`
    Enter ZIP code `98101`, Select county `King County`
    ZIP 98118, King County, HH=4
    Wyandotte County (zip 66101)

Not caught: a ZIP/county written in another shape, or MA's `city` field.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

from configuration.white_labels import white_label_config

SCREENER_TESTS = Path(__file__).resolve().parent
REPO_ROOT = SCREENER_TESTS.parent.parent
PROGRAMS_ROOT = REPO_ROOT / "programs" / "programs"
FIXTURE = SCREENER_TESTS / "fixtures" / "spec_locations_ks.md"

ZIP = r"(?i:zip)(?: code)?\s+`?(?P<zip>\d{5})`?"
NAME = r"[A-Z][\w.' -]*?"
# Unbackticked names end at a period, so allow only the one abbreviation specs use.
BARE_NAME = r"(?:St\. )?[A-Z][\w' -]*?"
PAIR_PATTERNS = [
    # ZIP `67202` (Wichita), county `Sedgwick County` / county St. Louis City.
    re.compile(
        ZIP + r"(?:\s*\([^)]*\))?,?\s+(?:Select\s+)?[Cc]ounty:?\s+\**(?:`(?P<ticked>[^`]+)`"
        r"|(?P<bare>" + BARE_NAME + r"))(?=\**(?:[,;()]|\.(?:\s|$)|\s+—|$))"
    ),
    # ZIP 98118, King County, HH=4
    re.compile(ZIP + r",\s+(?P<bare>" + NAME + r" County)\b"),
    # Wyandotte County (zip 66101)
    re.compile(r"(?P<bare>\b" + NAME + r" County) \((?i:zip) (?P<zip>\d{5})\)"),
]
LOCATION_ZIP = re.compile(r"Location\b.*?" + ZIP)
EXPECTS_ZIP_REJECTION = "400 on `zipcode`"
# Spec directories that are not a white label with a crosswalk.
NO_CROSSWALK = {"federal"}


def _spec_white_label(path: Path) -> str | None:
    """`white_labels/ks/...` or `cross_white_label/.../specs/ks.md` (also `wa_wftc.md`)."""
    parts = path.relative_to(PROGRAMS_ROOT).parts
    if parts[0] == "white_labels":
        return parts[1]
    if parts[-2] == "specs":
        return path.stem.split("_")[0]
    return None


def _sections(text: str):
    """(first lineno, lines) per `###` scenario section, so a line can see its own Expected."""
    start, lines = 1, []
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("### ") and lines:
            yield start, lines
            start, lines = lineno, []
        lines.append(line)
    if lines:
        yield start, lines


def _location_offenders(text: str, white_label: str) -> list[tuple[int, str]]:
    """(lineno, reason) for every spec ZIP or ZIP/county pair the crosswalk can't produce."""
    crosswalk = white_label_config[white_label].counties_by_zipcode
    offenders = []
    for start, lines in _sections(text):
        rejection_expected = any(EXPECTS_ZIP_REJECTION in line for line in lines)
        for lineno, line in enumerate(lines, start):
            pairs = {}
            for pattern in PAIR_PATTERNS:
                for match in pattern.finditer(line):
                    pairs.setdefault(match["zip"], match.groupdict().get("ticked") or match["bare"])
            zips = set(pairs) | {m["zip"] for m in LOCATION_ZIP.finditer(line)}
            for zipcode in sorted(zips):
                county = pairs.get(zipcode)
                if zipcode not in crosswalk:
                    if not rejection_expected:
                        offenders.append((lineno, f"ZIP {zipcode} is not in the {white_label} crosswalk"))
                elif county is not None and county.strip() not in crosswalk[zipcode]:
                    expected = sorted(crosswalk[zipcode])
                    offenders.append((lineno, f"county {county.strip()!r} is not one of {expected} for ZIP {zipcode}"))
    return offenders


def _spec_paths():
    for path in sorted(PROGRAMS_ROOT.rglob("*.md")):
        if path.name == "spec.md" or path.parent.name == "specs":
            yield path


class SpecLocationTests(SimpleTestCase):
    def test_spec_locations_match_the_crosswalk(self):
        offenders = []
        for path in _spec_paths():
            white_label = _spec_white_label(path)
            if white_label in NO_CROSSWALK or not white_label_config[white_label].counties_by_zipcode:
                continue
            for lineno, reason in _location_offenders(path.read_text(), white_label):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno} {reason}")

        self.assertEqual(
            offenders,
            [],
            "Spec ZIP/county pairs must come from the white label's counties_by_zipcode; "
            "screen creation rejects anything else with a 400. Copy the county exactly as "
            "the crosswalk stores it (KS/MO/WA suffixed, TX/IL bare, MA municipality).",
        )

    def test_every_spec_maps_to_a_white_label(self):
        unmapped = [
            str(path.relative_to(REPO_ROOT))
            for path in _spec_paths()
            if _spec_white_label(path) not in white_label_config.keys() | NO_CROSSWALK
        ]
        self.assertEqual(unmapped, [])

    def test_fixture_flags_each_bad_line(self):
        """The guard catches each known-bad shape in the fixture and passes the good ones."""
        offenders = _location_offenders(FIXTURE.read_text(), "ks")
        self.assertEqual(
            offenders,
            [
                (13, "county 'Sedgwick' is not one of ['Sedgwick County'] for ZIP 67202"),
                (18, "county 'Shawnee' is not one of ['Shawnee County'] for ZIP 66604"),
                (23, "county 'Riley County' is not one of ['Sedgwick County'] for ZIP 67202"),
                (28, "county 'Sedgwick' is not one of ['Sedgwick County'] for ZIP 67202"),
                (33, "county 'Wyandotte' is not one of ['Wyandotte County'] for ZIP 66101"),
                (38, "ZIP 97201 is not in the ks crosswalk"),
                (43, "ZIP 66602 is not in the ks crosswalk"),
            ],
        )
