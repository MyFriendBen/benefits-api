"""MA CCFA (configured as ``ma_ccdf``)."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
from screener.models import HouseholdMember
import programs.framework.pe_dependencies as dependency


class MaCcdf(PolicyEngineSpmCalulator):
    """
    Massachusetts Child Care Financial Assistance (CCFA).

    Reads Massachusetts' own model, ``ma_ccfa_eligible``, rather than the federal CCDF
    passthrough it replaced.

    ``program_code`` stays ``ma_ccdf``: it keys the Program row, the ``has_ccdf``
    current-benefit field and every translation. Only the model behind it changed.

    Eligibility is PolicyEngine's; the value is ours. ``ma_ccfa`` itself is not adopted
    here -- it returns $0 for a household reporting no childcare expense, which is most
    of the people screening for a childcare subsidy, and it needs two inputs the screener
    never asks for (provider type and childcare hours per day). So the age table below
    stays, gated on PolicyEngine's answer.

    The last tier runs to CCFA's disabled age limit rather than its general one, so every
    child PolicyEngine claims is priced. Massachusetts covers a child "prenatal to age
    13yo (16yo if the child has a diagnosed special need)", and PolicyEngine applies both
    bounds, so ages 13 to 15 reach the table only when disabled. They are paid the
    school-age rate rather than nothing.

    Source: https://mass211.org/childcare
    """

    program_code = "ma_ccdf"

    pe_name = "ma_ccfa_eligible"
    pe_inputs = [
        *dependency.ma_ccfa_income,
        dependency.spm.AssetsDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.IsDisabledDependency,
        # Must be the MA subclass, not TotalHoursWorkedDependency: two dependencies
        # writing different values to one field cannot share a payload, and every other
        # MA program sends this one.
        dependency.member.MaTotalHoursWorkedDependency,
        dependency.member.PregnancyDependency,
        dependency.household.MaStateCodeDependency,
    ]
    pe_outputs = [
        dependency.spm.MaCcfaEligible,
        dependency.member.MaCcfaEligibleChild,
    ]

    cost_by_age = (
        # cost, age
        (23_191, 2),
        (21_125, 3),
        (16_572, 4.5),
        # School age. Runs to 16, not 13, so a disabled child PolicyEngine claims past the
        # general age limit is paid this rate rather than nothing.
        (12_632, 16),
    )

    def household_value(self):
        """Nothing at the household level.

        ``pe_name`` is a boolean, so the inherited ``int(self.get_variable())`` would add
        $1 to an eligible household's total.
        """
        return 0

    def member_value(self, member: HouseholdMember):
        if not self.get_variable():
            return 0

        if not self.get_member_dependency_value(dependency.member.MaCcfaEligibleChild, member.id):
            return 0

        return self.child_care_cost(member)

    def child_care_cost(self, member: HouseholdMember):
        age = member.fraction_age()

        for [cost, age_limit] in self.cost_by_age:
            if age < age_limit:
                return cost

        return 0
