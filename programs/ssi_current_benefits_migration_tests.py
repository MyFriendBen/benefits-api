"""Run 0191's forwards against real rows, matched the way it matches them."""

import importlib

from django.apps import apps as django_apps
from django.test import TestCase

from programs.models import Program
from screener.models import CurrentBenefit, Screen, WhiteLabel


class TestMoveStateSsiCurrentBenefits(TestCase):
    def setUp(self):
        self.migration = importlib.import_module("programs.migrations.0191_move_state_ssi_current_benefits")
        self.federal_wl = WhiteLabel.objects.create(name="Federal Programs", code="federal")
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.tx = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.co_ssi = self._program(self.co, "ssi")
        self.tx_ssi = self._program(self.tx, "tx_ssi")
        self.co_snap = self._program(self.co, "co_snap", base_program="snap")

    def _program(self, white_label: WhiteLabel, name: str, base_program: str = "ssi") -> Program:
        program = Program.objects.new_program(white_label=white_label.code, name_abbreviated=name)
        program.base_program = base_program
        program.save()
        return program

    def _federal(self) -> Program:
        return self._program(self.federal_wl, "federal_ssi")

    def _screen(self, white_label: WhiteLabel, *programs: Program) -> Screen:
        screen = Screen.objects.create(white_label=white_label, zipcode="80202", household_size=1, completed=False)
        for program in programs:
            CurrentBenefit.objects.create(screen=screen, program=program)
        return screen

    def _programs_of(self, screen: Screen) -> set[str]:
        return set(CurrentBenefit.objects.filter(screen=screen).values_list("program__name_abbreviated", flat=True))

    def test_rows_on_state_ssi_programs_move_to_the_federal_row(self):
        federal = self._federal()
        co_screen = self._screen(self.co, self.co_ssi, self.co_snap)
        tx_screen = self._screen(self.tx, self.tx_ssi)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._programs_of(co_screen), {"federal_ssi", "co_snap"})
        self.assertEqual(self._programs_of(tx_screen), {"federal_ssi"})
        self.assertEqual(CurrentBenefit.objects.filter(program=federal).count(), 2)
        self.assertEqual(CurrentBenefit.objects.filter(program__in=[self.co_ssi, self.tx_ssi]).count(), 0)

    def test_a_screen_already_on_the_federal_row_loses_the_state_row(self):
        federal = self._federal()
        screen = self._screen(self.co, self.co_ssi, federal)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._programs_of(screen), {"federal_ssi"})
        self.assertEqual(CurrentBenefit.objects.filter(screen=screen).count(), 1)

    def test_two_state_rows_on_one_screen_collapse_to_one_federal_row(self):
        self._federal()
        cesn = WhiteLabel.objects.create(name="CESN", code="cesn", state_code="CO")
        cesn_ssi = self._program(cesn, "cesn_ssi")
        screen = self._screen(cesn, self.co_ssi, cesn_ssi)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._programs_of(screen), {"federal_ssi"})
        self.assertEqual(CurrentBenefit.objects.filter(screen=screen).count(), 1)

    def test_a_state_owned_program_with_the_ssi_base_program_is_not_moved(self):
        """The nine rows are matched by (white label, name), not by `base_program`: a state's
        own SSI-adjacent program such as Massachusetts' supplement shares the base program and
        must keep its current-benefit rows."""
        self._federal()
        ma = WhiteLabel.objects.create(name="Massachusetts", code="ma", state_code="MA")
        ma_ssp = self._program(ma, "ma_ssp", base_program="ssi")
        screen = self._screen(ma, ma_ssp)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._programs_of(screen), {"ma_ssp"})

    def test_without_a_federal_row_nothing_changes(self):
        screen = self._screen(self.co, self.co_ssi)

        self.migration.forwards(django_apps, None)

        self.assertEqual(self._programs_of(screen), {"ssi"})

    def test_rerunning_is_a_no_op(self):
        federal = self._federal()
        screen = self._screen(self.co, self.co_ssi)

        self.migration.forwards(django_apps, None)
        self.migration.forwards(django_apps, None)

        self.assertEqual(self._programs_of(screen), {"federal_ssi"})
        self.assertEqual(CurrentBenefit.objects.filter(program=federal).count(), 1)
