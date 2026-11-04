"""
Every state's CHIP program is marked "already has" for a member who reports CHIP coverage.

The results page skips a member's value, and hides a program nobody else qualifies for, when
`HouseholdMember.has_insurance(program_code)` is true. That lookup goes through
`Insurance.insurance_map()`, so a CHIP calculator whose code is missing there shows a child
already on CHIP the program as new coverage. The base's coverage test doesn't bar current
CHIP coverage, so this mapping is what keeps it off their results.
"""

from django.test import SimpleTestCase

from programs.framework.base import ProgramCalculator
from programs.framework.registry import build
from screener.models import Insurance

CHIP_PACKAGE = "programs.programs.cross_white_label.medicaid.chip"

#: Left unmapped on purpose. Missouri charges its CHIP premium once per family, and the
#: calculator nets it against the children's value, so marking an enrolled child as already
#: having it would still charge the premium against a newly eligible sibling. Missouri's
#: handling is settled when its spec is reviewed, not here.
UNMAPPED = {"mo_chip"}


class TestChipProgramsMapToChipCoverage(SimpleTestCase):
    def test_every_chip_calculator_reads_chip_coverage_as_already_held(self):
        codes = sorted(set(build(CHIP_PACKAGE, ProgramCalculator)) - UNMAPPED)
        self.assertIn("nj_chip", codes)

        reports_chip = Insurance(chp=True)
        reports_nothing = Insurance(none=True)
        for code in codes:
            with self.subTest(program=code):
                self.assertIn(code, reports_chip.insurance_map())
                self.assertTrue(reports_chip.has_insurance_types((code,)))
                self.assertFalse(reports_nothing.has_insurance_types((code,)))

    def test_unmapped_exceptions_are_still_chip_calculators(self):
        self.assertLessEqual(UNMAPPED, set(build(CHIP_PACKAGE, ProgramCalculator)))
        for code in UNMAPPED:
            self.assertNotIn(code, Insurance().insurance_map())
