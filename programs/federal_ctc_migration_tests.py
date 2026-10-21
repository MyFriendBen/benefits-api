"""`0191_move_state_ctc_current_benefits` against real rows, matched the way it matches them."""

import importlib

from django.apps import apps as django_apps
from django.test import TestCase

from programs.models import Program
from screener.models import CurrentBenefit, Screen, WhiteLabel


class TestMoveStateCtcCurrentBenefits(TestCase):
    def setUp(self):
        self.migration = importlib.import_module("programs.migrations.0191_move_state_ctc_current_benefits")
        self.federal_wl = WhiteLabel.objects.create(name="Federal", code="federal")
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.tx = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.il = WhiteLabel.objects.create(name="Illinois", code="il", state_code="IL")
        self.co_ctc = Program.objects.new_program(white_label="co", name_abbreviated="ctc")
        self.tx_ctc = Program.objects.new_program(white_label="tx", name_abbreviated="tx_ctc")
        self.il_federal_ctc = Program.objects.new_program(white_label="il", name_abbreviated="ctc")
        # The states' own credits. They carry base_program = ctc and must not be touched.
        self.coctc = self._state_credit("co", "coctc")
        self.il_ctc = self._state_credit("il", "il_ctc")

    def _state_credit(self, white_label: str, name_abbreviated: str) -> Program:
        program = Program.objects.new_program(white_label=white_label, name_abbreviated=name_abbreviated)
        program.base_program = "ctc"
        program.save()
        return program

    def _federal(self) -> Program:
        return Program.objects.new_program(white_label="federal", name_abbreviated="federal_ctc")

    def _screen(self, white_label: WhiteLabel) -> Screen:
        return Screen.objects.create(white_label=white_label, zipcode="80202", household_size=1, completed=False)

    def _has(self, screen: Screen, program: Program) -> CurrentBenefit:
        return CurrentBenefit.objects.create(screen=screen, program=program)

    def _programs_of(self, screen: Screen) -> list[str]:
        return sorted(cb.program.name_abbreviated for cb in screen.current_benefits.all())

    def test_rows_on_the_state_rows_move_to_the_federal_row(self):
        federal = self._federal()
        co_screen, tx_screen = self._screen(self.co), self._screen(self.tx)
        self._has(co_screen, self.co_ctc)
        self._has(co_screen, self.coctc)
        self._has(tx_screen, self.tx_ctc)

        self.migration.move_ctc_current_benefits(django_apps, None)

        self.assertEqual(self._programs_of(co_screen), ["coctc", "federal_ctc"])
        self.assertEqual(self._programs_of(tx_screen), ["federal_ctc"])
        self.assertEqual(CurrentBenefit.objects.filter(program__in=[self.co_ctc, self.tx_ctc]).count(), 0)
        self.assertEqual(CurrentBenefit.objects.filter(program=federal).count(), 2)

    def test_the_states_own_credits_are_not_moved(self):
        """`coctc` and `il_ctc` share `base_program = ctc` with the federal rows; only the
        federal copies, matched by (white label, name), move."""
        federal = self._federal()
        co_screen, il_screen = self._screen(self.co), self._screen(self.il)
        self._has(co_screen, self.coctc)
        self._has(il_screen, self.il_ctc)
        self._has(il_screen, self.il_federal_ctc)

        self.migration.move_ctc_current_benefits(django_apps, None)

        self.assertEqual(self._programs_of(co_screen), ["coctc"])
        self.assertEqual(self._programs_of(il_screen), ["federal_ctc", "il_ctc"])
        self.assertEqual(CurrentBenefit.objects.filter(program=self.coctc).count(), 1)
        self.assertEqual(CurrentBenefit.objects.filter(program=self.il_ctc).count(), 1)
        self.assertEqual(CurrentBenefit.objects.filter(program=federal).count(), 1)

    def test_a_screen_already_on_the_federal_row_loses_the_state_row(self):
        federal = self._federal()
        screen = self._screen(self.co)
        self._has(screen, self.co_ctc)
        self._has(screen, federal)

        self.migration.move_ctc_current_benefits(django_apps, None)

        self.assertEqual(self._programs_of(screen), ["federal_ctc"])
        self.assertEqual(CurrentBenefit.objects.filter(screen=screen).count(), 1)

    def test_running_twice_changes_nothing_more(self):
        self._federal()
        screen = self._screen(self.tx)
        self._has(screen, self.tx_ctc)

        self.migration.move_ctc_current_benefits(django_apps, None)
        self.migration.move_ctc_current_benefits(django_apps, None)

        self.assertEqual(self._programs_of(screen), ["federal_ctc"])

    def test_without_a_federal_row_nothing_is_touched(self):
        screen = self._screen(self.co)
        self._has(screen, self.co_ctc)

        self.migration.move_ctc_current_benefits(django_apps, None)

        self.assertEqual(self._programs_of(screen), ["ctc"])
