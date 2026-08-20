from screener.models import Screen, HouseholdMember
from programs.util import Dependencies, DependencyError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from programs.models import Program


class MemberEligibility:
    def __init__(self, member: HouseholdMember) -> None:
        self.member = member
        self.eligible = True
        self.value: int = 0

    def condition(self, passed: bool):
        """
        Set eligibility to False if the condition does not pass
        """
        if not passed:
            self.eligible = False


class Eligibility:
    def __init__(self):
        self.eligible: bool = True
        self.pass_messages = []
        self.fail_messages = []
        self.eligible_members: list[MemberEligibility] = []
        self.household_value: int = 0

    def condition(self, passed: bool, message=None):
        """
        Uses a condition to update the pass fail messages and eligibility.
        """

        if message is None:
            if not passed:
                self.eligible = False
            return

        if passed:
            self.passed(message)
        else:
            self.failed(message)

    def failed(self, msg):
        """
        Mark eligibility as failed and add a message to `fail_messages`
        """
        self.eligible = False
        self.fail_messages.append(msg)

    def passed(self, msg):
        """
        Add a message to `pass_messages`
        """
        self.pass_messages.append(msg)

    def add_member_eligibility(self, member_eligibility: MemberEligibility):
        """
        Store a members eligibility
        """
        self.eligible_members.append(member_eligibility)

    @property
    def value(self) -> int:
        """
        The total value of the household and each member
        """
        total = self.household_value

        for member in self.eligible_members:
            total += member.value

        return total


class ProgramCalculator:
    """
    Base class for all Programs

    Every subclass declares one of two things about itself:

    - ``program_code`` — the ``Program.name_abbreviated`` of the row it backs.
    - ``abstract=True`` in the class definition — it exists to be subclassed and
      backs no row of its own.

    Declaring neither raises when the registry is built. A class may declare a code
    *and* be subclassed: ``Snap`` backs the ``snap`` row and is inherited by seven
    states, so being a base and being a program are not mutually exclusive.
    """

    #: Whether this class declared ``abstract=True``. Set on every subclass, so it
    #: is a fact about that class rather than something it inherits: subclassing an
    #: abstract base does not make you abstract. ``MaHeadStart(HeadStart)`` is a real
    #: program even though ``HeadStart`` is a base.
    _abstract = True

    def __init_subclass__(cls, abstract: bool = False, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # Assigned unconditionally, which is what stops inheritance: a subclass that
        # says nothing gets False here rather than reading its parent's True.
        cls._abstract = abstract

    dependencies = tuple()
    amount = 0
    member_amount = 0

    def __init__(
        self, screen: Screen, program: "Program", data: dict[str, Eligibility], missing_dependencies: Dependencies
    ):
        self.screen = screen
        self.program = program
        self.data = data
        self.missing_dependencies = missing_dependencies

    def eligible(self) -> Eligibility:
        """
        Combine the eligibility for the household and the members
        """

        e = Eligibility()

        one_member_eligible = False
        for member in self.screen.household_members.all():
            member_eligibility = MemberEligibility(member)
            self.member_eligible(member_eligibility)
            e.add_member_eligibility(member_eligibility)

            if member_eligibility.eligible:
                one_member_eligible = True

        e.condition(one_member_eligible)

        # calculate the household eligibility last so that,
        # it has access to the member eligibility
        self.household_eligible(e)

        return e

    def household_eligible(self, e: Eligibility):
        """
        Updates the eligibility object with the household eligibility
        """
        pass

    def member_eligible(self, e: MemberEligibility):
        """
        Updates the eligibility object with the member eligibility
        """
        pass

    def value(self, e: Eligibility):
        """
        Update the eligibility with household and member values
        """
        if not e.eligible:
            return

        e.household_value = self.household_value()

        for member_eligibility in e.eligible_members:
            if member_eligibility.eligible:
                member_value = self.member_value(member_eligibility.member)
                member_eligibility.value = member_value

    def household_value(self) -> int:
        """
        Return the value of the program for the household
        """
        return self.amount

    def member_value(self, member: HouseholdMember) -> int:
        """
        An eligible household members eligibility
        """
        return self.member_amount

    def calc(self) -> Eligibility:
        """
        Calculate the eligibility and value for a screen
        """
        if not self.can_calc():
            raise DependencyError()

        eligibility = self.eligible()

        self.value(eligibility)

        return eligibility

    def program_eligible(self, program_code: str) -> bool:
        """
        Whether the household is eligible for ``program_code``, another program this one
        gates on. Callers name the program, so the dependency is visible in the file that
        has it.

        ``self.data`` holds only the programs already calculated, so this relies on
        `screener.views.CALC_ORDER` listing ``program_code`` first. An absent key means
        "not calculated", which is a different answer from "calculated, and not eligible" —
        so it raises instead of returning False. ``DependencyError`` is what the
        eligibility loop already catches for an uncalculable program, so the dependent
        program is left out of the results rather than reported ineligible on a guess.
        """
        if program_code not in self.data:
            raise DependencyError()

        return self.data[program_code].eligible

    def any_program_eligible(self, program_codes) -> bool:
        """
        Whether the household is eligible for any of ``program_codes``.

        A presumptive-eligibility list asks "does this household already qualify for one of
        these?", so it stops at the first yes and treats a program that was not calculated
        as one this household does not have. Requiring the whole list to be present would
        couple the caller to every sibling being active: one deactivated row would raise and
        drop the caller from results, even when an earlier program in the list already
        answered yes.

        Only for a list the caller must *qualify* through. Treating absence as "no" is the
        conservative reading there — the household loses a way in it may not have had. On an
        *exclusion* it is the permissive one: absence would read as "not eligible for the
        thing that disqualifies them", so the program is offered to someone who should have
        been screened out. Use `program_eligible` and let it raise for those, which is why
        `cesn_energy_ebt` and `cesn_eoccip` gate on `cesn_leap` strictly.
        """
        for program_code in program_codes:
            entry = self.data.get(program_code)
            if entry is not None and entry.eligible:
                return True

        return False

    def member_program_eligible(self, program_code: str, member: HouseholdMember) -> bool:
        """
        Whether `member` is eligible for ``program_code``, another program this one gates
        on at member rather than household scope.

        Same contract as `program_eligible`: an absent key means "not calculated", which is
        a different answer from "calculated, and not eligible", so it raises. A member with
        no entry in the upstream's results is not eligible for it — the upstream records a
        verdict for every member it evaluated, so a gap means it did not consider them.
        """
        if program_code not in self.data:
            raise DependencyError()

        for member_eligibility in self.data[program_code].eligible_members:
            if member_eligibility.member.id == member.id:
                return member_eligibility.eligible

        return False

    def can_calc(self):
        """
        Returns whether or not the program can be calculated with the missing dependencies
        """
        return not self.missing_dependencies.has(*self.dependencies)
