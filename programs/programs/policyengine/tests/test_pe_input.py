"""
Unit tests for PolicyEngine pe_input function core structure.

These tests verify the pe_input() function correctly generates the PolicyEngine API
request payload structure (household, people, tax_units, marital_units, etc.)
independent of any specific calculator's dependencies.

Calculator-specific dependency tests belong in the state's pe/tests/ directory.
"""

from unittest.mock import patch

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, Expense, IncomeStream
from programs.programs.policyengine.policy_engine import pe_input
from programs.programs.policyengine.calculators.constants import (
    MAIN_TAX_UNIT,
    SECONDARY_TAX_UNIT,
)


class PeInputTestBase(TestCase):
    """Base class with shared test fixtures for pe_input tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data that doesn't change between tests."""
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

    def setUp(self):
        """Set up test screen with household members."""
        # Import here to avoid circular imports at module level
        from programs.programs.tx.pe.spm import TxSnap

        self.calculator_class = TxSnap

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=3,
            household_assets=5000.00,
            completed=False,
        )

        # Head of household - 35 year old, disabled
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            disabled=True,
            student=False,
        )

        # Spouse - 32 year old
        self.spouse = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="spouse",
            age=32,
            disabled=False,
            student=False,
        )

        # Child - 8 year old
        self.child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=8,
            disabled=False,
            student=True,
        )


class TestPeInputHouseholdStructure(PeInputTestBase):
    """Tests for pe_input() household structure generation."""

    def test_returns_valid_household_structure(self):
        """Test that pe_input returns a properly structured household dict."""
        result = pe_input(self.screen, [self.calculator_class])

        # Verify top-level structure
        self.assertIn("household", result)
        household = result["household"]

        # Verify all required units exist
        self.assertIn("people", household)
        self.assertIn("tax_units", household)
        self.assertIn("families", household)
        self.assertIn("households", household)
        self.assertIn("spm_units", household)
        self.assertIn("marital_units", household)

    def test_creates_people_with_member_ids(self):
        """Test that pe_input creates people dict with household member IDs as keys."""
        result = pe_input(self.screen, [self.calculator_class])
        people = result["household"]["people"]

        # Should have 3 people
        self.assertEqual(len(people), 3)

        # Verify all member IDs are present
        head_id = str(self.head.id)
        spouse_id = str(self.spouse.id)
        child_id = str(self.child.id)

        self.assertIn(head_id, people)
        self.assertIn(spouse_id, people)
        self.assertIn(child_id, people)

        # Each person should be a dict
        self.assertIsInstance(people[head_id], dict)
        self.assertIsInstance(people[spouse_id], dict)
        self.assertIsInstance(people[child_id], dict)

    def test_assigns_members_to_family_unit(self):
        """Test that all members are assigned to the family unit."""
        result = pe_input(self.screen, [self.calculator_class])
        family_members = result["household"]["families"]["family"]["members"]

        # All 3 members should be in the family
        self.assertEqual(len(family_members), 3)
        self.assertIn(str(self.head.id), family_members)
        self.assertIn(str(self.spouse.id), family_members)
        self.assertIn(str(self.child.id), family_members)

    def test_assigns_members_to_household_unit(self):
        """Test that all members are assigned to the household unit."""
        result = pe_input(self.screen, [self.calculator_class])
        household_members = result["household"]["households"]["household"]["members"]

        # All 3 members should be in the household
        self.assertEqual(len(household_members), 3)
        self.assertIn(str(self.head.id), household_members)
        self.assertIn(str(self.spouse.id), household_members)
        self.assertIn(str(self.child.id), household_members)

    def test_assigns_members_to_spm_unit(self):
        """Test that all members are assigned to the SPM unit."""
        result = pe_input(self.screen, [self.calculator_class])
        spm_members = result["household"]["spm_units"]["spm_unit"]["members"]

        # All 3 members should be in the SPM unit
        self.assertEqual(len(spm_members), 3)
        self.assertIn(str(self.head.id), spm_members)
        self.assertIn(str(self.spouse.id), spm_members)
        self.assertIn(str(self.child.id), spm_members)

    def test_with_empty_screen_returns_basic_structure(self):
        """Test that pe_input returns valid structure even with no members."""
        empty_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=0,
            completed=False,
        )

        result = pe_input(empty_screen, [self.calculator_class])

        # Should still have household structure
        self.assertIn("household", result)
        household = result["household"]

        # All unit types should exist
        self.assertIn("people", household)
        self.assertIn("tax_units", household)
        self.assertIn("families", household)

        # People should be empty
        self.assertEqual(len(household["people"]), 0)


