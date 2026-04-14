from programs.programs.federal.pe.member import Wic
import programs.programs.policyengine.calculators.dependencies as dependency


class WaWic(Wic):
    # WIC uses a hybrid model: fixed Cash Value Benefit (CVB) for produce + quantity-based
    # food credits (milk, eggs, cereal, formula, etc.) estimated at local WA retail prices.
    # Total = CVB + estimated retail cost of food quantities. FY 2025/2026 values.
    #
    # INFANT ($135): No CVB; entire value is infant formula (~9 cans/mo) + jarred foods.
    # BREASTFEEDING ($114): Highest adult package — max CVB ($52) + expanded food (canned
    #   fish, extra cheese, double eggs).
    # PREGNANT ($92): $47 CVB + $45 food (larger dairy/grain package than postpartum).
    # POSTPARTUM ($78): $47 CVB + $31 food (reduced dairy/grains vs. pregnant).
    # CHILD ($68): $26 CVB + $42 food.
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
        dependency.household.NcStateCodeDependency,
    ]
