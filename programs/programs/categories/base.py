from collections.abc import Callable
from typing import Optional
from programs.programs.calc import Eligibility
from dataclasses import dataclass


@dataclass
class CategoryCap:
    programs: list[str]
    cap: int = 0
    member_cap: bool = False


@dataclass
class ReturnCategoryCap:
    programs: list[str]
    household_cap: int = 0
    member_caps: Optional[dict[str, int]] = None


class ProgramCategoryCapCalculator:
    # caps with a constant max
    static_caps: list[CategoryCap] = []

    # caps where the cap is the highest program value
    max_caps: list[CategoryCap] = []

    # caps where the cap is the average value of the program
    average_caps: list[CategoryCap] = []

    def __init__(self, eligibility: dict[str, Eligibility]) -> None:
        self.eligibility = eligibility

    def caps(self) -> list[ReturnCategoryCap]:
        static_caps = self._handle_caps(self.static_caps, self.calc_static_cap)
        max_caps = self._handle_caps(self.max_caps, self.calc_max_cap)
        average_caps = self._handle_caps(self.average_caps, self.calc_average_cap)

        return static_caps + max_caps + average_caps + self.other_caps()

    def other_caps(self) -> list[CategoryCap]:
        """
        Override this method to add custom caps
        """
        return []

    def calc_static_cap(self, cap: CategoryCap, values: list[int]) -> ReturnCategoryCap:
        if any(v > 0 for v in values):
            return cap.cap

        return 0

    def calc_max_cap(self, cap: CategoryCap, values: list[int]) -> ReturnCategoryCap:
        return max(*values)

    def calc_average_cap(self, cap: CategoryCap, values: list[int]) -> ReturnCategoryCap:
        non_0_values = [v for v in values if v > 0]

        if len(non_0_values) == 0:
            return 0

        return sum(non_0_values) / len(non_0_values)

    def _handle_caps(
        self, caps: list[CategoryCap], func: Callable[[CategoryCap, list[int]], int]
    ) -> list[ReturnCategoryCap]:
        """
        Take a caps and a function and calculate the category caps with that function
        """
        calculated_caps = []

        for cap in caps:
            if cap.member_cap:
                calculated_caps.append(self._handle_member_cap(cap, func))
                continue

            calculated_caps.append(self._handle_household_cap(cap, func))

        return calculated_caps

    def _handle_member_cap(self, cap: CategoryCap, func: Callable[[CategoryCap, list[int]], int]) -> ReturnCategoryCap:
        """
        Take a cap and a function and calculate the category cap for each member with that function
        """
        member_values: dict[str, list[int]] = {}

        new_cap = ReturnCategoryCap(cap.programs.copy(), member_caps={})

        for program in cap.programs:
            if program not in self.eligibility:
                new_cap.programs.remove(program)
                continue

            eligibility = self.eligibility[program]
            for member_eligibility in eligibility.eligible_members:
                member_id = str(member_eligibility.member.frontend_id)

                if member_id not in member_values:
                    member_values[member_id] = []

                member_values[member_id].append(member_eligibility.value)

        for member_id, values in member_values.items():
            new_cap.member_caps[member_id] = func(cap, values)

        return new_cap

    def _handle_household_cap(
        self, cap: CategoryCap, func: Callable[[CategoryCap, list[int]], int]
    ) -> ReturnCategoryCap:
        """
        Take a cap and a function and calculate the category cap for the household with that function
        """
        values: list[int] = []

        new_cap = ReturnCategoryCap(cap.programs.copy(), household_cap=0)

        for program in cap.programs:
            if program not in self.eligibility:
                new_cap.programs.remove(program)
                continue

            values.append(self.eligibility[program].value)

        new_cap.household_cap = func(cap, values)

        return new_cap
