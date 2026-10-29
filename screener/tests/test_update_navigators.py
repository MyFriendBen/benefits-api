"""
Tests for navigator filtering logic in update_navigators() (MFB-666).

Covers the filtering steps:
  0. filter_by_white_label     - tested by TestNavigatorWhiteLabelFilter
  1. filter_by_county          - tested by TestNavigatorCountyFilter
  2. filter_by_required_programs_eligibility - tested by TestNavigatorEligibilityProgramsFilter
  3. referrer_prioritization   - tested by TestNavigatorReferrerPrioritization
  4. update_navigators      - tested by TestUpdateNavigators

"""

from django.test import TestCase

from programs.models import County, Navigator, Program, ProgramNavigator, Referrer
from screener.models import WhiteLabel
from screener.navigators import (
    filter_by_county,
    filter_by_white_label,
    filter_by_required_programs_eligibility,
    referrer_prioritization,
)
from screener.views import update_navigators


class _Eligible:
    eligible = True


class _Ineligible:
    eligible = False


class TestNavigatorWhiteLabelFilter(TestCase):
    """A federal program shows `federal` navigators and the screen's white label's; other
    programs are not filtered by white label."""

    @classmethod
    def setUpTestData(cls):
        cls.federal, _ = WhiteLabel.objects.get_or_create(code="federal", defaults={"name": "Federal"})
        cls.co = WhiteLabel.objects.create(name="CO Test", code="co_test", state_code="CO")
        cls.ks = WhiteLabel.objects.create(name="KS Test", code="ks_test", state_code="KS")
        cls.federal_program = Program.objects.new_program(white_label="federal", name_abbreviated="federal_test")
        cls.co_program = Program.objects.new_program(white_label="co_test", name_abbreviated="co_test_program")
        cls.federal_nav = Navigator.objects.new_navigator("federal", "federal_nav_test")
        cls.co_nav = Navigator.objects.new_navigator("co_test", "co_nav_test")
        cls.ks_nav = Navigator.objects.new_navigator("ks_test", "ks_nav_test")

    def test_federal_program_keeps_federal_and_screen_white_label_navigators(self):
        result = filter_by_white_label([self.federal_nav, self.co_nav, self.ks_nav], self.federal_program, self.co)
        self.assertEqual(result, [self.federal_nav, self.co_nav])

    def test_federal_program_drops_another_states_navigator(self):
        result = filter_by_white_label([self.co_nav], self.federal_program, self.ks)
        self.assertEqual(result, [])

    def test_federal_program_keeps_navigator_from_another_white_label_in_the_screens_state(self):
        """A `cesn` screen in CO sees navigators owned by `co`, and the reverse."""
        cesn = WhiteLabel.objects.create(name="CESN Test", code="cesn_test", state_code="CO")
        result = filter_by_white_label([self.federal_nav, self.co_nav, self.ks_nav], self.federal_program, cesn)
        self.assertEqual(result, [self.federal_nav, self.co_nav])

    def test_federal_program_on_a_white_label_with_no_state_keeps_only_federal_and_its_own(self):
        no_state = WhiteLabel.objects.create(name="No State Test", code="no_state_test")
        own = Navigator.objects.new_navigator("no_state_test", "no_state_nav_test")
        WhiteLabel.objects.create(name="Other No State", code="other_no_state_test")
        other = Navigator.objects.new_navigator("other_no_state_test", "other_no_state_nav_test")
        result = filter_by_white_label([self.federal_nav, self.co_nav, own, other], self.federal_program, no_state)
        self.assertEqual(result, [self.federal_nav, own])

    def test_state_program_keeps_navigator_owned_by_another_white_label(self):
        """Navigators are shared by external_name, so a state program can use one another
        white label imported first."""
        result = filter_by_white_label([self.co_nav, self.ks_nav], self.co_program, self.co)
        self.assertEqual(result, [self.co_nav, self.ks_nav])

    def test_county_match_in_another_state_does_not_leak(self):
        """The reason county scoping can't do this: the same county name exists in two
        states, and the county filter matches on the name alone."""
        ProgramNavigator.objects.create(program=self.federal_program, navigator=self.co_nav)
        self.co_nav.counties.set([County.objects.create(name="Jackson County", white_label=self.co)])
        data = [{"navigators": []}]
        update_navigators(
            eligible_program_data=[(self.federal_program, 0)],
            program_eligibility={},
            data=data,
            screen_white_label=self.ks,
            screen_county="Jackson County",
            referrer=None,
        )
        self.assertEqual(data[0]["navigators"], [])
        self.assertEqual(filter_by_county([self.co_nav], "Jackson County"), [self.co_nav])


