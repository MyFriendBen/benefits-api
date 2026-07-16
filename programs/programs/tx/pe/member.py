from programs.programs.federal.pe.member import (
    Wic,
    Ssi,
    Medicaid,
    CommoditySupplementalFoodProgram,
    HeadStart,
    EarlyHeadStart,
    Msp,
)
from programs.programs.policyengine.calculators.base import (
    PolicyEngineMembersCalculator,
)
import programs.programs.policyengine.calculators.dependencies as dependency
from screener.models import HouseholdMember


class TxWic(Wic):
    """
    Texas WIC calculator that uses PolicyEngine's calculated benefit amounts
    instead of state-specific category amounts.
    """

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the PolicyEngine-calculated WIC benefit amount for this member.
        Unlike the parent class, this doesn't use hardcoded category-based amounts.
        """
        return self.get_member_variable(member.id)


class TxSsi(Ssi):
    """
    Texas SSI calculator that uses PolicyEngine's calculated benefit amounts.
    Extends the federal SSI calculator with Texas state code dependency.
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxCsfp(CommoditySupplementalFoodProgram):
    """
    Texas Commodity Supplemental Food Program (CSFP) calculator that uses PolicyEngine's calculations.
    Extends the federal CSFP calculator with Texas state code dependency.
    """

    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxMedicaidForChildren(Medicaid):
    """
    Texas Medicaid for Children calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides free health insurance for children under 19 who do not have
    other health insurance coverage.

    Eligibility requirements:
    - Must be under 19 years old (18 and under)
    - Must not have other health insurance
    - Income eligibility determined by PolicyEngine
    """

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the Medicaid benefit value for children under 19 without other insurance.
        """
        # Must be under 19
        if member.age >= 19:
            return 0

        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        # Return PolicyEngine-calculated value
        return self.get_member_variable(member.id)


class TxMedicaidForPregnantWomen(Medicaid):
    """
    Texas Medicaid for Pregnant Women calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides free health insurance for pregnant women who do not have
    other health insurance coverage.

    Eligibility requirements:
    - Must be pregnant
    - Must not have other health insurance
    - Income eligibility determined by PolicyEngine
    """

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the Medicaid benefit value for pregnant women without other insurance.
        """
        # Must be pregnant
        if not member.pregnant:
            return 0

        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        # Return PolicyEngine-calculated value
        return self.get_member_variable(member.id)


