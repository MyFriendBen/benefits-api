from screener.models import Screen, HouseholdMember
from programs.util import Dependencies, DependencyError, UpstreamAbsentError
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

    #: Upstream program codes this calculator reads through `program_eligible` or
    #: `member_program_eligible`. Those raise when the upstream was not calculated, so
    #: `can_calc` also requires the upstream's own screener fields — see
    #: `programs.framework.gates`. Declaring the code here rather than only passing it to
    #: the accessor is what makes the gate graph readable from production code.
    gates_on: tuple = tuple()

    #: Upstream program codes read through `any_program_eligible`, which treats an absent
    #: upstream as "no". Deliberately does *not* contribute to `can_calc`: a tolerant gate
    #: loses one route to eligibility rather than the whole program, so requiring the
    #: upstream's fields would turn a graceful degradation into a dropped program.
    gates_on_any: tuple = tuple()

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

        An upstream can be missing for three reasons, and this raises for all of them: its
        row is inactive, its own ``can_calc`` failed on a missing screener field, or — for a
        PolicyEngine upstream — the PolicyEngine call failed and returned no eligibility at
        all. The last case drops fifteen gates across fourteen programs at once, so a PE
        outage now omits them rather than reporting each one ineligible.

        Name the upstream in ``gates_on``. `all_dependencies` then requires its screener
        fields, so a field the upstream needs and you do not cannot make you calculable
        where it is not.
        """
        self._assert_declared(program_code, self.gates_on, "gates_on")

        if program_code not in self.data:
            raise UpstreamAbsentError(program_code)

        return self.data[program_code].eligible

    @classmethod
    def _assert_declared(cls, program_code: str, declared, attribute: str) -> None:
        """Refuse a gate the class did not declare.

        A programming error, not a data condition: the declarations are what
        `can_calc`, the force-calculated upstream set and `CALC_ORDER` are all derived
        from, so a call that bypasses them would reintroduce exactly the silent drift this
        replaced. `screener/tests/test_calc_order.py` compares the declarations against the
        source, so this cannot first surface in production.
        """
        if program_code not in declared:
            raise ValueError(f"{cls.__name__} gates on {program_code!r} without declaring it in {attribute}")

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

        Choosing between the two is a question about the rule, not the data: can this
        program be answered at all without the upstream? Every strict gate today is a
        program defined in terms of another — a Medicaid category, a program for people
        Medicaid does not cover, or the leftover category between two siblings — so an
        unknown upstream leaves nothing to report. A program where the upstream is one
        route in among several belongs here instead, where not knowing costs the household
        that route rather than the whole program.
        """
        for program_code in program_codes:
            self._assert_declared(program_code, self.gates_on_any, "gates_on_any")

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

        Declared in ``gates_on`` alongside the household-scope gates: the scope differs but
        the liveness requirement is the same.
        """
        self._assert_declared(program_code, self.gates_on, "gates_on")

        if program_code not in self.data:
            raise UpstreamAbsentError(program_code)

        for member_eligibility in self.data[program_code].eligible_members:
            if member_eligibility.member.id == member.id:
                return member_eligibility.eligible

        return False

    @classmethod
    def all_dependencies(cls) -> tuple:
        """Every screener field this program needs, including its strict upstreams'.

        A strict gate raises when its upstream is absent, and a missing screener field is
        one way an upstream gets there — `can_calc` drops it before it can be calculated.
        If the dependent needed fewer fields than the upstream, there would be screens
        where the dependent runs and the upstream did not, so the gate would raise and the
        program would disappear for a household it could otherwise have answered for.
        Unioning here makes the pair drop out together, and means no calculator has to
        restate its upstream's field list by hand.
        """
        from programs.framework.gates import strict_upstream_fields

        return tuple(sorted(set(cls.dependencies) | strict_upstream_fields(tuple(cls.gates_on))))

    def can_calc(self):
        """
        Returns whether or not the program can be calculated with the missing dependencies
        """
        return not self.missing_dependencies.has(*self.all_dependencies())
