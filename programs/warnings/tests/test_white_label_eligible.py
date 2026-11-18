"""`WarningCalculator.white_label_eligible`: only federal programs are filtered by white label."""

from django.test import TestCase

from programs.framework.base import Eligibility
from programs.models import Program, WarningMessage
from programs.util import Dependencies
from programs.warnings.base import WarningCalculator
from screener.models import Screen, WhiteLabel


class TestWhiteLabelEligible(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        WhiteLabel.objects.get_or_create(code="federal", defaults={"name": "Federal"})
        cls.co = WhiteLabel.objects.create(name="CO Test", code="co_warn", state_code="CO")
        cls.ks = WhiteLabel.objects.create(name="KS Test", code="ks_warn", state_code="KS")
        cls.co_program = Program.objects.new_program(white_label="co_warn", name_abbreviated="co_warn_program")
        cls.federal_program = Program.objects.new_program(white_label="federal", name_abbreviated="federal_warn")
        cls.co_warning = WarningMessage.objects.new_warning("co_warn", "_show", "co_warn_warning")
        cls.ks_warning = WarningMessage.objects.new_warning("ks_warn", "_show", "ks_warn_warning")

    def shown(self, warning: WarningMessage, program: Program | None, screen_white_label: WhiteLabel) -> bool:
        screen = Screen.objects.create(
            white_label=screen_white_label, zipcode="80202", household_size=1, completed=False
        )
        eligibility = Eligibility()
        eligibility.eligible = True
        return WarningCalculator(screen, warning, eligibility, Dependencies(), program=program).calc()

    def test_state_program_shows_its_own_white_labels_warning(self) -> None:
        self.assertTrue(self.shown(self.co_warning, self.co_program, self.co))

    def test_state_program_shows_a_warning_another_white_label_owns(self) -> None:
        self.assertTrue(self.shown(self.ks_warning, self.co_program, self.co))

    def test_warning_evaluated_without_a_program_is_not_filtered(self) -> None:
        self.assertTrue(self.shown(self.ks_warning, None, self.co))

    def test_federal_program_shows_a_state_warning_only_in_that_state(self) -> None:
        self.assertTrue(self.shown(self.co_warning, self.federal_program, self.co))
        self.assertFalse(self.shown(self.co_warning, self.federal_program, self.ks))
