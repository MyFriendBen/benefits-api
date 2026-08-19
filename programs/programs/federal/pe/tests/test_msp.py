"""
Unit tests for the shared federal Medicare Savings Program PolicyEngine calculator.

States subclass ``Msp`` to append their own state code and their Medicaid inputs. The
state code is load-bearing rather than boilerplate: it resolves
``gov.hhs.medicare.savings_programs.eligibility.asset.applies``, which decides whether
the resource test applies at all. A state that dropped it would silently stop screening
assets and report over-resourced households as eligible.

That makes the federal wiring a cross-state contract. The tests below assert it once
against every registered subclass rather than per state, so:

* every state's MSP is covered even where its own file has no tests (TX had none), and
* a newly added state inherits the whole contract the moment it is registered.

A state file therefore only needs to prove what is genuinely state-specific: that it
registers under the expected slug and sends its own state code.

The eligibility math, the QMB/SLMB/QI tiering, and the premium value itself live in
PolicyEngine (``msp``, ``msp_category``, ``msp_eligible``) and are covered by
PolicyEngine's own test suite, not duplicated here. Each state's spec pins the dollar
value and the tier boundaries for that state.
"""

from django.test import TestCase

from programs.programs.federal.pe.member import Medicaid, Msp
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import member
from programs.framework.pe_dependencies.household import StateCode
from integrations.clients.policyengine.registry import all_calculators, all_member_calculators


def _registered_subclasses(base: type) -> dict[str, type]:
    """Every calculator registered under a program slug that subclasses ``base``."""
    return {
        slug: calc for slug, calc in all_member_calculators.items() if isinstance(calc, type) and issubclass(calc, base)
    }


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
        self.assertNotIn(Msp, all_member_calculators.values())


class TestRegisteredMspSubclassContract(TestCase):
    """
    The cross-state contract, asserted against every registered subclass of ``Msp``.

    These are the assertions that were previously copy-pasted into each state's
    ``test_member.py``. Holding them here means a new state is covered as soon as it is
    registered, and a state that quietly drops a federal input fails here rather than
    passing because nobody wrote that state's copy of the test.
    """

    def setUp(self):
        self.subclasses = _registered_subclasses(Msp)

    def test_states_are_registered(self):
        """A guard on the discovery itself: if the registry stopped exposing these,
        every other test in this class would vacuously pass over an empty dict."""
        self.assertGreaterEqual(len(self.subclasses), 1)

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
        for slug, calc in self.subclasses.items():
            with self.subTest(slug=slug):
                self.assertIn(member.MspCategory, calc.pe_outputs)
                self.assertIn(member.Msp, calc.pe_outputs)

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
