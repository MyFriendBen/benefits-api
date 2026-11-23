from programs.programs.white_labels.cesn.utility_assistance import CesnGasUtilityAssistance


class EnergyCalculatorPercentageOfIncomePaymentPlan(CesnGasUtilityAssistance):
    program_code = "cesn_poipp"
    gates_on_any = (
        "cesn_leap",
        "cesn_eoc",
        "cesn_cowap",
    )
    gas_providers = ["co-atmos-energy"]
