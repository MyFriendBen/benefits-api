"""SUN Bucks excludes households already receiving SNAP or TANF.

Those households are auto-enrolled in Summer EBT, so surfacing SUN Bucks to them
would double-count. Asserted against a real screen with a received benefit rather
than a stubbed lookup, because the exclusion reads the resolved current-benefit set.
"""

from unittest.mock import Mock
from programs.framework.base import Eligibility
from programs.programs.white_labels.nc.sunbucks.calculator import SunBucks
from programs.programs.testing_fixtures.current_benefit_fixtures import ReceivesBenefitTestCase


class SunBucksPresumptiveExclusionTests(ReceivesBenefitTestCase):
    def _sun_bucks_eligible(self, income: int = 10_000) -> bool:
        """Run SunBucks.household_eligible() against the real screen, stubbing only the
        FPL lookup and the income figure."""
        program = Mock()
        program.year.get_limit.return_value = 30_000
        self.screen.calc_gross_income = Mock(return_value=income)
        missing_deps = Mock()
        missing_deps.has.return_value = False

        e = Eligibility()
        SunBucks(self.screen, program, {}, missing_deps).household_eligible(e)
        return e.eligible

    def test_sun_bucks_excludes_a_snap_household(self):
        """NC SUN Bucks excludes SNAP/TANF households because they're auto-enrolled."""
        self._receive("nc_snap", "snap")

        self.assertFalse(self._sun_bucks_eligible())

    def test_sun_bucks_excludes_a_tanf_household(self):
        self._receive("nc_tanf", "tanf")

        self.assertFalse(self._sun_bucks_eligible())

    def test_sun_bucks_allows_a_household_with_neither(self):
        self._receive("test_lifeline", "lifeline")

        self.assertTrue(self._sun_bucks_eligible())
