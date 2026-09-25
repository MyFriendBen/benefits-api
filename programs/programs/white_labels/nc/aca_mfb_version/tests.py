"""Tests for ACASubsidiesNC's county premium lookup.

member_value() used to raise KeyError for an unknown county. It now returns 0, which
the frontend filters out via its `value > 0` check -- so the program vanishes from
results with no error anywhere. The lookup must therefore report the miss.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from programs.models import FederalPoveryLimit
from programs.programs.white_labels.nc.aca_mfb_version.calculator import ACACache, ACASubsidiesNC


class TestACACacheProcess(SimpleTestCase):
    def setUp(self):
        self.cache = ACACache()

    def test_parses_county_rows(self):
        self.assertEqual(self.cache._process([["Wake", "1,234.50"]]), {"Wake County": 1234.50})

    def test_skips_short_rows(self):
        self.assertEqual(self.cache._process([["Wake"]]), {})

    def test_skips_unparseable_values(self):
        self.assertEqual(self.cache._process([["Wake", "n/a"]]), {})

    def test_keeps_good_rows_alongside_bad(self):
        result = self.cache._process([["Wake", "n/a"], ["Durham", "999"]])

        self.assertEqual(result, {"Durham County": 999.0})


class TestACASubsidiesNCMemberValue(SimpleTestCase):
    def _calculator(self, county):
        calc = ACASubsidiesNC.__new__(ACASubsidiesNC)
        calc.screen = type("Screen", (), {"county": county})()
        return calc

    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_known_county_returns_annualised_value(self, _get_data):
        self.assertEqual(self._calculator("Wake County").member_value(None), 1200.0)

    @patch("programs.programs.white_labels.nc.aca_mfb_version.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_unknown_county_returns_zero(self, _get_data, _capture):
        self.assertEqual(self._calculator("Nowhere County").member_value(None), 0)

    @patch("programs.programs.white_labels.nc.aca_mfb_version.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_unknown_county_is_reported(self, _get_data, capture):
        self._calculator("Nowhere County").member_value(None)

        capture.assert_called_once()
        self.assertIn("Nowhere County", capture.call_args.args[0])

    @patch("programs.programs.white_labels.nc.aca_mfb_version.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={})
    def test_empty_sheet_cache_is_reported(self, _get_data, capture):
        """The Redis-down case: get_data() falls back to {} and every county misses."""
        self.assertEqual(self._calculator("Wake County").member_value(None), 0)
        capture.assert_called_once()

    @patch("programs.programs.white_labels.nc.aca_mfb_version.calculator.capture_message")
    @patch.object(ACACache, "get_data", return_value={"Wake County": 100.0})
    def test_known_county_reports_nothing(self, _get_data, capture):
        self._calculator("Wake County").member_value(None)

        self.assertFalse(capture.called)


class TestACASubsidiesNCFplEdition(SimpleTestCase):
    """The income band must come from the PRIOR year's poverty guideline.

    26 U.S.C. 36B judges a coverage year against the guideline in effect when its open
    enrollment opened. The PolicyEngine-backed ACA programs get that lag applied inside
    PolicyEngine; this calculator reads the table itself, so the lag has to be here.

    Without it every band is one edition too generous -- at 400% FPL for a household of
    one that is $1,240/yr of income wrongly treated as eligible.
    """

    def _calculator(self, period):
        calc = ACASubsidiesNC.__new__(ACASubsidiesNC)
        calc.program = type("Program", (), {"year": FederalPoveryLimit(year=period, period=period)})()
        return calc

    def test_coverage_year_uses_the_prior_years_guideline(self):
        """2026 coverage is judged against the 2025 guideline: $15,650, not $15,960."""
        self.assertEqual(self._calculator("2026")._fpl_edition().period, "2025")
        self.assertEqual(self._calculator("2026")._fpl_edition().get_limit(1), 15_650)

    def test_the_lag_follows_the_configured_coverage_year(self):
        """Rolling the program forward moves the edition with it, with no constant to edit."""
        self.assertEqual(self._calculator("2025")._fpl_edition().get_limit(1), 15_060)

    def test_income_band_is_four_times_the_prior_guideline(self):
        """The 400% band for a household of one at 2026 coverage: 4 x $15,650."""
        calc = self._calculator("2026")
        calc.screen = type("Screen", (), {"household_size": 1})()

        band = int(calc._fpl_edition().get_limit(1) * ACASubsidiesNC.percent_of_fpl)

        self.assertEqual(band, 62_600)
        # The un-lagged band, which this test exists to keep us off.
        self.assertNotEqual(band, 63_840)

    def test_sizes_past_the_defined_table_extrapolate_rather_than_raise(self):
        """as_dict()[size] raised KeyError past 8; get_limit() adds the per-person amount."""
        edition = self._calculator("2026")._fpl_edition()

        self.assertEqual(edition.get_limit(9), edition.get_limit(8) + 5_500)

    def test_unresolvable_prior_edition_falls_back_to_the_configured_one(self):
        """2023 is the oldest edition defined, so 2023 coverage has no prior to fall back on.

        Banding a year too generously beats raising, which would remove the program from
        North Carolina's results entirely.
        """
        self.assertEqual(self._calculator("2023")._fpl_edition().period, "2023")

    def test_non_numeric_period_falls_back_to_the_configured_edition(self):
        """`period` is free text, so a typo reaches here rather than being rejected."""
        calc = self._calculator("not-a-year")

        self.assertEqual(calc._fpl_edition().period, "not-a-year")

    def test_missing_coverage_year_raises_with_the_program_named(self):
        """No configured year means nothing to lag from, so there is no sane fallback.

        Raising here names the misconfigured program; letting None through would surface
        as an AttributeError inside get_limit() several frames away.
        """
        calc = ACASubsidiesNC.__new__(ACASubsidiesNC)
        calc.program = type("Program", (), {"year": None})()

        with self.assertRaises(ValueError) as caught:
            calc._fpl_edition()

        self.assertIn("nc_aca_mfb_version", str(caught.exception))
