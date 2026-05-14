from programs.programs.federal.pe.tax import Ctc, Eitc
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator
import programs.programs.policyengine.calculators.dependencies as dependency


class WaEitc(PolicyEngineTaxUnitCalulator):
    pe_name = "eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Eitc]


class WaCtc(PolicyEngineTaxUnitCalulator):
    pe_name = "ctc_value"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ctc]


class WaWftc(PolicyEngineTaxUnitCalulator):
    """
    Washington Working Families Tax Credit — state EITC piggyback.

    A thin wrapper around PolicyEngine's `wa_working_families_tax_credit`
    variable. WFTC is a refundable Washington State credit modeled on the
    federal EITC: PolicyEngine computes the federal `eitc` (handling phase-in,
    phase-out, MFJ adjustments, the investment-income cap, the 25-64 age floor
    for childless filers, and the qualifying-child rules) and then applies the
    Washington-specific scaling and $50 minimum-credit floor for any otherwise-
    eligible filer.

    Inputs reuse the federal `Eitc.pe_inputs` set (member age, tax-unit
    composition, and the per-member IRS gross income breakdown) and add the WA
    state code so PolicyEngine knows to apply the WFTC instead of just the
    federal EITC.

    Screener gaps that the calculator does NOT block on (per spec.md):
      - Whether the filer will actually file a federal return for the year
      - Whether the filer is claimed as a dependent on someone else's return
      - 183-day WA physical-presence requirement
      - Whether qualifying children lived with the filer > 6 months
    These are surfaced to the user in the program description and accepted as
    inclusivity assumptions at screener time.

    Married-filing-separately is not modeled — the screener treats spouses as
    filing jointly (the most common case), matching the description copy.
    """

    pe_name = "wa_working_families_tax_credit"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.WaWftc]
