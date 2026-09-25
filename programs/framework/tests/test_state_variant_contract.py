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
- It reads the variable its base reads — the same ``pe_name`` and ``pe_outputs`` — unless
  it is listed in ``READS_OWN_VARIABLE`` with the variable it reads instead, as each
  state's TANF does.

The two state-code rules hold for every calculator that belongs to a state, variant or
not — ``IlAabd`` and ``KsChip`` subclass a generic PolicyEngine base but are just as
state-bound. What a calculator adds beyond that is state policy, and is tested beside it.
"""

from django.test import SimpleTestCase

from integrations.clients.policyengine.registry import all_calculators
from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.pe_dependencies.household import StateCode
from programs.programs.cross_white_label.medicaid.base import Medicaid
import programs.framework.pe_dependencies as dependency

STATES = {"co", "nc", "ma", "il", "tx", "wa", "ks", "mo"}

#: State programs that send no state code of their own. They are listed rather than
#: exempted by rule so a new one is a decision, not an accident: PolicyEngine takes
#: `state_code` once per household, so these read it from whichever program on the same
#: screen supplies it.
SENDS_NO_STATE_CODE = {"ma_eaedc", "ma_ssp"}

#: Variants that read something other than their base's PolicyEngine variable, and what
#: they read: ``(pe_name, pe_outputs)``. Every other variant reads its base's.
READS_OWN_VARIABLE = {
    "co_tanf": ("co_tanf", [dependency.spm.CoTanf]),
    "il_tanf": ("il_tanf", [dependency.spm.IlTanf]),
    "ks_tanf": ("ks_tanf", [dependency.spm.KsTanf]),
    "mo_tanf": ("mo_tanf", [dependency.spm.MoTanf]),
    "nc_tanf": ("nc_tanf", [dependency.spm.NcTanf]),
    "tx_tanf": ("tx_tanf", [dependency.spm.TxTanf]),
    "wa_tanf": ("wa_tanf", [dependency.spm.WaTanf]),
    # MassHealth also reads CHIP's category, to report a child it covers as CHIP.
    "ma_mass_health": ("medicaid", [*Medicaid.pe_outputs, dependency.member.ChipCategory]),
}


def state_of(calculator: type):
    """The state a calculator belongs to, read from where it is defined.

    ``white_labels/<state>/...`` names it directly. Under ``cross_white_label`` the module
    is named for the state — ``snap/tx.py``, ``eitc/co_coeitc.py``, ``eitc/ks_federal.py``.
    """
    parts = calculator.__module__.split(".")
    if parts[2] == "white_labels":
        return parts[3] if parts[3] in STATES else None

    prefix = parts[-1].split("_")[0]
    return prefix if prefix in STATES else None


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
            if state_of(calculator) is None or state_codes(calculator) or code in SENDS_NO_STATE_CODE:
                continue
            with self.subTest(program=code):
                base = variants.get(code)
                self.assertIsNotNone(base, f"{calculator.__name__} sends no state code")
                self.assertEqual(
                    list(calculator.pe_inputs),
                    list(base.pe_inputs),
                    f"{calculator.__name__} changes {base.__name__}'s inputs but sends no state code",
                )

    def test_the_exceptions_still_need_to_be_exceptions(self):
        """A listed program that starts sending its state code should leave the list."""
        for code in SENDS_NO_STATE_CODE:
            with self.subTest(program=code):
                self.assertEqual(state_codes(all_calculators[code]), set())

    def test_a_variant_reads_its_bases_variable_unless_listed(self):
        for code, calculator, base in state_variants():
            with self.subTest(program=code):
                expected = READS_OWN_VARIABLE.get(code, (base.pe_name, list(base.pe_outputs)))
                self.assertEqual((calculator.pe_name, list(calculator.pe_outputs)), expected)

    def test_every_listed_variable_belongs_to_a_variant(self):
        """A stale entry would otherwise sit here asserting nothing."""
        variants = {code for code, _, _ in state_variants()}
        self.assertEqual(set(READS_OWN_VARIABLE) - variants, set())
