"""
Member level (people) PolicyEngine input classes.

These inputs operate at the individual household member level.
"""

from .base import PolicyEngineInput


class SnapChildSupportInput(PolicyEngineInput):
    """Child support payments for a member."""
    field = "child_support_expense"
    unit = "people"
    dependencies = ("child_support_expense",)

    def value(self):
        if not self.member:
            return 0
        return self.member.calc_expenses("yearly", ["childSupport"])


class PropertyTaxExpenseInput(PolicyEngineInput):
    """Property tax expenses for a member."""
    field = "real_estate_taxes"
    unit = "people"

    def value(self):
        if not self.member:
            return 0
        return self.member.calc_expenses("yearly", ["propertyTax"])


class AgeInput(PolicyEngineInput):
    """Age of a household member."""
    field = "age"
    unit = "people"
    dependencies = ("age",)

    def value(self):
        if not self.member:
            return 0
        return self.member.age


class MedicalExpenseInput(PolicyEngineInput):
    """Medical expenses for a member."""
    field = "medical_out_of_pocket_expenses"
    unit = "people"

    def value(self):
        if not self.member:
            return 0
        return self.member.calc_expenses("yearly", ["medical"])


class IsDisabledInput(PolicyEngineInput):
    """Whether a member has a disability."""
    field = "is_disabled"
    unit = "people"
    dependencies = ("has_disability",)

    def value(self):
        if not self.member:
            return False
        return self.member.has_disability()


class SnapIneligibleStudentInput(PolicyEngineInput):
    """Whether a member is a SNAP-ineligible student."""
    field = "is_snap_ineligible_student"
    unit = "people"

    def value(self):
        if not self.member:
            return False
        # TODO: Implement student eligibility logic
        # For now, assume all students are eligible
        return False
