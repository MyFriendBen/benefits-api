"""
Unit tests for the shared federal Medicare Savings Program PolicyEngine calculator.

States subclass ``Msp`` to append their own state code and Medicaid inputs. The state
code resolves ``gov.hhs.medicare.savings_programs.eligibility.asset.applies``, which
decides whether the resource test applies at all — a state that dropped it would
silently stop screening assets and report over-resourced households as eligible.

The federal wiring is therefore a cross-state contract, asserted here once against every
registered subclass so that a state is covered the moment it is registered. A state file
only needs to prove what is state-specific: that it registers under the expected slug and
sends its own state code.

Eligibility, the QMB/SLMB/QI tiering and the premium value live in PolicyEngine and are
covered by its test suite. Each state's spec pins the dollar value and tier boundaries.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.programs.federal.pe.member import Medicaid, Msp
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import member
from programs.framework.pe_dependencies.household import StateCode
from programs.framework.pe_dependencies.payload import pe_input
from integrations.clients.policyengine.registry import all_calculators
from screener.models import HouseholdMember, Insurance, Screen, WhiteLabel


def _registered_subclasses(base: type) -> dict[str, type]:
    """Every calculator registered under a program slug that subclasses ``base``."""
    return {slug: calc for slug, calc in all_calculators.items() if isinstance(calc, type) and issubclass(calc, base)}


def _state_codes(calculator: type) -> set[type]:
    """
    The distinct state codes a calculator sends.

    A set rather than a list because a state's Medicaid input bundle may already carry
    that state's code, so composing ``*Msp.pe_inputs`` with ``*XxMedicaid.pe_inputs``
    can list the same class twice. The payload builder keys by field name, so a repeat
    is inert — what matters is that exactly one *distinct* state is named.
    """
    return {dep for dep in calculator.pe_inputs if isinstance(dep, type) and issubclass(dep, StateCode)}


class TestFederalMsp(TestCase):
    """The federal base class itself."""

    def test_is_a_member_calculator(self):
        self.assertTrue(issubclass(Msp, PolicyEngineMembersCalculator))

    def test_reads_the_person_level_pe_category(self):
        """MSP is per-person: two Medicare-enrolled spouses each get their own premium."""
        self.assertEqual(Msp.pe_category, "people")

    def test_pe_name_is_msp(self):
        self.assertEqual(Msp.pe_name, "msp")

    def test_pe_outputs_request_category_and_value(self):
        """The category drives QMB/SLMB/QI tiering; the value is the displayed amount."""
        self.assertIn(member.MspCategory, Msp.pe_outputs)
        self.assertIn(member.Msp, Msp.pe_outputs)

    def test_pe_inputs_include_medicare_enrollment_and_age(self):
        """The two gates on entry: MSP only helps with Medicare costs."""
        self.assertIn(member.IsMedicareEligibleDependency, Msp.pe_inputs)
        self.assertIn(member.AgeDependency, Msp.pe_inputs)

    def test_pe_inputs_include_quarters_of_coverage(self):
        """
        Regression guard on the value. Without it PolicyEngine does not assume
        premium-free Part A and adds a Part A premium on top of Part B, inflating every
        state's figure past what its spec asserts.
        """
        self.assertIn(member.MedicareQuartersOfCoverageDependency, Msp.pe_inputs)

    def test_federal_class_carries_no_state_code(self):
        """The base is state-agnostic; the code is each subclass's contribution."""
        self.assertEqual(_state_codes(Msp), set())

    def test_is_not_registered_directly(self):
        """Unlike Ctc/Eitc, MSP is never registered bare — the asset test needs a state."""
        self.assertNotIn(Msp, all_calculators.values())