class TxMedicaidForParentsAndCaretakers(Medicaid):
    """
    Texas Medicaid for Parents and Caretakers calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides free or low-cost health insurance for low-income caretakers of children
    who receive Medicaid. Eligible caretakers must meet income rules and have a qualifying relationship
    to a child in the household who has or qualifies for Medicaid.

    Eligibility requirements:
    - Must be 19 years or older (adult)
    - Must not have other health insurance
    - Household must have a child under 19
    - Child must have Medicaid or qualify for Medicaid (PE-calculated value > 0)
    - Must have a qualifying relationship to a child: parent, step-parent, sibling, step-sibling, grandparent, or related in some other way
    - Income eligibility determined by PolicyEngine
    """

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    # Relationships that qualify as caretakers for this program.
    # Note that the relationship field describes each member's relationship TO
    # the head of household. We're including "headOfHousehold" here because
    # the head has relationship="headOfHousehold", and we're assuming that
    # they're an adult.
    caretaker_relationships = [
        "headOfHousehold",
        "spouse",
        "domesticPartner",
        "parent",
        "stepParent",
        "grandParent",
        "sisterOrBrother",
        "stepSisterOrBrother",
        "relatedOther",
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the Medicaid benefit value for adults who are caretakers of children with Medicaid.
        """
        # Must be 19 or older (adult caretaker)
        if member.age < 19:
            return 0

        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        # Must have a qualifying caretaker relationship
        if member.relationship not in self.caretaker_relationships:
            return 0

        # Household must have a child under 19 who has or qualifies for Medicaid
        if not self._has_child_with_medicaid():
            return 0

        # Return PolicyEngine-calculated value
        return self.get_member_variable(member.id)

    def _has_child_with_medicaid(self) -> bool:
        """
        Check if the household has at least one child under 19 who has Medicaid
        or qualifies for Medicaid (based on PE calculation).
        """
        for member in self.screen.household_members.all():
            # Child must be under 19
            if member.age >= 19:
                continue

            # Check if child has Medicaid already
            if member.has_insurance("medicaid"):
                return True

            # Check if child qualifies for Medicaid (PE value > 0)
            child_medicaid_value = self.get_member_dependency_value(dependency.member.Medicaid, member.id)
            if child_medicaid_value > 0:
                return True

        return False


class TxEmergencyMedicaid(Medicaid):
    """
    Texas Emergency Medicaid for Non-Citizens calculator that uses PolicyEngine's calculated benefit amounts.

    This program provides limited public health insurance that covers only emergency health care costs.
    It helps people who cannot get standard Medicaid because of their immigration status.

    Eligibility requirements:
    - Must have a life-threatening or serious medical condition requiring urgent care
    - Immigration status makes them ineligible for standard Medicaid
    - Covers emergency services including emergency labor and delivery
    - Only covers services needed to stabilize the condition, not ongoing care

    Notes:
    - The citizenship eligibility is handled at the program configuration level
      (legal_status_required), not in this calculator.
    - We do not ask users whether they have an emergency medical condition in the screener.
      Instead, this requirement is communicated in the program's description so users understand
      they must have a qualifying condition to receive benefits.
    """

    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns 1 if the member is eligible for Emergency Medicaid, 0 otherwise.

        The actual benefit value varies based on the emergency care needed, so we return
        a nominal value of 1 to indicate eligibility rather than a specific dollar amount.
        """
        # Must not have other health insurance
        if not member.has_insurance_types(("none",)):
            return 0

        pe_value = self.get_member_variable(member.id)
        return 1 if pe_value > 0 else 0


class TxChip(PolicyEngineMembersCalculator):
    """
    Texas CHIP calculator that uses PolicyEngine's calculated benefit amounts
    for TX-specific CHIP eligibility determination.
    Inherits from PolicyEngineMembersCalculator and uses the same inputs as the federal Chip calculator.
    """

    pe_name = "chip"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        *Medicaid.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
    pe_outputs = [dependency.member.Chip]

    # NOTE: This feels like it belongs in member_eligible, but due to the PolicyEngineCalculator.member_eligible
    # implementation (which sets both MemberEligibilty.eligible and confusingly MemberEligibility.value), this turned
    # out to be the lesser of two evils. It also follows an established pattern for using business logic to act on PE's
    # results (see: benefits-be/programs/programs/co/pe/member.py#L74).
    def member_value(self, member):
        """
        Returns the CHIP benefit value for this member, applying additional insurance eligibility rules.
        """
        pe_value = self.get_member_variable(member.id)

        # If the member has any insurance, they are not eligible for CHIP
        # NOTE: all other eligibility logic (e.g age requirement) is built into the value returned from PE)
        if member.has_insurance_types(("none",)):
            return pe_value

        return 0


class TxHarrisCountyRides(PolicyEngineMembersCalculator):
    """
    Texas Harris County RIDES program calculator.

    Provides discounted rides on public transit for individuals who are 65 or older
    or have a disability and are unable to access METRO services.

    The pe_name is "tx_harris_rides_eligible" which returns a boolean from PolicyEngine.
    When eligible, we return 1 to indicate eligibility (the actual value will be
    overridden to "Varies" in the admin console).

    PolicyEngine handles all eligibility requirements
    """

    pe_name = "tx_harris_rides_eligible"
    pe_outputs = [dependency.member.TxHarrisRidesEligible]
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsBlindDependency,
        dependency.household.TxStateCodeDependency,
        dependency.household.TxCountyDependency,
    ]
    dependencies = ["county"]

    def member_value(self, member):
        pe_eligible = self.get_member_variable(member.id)

        return 1 if pe_eligible else 0


class TxDart(PolicyEngineMembersCalculator):
    """
    Texas Dallas Area Rapid Transit (DART) reduced fare program calculator.

    DART provides transit benefits to Dallas area residents:
    - Free Ride: Children under 5 ride free
    - Reduced Fare available to:
      - Seniors (65+) or children ages 5-14
      - Disabled individuals
      - Veterans
      - Full-time students
      - People enrolled in qualifying programs (SNAP, Medicaid, Medicare, CHIP, WIC, TANF)

    PolicyEngine returns the maximum of free ride and reduced fare benefits.

    Reference: https://www.dart.org/fare/general-fares-and-overview/reduced-fares
    """

    pe_name = "tx_dart_benefit_person"
    pe_inputs = [
        # Core demographics
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.IsVeteranDependency,
        dependency.member.FullTimeCollegeStudentDependency,
        # TX state code for state-specific calculations
        dependency.household.TxStateCodeDependency,
        # Income dependencies for program eligibility calculations
        *Medicaid.pe_inputs,
    ]
    pe_outputs = [dependency.member.TxDartBenefitPerson]

    def member_value(self, member: HouseholdMember):
        """
        Returns the DART benefit value for this member.

        PolicyEngine handles all eligibility logic including:
        - Age-based eligibility (free for under 5, reduced for 5-14 or 65+)
        - Disability status
        - Veteran status
        - Student status
        - Enrollment in qualifying assistance programs

        We return the PolicyEngine-calculated value directly.
        """
        return self.get_member_variable(member.id)


class TxHeadStart(HeadStart):
    """Texas Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + TX state code."""

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxEarlyHeadStart(EarlyHeadStart):
    """Texas Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + TX state code."""

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxMsp(Msp):
    """Texas Medicare Savings Program. Federal ``Msp`` plus the TX state code and the state's
    Medicaid inputs (see ``Msp`` for why the Medicaid inputs are required)."""

    pe_inputs = [
        *Msp.pe_inputs,
        dependency.household.TxStateCodeDependency,
        *Medicaid.pe_inputs,
    ]


