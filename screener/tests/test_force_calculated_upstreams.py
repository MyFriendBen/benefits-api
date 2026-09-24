"""A gated upstream is calculated even when its `Program` row says not to display it.

Twenty of the 42 gate edges are strict: `program_eligible` raises when the upstream was not
calculated, and the eligibility loop drops the dependent rather than report it ineligible on
a guess. Four things put a row outside the loop, and none of them is a statement about the
household — `active=False`, a NULL category, `has_calculator=False`, and a referrer's
`remove_programs`. Any one of them silently costs the household every program gating on that
row.

`eligibility_results` now fetches the custom gated upstreams separately, unfiltered, and
calculates them for their result only. `skip` withholds them from the response.

The real calculators are stubbed through `Program.eligibility`, because what is under test is
the loop's bookkeeping — which rows it fetches, which results it keeps, which it publishes —
rather than any program's rule.
"""

from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from programs.framework.base import Eligibility
from programs.framework.gates import force_calculated_codes
from programs.models import Navigator, Program, ProgramCategory, ProgramNavigator
from programs.util import DependencyError, UpstreamAbsentError
from integrations.services.income_limits import Smi
from programs.models import FederalPoveryLimit
from programs.programs.cross_white_label.liheap.co import LeapValueCache
from screener.models import (
    EligibilitySnapshot,
    EnergyCalculatorMember,
    EnergyCalculatorScreen,
    HouseholdMember,
    IncomeStream,
    Screen,
    WhiteLabel,
)
from screener.tests.helpers import seed_program
from screener.views import eligibility_results

# A real force-calculated upstream and a real dependent that gates on it strictly, so the
# codes these assertions turn on are the ones production derives.
UPSTREAM = "cesn_leap"
DEPENDENT = "cesn_eoccip"


def eligible(is_eligible=True, value=1):
    e = Eligibility()
    e.eligible = is_eligible
    e.household_value = value if is_eligible else 0
    return e


class ForceCalculatedUpstreamTestCase(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="CESN", code="cesn", state_code="CO")
        self.category = ProgramCategory.objects.new_program_category(
            white_label="cesn", external_name="energy_savings", icon=""
        )
        self.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="80202", county="Denver County", household_size=1, completed=False
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)

        seed_program(self.white_label, UPSTREAM, DEPENDENT)
        self.upstream = Program.objects.get(white_label=self.white_label, name_abbreviated=UPSTREAM)
        self.dependent = Program.objects.get(white_label=self.white_label, name_abbreviated=DEPENDENT)

        for program in (self.upstream, self.dependent):
            program.active = True
            program.has_calculator = True
            program.category = self.category
            program.year = self.fpl_year
            program.save()

    def withhold_extra(self, code):
        """Seed another force-calculated code and deactivate it, configured like the rest.

        A `year` matters: the FK access in `fake_eligibility` only costs a query when there
        is a row to fetch, so a null one would hide a missing `select_related`.
        """
        seed_program(self.white_label, code)
        program = Program.objects.get(white_label=self.white_label, name_abbreviated=code)
        program.active = False
        program.category = self.category
        program.year = self.fpl_year
        program.save()
        return program

    def run_results(self, calculated=None):
        """Run the loop with every calculator stubbed, recording which rows it ran.

        `calculated` maps a program code to the Eligibility to return, or to an exception
        instance to raise. Anything unlisted returns an eligible result.
        """
        calculated = calculated or {}
        ran = []

        def fake_eligibility(program_self, screen, data, missing_dependencies):
            ran.append(program_self.name_abbreviated)
            # Every force-calculated calculator reads `self.program.year` (the SMI/FPL
            # vintage), so the stub does too. Without that access the query-count test
            # below cannot see a missing `select_related("year")` on the unfiltered fetch.
            program_self.year
            outcome = calculated.get(program_self.name_abbreviated, eligible())
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        with patch.object(Program, "eligibility", fake_eligibility), patch(
            "screener.views.calc_pe_eligibility", return_value={"eligibility": {}, "_pe_data": {}}
        ):
            data, missing_programs, _, _ = eligibility_results(self.screen)

        return {
            "ran": ran,
            "published": sorted(entry["name_abbreviated"] for entry in data),
            "missing_programs": missing_programs,
            "data": data,
        }


