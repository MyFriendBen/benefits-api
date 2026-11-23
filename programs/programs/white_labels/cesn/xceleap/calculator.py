from programs.programs.white_labels.cesn.utility_assistance import CesnElectricUtilityAssistance


class EnergyCalculatorElectricityAffordabilityXcel(CesnElectricUtilityAssistance):
    program_code = "cesn_xceleap"
    gates_on_any = (
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
    )
    electricity_providers = ["co-xcel-energy"]