class TestPeInputTaxUnits(PeInputTestBase):
    """Tests for pe_input() tax unit assignment."""

    def test_creates_main_tax_unit_with_members(self):
        """Test that adults are assigned to the main tax unit."""
        result = pe_input(self.screen, [self.calculator_class])
        tax_units = result["household"]["tax_units"]

        # Main tax unit should exist
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        main_tax_members = tax_units[MAIN_TAX_UNIT]["members"]

        # Head and spouse should be in main tax unit
        self.assertIn(str(self.head.id), main_tax_members)
        self.assertIn(str(self.spouse.id), main_tax_members)
        self.assertIn(str(self.child.id), main_tax_members)

    def test_removes_empty_secondary_tax_unit(self):
        """Test that empty secondary tax unit is removed."""
        result = pe_input(self.screen, [self.calculator_class])
        tax_units = result["household"]["tax_units"]

        # Secondary tax unit should not exist if empty
        self.assertNotIn(SECONDARY_TAX_UNIT, tax_units)

    def test_keeps_secondary_tax_unit_when_has_members(self):
        """Test that secondary tax unit is kept when it has members."""
        # Create an adult child (not in main tax unit)
        adult_child = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="child",
            age=25,
            disabled=False,
            student=False,
        )

        result = pe_input(self.screen, [self.calculator_class])
        tax_units = result["household"]["tax_units"]

        # Secondary tax unit should exist if adult child is not in main tax unit
        if not adult_child.is_in_tax_unit():
            self.assertIn(SECONDARY_TAX_UNIT, tax_units)
            self.assertIn(str(adult_child.id), tax_units[SECONDARY_TAX_UNIT]["members"])


class TestPeInputMaritalUnits(PeInputTestBase):
    """Tests for pe_input() marital unit assignment."""

    def test_creates_marital_unit_for_head_and_spouse(self):
        """Test that married couples are assigned to marital units."""
        result = pe_input(self.screen, [self.calculator_class])
        marital_units = result["household"]["marital_units"]

        # Should have one marital unit for head and spouse
        self.assertEqual(len(marital_units), 1)

        # Marital unit key should be "member_id-member_id"
        marital_unit_key = list(marital_units.keys())[0]
        marital_unit = marital_units[marital_unit_key]

        # Should contain exactly 2 members
        self.assertEqual(len(marital_unit["members"]), 2)

        # Should contain head and spouse IDs (order may vary)
        member_ids = set(marital_unit["members"])
        expected_ids = {str(self.head.id), str(self.spouse.id)}
        self.assertEqual(member_ids, expected_ids)

    def test_single_adult_has_no_marital_unit(self):
        """Test that single adults without a spouse have no marital unit."""
        # Create screen with single adult
        single_screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=1,
            completed=False,
        )
        HouseholdMember.objects.create(
            screen=single_screen,
            relationship="headOfHousehold",
            age=30,
        )

        result = pe_input(single_screen, [self.calculator_class])
        marital_units = result["household"]["marital_units"]

        # Single adults without a spouse should have no marital unit
        self.assertEqual(len(marital_units), 0)