class TestTheUpstreamIsCalculatedWhateverItsRowSays(ForceCalculatedUpstreamTestCase):
    def test_an_inactive_upstream_is_still_calculated(self):
        self.upstream.active = False
        self.upstream.save()

        result = self.run_results()

        self.assertIn(UPSTREAM, result["ran"])
        self.assertIn(DEPENDENT, result["published"])

    def test_an_upstream_with_no_category_is_still_calculated(self):
        self.upstream.category = None
        self.upstream.save()

        result = self.run_results()

        self.assertIn(UPSTREAM, result["ran"])
        self.assertIn(DEPENDENT, result["published"])

    def test_an_upstream_flagged_as_having_no_calculator_is_still_calculated(self):
        self.upstream.has_calculator = False
        self.upstream.save()

        result = self.run_results()

        self.assertIn(UPSTREAM, result["ran"])
        self.assertIn(DEPENDENT, result["published"])

    def test_the_dependent_survives_all_four_at_once(self):
        self.upstream.active = False
        self.upstream.category = None
        self.upstream.has_calculator = False
        self.upstream.save()

        result = self.run_results()

        self.assertIn(DEPENDENT, result["published"])
        self.assertFalse(result["missing_programs"])


class TestTheUpstreamIsNotPublished(ForceCalculatedUpstreamTestCase):
    def test_an_inactive_upstream_stays_out_of_the_response(self):
        self.upstream.active = False
        self.upstream.save()

        result = self.run_results()

        self.assertNotIn(UPSTREAM, result["published"])

    def test_it_stays_out_even_when_the_row_is_active_but_was_never_displayable(self):
        """A row removed for a referrer is active; `skip` is what withholds it, not
        `program.active`."""
        self.upstream.category = None
        self.upstream.save()

        result = self.run_results()

        self.assertNotIn(UPSTREAM, result["published"])

    def test_it_writes_no_program_snapshot(self):
        self.upstream.active = False
        self.upstream.save()

        self.run_results()

        snapshot = EligibilitySnapshot.objects.filter(screen=self.screen).latest("submission_date")
        names = list(snapshot.program_snapshots.values_list("name_abbreviated", flat=True))
        self.assertNotIn(UPSTREAM, names)

    def test_a_displayable_upstream_is_published_as_normal(self):
        """Force-calculation adds a second, unfiltered fetch; it must not shadow the row
        the normal query already returned, or an active LEAP would stop being offered."""
        result = self.run_results()

        self.assertIn(UPSTREAM, result["published"])
        self.assertEqual(result["ran"].count(UPSTREAM), 1)


class TestFailureIsNoWorseThanBefore(ForceCalculatedUpstreamTestCase):
    """This row was not being calculated at all before, so adding it must not be able to
    make the response worse than it already was."""

    def test_an_upstream_raising_dependency_error_drops_only_its_dependents(self):
        self.upstream.active = False
        self.upstream.save()

        result = self.run_results({UPSTREAM: DependencyError(), DEPENDENT: UpstreamAbsentError(UPSTREAM)})

        self.assertNotIn(DEPENDENT, result["published"])
        self.assertTrue(result["missing_programs"])

    def test_an_upstream_raising_anything_else_does_not_propagate(self):
        self.upstream.active = False
        self.upstream.save()

        with patch("screener.views.capture_exception"), patch("screener.views.capture_message"):
            result = self.run_results({UPSTREAM: RuntimeError("boom"), DEPENDENT: UpstreamAbsentError(UPSTREAM)})

        self.assertNotIn(DEPENDENT, result["published"])

    def test_a_displayed_program_raising_something_else_still_propagates(self):
        """The broad `except` is scoped to force-calculated rows. A bug in a program the
        household was going to be shown is not something to swallow."""
        with self.assertRaises(RuntimeError):
            self.run_results({DEPENDENT: RuntimeError("boom")})