class TxFpp(PolicyEngineMembersCalculator):
    """
    Texas Family Planning Program (FPP).

    State-funded HHSC program offering free or low-cost reproductive and preventive
    health care to Texans through age 64.

    Hybrid PolicyEngine calculator: PolicyEngine owns the income determination — the
    countable-income formula and its earned/unearned source lists (1 TAC 382.109), the
    child-earnings exemption, the child-support/dependent-care deductions, and the 250%
    FPG limit — read back as ``tx_fpp_income_eligible``. Age (§4130) is read as
    ``tx_fpp_age_eligible``. MFB layers on the two rules PolicyEngine cannot model because
    they depend on data PE never sees (MFB-1088):
      - §4140 adjunctive income bypass — enrollment in SNAP, WIC, or CHIP (applicant or
        their child) makes the household income-eligible regardless of the FPG test.
      - §4100 insurance rule — only *full* Medicaid disqualifies; Emergency Medicaid
        (underinsured) and other coverage remain eligible (§4200 exception surfaced in copy).

    Deferring the income math to PolicyEngine is the point of this shape: PE's periodic
    fixes to the FPP income sources / countable-income formula flow in automatically instead
    of silently drifting from a hand-maintained copy. MFB-1088 originally migrated this to a
    fully custom calculator to enforce §4140/§4100; those overlays are preserved here while
    the income calculation moves back to PE.

    Texas residency is handled automatically by the TX white label.

    Benefit value:
    - $266.84/year per eligible participant — the average annual benefit from the TX HHS
      Women's Health Programs Report FY2024 ($78,705,897 / 294,954 clients). Mirrors
      PolicyEngine's ``gov.states.tx.fpp.annual_benefit``. Kept as an MFB constant rather
      than read from PE's ``tx_fpp_benefit``, because that variable is $0 whenever the
      household is not income-eligible and so would zero out the §4140 adjunctive-bypass
      cases. The household total is the sum across eligible members.
    """

    member_amount = 266.84

    # Required by the base class. We read the two eligibility sub-variables (pe_outputs)
    # rather than this benefit value, so the household total stays member_amount even in
    # §4140 adjunctive-bypass cases (where tx_fpp_benefit itself would be $0).
    pe_name = "tx_fpp_benefit"

    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.household.TxStateCodeDependency,
        # Feed PolicyEngine's countable-income calculation.
        *dependency.irs_gross_income,
    ]
    pe_outputs = [
        dependency.member.TxFppAgeEligible,
        dependency.spm.TxFppIncomeEligible,
    ]

    # can_calc gate: insurance (§4100 overlay) and income (feeds PE's income test) must be
    # present. Age is required via the AgeDependency pe_input.
    dependencies = ("age", "insurance", "income_amount", "income_frequency")

    def member_value(self, member: HouseholdMember) -> float:
        # §4130 age: 64 or younger — PolicyEngine's tx_fpp_age_eligible (upper bound only,
        # no minimum age). A member with no recorded age comes back not age-eligible.
        if not self.get_member_dependency_value(dependency.member.TxFppAgeEligible, member.id):
            return 0

        # §4100: only full Medicaid disqualifies. Emergency Medicaid (a separate insurance
        # flag) is underinsured and stays eligible; employer/private/CHIP does not disqualify.
        if member.insurance.has_insurance_types(("medicaid",)):
            return 0

        # Income: PolicyEngine's 250% FPG countable-income test, OR the §4140 adjunctive
        # bypass (SNAP/WIC/CHIP enrollment), which makes the income test moot.
        if self._income_eligible() or self._has_adjunctive_bypass():
            return self.member_amount

        return 0

    def _income_eligible(self) -> bool:
        """PolicyEngine's SPM-unit ``tx_fpp_income_eligible`` (countable income <= 250% FPG)."""
        return bool(self.get_dependency_value(dependency.spm.TxFppIncomeEligible))

    def _has_adjunctive_bypass(self) -> bool:
        """§4140 — SNAP/WIC read from the CurrentBenefit join table under their TX-scoped
        names (tx_snap, tx_wic) via has_benefit(); CHIP read from per-member insurance
        (applicant or their child) via has_insurance_types(("chp",)). CHIP is never a
        current-benefit tile (tx_chip is a PE eligibility program, so has_benefit("tx_chip")
        is always False). Do NOT read the legacy has_snap/has_wic/has_chp columns — the
        join-table migration (MFB-720) left them permanently False.

        CHIP Perinatal, the 4th §4140 program, is not collected by the screener (data gap).
        """
        return (
            self.screen.has_benefit("tx_snap")
            or self.screen.has_benefit("tx_wic")
            or self.screen.has_insurance_types(("chp",))
        )