class TestNavigatorCountyFilter(TestCase):
    """Unit tests for navigator county filtering."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="NC Test", code="nc_test", state_code="CO")
        cls.durham_county = County.objects.create(name="Durham County", white_label=cls.white_label)
        cls.davie_county = County.objects.create(name="Davie County", white_label=cls.white_label)
        cls.statewide_nav = Navigator.objects.new_navigator("nc_test", "statewide_nav_test")
        cls.durham_nav = Navigator.objects.new_navigator("nc_test", "durham_nav_test")
        cls.davie_nav = Navigator.objects.new_navigator("nc_test", "davie_nav_test")

    def setUp(self):
        # Reset county M2M before each test so tests are independent.
        self.statewide_nav.counties.clear()
        self.durham_nav.counties.set([self.durham_county])
        self.davie_nav.counties.set([self.davie_county])

    def test_no_counties_matches_any_screen_county(self):
        """Navigator with no county restrictions is always included regardless of screen county."""
        result = filter_by_county([self.statewide_nav], "Durham")
        self.assertIn(self.statewide_nav, result)

    def test_no_counties_matches_none_screen_county(self):
        """Navigator with no county restrictions is included even when screen county is None."""
        result = filter_by_county([self.statewide_nav], None)
        self.assertIn(self.statewide_nav, result)

    def test_matching_county_includes_navigator(self):
        """Navigator is included when screen county appears as a substring of its county name."""
        result = filter_by_county([self.durham_nav], "Durham")
        self.assertIn(self.durham_nav, result)

    def test_non_matching_county_excludes_navigator(self):
        """Navigator is excluded when screen county does not match any of its counties."""
        result = filter_by_county([self.durham_nav], "Davie")
        self.assertNotIn(self.durham_nav, result)

    def test_none_screen_county_excludes_county_restricted_navigator(self):
        """Navigator with county restrictions is excluded when screen county is None."""
        result = filter_by_county([self.durham_nav], None)
        self.assertNotIn(self.durham_nav, result)

    def test_mixed_navigators_filtered_independently(self):
        """Statewide and county-specific navigators are evaluated independently."""
        result = filter_by_county([self.statewide_nav, self.durham_nav, self.davie_nav], "Durham")
        self.assertIn(self.statewide_nav, result)
        self.assertIn(self.durham_nav, result)
        self.assertNotIn(self.davie_nav, result)


class TestNavigatorEligibilityProgramsFilter(TestCase):
    """Unit tests for navigator eligibility_programs filtering."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="NC Test", code="nc_test", state_code="NC")
        cls.medicare_savings = Program.objects.new_program(
            white_label="nc_test", name_abbreviated="nc_medicare_savings"
        )
        cls.snap = Program.objects.new_program(white_label="nc_test", name_abbreviated="nc_snap")
        cls.duke_bec = Navigator.objects.new_navigator("nc_test", "duke_bec_test")
        cls.general_nav = Navigator.objects.new_navigator("nc_test", "general_nav_test")

    def setUp(self):
        # Reset eligibility_programs before each test so tests are independent.
        self.duke_bec.eligibility_programs.set([self.medicare_savings])
        self.general_nav.eligibility_programs.clear()

    def test_no_required_programs_always_shown(self):
        """Navigator with no eligibility_programs shows regardless of household eligibility."""
        result = filter_by_required_programs_eligibility([self.general_nav], {})
        self.assertIn(self.general_nav, result)

    def test_required_program_eligible_shows_navigator(self):
        """Navigator appears when household qualifies for all required programs."""
        program_eligibility = {"nc_medicare_savings": _Eligible()}
        result = filter_by_required_programs_eligibility([self.duke_bec], program_eligibility)
        self.assertIn(self.duke_bec, result)

    def test_required_program_ineligible_hides_navigator(self):
        """Navigator hidden when household does not qualify for a required program."""
        program_eligibility = {"nc_medicare_savings": _Ineligible()}
        result = filter_by_required_programs_eligibility([self.duke_bec], program_eligibility)
        self.assertNotIn(self.duke_bec, result)

    def test_required_program_missing_hides_navigator(self):
        """Navigator hidden when required program has not been calculated yet."""
        result = filter_by_required_programs_eligibility([self.duke_bec], {})
        self.assertNotIn(self.duke_bec, result)

    def test_all_required_programs_must_be_eligible(self):
        """Navigator hidden when only a subset of required programs are eligible."""
        self.duke_bec.eligibility_programs.add(self.snap)

        program_eligibility = {
            "nc_medicare_savings": _Eligible(),
            "nc_snap": _Ineligible(),
        }
        result = filter_by_required_programs_eligibility([self.duke_bec], program_eligibility)
        self.assertNotIn(self.duke_bec, result)

    def test_all_required_programs_eligible_shows_navigator(self):
        """Navigator shown when every required program is eligible."""
        self.duke_bec.eligibility_programs.add(self.snap)

        program_eligibility = {
            "nc_medicare_savings": _Eligible(),
            "nc_snap": _Eligible(),
        }
        result = filter_by_required_programs_eligibility([self.duke_bec], program_eligibility)
        self.assertIn(self.duke_bec, result)

    def test_mixed_navigators_filtered_independently(self):
        """Each navigator is evaluated independently against its own required programs."""
        program_eligibility = {"nc_medicare_savings": _Ineligible()}
        result = filter_by_required_programs_eligibility([self.duke_bec, self.general_nav], program_eligibility)

        self.assertNotIn(self.duke_bec, result)
        self.assertIn(self.general_nav, result)


