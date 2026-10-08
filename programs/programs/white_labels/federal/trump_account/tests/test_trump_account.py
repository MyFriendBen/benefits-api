"""Trump Account scenarios, one per spec §8.

The pilot window is a pair of absolute dates, so the household is built from
`birth_year_month` rather than an age and the clock is pinned by `reference_date` — an age
would walk out of the window as the suite ages.

§4's `us_citizen` has no scenario here: it is `Enforced by: program-record`
(`legal_status_required`), which the calculator never reads, so no calculator test can catch
a change to it.
"""

from datetime import date

from programs.framework.base import ProgramCalculator
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.federal.trump_account.calculator import TrumpAccount


class TrumpAccountTestCase(CustomCalculatorTestCase):
    calculator_class = TrumpAccount
    white_label_code = "federal"
    state_code = ""
    # Mid-window, so a child born in any month the scenarios name is already born and the
    # 2028 upper bound is still ahead.
    reference_date = date(2026, 6, 15)
    # The calculator reads age only through `calc_age()`.
    stores_age = False


class TestTrumpAccountRegistration(TrumpAccountTestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TrumpAccount, ProgramCalculator))

    def test_program_code_is_the_prefixed_federal_name(self):
        """The registry resolves a calculator by matching `program_code` to
        `Program.name_abbreviated`, so the federal row's prefixed name has to be here."""
        self.assertEqual(TrumpAccount.program_code, "federal_trump_account")


class TestScenario01NewbornInACitizenHousehold(TrumpAccountTestCase):
    """Scenario 1: `birth_window` — golden path."""

    def test_a_newborn_is_eligible_for_one_thousand(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=30)
        self.add_member(screen, "child", age=None, birth_year_month=date(2026, 3, 1))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_000)


class TestScenario02FirstMonthOfTheWindow(TrumpAccountTestCase):
    """Scenario 2: `birth_window` — at the lower limit."""

    def test_january_2025_is_eligible(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=30)
        self.add_member(screen, "child", age=None, birth_year_month=date(2025, 1, 1))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_000)


class TestScenario03MonthBeforeTheWindow(TrumpAccountTestCase):
    """Scenario 3: `birth_window` — one step before the lower limit."""

    def test_december_2024_is_ineligible(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=30)
        self.add_member(screen, "child", age=None, birth_year_month=date(2024, 12, 1))

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestScenario04LastMonthOfTheWindow(TrumpAccountTestCase):
    """Scenario 4: `birth_window` — at the upper limit."""

    # December 2028 is in the future from the window's midpoint, so the clock moves to a
    # date by which that child is born; the window itself is unchanged.
    reference_date = date(2029, 6, 15)

    def test_december_2028_is_eligible(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=30)
        self.add_member(screen, "child", age=None, birth_year_month=date(2028, 12, 1))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1_000)


class TestScenario05MonthAfterTheWindow(TrumpAccountTestCase):
    """Scenario 5: `birth_window` — one step past the upper limit."""

    reference_date = date(2029, 6, 15)

    def test_january_2029_is_ineligible(self):
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", age=30)
        self.add_member(screen, "child", age=None, birth_year_month=date(2029, 1, 1))

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestScenario06PregnantNoChildBornYet(TrumpAccountTestCase):
    """Scenario 6: `birth_window` — no member has a birth month in the window.

    26 U.S.C. §6434(e) requires the child's Social Security number with the election, and an
    unborn child has none.
    """

    def test_a_pregnancy_alone_is_ineligible(self):
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age=28, pregnant=True)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestScenario07TwinsAndAnOlderSibling(TrumpAccountTestCase):
    """Scenario 7: `birth_window` — tested per member, and the value counts only those in it."""

    def test_only_the_two_children_in_the_window_are_paid(self):
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", age=32)
        self.add_member(screen, "child", age=None, birth_year_month=date(2026, 6, 1))
        self.add_member(screen, "child", age=None, birth_year_month=date(2026, 6, 1))
        self.add_member(screen, "child", age=None, birth_year_month=date(2022, 5, 1))

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_000)
