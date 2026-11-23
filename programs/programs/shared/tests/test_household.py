from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.programs.shared.household import needs_child_development_help


def make_screen(needs_help, children: int) -> Mock:
    screen = Mock()
    screen.needs_child_dev_help = needs_help
    screen.num_children.return_value = children
    return screen


class TestNeedsChildDevelopmentHelp(SimpleTestCase):
    def test_needs_help_and_has_a_child(self):
        self.assertIs(needs_child_development_help(make_screen(True, 1), 21), True)

    def test_needs_help_without_a_child(self):
        self.assertIs(needs_child_development_help(make_screen(True, 0), 21), False)

    def test_has_a_child_without_needing_help(self):
        self.assertIs(needs_child_development_help(make_screen(False, 2), 21), False)

    def test_unanswered_need_reads_as_no(self):
        self.assertIs(needs_child_development_help(make_screen(None, 2), 21), False)

    def test_counts_children_up_to_the_age_including_pregnancy(self):
        screen = make_screen(True, 1)
        needs_child_development_help(screen, 21)
        screen.num_children.assert_called_once_with(age_max=21, include_pregnant=True)