class TestRegisteredMspSubclassContract(TestCase):
    """
    The cross-state contract, asserted against every registered subclass of ``Msp``.

    Holding these here means a state that quietly drops a federal input fails, rather
    than passing because nobody wrote that state's copy of the test.
    """

    def setUp(self):
        self.subclasses = _registered_subclasses(Msp)

    def test_states_are_registered(self):
        """
        A guard on the discovery itself. Every other test here loops over
        ``self.subclasses``, so a state that stopped being registered would take its
        coverage with it and leave the rest of the class passing on the states that
        remain.

        Pinned to the exact expected set rather than a minimum count, so both losing a
        state and gaining one are deliberate edits to this line.
        """
        self.assertEqual(
            set(self.subclasses),
            {"il_msp", "ks_medicare_savings", "mo_medicare_savings", "tx_medicare_savings_program"},
        )

    def test_registered_in_the_global_registry(self):
        """A calculator missing from the registry never runs — screener/views.py
        iterates it to decide which programs to evaluate."""
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                self.assertIs(all_calculators[slug], calc)

    def test_pe_category_is_inherited_unchanged(self):
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                self.assertEqual(calc.pe_category, "people")

    def test_pe_name_is_inherited_unchanged(self):
        """States vary in *who* qualifies, never in which PE variable is read."""
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                self.assertEqual(calc.pe_name, "msp")

    def test_pe_outputs_are_inherited_unchanged(self):
        """Equality, not membership: a state that added or swapped an output would still
        contain the two federal ones, so containment would not catch it."""
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                self.assertEqual(list(calc.pe_outputs), list(Msp.pe_outputs))

    def test_no_federal_input_is_dropped(self):
        """A subclass appends; it must never subtract. Dropping
        ``MedicareQuartersOfCoverageDependency`` inflates the value, dropping
        ``IsMedicareEligibleDependency`` removes the entry gate."""
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                missing = set(Msp.pe_inputs) - set(calc.pe_inputs)
                self.assertEqual(missing, set(), f"{slug} drops {[d.__name__ for d in missing]}")

    def test_sends_the_medicaid_input_set(self):
        """
        Two things depend on it: QI excludes anyone PolicyEngine finds Medicaid-eligible,
        and the asset test reads ``ssi_countable_resources`` from this bundle. Without it
        QI would never exclude, and the resource test would see $0 and pass everyone.

        Asserted on the shared federal ``Medicaid`` inputs, which a state's own Medicaid
        subclass carries by the same no-dropping rule tested above.
        """
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                missing = set(Medicaid.pe_inputs) - set(calc.pe_inputs)
                self.assertEqual(missing, set(), f"{slug} omits {[d.__name__ for d in missing]}")

    def test_sends_exactly_one_state_code(self):
        """The state code resolves whether the resource test applies. Sending none
        leaves it unresolved; naming two states is ambiguous."""
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                codes = _state_codes(calc)
                self.assertEqual(len(codes), 1, f"{slug} state codes: {sorted(c.__name__ for c in codes)}")

    def test_state_code_matches_the_slug(self):
        """Guards the copy-paste failure this pattern invites: a state cloned from
        another and left sending the source state's code would resolve the wrong
        state's asset-test parameter while looking correctly registered."""
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                self.assertEqual(next(iter(_state_codes(calc))).state.lower(), slug.split("_", 1)[0])

    def test_adds_nothing_beyond_the_state_code_and_medicaid_inputs(self):
        """
        A subclass's inputs are exactly the federal set, its Medicaid bundle, and its
        state code. Anything further is a state-variance claim that MSP's federal income
        floor says does not exist.

        Expressed as a set difference rather than a count so that adding a federal input
        updates every state at once instead of failing N state tests.
        """
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                extra = set(calc.pe_inputs) - set(Msp.pe_inputs) - set(Medicaid.pe_inputs) - _state_codes(calc)
                self.assertEqual(extra, set(), f"{slug} adds {sorted(d.__name__ for d in extra)}")

    def test_no_subclass_overrides_member_value(self):
        """The value is PolicyEngine's premium figure, taken as-is. Overriding
        ``member_value`` would introduce state variance the tier says does not exist."""
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                self.assertIs(calc.member_value, PolicyEngineMembersCalculator.member_value)


