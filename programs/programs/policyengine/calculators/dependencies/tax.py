from .base import TaxUnit
from .member import TaxUnitHeadDependency, TaxUnitSpouseDependency


class Eitc(TaxUnit):
    field = "eitc"


class Ctc(TaxUnit):
    field = "ctc_value"


class Coeitc(TaxUnit):
    field = "co_eitc"


class Coctc(TaxUnit):
    field = "co_ctc"


class Maeitc(TaxUnit):
    field = "ma_eitc"


class Ileitc(TaxUnit):
    field = "il_eitc"


class Ilctc(TaxUnit):
    field = "il_ctc"


class MaChildFamilyCredit(TaxUnit):
    field = "ma_child_and_family_credit"


class Aca(TaxUnit):
    field = "aca_ptc"


# WARN: this does not take into account multiple tax units
class PellGrantPrimaryIncomeDependency(TaxUnit):
    field = "pell_grant_primary_income"

    def value(self):
        total = 0
        for member in self.screen.household_members.all():
            is_head = TaxUnitHeadDependency(self.screen, member, self.relationship_map).value()
            is_spouse = TaxUnitSpouseDependency(self.screen, member, self.relationship_map).value()
            if is_head or is_spouse:
                total += int(member.calc_gross_income("yearly", ["all"]))

        return total


# WARN: this does not take into account multiple tax units
class PellGrantDependentsInCollegeDependency(TaxUnit):
    field = "pell_grant_dependents_in_college"
    dependencies = ("student",)

    def value(self):
        pell_grant_dependents_in_college = 0
        for member in self.members:
            if member.student:
                pell_grant_dependents_in_college += 1

        return pell_grant_dependents_in_college
