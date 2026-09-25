"""The contract every state variant of a PolicyEngine program keeps with its base.

A state variant — ``CoLifeline``, ``TxSnap``, ``KsTanf`` — subclasses a federal
calculator under ``cross_white_label/<program>/`` and adds what its state needs. Four
things hold for all of them, and are asserted here once over the registry rather than
restated in a test file per state:

- It keeps every input its base sends. A variant may swap one for a subclass —
  ``MaSnap`` sends ``MaTotalHoursWorkedDependency`` in place of the federal hours class —
  but dropping one silently changes what PolicyEngine computes from.
- A state code it sends is its own. A copied ``TxStateCodeDependency`` in a Kansas class
  computes Texas rules for Kansas households, and nothing else fails.
- It sends its state code unless it is a federal passthrough: a class that only relabels
  a federal credit for one white label (``TxEitc``, ``KsCdccFederal``) and sends exactly
  its base's inputs, because PolicyEngine reads no state for it.
- It reads its base's variable or its own state's. Each state's TANF reads ``<state>_tanf``
  in place of the federal ``tanf_if_takes_up``; MassHealth reads the federal ``medicaid``
  and requests CHIP's category as well. A variable named for another state is a copy.

The two state-code rules hold for every calculator that belongs to a state, variant or
not — ``IlAabd`` and ``KsChip`` subclass a generic PolicyEngine base but are just as
state-bound. What a calculator adds beyond that is state policy, and is tested beside it.

A calculator's state comes from where it is filed, the layout the tree is organized by:
``white_labels/<white label>/`` or ``cross_white_label/<program>/<state>.py``, with the
federal class in ``base.py``. A calculator filed anywhere else fails here rather than being
taken for a federal one.
"""

from django.test import SimpleTestCase

from configuration.white_labels import white_label_config
from integrations.clients.policyengine.registry import all_calculators
from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.pe_dependencies.household import StateCode

#: Every state we can send PolicyEngine, one per `StateCode` subclass in `household.py`.
STATES = {dep.state.lower() for dep in StateCode.__subclasses__()}


def state_of(calculator: type):
    """The state a calculator belongs to, or None for a federal one.

    ``white_labels/<code>/`` is a white label's own programs, and belongs to that state when
    the white label is one — ``cesn`` is a Colorado sub-brand with no PolicyEngine programs
    of its own. ``white_labels/federal/`` belongs to no state. Under ``cross_white_label``,
    ``base.py`` holds the federal class and every other module is named for its state —
    ``snap/tx.py``, ``eitc/co_coeitc.py``, ``eitc/ks_federal.py``.
    """
    parts = calculator.__module__.split(".")

    if parts[2] == "white_labels":
        directory = parts[3]
        if directory == "federal":
            return None
        if directory not in white_label_config:
            raise LookupError(
                f"{calculator.__name__} is filed under white_labels/{directory}/, which is no white label"
            )
        return directory if directory in STATES else None

    module = parts[-1]
    if module == "base":
        return None
    prefix = module.split("_")[0]
    if prefix not in STATES:
        raise LookupError(
            f"{calculator.__name__} is defined in {module}.py, which names no state; a state variant's "
            "module starts with its state, and the federal class lives in base.py"
        )
    return prefix


def state_codes(calculator: type) -> set:
    return {dep.state for dep in calculator.pe_inputs if issubclass(dep, StateCode)}


def state_variants():
    """Each registered calculator that specializes a ``cross_white_label`` base for one state."""
    for code, calculator in sorted(all_calculators.items()):
        base = calculator.__mro__[1]
        if (
            state_of(calculator)
            and issubclass(base, PolicyEngineCalulator)
            and base.__module__.startswith("programs.programs.cross_white_label")
        ):
            yield code, calculator, base


class StateVariantContractTests(SimpleTestCase):
    def test_every_calculator_is_filed_where_its_state_can_be_read(self):
        for code, calculator in sorted(all_calculators.items()):
            with self.subTest(program=code):
                state_of(calculator)

    def test_the_walk_finds_the_variants(self):
        """Guards the rest: an empty walk would pass every assertion below."""
        self.assertGreater(len(list(state_variants())), 50)

    def test_every_base_input_is_kept_or_specialized(self):
        for code, calculator, base in state_variants():
            for dep in base.pe_inputs:
                with self.subTest(program=code, dependency=dep.__name__):
                    self.assertTrue(
                        any(issubclass(sent, dep) for sent in calculator.pe_inputs),
                        f"{calculator.__name__} drops {dep.__name__}, which {base.__name__} sends",
                    )

    def test_a_state_code_sent_is_the_calculators_own(self):
        for code, calculator in sorted(all_calculators.items()):
            state = state_of(calculator)
            with self.subTest(program=code):
                sent = state_codes(calculator)
                if state is None:
                    self.assertEqual(sent, set(), f"{calculator.__name__} belongs to no state")
                elif sent:
                    self.assertEqual(sent, {state.upper()})

    def test_a_state_calculator_sends_its_state_code_unless_it_is_a_federal_passthrough(self):
        variants = {code: base for code, _, base in state_variants()}

        for code, calculator in sorted(all_calculators.items()):
            if state_of(calculator) is None or state_codes(calculator):
                continue
            with self.subTest(program=code):
                base = variants.get(code)
                self.assertIsNotNone(base, f"{calculator.__name__} sends no state code")
                self.assertEqual(
                    list(calculator.pe_inputs),
                    list(base.pe_inputs),
                    f"{calculator.__name__} changes {base.__name__}'s inputs but sends no state code",
                )

    def test_a_variant_reads_its_bases_variable_or_its_own_states(self):
        for code, calculator, base in state_variants():
            with self.subTest(program=code):
                if calculator.pe_name != base.pe_name:
                    self.assertTrue(
                        calculator.pe_name.startswith(f"{state_of(calculator)}_"),
                        f"{calculator.__name__} reads {calculator.pe_name!r}, which is neither "
                        f"{base.__name__}'s variable nor named for its own state",
                    )

    def test_a_variant_keeps_its_bases_outputs_unless_it_reads_its_own_variable(self):
        for code, calculator, base in state_variants():
            with self.subTest(program=code):
                if calculator.pe_name == base.pe_name:
                    for output in base.pe_outputs:
                        self.assertIn(
                            output,
                            calculator.pe_outputs,
                            f"{calculator.__name__} drops {output.__name__}, which {base.__name__} reads",
                        )
                else:
                    self.assertIn(
                        calculator.pe_name,
                        {output.field for output in calculator.pe_outputs},
                        f"{calculator.__name__} reads {calculator.pe_name!r} without requesting it",
                    )
