"""Structural guards on the program vintage map.

These check that the map is internally coherent and that every claim in it is resolvable.
They deliberately do NOT check the map against the database or the config JSONs -- that is
the environment audit's job, and asserting it here would go red until the correcting
migration lands.

The one exception is `test_fpl_defaults_covers_the_current_calendar_year`, which is the guard
that makes the whole scheme safe: every edition in the map has to be a period `_FPL_DEFAULTS`
defines, so if the constant stops covering the present the map cannot express a current
edition and this suite says so in January rather than in a partner's QA session.
"""

from datetime import date

from django.test import SimpleTestCase

from programs.models import _get_fpl_data
from programs.vintage import PROGRAM_VINTAGE, Basis, Status


class TestProgramVintageMap(SimpleTestCase):
    def test_every_entry_states_a_rule(self):
        """A vintage with no stated reason is the thing this map exists to abolish."""
        for key, vintage in PROGRAM_VINTAGE.items():
            with self.subTest(program=key):
                self.assertTrue(
                    vintage.rule.strip(),
                    f"{key} records an edition with no rule. An edition nobody can explain is "
                    "indistinguishable from drift, which is the defect this map replaces.",
                )

    def test_confirmed_entries_cite_a_source(self):
        """CONFIRMED asserts someone established this. That claim needs a citation."""
        for key, vintage in PROGRAM_VINTAGE.items():
            if vintage.status is not Status.CONFIRMED:
                continue
            with self.subTest(program=key):
                self.assertTrue(
                    vintage.source.strip(),
                    f"{key} is marked CONFIRMED but cites no source. Downgrade it to "
                    "UNVERIFIED or add the statute, notice or validated case it rests on.",
                )

    def test_unverified_entries_do_not_pose_as_researched(self):
        """UNVERIFIED means nobody checked. A source there would overstate what is known."""
        for key, vintage in PROGRAM_VINTAGE.items():
            if vintage.status is not Status.UNVERIFIED:
                continue
            with self.subTest(program=key):
                self.assertFalse(
                    vintage.source.strip(),
                    f"{key} is UNVERIFIED but cites {vintage.source!r}. If the source settles "
                    "the edition, mark it CONFIRMED; if it does not, drop it.",
                )

    def test_every_edition_is_a_period_the_fpl_table_defines(self):
        """`as_dict()` raises a bare KeyError for a period the constant does not define.

        An edition here that the table cannot resolve would be a crash inside eligibility
        calculation for every program pointed at it, not a wrong number.
        """
        defined = set(_get_fpl_data())
        for key, vintage in PROGRAM_VINTAGE.items():
            with self.subTest(program=key):
                self.assertIn(
                    vintage.edition,
                    defined,
                    f"{key} names edition {vintage.edition!r}, which _FPL_DEFAULTS does not "
                    f"define (it has {sorted(defined)}). Add the year to the constant first.",
                )

    def test_editions_are_four_digit_years(self):
        for key, vintage in PROGRAM_VINTAGE.items():
            with self.subTest(program=key):
                self.assertRegex(vintage.edition, r"^\d{4}$")

    def test_keys_are_white_label_and_abbreviation_pairs(self):
        for key in PROGRAM_VINTAGE:
            with self.subTest(program=key):
                self.assertIsInstance(key, tuple)
                self.assertEqual(len(key), 2)
                self.assertTrue(all(isinstance(part, str) and part for part in key))

    def test_both_bases_are_represented(self):
        """A map that had drifted to one basis would mean the distinction had been lost.

        `COVERAGE_YEAR` and `TABLE_EDITION` look identical in the database and mean opposite
        things -- reading one as the other is how a correct row gets "fixed" into a wrong
        one. If either disappears, the reading has collapsed.
        """
        bases = {vintage.basis for vintage in PROGRAM_VINTAGE.values()}

        self.assertEqual(bases, {Basis.COVERAGE_YEAR, Basis.TABLE_EDITION})

    def test_fpl_defaults_covers_the_current_calendar_year(self):
        """The guard that keeps the rest honest.

        Every edition in the map has to be a period the constant defines. If the constant
        stops covering the present, no program can be moved to the current edition and the
        map silently caps out a year behind -- which is the original defect. Failing here in
        January is the cheap way to find out.
        """
        current = str(date.today().year)

        self.assertIn(
            current,
            _get_fpl_data(),
            f"_FPL_DEFAULTS has no {current} poverty guideline. Add it (programs/models.py) "
            "before anything can be moved to the current edition.",
        )
