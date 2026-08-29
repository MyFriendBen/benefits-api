"""
ConfigurableCalculator: a protocol-only adapter for PE-backed programs, per
DECISIONS.md D-012.

Deliberately does NOT import or inherit from PolicyEngineCalulator or
ProgramCalculator. Grepping policy_engine.py/views.py/registry.py confirmed
the real orchestration path (screener/views.py -> calc_pe_eligibility ->
pe_input()/all_eligibility()) is 100% duck-typed -- the only issubclass()
calls anywhere in policy_engine.py check a *dependency* class, never the
calculator -- so this class only needs to expose the exact attribute/method
surface those functions actually read:

    pe_inputs, pe_outputs, pe_period, pe_output_period, can_calc(),
    set_engine(sim), calc(), and a 3-arg __init__(screen, program,
    missing_dependencies) matching the real call site
    (screener/views.py:424).

config/benefit_data are bound onto the instance by CalculatorFactory at
*registration* time (see factories/calculator_factory.py), passed as
keyword-only constructor args, since the real call site only ever supplies
the 3 positional args and has no slot for anything else.

The eligible()/household_eligible()/member_eligible() loop below is an
intentional reimplementation of ProgramCalculator.eligible()
(programs/programs/calc.py) and PolicyEngineCalulator.eligible()
(policyengine/calculators/base.py) -- not inherited, since inheriting either
would reintroduce the coupling this class exists to avoid, or mismatch on
constructor arity (ProgramCalculator takes a 4th `data` arg unused here).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from programs.programs.calc import Eligibility, MemberEligibility
from programs.programs.config.loader import ConfigLayer
from programs.programs.data.loader import DataLayer
from programs.programs.policyengine.client import PolicyEngineClient
from programs.programs.policyengine.engines import Sim
from programs.util import Dependencies, DependencyError
from screener.models import HouseholdMember, Screen

if TYPE_CHECKING:
    from programs.models import Program


class ConfigurableCalculator:
    dependencies: tuple = tuple()  # ProgramCalculator.can_calc()'s own-dependency analog

    def __init__(
        self,
        screen: Screen,
        program: "Program",
        missing_dependencies: Dependencies,
        *,
        config: ConfigLayer,
        benefit_data: Optional[DataLayer] = None,
    ):
        self.screen = screen
        self.program = program
        self.missing_dependencies = missing_dependencies
        self.config = config
        self.benefit_data = benefit_data
        self._sim: Optional[Sim] = None
        self._client: Optional[PolicyEngineClient] = None

    # ---- duck-typed orchestration surface (pe_input()/all_eligibility()) ----

    @property
    def pe_inputs(self) -> list:
        return self.config.pe_inputs

    @property
    def pe_outputs(self) -> list:
        return self.config.pe_outputs

    @property
    def pe_period(self) -> str:
        if self.program.year is None:
            raise Exception(f"the period is not configured for: {self.config.pe_name}")
        return self.program.year.period

    @property
    def pe_output_period(self) -> str:
        # policy_engine.py gates use of this on hasattr(program,
        # "pe_output_period") -- reproduces Snap's real min-period-vs-
        # output-period split (pe_period_month is null for every non-SNAP
        # config today) generically, via AttributeError, with no SNAP-only
        # subclass.
        if self.config.pe_period_month is None:
            raise AttributeError("pe_output_period")
        return f"{self.pe_period}-{self.config.pe_period_month}"

    def can_calc(self) -> bool:
        for input_cls in self.pe_inputs:
            if self.missing_dependencies.has(*input_cls.dependencies):
                return False
        return not self.missing_dependencies.has(*self.dependencies)

    def set_engine(self, sim: Sim) -> None:
        self._sim = sim
        self._client = PolicyEngineClient(sim, self.pe_period)

    @property
    def client(self) -> PolicyEngineClient:
        if self._client is None:
            raise Exception("Engine is not configured")
        return self._client

    def calc(self) -> Eligibility:
        if not self.can_calc():
            raise DependencyError()
        return self.eligible()

    # ---- eligibility loop (reimplements calc.py/PolicyEngineCalulator's, not inherited) ----

    def eligible(self) -> Eligibility:
        e = Eligibility()
        one_member_eligible = False
        for member in self.screen.household_members.all():
            member_eligibility = MemberEligibility(member)
            self.member_eligible(member_eligibility)
            e.add_member_eligibility(member_eligibility)
            if member_eligibility.eligible:
                one_member_eligible = True
        e.condition(one_member_eligible)
        self.household_eligible(e)
        e.eligible = e.value > 0
        return e

    def household_eligible(self, e: Eligibility) -> None:
        e.household_value = self.household_value()

    def member_eligible(self, e: MemberEligibility) -> None:
        value = self.member_value(e.member)
        e.value = value
        e.condition(value > 0)

    # ---- composition logic: reads config/data, calls PolicyEngineClient ----

    def household_value(self) -> int:
        """Pure pass-through only (D-000's SNAP/TANF shape). Known, flagged
        gap: reads at pe_period, not pe_output_period, so this does not
        reproduce Snap's real monthly->annual *12 conversion -- see
        ROADMAP.md Phase 3 non-goals. category_amounts (benefit_data)-driven
        lookup logic is also out of scope; benefit_data is bound and
        available for a future subclass."""
        if self.config.pe_entity == "spm_unit":
            return self.client.get_spm_value(self.config.pe_name)
        if self.config.pe_entity == "household":
            value = self.client.get_household_value("households", "household", self.config.pe_name)
            return int(value) if isinstance(value, (int, float)) else 0
        return 0  # person/tax_unit value comes from member_value()/a future override

    def member_value(self, member: HouseholdMember) -> int:
        if self.config.pe_entity != "person":
            return 0
        value = self.client.get_member_value(member.id, self.config.pe_name)
        return int(value) if isinstance(value, (int, float)) else 0
