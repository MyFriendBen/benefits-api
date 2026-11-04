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


class TestChipProgramsMapToChipCoverage(SimpleTestCase):
    def test_every_chip_calculator_reads_chip_coverage_as_already_held(self):
        codes = sorted(build(CHIP_PACKAGE, ProgramCalculator))
        self.assertIn("nj_chip", codes)

        reports_chip = Insurance(chp=True)
        reports_nothing = Insurance(none=True)
        for code in codes:
            with self.subTest(program=code):
                self.assertIn(code, reports_chip.insurance_map())
                self.assertTrue(reports_chip.has_insurance_types((code,)))
                self.assertFalse(reports_nothing.has_insurance_types((code,)))