class TestPeInputMultipleCalculators(PeInputTestBase):
    """Tests for pe_input() with multiple calculators."""

    def test_with_multiple_calculators(self):
        """Test that pe_input handles multiple calculator inputs correctly."""
        from programs.programs.federal.pe.spm import SchoolLunch

        result = pe_input(self.screen, [self.calculator_class, SchoolLunch])

        # Should have all dependencies from both calculators
        household = result["household"]
        self.assertIn("people", household)
        self.assertIn("spm_units", household)

        # Verify structure is valid
        self.assertIsInstance(household["people"], dict)
        self.assertIsInstance(household["spm_units"], dict)

    def test_calculator_dependencies_are_merged(self):
        """Test that dependencies from multiple calculators are merged."""
        from programs.programs.tx.pe.member import TxWic

        result = pe_input(self.screen, [self.calculator_class, TxWic])

        # Both SNAP and WIC dependencies should be present
        spm_unit = result["household"]["spm_units"]["spm_unit"]
        people = result["household"]["people"]

        # SNAP adds snap output
        self.assertIn("snap", spm_unit)

        # WIC adds pregnancy/breastfeeding fields to people
        head_id = str(self.head.id)
        self.assertIn("age", people[head_id])


class TestPeInputVersionGating(PeInputTestBase):
    """Tests that version-gated inputs (min_pe_version) are only sent to models that
    support them. meets_ssi_disability_criteria (min 1.715.2) is the canonical case:
    it does not exist in the current model (1.691.1) and 400s the whole request there."""

    def setUp(self):
        super().setUp()
        from programs.programs.federal.pe.member import Ssi

        self.ssi = Ssi
        self.head_id = str(self.head.id)

    def _meets_ssi_field_present(self, version):
        result = pe_input(self.screen, [self.ssi], pe_version=version)
        return "meets_ssi_disability_criteria" in result["household"]["people"][self.head_id]

    # When unpinned (None / "current"), gating resolves what PE's current model is via
    # resolve_unpinned_comparable_version(); mock it so these tests are deterministic and
    # never hit the network. meets_ssi_disability_criteria's floor is (1, 715, 2).
    def _mock_unpinned(self, resolved):
        return patch(
            "programs.programs.policyengine.policy_engine.pe_versions.resolve_unpinned_comparable_version",
            return_value=resolved,
        )

    def test_omitted_when_no_pin_and_current_below_floor(self):
        # Unpinned + PE current resolves below the floor => variable does not exist there.
        with self._mock_unpinned((1, 691, 1)):
            self.assertFalse(self._meets_ssi_field_present(None))

    def test_sent_when_no_pin_and_current_at_or_above_floor(self):
        # Unpinned + PE current resolves at/above the floor => send it (this is the
        # fix: gated inputs activate on an empty pin once current supports them).
        with self._mock_unpinned((1, 732, 0)):
            self.assertTrue(self._meets_ssi_field_present(None))

    def test_omitted_when_no_pin_and_pe_unreachable(self):
        # /versions/us unreachable => resolve returns None => conservative withhold.
        with self._mock_unpinned(None):
            self.assertFalse(self._meets_ssi_field_present(None))

    def test_current_alias_resolves_like_no_pin(self):
        with self._mock_unpinned((1, 732, 0)):
            self.assertTrue(self._meets_ssi_field_present("current"))

    def test_omitted_on_older_pinned_version(self):
        self.assertFalse(self._meets_ssi_field_present("1.691.1"))

    def test_sent_on_supporting_version(self):
        self.assertTrue(self._meets_ssi_field_present("1.715.2"))

    def test_sent_on_newer_version(self):
        self.assertTrue(self._meets_ssi_field_present("1.800.0"))

    def test_sent_on_frontier_alias(self):
        # frontier is the newest released model, so gated inputs are sent without a lookup.
        self.assertTrue(self._meets_ssi_field_present("frontier"))

    def test_ungated_input_always_present(self):
        # A non-gated input (is_disabled) is sent regardless of version. Ssi carries a
        # gated input too, so an unpinned request resolves current — mock it offline.
        with self._mock_unpinned(None):
            result = pe_input(self.screen, [self.ssi], pe_version=None)
        self.assertIn("is_disabled", result["household"]["people"][self.head_id])