class TestDroppedProgramsAreRecordedWithAReason(ForceCalculatedUpstreamTestCase):
    """`missing_programs` says only that something was omitted. The reasons are not
    interchangeable, and only one of them is outside our control."""

    def snapshot(self):
        return EligibilitySnapshot.objects.filter(screen=self.screen).latest("submission_date")

    def test_nothing_dropped_records_an_empty_dict(self):
        self.run_results()

        self.assertEqual(self.snapshot().dropped_programs, {})

    def test_a_missing_screener_field_is_distinguished_from_an_absent_upstream(self):
        result = self.run_results({DEPENDENT: DependencyError()})

        self.assertTrue(result["missing_programs"])
        self.assertEqual(
            self.snapshot().dropped_programs,
            {DEPENDENT: EligibilitySnapshot.DROPPED_MISSING_FIELD},
        )

    def test_an_absent_upstream_is_recorded_as_such(self):
        result = self.run_results({DEPENDENT: UpstreamAbsentError(UPSTREAM)})

        self.assertTrue(result["missing_programs"])
        self.assertEqual(
            self.snapshot().dropped_programs,
            {DEPENDENT: EligibilitySnapshot.DROPPED_UPSTREAM_ABSENT},
        )

    def test_a_force_calculated_upstream_erroring_is_recorded(self):
        self.upstream.active = False
        self.upstream.save()

        with patch("screener.views.capture_exception"), patch("screener.views.capture_message"):
            self.run_results({UPSTREAM: RuntimeError("boom"), DEPENDENT: UpstreamAbsentError(UPSTREAM)})

        dropped = self.snapshot().dropped_programs
        self.assertEqual(dropped[UPSTREAM], EligibilitySnapshot.DROPPED_UPSTREAM_ERROR)
        self.assertEqual(dropped[DEPENDENT], EligibilitySnapshot.DROPPED_UPSTREAM_ABSENT)

    def test_a_force_calculated_upstream_is_not_itself_a_missing_program(self):
        """It was never part of the household's results, so its absence is not something to
        warn them about — the dependent reports that for itself."""
        self.upstream.active = False
        self.upstream.save()

        result = self.run_results({UPSTREAM: DependencyError()})

        self.assertNotIn(UPSTREAM, self.snapshot().dropped_programs)
        self.assertFalse(result["missing_programs"])


class TestTheFetchIsScopedToGatedCustomUpstreams(ForceCalculatedUpstreamTestCase):
    def test_an_ungated_inactive_program_is_not_calculated(self):
        """The unfiltered fetch is `name_abbreviated__in=force_calculated_codes()`, not
        "every inactive row"."""
        seed_program(self.white_label, "cesn_ilp")
        ungated = Program.objects.get(white_label=self.white_label, name_abbreviated="cesn_ilp")
        ungated.active = False
        ungated.has_calculator = True
        ungated.category = self.category
        ungated.save()

        result = self.run_results()

        self.assertNotIn("cesn_ilp", result["ran"])
        self.assertNotIn("cesn_ilp", result["published"])

    def test_an_upstream_with_no_row_in_this_white_label_is_simply_absent(self):
        """Deactivation and non-existence look identical to the gate, but only one is
        recoverable — there is no row to construct a calculator from."""
        self.assertIn("il_family_care", force_calculated_codes())
        self.assertFalse(
            Program.objects.filter(white_label=self.white_label, name_abbreviated="il_family_care").exists()
        )

        result = self.run_results()

        self.assertNotIn("il_family_care", result["ran"])