class TestRegisteredMspPayloadContract(TestCase):
    """
    What each registered MSP subclass serializes into the PolicyEngine payload.

    The contract above asserts the dependencies are *declared*; this asserts they
    *arrive*. The two can diverge — a version-gated dependency, or one whose field the
    payload builder drops, is declared but never sent — so the fields every MSP scenario
    turns on are pinned against a real Screen rather than inferred from ``pe_inputs``.

    Run per state, because each state's screen resolves its own state code.
    """

    PERIOD = "2026"

    def _screen_for(self, state_code: str):
        white_label, _ = WhiteLabel.objects.get_or_create(
            code=state_code.lower(),
            defaults={"name": state_code, "state_code": state_code},
        )
        screen = Screen.objects.create(
            white_label=white_label,
            agree_to_tos=True,
            is_test=True,
            completed=False,
            household_size=1,
            household_assets=3_000,
        )
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=71)
        Insurance.objects.create(household_member=head, medicare=True)
        return screen, head

    def _payload_for(self, calculator: type, screen: Screen):
        program = Mock()
        program.year.period = self.PERIOD
        return pe_input(screen, [calculator(screen, program, screen.missing_fields())])

    def _each_state(self):
        for slug, calc in _registered_subclasses(Msp).items():
            state = next(iter(_state_codes(calc))).state
            screen, head = self._screen_for(state)
            yield slug, calc, state, screen, head

    def test_sends_the_state_code(self):
        """The asset-test-applies parameter resolves off this; without it the resource
        test silently does not apply."""
        for slug, calc, state, screen, _ in self._each_state():
            with self.subTest(slug=slug):
                household = self._payload_for(calc, screen)["household"]["households"]["household"]
                self.assertIn(state, household["state_code"].values())

    def test_sends_the_msp_eligibility_inputs(self):
        """The per-member fields the QMB/SLMB/QI determination reads."""
        for slug, calc, _, screen, head in self._each_state():
            with self.subTest(slug=slug):
                person = self._payload_for(calc, screen)["household"]["people"][str(head.id)]
                for field in (
                    "age",
                    "is_medicare_eligible",
                    "ssi_earned_income",
                    "ssi_unearned_income",
                    "ssi_countable_resources",
                    "medicare_quarters_of_coverage",
                ):
                    self.assertIn(field, person, f"{slug} omits {field}")

    def test_sends_household_assets_for_the_asset_test(self):
        """Reported assets must reach PolicyEngine, or an over-resourced household passes
        the resource test on $0."""
        for slug, calc, _, screen, _ in self._each_state():
            with self.subTest(slug=slug):
                spm_unit = self._payload_for(calc, screen)["household"]["spm_units"]["spm_unit"]
                self.assertEqual(spm_unit["spm_unit_cash_assets"], {self.PERIOD: 3_000})

    def test_assumes_premium_free_part_a(self):
        """40 quarters — ~99% of beneficiaries — which zeroes the Part A premium. Without
        it PolicyEngine adds a Part A premium and every state's value inflates."""
        for slug, calc, _, screen, head in self._each_state():
            with self.subTest(slug=slug):
                person = self._payload_for(calc, screen)["household"]["people"][str(head.id)]
                self.assertEqual(person["medicare_quarters_of_coverage"], {self.PERIOD: 40})

    def test_requests_the_msp_output(self):
        for slug, calc, _, screen, head in self._each_state():
            with self.subTest(slug=slug):
                person = self._payload_for(calc, screen)["household"]["people"][str(head.id)]
                self.assertIn("msp", person)

    def test_sends_the_medicaid_determination_inputs(self):
        """
        QI is barred for anyone eligible for full Medicaid. PolicyEngine *derives* that
        flag rather than accepting a reported value: it appears in the payload as a
        requested output (``None``), not as an input we set. What each state must supply
        is the evidence behind it — the income, resource and categorical facts PE needs
        to make the determination. Without them the QI exclusion cannot bind.
        """
        for slug, calc, _, screen, head in self._each_state():
            with self.subTest(slug=slug):
                person = self._payload_for(calc, screen)["household"]["people"][str(head.id)]
                for field in (
                    "is_pregnant",
                    "is_disabled",
                    "employment_income",
                    "social_security",
                    "ssi",
                    "receives_ssi",
                    "takes_up_ssi_if_eligible",
                    "ssi_countable_resources",
                ):
                    self.assertIn(field, person, f"{slug} omits {field}")
                self.assertEqual(person["is_medicaid_eligible"], {self.PERIOD: None})