class TestVersionSupports(TestCase):
    """Unit tests for the min/max version window logic, covering all three gating
    shapes (new / removed / windowed variable) and the asymmetric unknown-version rule."""

    def setUp(self):
        from programs.programs.policyengine import versions as pe_versions

        self.supports = pe_versions.version_supports
        self.v = pe_versions.to_comparable_pe_version

    def test_ungated_always_supported(self):
        # No bounds => always sent, including on unknown version.
        self.assertTrue(self.supports(None, (), ()))
        self.assertTrue(self.supports(self.v("1.715.2"), (), ()))

    def test_min_only_new_variable(self):
        new = (1, 715, 2)  # added at 1.715.2
        self.assertFalse(self.supports(None, new, ()))  # unknown/current: omit
        self.assertFalse(self.supports(self.v("1.691.1"), new, ()))  # older: omit
        self.assertTrue(self.supports(self.v("1.715.2"), new, ()))  # at floor: send
        self.assertTrue(self.supports(self.v("1.800.0"), new, ()))  # newer: send

    def test_max_only_removed_variable(self):
        # Variable existed through 1.719.999, removed after.
        last = (1, 719, 999)
        self.assertTrue(self.supports(None, (), last))  # unknown/current still has it: send
        self.assertTrue(self.supports(self.v("1.691.1"), (), last))  # older: send
        self.assertTrue(self.supports(self.v("1.719.999"), (), last))  # at ceiling: send
        self.assertFalse(self.supports(self.v("1.720.0"), (), last))  # past removal: omit

    def test_windowed_variable(self):
        # Existed only 1.700.0 .. 1.715.0.
        lo, hi = (1, 700, 0), (1, 715, 0)
        self.assertFalse(self.supports(None, lo, hi))  # unknown fails the floor
        self.assertFalse(self.supports(self.v("1.699.0"), lo, hi))  # below window
        self.assertTrue(self.supports(self.v("1.700.0"), lo, hi))  # at floor
        self.assertTrue(self.supports(self.v("1.710.0"), lo, hi))  # inside
        self.assertTrue(self.supports(self.v("1.715.0"), lo, hi))  # at ceiling
        self.assertFalse(self.supports(self.v("1.715.2"), lo, hi))  # above window

    def test_frontier_alias_satisfies_floor(self):
        self.assertTrue(self.supports(self.v("frontier"), (1, 715, 2), ()))


class TestResolveUnpinnedVersion(TestCase):
    """Unit tests for resolving PE's `current` from /versions/us for input gating
    when there is no pin. Network is always mocked; cache is cleared per test."""

    def setUp(self):
        from programs.programs.policyengine import versions as pe_versions
        from django.core.cache import cache

        self.pe_versions = pe_versions
        cache.delete(pe_versions._PE_VERSIONS_CACHE_KEY)

    def _mock_get(self, *, json_data=None, exc=None, status_ok=True):
        mock_resp = type("R", (), {})()
        mock_resp.json = lambda: json_data
        mock_resp.raise_for_status = (lambda: None) if status_ok else self._raise_http
        if exc is not None:
            return patch(
                "programs.programs.policyengine.versions.requests.get",
                side_effect=exc,
            )
        return patch(
            "programs.programs.policyengine.versions.requests.get",
            return_value=mock_resp,
        )

    @staticmethod
    def _raise_http():
        import requests

        raise requests.HTTPError("500")

    def test_resolves_current_to_tuple(self):
        with self._mock_get(json_data={"current": "1.732.0", "frontier": "1.744.0"}):
            self.assertEqual(self.pe_versions.resolve_unpinned_comparable_version(), (1, 732, 0))

    def test_network_error_returns_none(self):
        import requests

        with self._mock_get(exc=requests.ConnectionError("down")):
            self.assertIsNone(self.pe_versions.resolve_unpinned_comparable_version())

    def test_malformed_payload_returns_none(self):
        with self._mock_get(json_data={"unexpected": "shape"}):
            self.assertIsNone(self.pe_versions.resolve_unpinned_comparable_version())

    def test_result_is_cached(self):
        with self._mock_get(json_data={"current": "1.732.0", "frontier": "1.744.0"}) as mock_get:
            self.pe_versions.resolve_unpinned_comparable_version()
            self.pe_versions.resolve_unpinned_comparable_version()
            self.assertEqual(mock_get.call_count, 1)  # second call served from cache

    def test_failure_not_cached(self):
        import requests

        with self._mock_get(exc=requests.ConnectionError("down")) as mock_get:
            self.pe_versions.resolve_unpinned_comparable_version()
            self.pe_versions.resolve_unpinned_comparable_version()
            self.assertEqual(mock_get.call_count, 2)  # retried, not cached


