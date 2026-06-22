from programs.models import Program
from programs.programs.policyengine.calculators.constants import ALL_TAX_UNITS
from programs.util import Dependencies, DependencyError
from screener.models import HouseholdMember, Screen
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from .dependencies.base import PolicyEngineScreenInput
from typing import List
from ..engines import Sim


class PolicyEngineCalulator(ProgramCalculator):
    """
    Base class for all Policy Engine programs
    """

    pe_inputs: List[type[PolicyEngineScreenInput]] = []
    pe_outputs: List[type[PolicyEngineScreenInput]] = []

    pe_name = ""
    pe_category = ""
    pe_sub_category = ""

    def __init__(self, screen: Screen, program: "Program", missing_dependencies: Dependencies) -> None:
        self.screen = screen
        self.program = program
        self.missing_dependencies = missing_dependencies
        self._sim = None

    def set_engine(self, sim: Sim) -> None:
        self._sim = sim

    def eligible(self) -> Eligibility:
        e = super().eligible()

        e.eligible = e.value > 0

        return e

    def household_eligible(self, e: Eligibility) -> None:
        household_value = self.household_value()

        e.household_value = household_value

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        member_value = self.member_value(member)

        e.value = member_value
        e.condition(member_value > 0)

    def household_value(self):
        return int(self.get_variable())

    def calc(self) -> Eligibility:
        if not self.can_calc():
            raise DependencyError()

        eligibility = self.eligible()

        return eligibility

    @property
    def pe_period(self) -> str:
        if self.program.year is None:
            raise Exception(f"the period is not configured for: {self.pe_name}")

        return self.program.year.period

    @property
    def sim(self) -> Sim:
        if self._sim is None:
            raise Exception("Engine is not configured")

        return self._sim

    def get_variable(self):
        """
        Return value of the default variable
        """
        return self.sim.value(self.pe_category, self.pe_sub_category, self.pe_name, self.pe_period)

    def get_tax_variable(self, unit: str):
        return self.sim.value(self.pe_category, unit, self.pe_name, self.pe_period)

    def get_dependency_value(self, dependency: PolicyEngineScreenInput):
        return self.sim.value(dependency.unit, dependency.sub_unit, dependency.field, self.pe_period)

    def can_calc(self):
        for input in self.pe_inputs:
            if self.missing_dependencies.has(*input.dependencies):
                return False

        return super().can_calc()


class PolicyEngineSpmCalulator(PolicyEngineCalulator):
    pe_category = "spm_units"
    pe_sub_category = "spm_unit"


class PolicyEngineTaxUnitCalulator(PolicyEngineCalulator):
    pe_category = "tax_units"

    def household_value(self):
        total = 0
        for unit in ALL_TAX_UNITS:
            total += self.tax_unit_value(unit)
        return total

    def tax_unit_value(self, unit: str):
        try:
            return int(self.get_tax_variable(unit))
        except KeyError:
            return 0  # if the second tax unit does not exist


class PolicyEngineMembersCalculator(PolicyEngineCalulator):
    pe_category = "people"

    def household_value(self) -> int:
        return 0

    def member_value(self, member: HouseholdMember):
        return self.get_member_variable(member.id)

    def get_member_variable(self, member_id: int):
        return self.sim.value(self.pe_category, str(member_id), self.pe_name, self.pe_period)

    def get_member_dependency_value(self, dependency: PolicyEngineScreenInput, member_id: int):
        return self.sim.value(dependency.unit, str(member_id), dependency.field, self.pe_period)
