import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Lifeline, Snap, SchoolLunch, Tanf


class IlSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]


class IlNslp(SchoolLunch):
    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]

    tier_1_fpl = 1.30
    tier_2_fpl = 1.85

    tier_1_amount = 935
    tier_2_amount = 805

    def household_value(self):
        value = 0
        num_children = self.screen.num_children(3, 18)
        if self.get_variable() > 0 and num_children > 0:
            if self.get_dependency_value(dependency.spm.SchoolMealTier) != "PAID":
                countable_income = self.get_dependency_value(dependency.spm.SchoolMealCountableIncomeDependency)
                fpl_limit = self.program.year.get_limit(self.screen.household_size)

                if countable_income <= int(self.tier_1_fpl * fpl_limit):
                    value = self.tier_1_amount * num_children

                elif countable_income <= int(self.tier_2_fpl * fpl_limit):
                    value = self.tier_2_amount * num_children

        return value


class IlTanf(Tanf):
    pe_name = "il_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.IlStateCodeDependency,
        dependency.spm.IlTanfCountableEarnedIncomeDependency,
        dependency.spm.IlTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.IlTanf]


class IlLifeline(Lifeline):
    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.spm.Lifeline]

    def household_value(self):
        print("IL Lifeline postprocess")
        lifeline = getattr(self, "lifeline", 0)
        income = int(self.screen.calc_gross_income("yearly", ["all"]))
        print("Income:", income)

        fpl_limit = self.program.year.get_limit(self.screen.household_size)

        has_disability = any(m.has_disability() for m in self.screen.household_members.all())

        fpl_threshold = 2.0 if has_disability else 1.65

        eligible = income <= int(fpl_threshold * fpl_limit)

        return lifeline if eligible else 0
