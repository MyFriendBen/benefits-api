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
    """

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

    def can_calc(self):
        """
        Returns whether or not the program can be calculated with the missing dependencies
        """
        return not self.missing_dependencies.has(*self.dependencies)
