"""WIC receipt bypasses the Nurse-Family Partnership income test.

A household on WIC has already been income-screened, so NFP accepts that in place
of its own test. Pins that the federal WIC program satisfies the check.
"""

from programs.framework.base import Eligibility
from programs.programs.testing_fixtures.current_benefit_fixtures import (
    ReceivesBenefitTestCase,
    receive_federal_benefit,
)


class NurseFamilyPartnershipWicBypassTests(ReceivesBenefitTestCase):
    def test_wic_resolves_for_nurse_family_partnership(self):
        """CO/IL Nurse-Family Partnership treat WIC receipt as an income-test bypass. WIC is one
        federal program every white label sees."""
        receive_federal_benefit(self.screen, "federal_wic", "wic")

        self.assertTrue(self.screen.has_base_benefit("wic"))
        self.assertFalse(self.screen.has_benefit("wic"))
