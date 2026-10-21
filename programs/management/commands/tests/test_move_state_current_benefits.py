"""`move_state_current_benefits` against real rows: the recovery path for a migration that
ran before the federal row existed."""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from programs.models import Program
from screener.models import CurrentBenefit, Screen, WhiteLabel


class TestMoveStateCurrentBenefits(TestCase):
    def setUp(self):
        WhiteLabel.objects.create(name="Federal", code="federal")
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.tx = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.co_ctc = Program.objects.new_program(white_label="co", name_abbreviated="ctc")
        self.tx_ctc = Program.objects.new_program(white_label="tx", name_abbreviated="tx_ctc")
        self.coctc = Program.objects.new_program(white_label="co", name_abbreviated="coctc")
        self.coctc.base_program = "ctc"
        self.coctc.save()

    def _federal(self) -> Program:
        return Program.objects.new_program(white_label="federal", name_abbreviated="federal_ctc")

    def _screen(self, white_label: WhiteLabel) -> Screen:
        return Screen.objects.create(white_label=white_label, zipcode="80202", household_size=1, completed=False)

    def _run(self, *args: str) -> str:
        out = StringIO()
        call_command("move_state_current_benefits", *args, stdout=out)
        return out.getvalue()

    def _programs_of(self, screen: Screen) -> list[str]:
        return sorted(cb.program.name_abbreviated for cb in screen.current_benefits.all())

    def test_moves_the_recorded_state_rows_and_prints_counts(self):
        federal = self._federal()
        co_screen, tx_screen, both = self._screen(self.co), self._screen(self.tx), self._screen(self.co)
        CurrentBenefit.objects.create(screen=co_screen, program=self.co_ctc)
        CurrentBenefit.objects.create(screen=co_screen, program=self.coctc)
        CurrentBenefit.objects.create(screen=tx_screen, program=self.tx_ctc)
        CurrentBenefit.objects.create(screen=both, program=self.co_ctc)
        CurrentBenefit.objects.create(screen=both, program=federal)

        output = self._run("federal_ctc")

        self.assertEqual(self._programs_of(co_screen), ["coctc", "federal_ctc"])
        self.assertEqual(self._programs_of(tx_screen), ["federal_ctc"])
        self.assertEqual(self._programs_of(both), ["federal_ctc"])
        self.assertIn("federal_ctc: 2 current-benefit row(s) moved, 1 duplicate(s) dropped", output)

    def test_running_twice_moves_nothing_more(self):
        self._federal()
        screen = self._screen(self.tx)
        CurrentBenefit.objects.create(screen=screen, program=self.tx_ctc)

        self._run("federal_ctc")
        output = self._run("federal_ctc")

        self.assertEqual(self._programs_of(screen), ["federal_ctc"])
        self.assertIn("federal_ctc: 0 current-benefit row(s) moved, 0 duplicate(s) dropped", output)

    def test_fails_when_the_federal_row_is_missing(self):
        screen = self._screen(self.co)
        CurrentBenefit.objects.create(screen=screen, program=self.co_ctc)

        with self.assertRaises(CommandError):
            self._run("federal_ctc")

        self.assertEqual(self._programs_of(screen), ["ctc"])

    def test_from_overrides_the_recorded_rows(self):
        self._federal()
        co_screen, tx_screen = self._screen(self.co), self._screen(self.tx)
        CurrentBenefit.objects.create(screen=co_screen, program=self.co_ctc)
        CurrentBenefit.objects.create(screen=tx_screen, program=self.tx_ctc)

        self._run("federal_ctc", "--from", "tx:tx_ctc")

        self.assertEqual(self._programs_of(co_screen), ["ctc"])
        self.assertEqual(self._programs_of(tx_screen), ["federal_ctc"])

    def test_an_unrecorded_federal_program_needs_from(self):
        with self.assertRaises(CommandError):
            self._run("federal_other")

    def test_a_from_on_the_federal_white_label_is_rejected_before_anything_runs(self):
        federal = self._federal()
        screen = self._screen(self.co)
        CurrentBenefit.objects.create(screen=screen, program=federal)

        with self.assertRaises(CommandError):
            self._run("federal_ctc", "--from", "federal:federal_ctc")

        self.assertEqual(self._programs_of(screen), ["federal_ctc"])

    def test_a_malformed_from_is_rejected(self):
        self._federal()
        with self.assertRaises(CommandError):
            self._run("federal_ctc", "--from", "tx_ctc")
