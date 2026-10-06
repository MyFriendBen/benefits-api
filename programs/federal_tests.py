"""Unit tests for the shared federal-program helpers in `programs/federal.py`.

The read paths that call these (results, current benefits, the screener options, the
current-benefits endpoints) are covered in `screener/tests/test_federal_programs.py`.
"""

from django.test import TestCase

from programs.federal import (
    FEDERAL_WHITE_LABEL,
    active_duplicates,
    filter_programs_by_name,
    preferred_program,
    visible_program,
    visible_to,
    visible_to_code,
)
from programs.models import Program
from screener.models import WhiteLabel


class FederalHelpersTestCase(TestCase):
    def setUp(self) -> None:
        self.federal = WhiteLabel.objects.create(name="Federal Programs", code=FEDERAL_WHITE_LABEL)
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.wa = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")

    def program(self, white_label: WhiteLabel, name: str, *, active: bool = True) -> Program:
        program = Program.objects.new_program(white_label.code, name)
        program.active = active
        program.save()
        return program


class TestVisibleTo(FederalHelpersTestCase):
    def test_a_white_label_sees_its_own_programs_and_federal_ones(self) -> None:
        own = self.program(self.co, "co_only")
        federal = self.program(self.federal, "fed_only")
        self.program(self.wa, "wa_only")

        self.assertEqual(set(Program.objects.filter(visible_to(self.co))), {own, federal})
        self.assertEqual(set(Program.objects.filter(visible_to_code("co"))), {own, federal})


class TestFilterProgramsByName(FederalHelpersTestCase):
    def test_keeps_first_appearance_order(self) -> None:
        a = self.program(self.co, "a")
        shared_state = self.program(self.co, "shared", active=False)
        b = self.program(self.co, "b")
        shared_federal = self.program(self.federal, "shared")

        kept = filter_programs_by_name([a, shared_state, b, shared_federal], "test")

        self.assertEqual(kept, [a, shared_federal, b])

    def test_names_without_a_federal_row_pass_through(self) -> None:
        a = self.program(self.co, "a")
        b = self.program(self.co, "b")

        self.assertEqual(filter_programs_by_name([a, b], "test"), [a, b])


class TestPreferredProgram(FederalHelpersTestCase):
    def test_the_first_program_for_a_name_is_kept(self) -> None:
        own = self.program(self.co, "shared")

        self.assertEqual(preferred_program(None, own, "test"), own)

    def test_the_federal_program_wins_in_either_order(self) -> None:
        """A name matches at most a state row and a federal row, so order can't change the winner."""
        state = self.program(self.co, "shared", active=False)
        federal = self.program(self.federal, "shared")

        self.assertEqual(preferred_program(state, federal, "test"), federal)
        self.assertEqual(preferred_program(federal, state, "test"), federal)

    def test_an_inactive_state_row_losing_is_not_logged(self) -> None:
        state = self.program(self.co, "shared", active=False)
        federal = self.program(self.federal, "shared")

        with self.assertNoLogs("programs.federal", level="ERROR"):
            preferred_program(state, federal, "test")

    def test_two_active_programs_are_logged_with_the_read_path(self) -> None:
        state = self.program(self.co, "shared")
        federal = self.program(self.federal, "shared")

        with self.assertLogs("programs.federal", level="ERROR") as logs:
            kept = preferred_program(state, federal, "the test path")

        self.assertEqual(kept, federal)
        self.assertIn("shared", logs.output[0])
        self.assertIn("the test path", logs.output[0])


class TestVisibleProgram(FederalHelpersTestCase):
    def test_returns_the_federal_row_over_the_deactivated_state_row(self) -> None:
        self.program(self.co, "shared", active=False)
        federal = self.program(self.federal, "shared")

        self.assertEqual(visible_program(self.co, "shared", "test"), federal)

    def test_returns_an_inactive_own_row(self) -> None:
        """Callers resolve held benefits, which may no longer be offered."""
        own = self.program(self.co, "retired", active=False)

        self.assertEqual(visible_program(self.co, "retired", "test"), own)

    def test_returns_none_for_another_white_labels_program(self) -> None:
        self.program(self.wa, "wa_only")

        self.assertIsNone(visible_program(self.co, "wa_only", "test"))


class TestActiveDuplicates(FederalHelpersTestCase):
    def test_lists_each_state_still_active_beside_the_federal_row(self) -> None:
        self.program(self.federal, "shared")
        self.program(self.co, "shared")
        self.program(self.wa, "shared")
        self.program(self.federal, "clean")
        self.program(self.co, "clean", active=False)

        self.assertEqual(active_duplicates(), {"shared": ["co", "wa"]})

    def test_can_be_limited_to_names(self) -> None:
        self.program(self.federal, "shared")
        self.program(self.co, "shared")

        self.assertEqual(active_duplicates(["other"]), {})
        self.assertEqual(active_duplicates(["shared"]), {"shared": ["co"]})