class TestPeInputReservedOutputSlots(TestCase):
    """A field this request asks PolicyEngine to compute must be sent as None.

    `spm.Snap` is the SNAP calculators' `pe_output` and Head Start's `pe_input`; `spm.Tanf`
    is shaped the same way. Before the guard, a household reporting SNAP had the receipt
    value written into both the annual input period and the SNAP calculator's monthly
    output period, pinning the answer PE was asked for — measured against the live API,
    computed SNAP fell from $3,708/yr to $12/yr.
    """

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

    def setUp(self):
        from programs.models import FederalPoveryLimit, Program
        from programs.programs.tx.pe.member import TxHeadStart
        from programs.programs.tx.pe.spm import TxSnap
        from programs.util import Dependencies

        self.fpl = FederalPoveryLimit.objects.create(year="2025", period="2025")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=2,
            household_assets=0,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=30, disabled=False, student=False
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4, disabled=False, student=False)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=1500, frequency="monthly"
        )

        def program(name, base_program=None):
            p = Program.objects.new_program(self.white_label.code, name)
            p.year = self.fpl
            p.base_program = base_program
            p.save()
            return p

        self.snap_program = program("tx_snap", base_program="snap")
        self.calculators = [
            TxSnap(self.screen, self.snap_program, Dependencies()),
            TxHeadStart(self.screen, program("tx_head_start"), Dependencies()),
        ]
        self.snap_calculator = self.calculators[0]

    def _report_snap(self, monthly_amount=None):
        from screener.models import CurrentBenefit

        CurrentBenefit.objects.create(screen=self.screen, program=self.snap_program)
        if monthly_amount is not None:
            IncomeStream.objects.create(
                screen=self.screen,
                household_member=self.head,
                type="snap",
                amount=monthly_amount,
                frequency="monthly",
            )
        self.screen.invalidate_current_benefits_cache()

    def _snap_block(self):
        payload = pe_input(self.screen, self.calculators)
        return payload["household"]["spm_units"]["spm_unit"]["snap"]

    def test_every_output_slot_is_sent_as_none(self):
        """The general rule, across every program in the request: an output slot no input
        claimed goes out as None. A slot an input *did* claim keeps the reported value —
        see TestPeInputInputOutputCollision."""
        self._report_snap(monthly_amount=200)
        payload = pe_input(self.screen, self.calculators)

        input_slots = {
            (Data.field, calculator.pe_period)
            for calculator in self.calculators
            for Data in calculator.pe_inputs
        }

        for calculator in self.calculators:
            period = getattr(calculator, "pe_output_period", None) or calculator.pe_period
            for Data in calculator.pe_outputs:
                if (Data.field, period) in input_slots:
                    continue
                for sub_unit in payload["household"].get(Data.unit, {}).values():
                    if Data.field in sub_unit and period in sub_unit[Data.field]:
                        self.assertIsNone(
                            sub_unit[Data.field][period],
                            f"{Data.field} at {period} is an output of {type(calculator).__name__} "
                            f"but was sent with a value, which pins PolicyEngine's answer",
                        )

    def test_snap_output_period_reserved_while_input_period_carries_amount(self):
        """The reported annual amount still reaches PE; only the monthly output slot is None."""
        self._report_snap(monthly_amount=200)

        snap = self._snap_block()
        self.assertEqual(snap[self.snap_calculator.pe_period], 2400)  # $200/mo -> annual
        self.assertIsNone(snap[self.snap_calculator.pe_output_period])

    def test_snap_sentinel_when_receipt_reported_without_amount(self):
        """Tile-only receipt still confers categorical eligibility via the sentinel."""
        self._report_snap()

        snap = self._snap_block()
        self.assertEqual(snap[self.snap_calculator.pe_period], 1)
        self.assertIsNone(snap[self.snap_calculator.pe_output_period])

    def test_snap_unset_when_nothing_reported(self):
        snap = self._snap_block()
        self.assertIsNone(snap[self.snap_calculator.pe_period])
        self.assertIsNone(snap[self.snap_calculator.pe_output_period])


