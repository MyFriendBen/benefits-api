from programs.programs.federal.pe.spm import SchoolLunch
import programs.programs.policyengine.calculators.dependencies as dependency


class WaSchoolLunch(SchoolLunch):
    class NotTanfEligibility(dependency.spm.SpmUnit):
        # TODO: remove this when we add calculation for WaTanf
        # the issue is that we can't add tanf to the base class
        # like we did for SNAP because TANF differs by state
        field = "wa_tanf"

        def value(self):
            return 0

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        NotTanfEligibility,
        dependency.household.WaStateCodeDependency,
    ]
    amount = 1_116
