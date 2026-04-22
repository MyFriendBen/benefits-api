from programs.programs.federal.pe.member import Wic
import programs.programs.policyengine.calculators.dependencies as dependency


class WaWic(Wic):
    class NotTanfEligibility(dependency.spm.SpmUnit):
        # TODO: remove this when we add calculation for WaTanf
        # the issue is that we can't add tanf to the base class
        # like we did for SNAP because TANF differs by state
        field = "wa_tanf"

        def value(self):
            return 0

    # Monthly values per participant category. Hybrid model: fixed Cash Value
    # Benefit (CVB) for produce + estimated retail cost of the quantity-based
    # food package (milk, eggs, cereal, formula, etc.). See spec.md "Benefit
    # Value" section for the CVB/food split and citations.
    wic_categories = {
        "NONE": 0,
        "INFANT": 135,
        "CHILD": 68,
        "PREGNANT": 92,
        "POSTPARTUM": 78,
        "BREASTFEEDING": 114,
    }
    pe_inputs = [
        *Wic.pe_inputs,
        NotTanfEligibility,
        dependency.household.WaStateCodeDependency,
    ]