class TestPeInputInputOutputCollision(TestCase):
    """When an input and an output claim the *same* (field, period), the reported value wins.

    SNAP is the easy case: its output slot is monthly and inputs write annual, so the two
    never meet. Every other dual-role field is annual on both sides. `member.Ssi` is the SSI
    calculators' `pe_output` (federal `Ssi`, `ks_ssi`, `tx_ssi`, `wa_ssi`) *and* an input of
    `ks_tanf`, `il_aabd` and the Head Start / Early Head Start calculators — all at the
    annual period. Reserving that slot unconditionally sent reported SSI as None, which
    breaks KEESM 2210: `ks_tanf_is_assistance_unit_member` excludes SSI recipients, so
    without the reported amount the unit size inflates and an all-SSI household that should
    be ineligible is shown as eligible (ks/pe/spm.py documents this).
    """

    def setUp(self):
        from programs.models import FederalPoveryLimit, Program
        from programs.programs.ks.pe.member import KsSsi
        from programs.programs.ks.pe.spm import KsTanf
        from programs.util import Dependencies

        self.white_label = WhiteLabel.objects.create(name="Kansas", code="ks", state_code="KS")
        self.fpl = FederalPoveryLimit.objects.create(year="2026", period="2026")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="67202",
            county="Sedgwick County",
            household_size=2,
            household_assets=100,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=40, disabled=True, student=False
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4, disabled=False, student=False)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="sSI", amount=900, frequency="monthly"
        )

        def program(name):
            p = Program.objects.new_program(self.white_label.code, name)
            p.year = self.fpl
            p.save()
            return p

        # ks_ssi claims (ssi, 2026) as its output; ks_tanf supplies it as an input.
        self.ssi_calculator = KsSsi(self.screen, program("ks_ssi"), Dependencies())
        self.tanf_calculator = KsTanf(self.screen, program("ks_tanf"), Dependencies())

    def _ssi_values(self, calculators):
        payload = pe_input(self.screen, calculators)
        period = self.ssi_calculator.pe_period
        return [
            person["ssi"][period] for person in payload["household"]["people"].values() if "ssi" in person
        ]

    def test_reported_ssi_survives_when_the_ssi_program_claims_the_same_slot(self):
        """Both programs in one request: the reporting member's $900/mo reaches PE."""
        values = self._ssi_values([self.ssi_calculator, self.tanf_calculator])

        self.assertIn(10800, values)  # $900/mo -> annual

    def test_order_does_not_matter(self):
        """Precedence comes from the input/output pass, not from calculator ordering."""
        values = self._ssi_values([self.tanf_calculator, self.ssi_calculator])

        self.assertIn(10800, values)

    def test_output_slot_is_none_without_a_consuming_input(self):
        """With no input claiming `ssi`, the SSI program's own output slot is reserved so PE
        computes the amount rather than echoing ours back."""
        values = self._ssi_values([self.ssi_calculator])

        self.assertEqual(values, [None, None])