class TestWithheldUpstreamsDoNotReachDisplayConsumers(ForceCalculatedUpstreamTestCase):
    """A withheld upstream stays readable by gates but is invisible to what renders.

    Before force-calculation, an inactive or removed upstream was absent from the
    eligibility map entirely, so a navigator requiring it was filtered out and no category
    cap counted it. Force-calculating it must not change either.
    """

    def setUp(self):
        super().setUp()
        self.navigator = Navigator.objects.new_navigator("cesn", "leap_only_navigator")
        self.navigator.eligibility_programs.set([self.upstream])
        ProgramNavigator.objects.create(program=self.dependent, navigator=self.navigator)

    def navigator_ids(self, result):
        entry = next(e for e in result["data"] if e["name_abbreviated"] == DEPENDENT)
        return [navigator["id"] for navigator in entry["navigators"]]

    def test_a_navigator_requiring_a_withheld_upstream_is_not_shown(self):
        self.upstream.active = False
        self.upstream.save()

        result = self.run_results()

        self.assertIn(UPSTREAM, result["ran"])
        self.assertNotIn(self.navigator.id, self.navigator_ids(result))

    def test_a_navigator_requiring_a_displayed_upstream_is_shown(self):
        result = self.run_results()

        self.assertIn(self.navigator.id, self.navigator_ids(result))

    def test_category_caps_do_not_see_a_withheld_upstream(self):
        self.upstream.active = False
        self.upstream.save()
        seen = []

        class RecordingCapCalculator:
            def __init__(self, eligibility):
                seen.append(set(eligibility))

            def caps(self):
                return []

        with patch("screener.views.ProgramCategoryCapCalculator", RecordingCapCalculator):
            self.run_results()

        self.assertTrue(seen)
        for codes in seen:
            self.assertNotIn(UPSTREAM, codes)
            self.assertIn(DEPENDENT, codes)


class TestTheExtraFetchDoesNotScale(ForceCalculatedUpstreamTestCase):
    """One query for every withheld upstream, not one each.

    The unfiltered fetch is a single `name_abbreviated__in` with `select_related("year")`,
    and a withheld row is skipped before warnings are read. All three are easy to lose —
    dropping the `select_related` gives an N+1 on `Program.year`, which every one of these
    calculators reads — so this pins the property rather than an absolute count that any
    unrelated query would break.
    """

    def withhold(self, *codes):
        for code in codes:
            if code in (UPSTREAM, DEPENDENT):
                program = Program.objects.get(white_label=self.white_label, name_abbreviated=code)
                program.active = False
                program.save()
            else:
                self.withhold_extra(code)

    def queries_for(self, *withheld):
        """Query count for one run, measured from a state where a previous snapshot exists.

        The first run of a screen has no `EligibilitySnapshot` to diff against and so skips
        a query the second run makes. Warming up first is what makes two measurements
        comparable — without it this compares snapshot history, not the fetch.
        """
        self.withhold(*withheld)
        self.run_results()

        with CaptureQueriesContext(connection) as captured:
            self.run_results()

        return list(captured)

    def test_a_second_withheld_upstream_adds_no_queries(self):
        """The property, rather than an absolute count any unrelated query would break.

        A missing `select_related("year")` would add one per withheld row, as would losing
        the `not skip` guard on warning messages or fetching the upstreams individually.
        """
        one = len(self.queries_for(UPSTREAM))
        two = len(self.queries_for("cesn_eoc"))

        self.assertEqual(two, one)

    def test_a_withheld_upstream_costs_no_warning_message_query(self):
        """Warnings are read before the display gate, so the `not skip` guard is the only
        thing keeping a withheld row from querying for messages nobody will render."""
        with_upstream = self.queries_for(UPSTREAM)
        warnings = [q for q in with_upstream if "warning" in q["sql"].lower()]

        self.assertEqual(
            [q for q in warnings if str(self.upstream.id) in q["sql"]],
            [],
        )


