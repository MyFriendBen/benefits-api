from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility


class IlNurseFamilyPartnership(ProgramCalculator):
    # TODO: add more context on where we got this number
    fpl_percent = 3
    child_relationships = ["child"]
    amount = 0
    dependencies = [
        "relationship",
        "income_frequency",
        "income_amount",
        "age",
        "pregnant",
    ]

    def household_eligible(self, e: Eligibility):
        # no other children
        e.condition(self.screen.num_children(child_relationship=self.child_relationships) == 0)

        # income eligibility: 300% FPL or has WIC (presumed eligibility)
        income_limit = self.program.year.as_dict()[2] * self.fpl_percent
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        is_income_eligible = gross_income <= income_limit

        has_wic = self.screen.has_benefit("wic")

        e.condition(is_income_eligible or has_wic)

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # pregnant
        e.condition(member.pregnant is True)
