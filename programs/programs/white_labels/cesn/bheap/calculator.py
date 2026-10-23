from programs.programs.white_labels.cesn.utility_assistance import CesnElectricUtilityAssistance


class EnergyCalculatorElectricityAffordabilityBlackHills(CesnElectricUtilityAssistance):
    program_code = "cesn_bheap"
    gates_on_any = (
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
        "cesn_care",
    )
    electricity_providers = ["co-black-hills-energy"]