class TestARealCalculatorRunsThroughTheUnfilteredPath(TestCase):
    """The rest of this module stubs `Program.eligibility` to test the loop's bookkeeping.

    Nothing there proves a real calculator survives being reached that way — the unfiltered
    fetch carries only `select_related("year")`, and all six force-calculated calculators
    read `self.program.year`. So this runs CESN's LEAP for real, from an inactive row, and
    lets `cesn_eoccip` read the result through its gate.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="CESN", code="cesn", state_code="CO")
        self.category = ProgramCategory.objects.new_program_category(
            white_label="cesn", external_name="energy_savings", icon=""
        )
        self.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="80202",
            county="Denver County",
            household_size=1,
            household_assets=0,
            path="homeowner",
            completed=False,
        )
        self.member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        # Both halves of `energy_calculator` are required: `Screen.missing_fields` reads the
        # screen row and `HouseholdMember.missing_fields` the member one, and either
        # missing makes `cesn_eoccip` uncalculable before its gate is ever reached.
        EnergyCalculatorScreen.objects.create(screen=self.screen, needs_hvac=True)
        EnergyCalculatorMember.objects.create(household_member=self.member)

        seed_program(self.white_label, UPSTREAM, DEPENDENT)
        self.upstream = Program.objects.get(white_label=self.white_label, name_abbreviated=UPSTREAM)
        self.dependent = Program.objects.get(white_label=self.white_label, name_abbreviated=DEPENDENT)
        for program in (self.upstream, self.dependent):
            program.active = True
            program.has_calculator = True
            program.category = self.category
            program.year = self.fpl_year
            program.save()

        # LEAP is deactivated: the state force-calculation exists to survive.
        self.upstream.active = False
        self.upstream.save()

    def set_income(self, monthly):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.member, type="wages", amount=monthly, frequency="monthly"
        )

    def run_results(self):
        # 60% of $50,000 SMI = $30,000/yr, the only condition CESN's LEAP applies.
        smi = {"2025": {"CO": {1: 50_000}}}
        with patch.object(Smi, "get_data", return_value=smi), patch.object(
            LeapValueCache, "get_data", return_value=[]
        ), patch("screener.views.calc_pe_eligibility", return_value={"eligibility": {}, "_pe_data": {}}):
            data, missing_programs, _, _ = eligibility_results(self.screen)

        return {
            # `data` carries ineligible programs too, so presence is not the same as being
            # offered — `eligible` is the assertion that matters for the gate.
            "published": sorted(entry["name_abbreviated"] for entry in data),
            "eligible": sorted(entry["name_abbreviated"] for entry in data if entry["eligible"]),
            "missing_programs": missing_programs,
            "dropped": EligibilitySnapshot.objects.filter(screen=self.screen)
            .latest("submission_date")
            .dropped_programs,
        }

    def test_the_dependent_is_offered_on_a_real_leap_pass(self):
        self.set_income(1_000)  # $12,000/yr, under the limit

        result = self.run_results()

        self.assertIn(DEPENDENT, result["eligible"])
        self.assertNotIn(UPSTREAM, result["published"])
        self.assertEqual(result["dropped"], {})

    def test_the_dependent_is_withheld_on_a_real_leap_fail(self):
        """The negative control: without it, a stubbed-looking pass could come from the
        gate never being evaluated rather than from LEAP's income test."""
        self.set_income(5_000)  # $60,000/yr, over the limit

        result = self.run_results()

        # Still returned, and correctly marked ineligible — which is the point. A gate that
        # could not be evaluated would have dropped it from the response entirely instead.
        self.assertIn(DEPENDENT, result["published"])
        self.assertNotIn(DEPENDENT, result["eligible"])
        self.assertEqual(result["dropped"], {})

    def test_the_upstream_computing_needs_its_year_which_the_fetch_selects(self):
        """`self.program.year.period` keys the SMI table. A row fetched without it raises
        `AttributeError`, which the broad `except` turns into a dropped upstream rather
        than a 500 — so the failure would be silent without this."""
        self.set_income(1_000)
        self.upstream.year = None
        self.upstream.save()

        with patch("screener.views.capture_exception"), patch("screener.views.capture_message"):
            result = self.run_results()

        self.assertEqual(result["dropped"][UPSTREAM], EligibilitySnapshot.DROPPED_UPSTREAM_ERROR)
        self.assertEqual(result["dropped"][DEPENDENT], EligibilitySnapshot.DROPPED_UPSTREAM_ABSENT)
        self.assertNotIn(DEPENDENT, result["published"])