class TestNavigatorReferrerPrioritization(TestCase):
    """Unit tests for navigator referrer prioritization."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="IL Test", code="il_test", state_code="IL")
        cls.nav_a = Navigator.objects.new_navigator("il_test", "nav_a_test")
        cls.nav_b = Navigator.objects.new_navigator("il_test", "nav_b_test")
        cls.nav_c = Navigator.objects.new_navigator("il_test", "nav_c_test")
        cls.referrer = Referrer.objects.create(
            white_label=cls.white_label,
            referrer_code="partner_test",
            name="Test Partner",
        )

    def setUp(self):
        # Reset primary_navigators before each test so tests are independent.
        self.referrer.primary_navigators.clear()

    def test_no_primary_navigators_returns_full_eligibility_list(self):
        """When the referrer has no primary navigators, the full eligibility_filtered list is returned."""
        eligibility_filtered = [self.nav_a, self.nav_b]
        result = referrer_prioritization(eligibility_filtered, primary_navigators=[])
        self.assertEqual(result, eligibility_filtered)

    def test_overlapping_primary_navigators_returns_only_overlap(self):
        """When primary navigators overlap with eligibility_filtered, only the overlap is returned."""
        eligibility_filtered = [self.nav_a, self.nav_b]
        primary_navigators = [self.nav_b, self.nav_c]
        result = referrer_prioritization(eligibility_filtered, primary_navigators)
        self.assertEqual(result, [self.nav_b])
        self.assertNotIn(self.nav_a, result)
        self.assertNotIn(self.nav_c, result)

    def test_no_overlap_falls_back_to_full_eligibility_list(self):
        """When no primary navigator passes eligibility filtering, the full list is returned as fallback."""
        eligibility_filtered = [self.nav_a, self.nav_b]
        primary_navigators = [self.nav_c]
        result = referrer_prioritization(eligibility_filtered, primary_navigators)
        self.assertEqual(result, eligibility_filtered)

    def test_primary_navigators_subset_returns_matching_subset(self):
        """When primary navigators are a subset of eligibility_filtered, only that subset is returned."""
        eligibility_filtered = [self.nav_a, self.nav_b, self.nav_c]
        primary_navigators = [self.nav_a, self.nav_c]
        result = referrer_prioritization(eligibility_filtered, primary_navigators)
        self.assertIn(self.nav_a, result)
        self.assertIn(self.nav_c, result)
        self.assertNotIn(self.nav_b, result)

    def test_primary_navigators_order_preserved_from_primary_list(self):
        """The overlap is returned in primary_navigators iteration order, not eligibility_filtered order."""
        eligibility_filtered = [self.nav_a, self.nav_b, self.nav_c]
        # primary_navigators lists nav_c before nav_a
        primary_navigators = [self.nav_c, self.nav_a]
        result = referrer_prioritization(eligibility_filtered, primary_navigators)
        self.assertEqual(result, [self.nav_c, self.nav_a])


class TestUpdateNavigators(TestCase):
    """Integration tests for update_navigators() — verifies the full pipeline:
    county filter → eligibility filter → referrer prioritization → data population."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="TX Test", code="tx_test", state_code="TX")
        cls.program = Program.objects.new_program(white_label="tx_test", name_abbreviated="tx_snap")
        cls.dallas_county = County.objects.create(name="Dallas County", white_label=cls.white_label)
        cls.statewide_nav = Navigator.objects.new_navigator("tx_test", "tx_statewide_nav_test")
        cls.dallas_nav = Navigator.objects.new_navigator("tx_test", "tx_dallas_nav_test")
        cls.referrer = Referrer.objects.create(
            white_label=cls.white_label,
            referrer_code="tx_partner_test",
            name="TX Partner",
        )
        ProgramNavigator.objects.create(program=cls.program, navigator=cls.statewide_nav)
        ProgramNavigator.objects.create(program=cls.program, navigator=cls.dallas_nav)

    def setUp(self):
        self.statewide_nav.counties.clear()
        self.dallas_nav.counties.set([self.dallas_county])
        self.statewide_nav.eligibility_programs.clear()
        self.dallas_nav.eligibility_programs.clear()
        self.referrer.primary_navigators.clear()

    def _run(self, screen_county, program_eligibility=None, referrer=None):
        data = [{"navigators": []}]
        update_navigators(
            eligible_program_data=[(self.program, 0)],
            program_eligibility=program_eligibility or {},
            data=data,
            screen_white_label=self.white_label,
            screen_county=screen_county,
            referrer=referrer,
        )
        return [n["id"] for n in data[0]["navigators"]]

    def test_statewide_nav_shown_for_any_county(self):
        """Navigator with no county restriction appears regardless of screen county."""
        ids = self._run(screen_county="Dallas")
        self.assertIn(self.statewide_nav.id, ids)

    def test_county_nav_shown_for_matching_county(self):
        """Navigator restricted to Dallas appears when screen county is Dallas."""
        ids = self._run(screen_county="Dallas")
        self.assertIn(self.dallas_nav.id, ids)

    def test_county_nav_hidden_for_non_matching_county(self):
        """Navigator restricted to Dallas is excluded when screen county differs."""
        ids = self._run(screen_county="Houston")
        self.assertNotIn(self.dallas_nav.id, ids)

    def test_referrer_primary_nav_takes_priority(self):
        """When referrer has a primary navigator that passes filters, only it is returned."""
        self.referrer.primary_navigators.set([self.statewide_nav])
        ids = self._run(screen_county="Dallas", referrer=self.referrer)
        self.assertIn(self.statewide_nav.id, ids)
        self.assertNotIn(self.dallas_nav.id, ids)

    def test_referrer_falls_back_when_no_primary_nav_passes(self):
        """When no primary navigator passes county/eligibility filters, all filtered navigators are returned."""
        self.referrer.primary_navigators.set([self.dallas_nav])
        ids = self._run(screen_county="Houston", referrer=self.referrer)
        self.assertIn(self.statewide_nav.id, ids)

    def test_data_navigators_field_is_populated(self):
        """update_navigators populates data in place; county-restricted navigators excluded when screen_county is None."""
        data = [{"navigators": []}]
        update_navigators(
            eligible_program_data=[(self.program, 0)],
            program_eligibility={},
            data=data,
            screen_white_label=self.white_label,
            screen_county=None,
            referrer=None,
        )
        navigators = data[0]["navigators"]
        self.assertEqual(len(navigators), 1)
        self.assertEqual(navigators[0]["id"], self.statewide_nav.id)
