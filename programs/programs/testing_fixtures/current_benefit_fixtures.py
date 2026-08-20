"""A screen that receives a named benefit, for tests of presumptive-eligibility lists.

Builds real ``Program`` and ``CurrentBenefit`` rows rather than stubbing
``has_benefit_from_list``, because the thing under test is whether a state-prefixed
program name resolves against a calculator's declared base-program list.
"""

from django.test import TestCase

from screener.models import Screen, WhiteLabel
from screener.serializers import _write_current_benefits
from screener.tests.helpers import seed_program


class ReceivesBenefitTestCase(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="80202", household_size=3, completed=False
        )

    def _receive(self, name_abbreviated: str, base_program: str) -> None:
        seed_program(self.white_label, name_abbreviated, base_program=base_program)
        _write_current_benefits(self.screen, [name_abbreviated])
        self.screen.invalidate_current_benefits_cache()
