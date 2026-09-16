from screener.models import EARNED_INCOME_TYPES

from .base import Member
from .receipt import SSI_INCOME_TYPE, member_reports_ssi_amount, screen_reports_ssi_without_amount


class AgeDependency(Member):
    field = "age"
    dependencies = ("age",)

    def value(self):
        return self.member.calc_age()


class AgeAtEndOfClaimYearDependency(Member):
    """
    Age as of December 31 of the year being claimed.

    ``AgeDependency`` reports age on the screening date, which understates by one year
    anybody whose birthday falls later in the calendar year. A rule that awards a benefit
    on age "attained on or before December 31" of the claim year needs the end-of-year
    age, or a household screened in August qualifies only if it screens again in
    December.

    The claim year is the period the variable is being sent at, which comes from the
    program's configured year, so this follows a program rolled forward to a new year
    without anybody remembering to change a constant here. It used to be a class attribute
    on a subclass hardcoded to 2026, which would have gone on sending 2026 ages under a
    2027 period.

    Both this and ``AgeDependency`` write ``age``, so a screen carrying both splits into two
    PolicyEngine requests for any member whose birthday falls later in the year (see
    ``build_pe_input``). That is the intended cost: age on the screening date is the right
    input for a program whose eligibility is judged today, and the end-of-year age is right
    for one judged over a tax year, and no single value serves both.

    Falls back to the screening-date age when the member's birth year is unknown, or when
    there is no period to read a year from.
    """

    field = "age"
    dependencies = ("age",)

    def value(self):
        birth_year = self.member.birth_year
        claim_year = self.period_year

        if birth_year is None or claim_year is None:
            return self.member.calc_age()

        return claim_year - birth_year


class PregnancyDependency(Member):
    field = "is_pregnant"

    def value(self):
        return self.member.pregnant or False


class MaTafdcPregnancyEligibleDependency(Member):
    field = "ma_tafdc_pregnancy_eligible"
    dependencies = ("pregnant",)

    def value(self):
        # We don't collect pregnancy month, so treat any pregnant member as
        # meeting PE's 5-month TAFDC eligibility threshold.
        return self.member.pregnant or False


class ExpectedChildrenPregnancyDependency(Member):
    field = "current_pregnancies"

    def value(self):
        return 1 if self.member.pregnant else 0


class FullTimeCollegeStudentDependency(Member):
    field = "is_full_time_college_student"

    def value(self):
        return bool(self.member.student and self.member.student_full_time)


class PartTimeCollegeStudentDependency(Member):
    field = "is_part_time_college_student"

    def value(self):
        return bool(self.member.student and self.member.student_full_time is False)


class SnapWorkExceptionDependency(Member):
    field = "meets_snap_work_exception"

    def value(self):
        return bool(self.member.student_works_20_plus_hrs or self.member.student_has_work_study)


class SnapJobTrainingStudentDependency(Member):
    field = "is_snap_employment_training_or_work_incentive_student"
    # First released in policyengine-us 1.752.0 (merged to main 2026-07-01).
    min_pe_version = (1, 752, 0)

    def value(self):
        return self.member.student_job_training_program or False


class TaxUnitHeadDependency(Member):
    field = "is_tax_unit_head"
    dependencies = ("relationship",)

    def value(self):
        if self.member.is_head():
            return True

        other_unit = self.screen.other_tax_unit_structure()

        if other_unit["head"] is None:
            return False

        return other_unit["head"].id == self.member.id


class TaxUnitSpouseDependency(Member):
    field = "is_tax_unit_spouse"
    dependencies = ("relationship",)

    def value(self):
        if self.member.is_spouse():
            return True

        other_unit = self.screen.other_tax_unit_structure()

        if other_unit["spouse"] is None:
            return False

        return other_unit["spouse"].id == self.member.id


class TaxUnitDependentDependency(Member):
    field = "is_tax_unit_dependent"
    dependencies = (
        "relationship",
        "age",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        if self.member.is_dependent():
            return True

        other_unit = self.screen.other_tax_unit_structure()

        for member in other_unit["dependents"]:
            if member.id == self.member.id:
                return True

        return False


class WicCategory(Member):
    field = "wic_category"


class MedicaidCategory(Member):
    field = "medicaid_category"


class MedicaidSeniorOrDisabled(Member):
    field = "is_optional_senior_or_disabled_for_medicaid"


class Wic(Member):
    """
    PolicyEngine's ``wic`` person output — the member's WIC entitlement by food package.

    Already the would-be value for our payloads, unlike SSI/SNAP/TANF, whose programs need the
    ``*_if_takes_up`` variants: ``wic`` is ``wic_if_takes_up`` gated on
    ``takes_up_wic_if_eligible``, which defaults True and which we never send, so the two are
    equal for every household we submit. (``receives_wic`` is measurably inert, so it is not
    wired either.) Being ungated also keeps WIC clear of the ``min_pe_version`` floor, and so of
    ``_drop_unreadable_programs``.
    """

    field = "wic"


class Medicaid(Member):
    field = "medicaid"


class Ssi(Member):
    """
    The member's reported SSI amount, as PolicyEngine's person-level ``ssi`` input; None when
    they report none, leaving PolicyEngine to compute it.

    A reported amount replaces PolicyEngine's own figure, counting as income downstream and
    conferring the categorical eligibility SSI receipt carries. It also wins over the take-up
    flag, which only suppresses PolicyEngine's *computed* value.
    """

    field = "ssi"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        ssi = self.member.calc_gross_income("yearly", [SSI_INCOME_TYPE])
        return None if ssi == 0 else ssi


class SsiIfTakesUp(Member):
    """
    PolicyEngine's ``ssi_if_takes_up`` person output: the SSI this member would get if they took
    the program up, regardless of reported take-up.

    What the SSI program reads, since the plain ``ssi`` output is gated on
    ``takes_up_ssi_if_eligible`` and so reads 0 for exactly the non-recipients the program
    should be recommended to — and the frontend filters out programs valued at $0.
    """

    field = "ssi_if_takes_up"
    min_pe_version = (1, 779, 3)


class ReceivesSsiDependency(Member):
    """
    PolicyEngine's ``receives_ssi`` person input: this member is a reported SSI recipient.

    Read alongside the ``ssi`` amount rather than instead of it — every consumer tests
    ``(ssi > 0) | receives_ssi`` (``meets_snap_categorical_eligibility``,
    ``is_ssi_recipient_for_medicaid`` and its 209(b) variant). So the boolean is what carries
    receipt when PolicyEngine computes the member's own entitlement as $0, the one case an
    amount cannot express.

    Set from a reported amount only, since that is the only per-member signal the screener
    captures. PolicyEngine treats the flag as conclusive — it confers the SSI-recipient
    Medicaid pathway with no demographic or income test — so it is never inferred.
    """

    field = "receives_ssi"
    min_pe_version = (1, 779, 3)
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return member_reports_ssi_amount(self.member)


class TakesUpSsiIfEligibleDependency(Member):
    """
    PolicyEngine's ``takes_up_ssi_if_eligible`` person input, default True. False stops
    PolicyEngine from counting the SSI it simulates for this member as income they receive, and
    withdraws the categorical eligibility that receipt confers — reaching IL AABD, SNAP's
    income test, TX CEAP and the Medicaid/MSP SSI methodologies.

    Lowered for a member reporting no SSI amount, which is the point of the receipt contract:
    a simulated entitlement is not income.

    Held at the default for a household that ticked the SSI tile without an amount — somebody
    receives SSI but nothing says who, and zeroing them all would suppress a real benefit. See
    ``screen_reports_ssi_without_amount``.
    """

    field = "takes_up_ssi_if_eligible"
    min_pe_version = (1, 779, 3)
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        if member_reports_ssi_amount(self.member):
            return True

        return screen_reports_ssi_without_amount(self.screen)


class IsDisabledDependency(Member):
    field = "is_disabled"

    def value(self):
        # per discussion with PolicyEngine 01/02/2026, should include blindness in is_disabled
        return self.member.disabled or self.member.long_term_disability or self.member.visually_impaired


class IsIncapableOfSelfCareDependency(Member):
    """
    PolicyEngine's `is_incapable_of_self_care` person input — used across care-related
    calculations (e.g. the federal CDCC, where such a person is a qualifying individual
    at any age). We infer it from the same self-reported disability signals as
    is_disabled, since the screener has no dedicated incapable-of-self-care field.
    """

    field = "is_incapable_of_self_care"

    def value(self):
        return self.member.disabled or self.member.long_term_disability or self.member.visually_impaired


class CareExpensesDependency(Member):
    """
    PolicyEngine's `care_expenses` person input — the cost of caring for a member who
    is incapable of self-care. Distinct from the spm-unit-level `childcare_expenses`,
    which PE aggregates into `tax_unit_childcare_expenses` by distributing only across
    under-13 children (so an adult qualifying individual gets $0 from that path). It
    feeds the federal CDCC and any state credit derived from it.

    Our screener captures a single household-level "Dependent Care" (dependentCare)
    expense with no per-member attribution, so we split it evenly across the members
    who are incapable of self-care and assign this member their share (others get 0).
    The even split is safe for the CDCC, which caps relevant expenses at $3,000 (one
    qualifying individual) / $6,000 (two or more) — the split lands on the cap in the
    cases that matter.
    """

    field = "care_expenses"

    def value(self):
        if not (self.member.disabled or self.member.long_term_disability or self.member.visually_impaired):
            return 0

        incapable_members = [
            m
            for m in self.screen.household_members.all()
            if (m.disabled or m.long_term_disability or m.visually_impaired)
        ]
        if not incapable_members:
            return 0

        dependent_care_total = self.screen.calc_expenses("yearly", ["dependentCare"])
        return dependent_care_total / len(incapable_members)


class MeetsSsiDisabilityCriteriaDependency(Member):
    """
    PolicyEngine frontier (policyengine-us 1.715.2) requires this person input to
    classify someone as SSI-disabled — it no longer falls back to is_disabled /
    reported SSI receipt. Without it, a disabled non-aged/non-blind person gets
    ssi: 0 (MFB-1102).

    Source mirrors IsDisabledDependency: SSI eligibility is
    is_ssi_aged OR is_blind OR is_ssi_disabled (verified in policyengine-us source),
    so including blindness here only adds to an OR and can never reduce eligibility.

    min_pe_version gates this so it's only sent to models that define it (first added in
    1.715.2); sending it to an earlier pinned version would 400 the whole request.
    """

    field = "meets_ssi_disability_criteria"
    min_pe_version = (1, 715, 2)

    def value(self):
        return self.member.disabled or self.member.long_term_disability or self.member.visually_impaired


class MedicalExpenseDependency(Member):
    """
    Medical expenses for PolicyEngine SNAP and other deduction calculations.

    Our screener captures medical expenses as a household-level expense, so we
    attribute the full amount to the head; other members get 0.
    """

    field = "other_medical_expenses"

    def value(self):
        if not self.member.is_head():
            return 0

        return int(self.screen.calc_expenses("yearly", ["medical"]))


class PropertyTaxExpenseDependency(Member):
    """
    Property tax expense for PolicyEngine tax calculations.

    PE treats this as a person-level field for state tax calculations.
    We split the household's total property tax between head and spouse only
    (the tax filers), not all adults, since this is used for tax filing purposes.
    """

    field = "real_estate_taxes"

    def value(self):
        # Only assign to head and spouse (tax filers)
        if not (self.member.is_head() or self.member.is_spouse()):
            return 0

        total_property_tax = self.screen.calc_expenses("yearly", ["propertyTax"])

        # If married/joint filing, split between head and spouse
        if self.screen.is_joint():
            return int(total_property_tax / 2)

        return int(total_property_tax)


class HeatingExpensePersonDependency(Member):
    """
    PolicyEngine's state LIHEAP calculators (MA, DC, IL) read heating expense
    from a person-level field (heating_expense_person) and auto-aggregate
    back to the spm_unit/household total used in the payment cap formula.

    Our screener captures heating as a household-level expense, so we attribute
    the full amount to the head; other members get 0.
    """

    field = "heating_expense_person"

    def value(self):
        if not self.member.is_head():
            return 0

        return int(self.screen.calc_expenses("yearly", ["heating", "cooling"]))


class IsBlindDependency(Member):
    field = "is_blind"

    def value(self):
        return self.member.visually_impaired or False


class SsdiReportedDependency(Member):
    # Amount in "Social Security disability benefits (SSDI)"
    field = "social_security_disability"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return self.member.calc_gross_income("yearly", ["sSDisability"])


class SsiCountableResourcesDependency(Member):
    field = "ssi_countable_resources"
    dependencies = (
        "household_assets",
        "age",
    )

    def value(self):
        ssi_assets = 0
        if self.member.age >= 19:
            ssi_assets = self.screen.household_assets / self.screen.num_adults()

        return int(ssi_assets)


class Andcs(Member):
    field = "co_state_supplement"


class Oap(Member):
    field = "co_oap"


class FamilyAffordabilityTaxCredit(Member):
    field = "co_family_affordability_credit"


class CareWorkerEligibleDependency(Member):
    field = "co_care_worker_credit_eligible_care_worker"
    dependencies = ("is_care_worker",)

    def value(self):
        return self.member.is_care_worker or False


class PellGrant(Member):
    field = "pell_grant"


class PellGrantDependentAvailableIncomeDependency(Member):
    field = "pell_grant_dependent_available_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["all"]))


class PellGrantCountableAssetsDependency(Member):
    field = "pell_grant_countable_assets"
    dependencies = ("household_assets",)

    def value(self):
        return int(self.screen.household_assets)


class CostOfAttendingCollegeDependency(Member):
    field = "cost_of_attending_college"
    dependencies = ("age", "student")

    def value(self):
        return 22_288 * (self.member.age >= 16 and self.member.student)


class PellGrantMonthsInSchoolDependency(Member):
    field = "pell_grant_months_in_school"

    def value(self):
        return 9


class ChpEligible(Member):
    field = "co_chp_eligible"


class CommoditySupplementalFoodProgram(Member):
    field = "commodity_supplemental_food_program"


class SnapChildSupportDependency(Member):
    field = "child_support_expense"
    dependencies = ("age", "household_size")

    def value(self):
        return self.screen.calc_expenses("yearly", ["childSupport"]) / self.screen.household_size


class TotalHoursWorkedDependency(Member):
    """
    Weekly hours worked, taken from hourly income streams and approximated from the
    rest at minimum wage.

    Only *earned* income counts. The approximation branch divides income by a wage,
    which is only meaningful for money paid for work: run over an unearned stream it
    invents hours nobody worked, and PolicyEngine's SNAP/TANF work screens read this
    field. A 45-year-old with $2,000/mo of SSDI would otherwise be credited ~69
    "work" hours a week and clear every work requirement.

    Subclasses override ``minimum_wage`` with their state's rate; the federal floor
    is the conservative default, since a lower wage buys more approximated hours.

    Reported hours are floored at ``assumed_weekly_hours`` for anyone old enough for a
    SNAP work test to reach (``work_test_minimum_age``). PolicyEngine dropped this
    field's 40-hour default in 1.815.1, and its SNAP work screens deny the *whole* SPM
    unit when any member reads under 30 hours (20 for ABAWD) without an exemption --
    ``meets_snap_work_requirements`` is ANDed into ``is_snap_eligible`` and categorical
    eligibility does not override it. We collect income, not employment: an adult with
    no earned income may be working unpaid, between jobs, or under a waiver or the
    ABAWD grace period, and part-time earnings say nothing about work *registration*,
    which is what the general requirement actually tests. Screening errs inclusive, so
    the floor asserts the work test is met rather than denying on data we never asked
    for -- the same result PolicyEngine's own default produced, now stated explicitly
    (MFB-1637).

    The floor reaches every consumer of this field on purpose. All programs in a screen
    share one payload, so one value per member per screen was a hard constraint when this
    was written, and it costs accuracy on the field's other readers: ``tx_ccs``'s work
    requirement and the MA TAFDC/EAEDC dependent-care deductions both read hours and both
    get more generous. Accepted deliberately; modelling the SNAP work test properly is
    follow-up work.

    Payload assembly can now answer disagreeing programs with a second request rather than
    failing, so the constraint is a cost rather than a wall -- but a per-reader value would
    buy accuracy with a round trip, which is a trade to make deliberately and not a reason to
    split this field today.
    """

    field = "weekly_hours_worked_before_lsr"
    dependencies = (
        "age",
        "income_type",
        "income_amount",
        "income_frequency",
    )

    minimum_wage = 7.25
    work_weeks_in_month = 4

    assumed_weekly_hours = 40
    # PolicyEngine exempts under-16s from the general work requirement and under-18s
    # from ABAWD, so no work test can reach a member below this age and the floor would
    # only put phantom hours in the payload -- which the MA dependent-care deduction
    # sums over every member, children included. No upper bound: the ABAWD exempt age
    # has moved twice (50 -> 55 -> 65), and a stale ceiling here would read as a denial.
    work_test_minimum_age = 16

    def value(self):
        reported = self.reported_hours()

        if self.member.calc_age() < self.work_test_minimum_age:
            return reported

        return max(reported, self.assumed_weekly_hours)

    def reported_hours(self):
        """Hours the screen actually evidences, before the work-test floor."""
        hours = 0

        for income in self.member.income_streams.all():
            if income.type not in EARNED_INCOME_TYPES:
                continue

            if income.frequency == "hourly":
                # hours_worked is nullable and, unlike type/amount/frequency, is not
                # reported by IncomeStream.missing_fields(), so can_calc() will not
                # hold the request back when it is absent. An hourly stream's amount
                # is a rate, so there is nothing to approximate hours from either.
                # Contribute nothing rather than raising and failing the whole build.
                if income.hours_worked is None:
                    continue

                hours += int(income.hours_worked)
                continue

            # approximate weekly hours by valuing the income at minimum wage
            hours += int(income.monthly()) / self.minimum_wage / self.work_weeks_in_month

        return hours


class MaTotalHoursWorkedDependency(TotalHoursWorkedDependency):
    """
    Massachusetts approximation, at the state minimum wage.

    Every MA calculator sending this field must use this subclass. Two dependencies
    writing different values to the same field and period cannot share a payload, so
    mixing this with the base class inside one MA screen costs a second PolicyEngine
    request for the programs on the losing side.
    """

    minimum_wage = 15


class MaTanfCountableGrossEarnedIncomeDependency(Member):
    field = "ma_tcap_gross_earned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["earned"]))


class MaTanfCountableGrossUnearnedIncomeDependency(Member):
    field = "ma_tcap_gross_unearned_income"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        return int(self.member.calc_gross_income("yearly", ["unearned"], exclude=["cashAssistance"]))


class MaTapCharlieCardEligible(Member):
    field = "ma_mbta_tap_charlie_card_eligible"


class MaSeniorCharlieCardEligible(Member):
    field = "ma_mbta_senior_charlie_card_eligible"


class MaMbtaProgramsEligible(Member):
    field = "ma_mbta_enrolled_in_applicable_programs"


class MaMbtaAgeEligible(Member):
    field = "ma_mbta_income_eligible_reduced_fare_eligible"


class Ccdf(Member):
    field = "is_ccdf_eligible"


class CcdfReasonCareEligibleDependency(Member):
    field = "is_ccdf_reason_for_care_eligible"

    def value(self):
        return True


class ChildcareAttendingDaysPerMonthDependency(Member):
    """
    Number of days per month a child attends childcare.

    Set to 10 days/month instead of default 20 days/month to align with Texas CCS (Child Care Services) validation
    references and provider payment rate calculations. Using 20 days resulted in
    tx_ccs benefit values approximately 2x higher than expected, because the Board's
    maximum daily reimbursement rate is multiplied by attending days per month.

    Note: If other state childcare subsidy programs require a different default,
    this value may need to be made program-specific.
    """

    field = "childcare_attending_days_per_month"

    def value(self):
        return 10


class MaStateSupplementProgram(Member):
    field = "ma_state_supplement"


class ChipCategory(Member):
    field = "chip_category"


class Chip(Member):
    field = "chip"


class ChipGross(Member):
    # CHIP's per-child value before PolicyEngine's cost-sharing offsets. Read instead of
    # `chip` (the net figure) by any program that subtracts a state premium itself —
    # netting both would count cost-sharing twice.
    field = "chip_gross"


class IncomeDependency(Member):
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )
    income_types = []
    exclude_income_types = []

    def value(self):
        return int(self.member.calc_gross_income("yearly", self.income_types, exclude=self.exclude_income_types))


class EmploymentIncomeDependency(IncomeDependency):
    field = "employment_income"
    income_types = ["wages"]


class SelfEmploymentIncomeDependency(IncomeDependency):
    field = "self_employment_income"
    income_types = ["selfEmployment"]


class RentalIncomeDependency(IncomeDependency):
    field = "rental_income"
    income_types = ["rental"]


class PensionIncomeDependency(IncomeDependency):
    field = "taxable_pension_income"
    income_types = ["pension", "veteran"]


class PensionIncomeWithoutVeteranDependency(IncomeDependency):
    """
    Pension income with the ``veteran`` income stream held back, for calculators that
    also send ``VeteransBenefitsDependency``.

    ``PensionIncomeDependency`` folds ``veteran`` into ``taxable_pension_income``. A
    calculator that reads PolicyEngine's ``veterans_benefits`` variable needs the
    veteran stream to arrive there instead; sending it in both places would double-count
    it. Pairing this class with ``VeteransBenefitsDependency`` routes each stream to
    exactly one PolicyEngine field.
    """

    field = "taxable_pension_income"
    income_types = ["pension"]


class VeteransBenefitsDependency(IncomeDependency):
    """
    The ``veteran`` income stream as PolicyEngine's ``veterans_benefits``.

    State rules that exclude veterans' payments from countable income read
    ``veterans_benefits`` specifically. Income routed through
    ``taxable_pension_income`` reaches those formulas by a different path
    (``adjusted_gross_income``) that the exclusion cannot see, so the exclusion never
    fires. Use with ``PensionIncomeWithoutVeteranDependency`` to avoid double-counting.
    """

    field = "veterans_benefits"
    income_types = ["veteran"]


class IsFullyDisabledServiceConnectedVeteranDependency(Member):
    """
    PolicyEngine's ``is_fully_disabled_service_connected_veteran`` person input, which
    gates the exclusion of veterans' benefits from countable income in state formulas
    such as Missouri's property tax credit.

    PolicyEngine defines no formula for it, so it is only ever true if we send it. The
    screener has no VA disability-rating or service-causation field, and
    ``HouseholdMember.veteran`` is not populated by the frontend, so this proxies off
    the two signals that are collected: a ``veteran`` income stream (the established
    veteran proxy, also used by KS K-40H and CO Denver property tax relief) combined
    with self-reported disability. The proxy is inclusive — it does not distinguish a
    100% rating from a lower one.
    """

    field = "is_fully_disabled_service_connected_veteran"
    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def value(self):
        receives_veteran_income = self.member.calc_gross_income("yearly", ["veteran"]) > 0
        return receives_veteran_income and (self.member.disabled or self.member.long_term_disability)


class SocialSecurityIncomeDependency(IncomeDependency):
    """
    Social Security benefits (not including SSI).

    Note: SSI (Supplemental Security Income) is a separate needs-based program,
    not funded by Social Security payroll taxes. It is handled separately via
    SsiReportedDependency and the Ssi output dependency.
    """

    field = "social_security"
    income_types = ["sSDisability", "sSSurvivor", "sSRetirement", "sSDependent"]


class SocialSecuritySurvivorsIncomeDependency(IncomeDependency):
    """
    The ``sSSurvivor`` income stream as PolicyEngine's ``social_security_survivors``.

    ``SocialSecurityIncomeDependency`` reports the four Social Security streams as a
    single ``social_security`` total. PolicyEngine defines ``social_security`` as the sum
    of its four components, so setting the total leaves every component at zero — and a
    rule that tests survivor benefits specifically reads ``social_security_survivors``,
    which never sees the money. Sending the component alongside the total does not
    double-count: the total we send already includes it.
    """

    field = "social_security_survivors"
    income_types = ["sSSurvivor"]


class InvestmentIncomeDependency(IncomeDependency):
    field = "long_term_capital_gains"
    income_types = ["investment"]


class MiscellaneousIncomeDependency(IncomeDependency):
    field = "miscellaneous_income"
    income_types = ["gifts"]


class NonTanfCashAssistanceIncomeDependency(IncomeDependency):
    """
    ``cashAssistanceOther`` — General Assistance, another state's TANF, a local fund — as
    PolicyEngine's ``financial_assistance``.

    Picked for its treatment, not its name: measured, it is the only source in TANF's unearned
    list that also counts in ``snap_gross_income`` and stays out of ``adjusted_gross_income``,
    which is what non-taxable cash aid needs.
    """

    field = "financial_assistance"
    income_types = ["cashAssistanceOther"]


class UnemploymentIncomeDependency(IncomeDependency):
    field = "unemployment_compensation"
    income_types = ["unemployment"]


class WorkersCompensationDependency(IncomeDependency):
    field = "workers_compensation"
    income_types = ["workersComp"]


class AlimonyIncomeDependency(IncomeDependency):
    field = "alimony_income"
    income_types = ["alimony"]


class ChildSupportReceivedDependency(IncomeDependency):
    """
    Child support *received*, as income.

    Distinct from ``SnapChildSupportDependency`` above, which sends child support
    *paid* as an expense (``child_support_expense``). A household can report both.
    """

    field = "child_support_received"
    income_types = ["childSupport"]


class RetirementDistributionsDependency(IncomeDependency):
    field = "taxable_ira_distributions"
    income_types = ["deferredComp"]


class SsiEarnedIncomeDependency(IncomeDependency):
    field = "ssi_earned_income"
    income_types = ["earned"]


class SsiUnearnedIncomeDependency(IncomeDependency):
    field = "ssi_unearned_income"
    income_types = ["unearned"]
    # Nurturing Futures is only offered as an income source on the CO white label, so
    # this exclusion is a no-op everywhere else. It reaches SSI, CO ANDCS and CO OAP,
    # which all read ssi_unearned_income.
    exclude_income_types = ["nurturingFutures"]


class IlAabd(Member):
    field = "il_aabd_person"


class RentDependency(Member):
    """
    Rent expense for PolicyEngine tax calculations.

    PE treats this as a person-level field for state tax calculations.
    We split the household's total rent between head and spouse only
    (the tax filers), not all adults, since this is used for tax filing purposes.
    """

    field = "rent"

    def value(self):
        # Only assign to head and spouse (tax filers)
        if not (self.member.is_head() or self.member.is_spouse()):
            return 0

        total_rent = self.screen.calc_expenses("yearly", ["rent"])

        # If married/joint filing, split between head and spouse
        if self.screen.is_joint():
            return int(total_rent / 2)

        return int(total_rent)


class IlHbwdEligible(Member):
    """Illinois HBWD eligibility determination (boolean)."""

    field = "il_hbwd_eligible"


class IlHbwdPremium(Member):
    """
    Illinois HBWD monthly premium amount (negative value).

    This represents the PREMIUM that the user will pay for HBWD insurance,
    not the value of the benefit itself. Will be a negative number.
    """

    field = "il_hbwd_person"


class HeadStart(Member):
    field = "head_start"


class EarlyHeadStart(Member):
    field = "early_head_start"


class IlBccFemaleDependency(Member):
    field = "is_female"

    def value(self):
        # We don't collect sex
        # Hardcode to True so that all households are shown the IBCCP program in results
        return True


class ReceivesMedicaidDependency(Member):
    """
    Sends whether the member currently receives Medicaid (based on user selection).
    Matches PolicyEngine's receives_medicaid input variable.
    """

    field = "receives_medicaid"

    def value(self):
        # Medicaid, CHIP/CHP, or Family Planning coverage counts as receiving Medicaid
        return self.member.has_insurance_types(("medicaid", "chp", "family_planning"))


class HasEsiDependency(Member):
    """
    Sends whether the member currently has employer-sponsored insurance.
    Matches PolicyEngine's ``has_esi`` input variable.

    Load-bearing for ACA PTC: 26 U.S.C. 36B(c)(2)(C) disqualifies anyone enrolled in an
    eligible employer plan, and PolicyEngine reads exactly this field to apply it. Without
    it an otherwise-eligible household with job-based coverage is scored as PTC-eligible.

    Sending ``False`` is equivalent to omitting the field (verified against the PE API), so
    this is safe to send unconditionally rather than returning ``None`` for the negative
    case the way ``IsMedicareEligibleDependency`` does.
    """

    field = "has_esi"

    def value(self):
        return self.member.has_insurance_types(("employer",))


class HasBccQualifyingCoverageDependency(Member):
    """
    Determines whether the member has disqualifying insurance coverage for IL BCC program.
    Matches PolicyEngine's has_bcc_qualifying_coverage input variable.
    """

    field = "has_bcc_qualifying_coverage"

    def value(self):
        # Should include everything except for family planning, emergency medicaid, and none/dont know
        return self.member.has_insurance_types(
            (
                "employer",
                "private",
                "medicaid",
                "medicare",
                "chp",
                "va",
            )
        )


class IlBccEligible(Member):
    field = "il_bcc_eligible"


class IlFppEligible(Member):
    """Output dependency for IL Family Planning Program eligibility."""

    field = "il_fpp_eligible"


class IlMpeEligible(Member):
    field = "il_mpe_eligible"


class TxHarrisRidesEligible(Member):
    field = "tx_harris_rides_eligible"


class IsVeteranDependency(Member):
    """
    Veteran status for PolicyEngine calculations.
    Used by DART and other programs that provide benefits to veterans.
    """

    field = "is_veteran"
    dependencies = ("veteran",)

    def value(self):
        return self.member.veteran or False


class TxDartBenefitPerson(Member):
    """
    Output dependency for TX DART benefit value per person.
    Returns the annual dollar value of the DART transit benefit.
    """

    field = "tx_dart_benefit_person"


class TxFpp(Member):
    """Output dependency for TX Family Planning Program benefit."""

    field = "tx_fpp_benefit"


class MspEligible(Member):
    """Output dependency for Medicare Savings Program eligibility."""

    field = "msp_eligible"


class MspCategory(Member):
    """Output dependency for Medicare Savings Program category (QMB, SLMB, QI, or NONE)."""

    field = "msp_category"


class Msp(Member):
    """Benefit value for Medicare Savings Programs"""

    field = "msp"


class MedicareQuartersOfCoverageDependency(Member):
    """
    Number of quarters of Medicare-covered employment for Part A premium calculation.

    We return 40 quarters because approximately 99% of Medicare beneficiaries have at least
    40 quarters of Medicare-covered employment, which makes Part A premium-free.

    Source: https://www.cms.gov/newsroom/fact-sheets/2026-medicare-parts-b-premiums-deductibles
    """

    field = "medicare_quarters_of_coverage"

    def value(self):
        return 40


class IsMedicareEligibleDependency(Member):
    """
    Override PolicyEngine's is_medicare_eligible calculation when we know the user has Medicare.

    PolicyEngine calculates Medicare eligibility based on age (65+) or disability pathway
    (SSDI for 24+ months). However, we don't collect months_receiving_social_security_disability,
    so disabled individuals under 65 with Medicare would fail PolicyEngine's check.

    This dependency:
    - Returns True if the member has Medicare selected (they are definitionally Medicare eligible)
    - Returns None if they don't have Medicare, letting PolicyEngine calculate eligibility
      based on age (which may show MSP to age-eligible users who don't actually have Medicare yet)
    """

    field = "is_medicare_eligible"

    def value(self):
        has_medicare = self.member.has_insurance_types(("medicare",), strict=False)
        if has_medicare:
            return True
        return None


class IsMedicaidEligibleDependency(Member):
    """
    Override PolicyEngine's is_medicaid_eligible calculation when we know the user has Medicaid.

    This is used by MSP to enforce the QI exclusion: QI is only available to Medicare beneficiaries
    who are NOT eligible for Medicaid. If the user has indicated they have Medicaid, we return True
    directly (they are definitionally Medicaid-eligible and thus ineligible for QI). If they have not
    indicated Medicaid, we return None so PolicyEngine can calculate Medicaid eligibility from age,
    income, disability, and pregnancy — ensuring applicants who would qualify for Medicaid are
    excluded from QI even if they haven't explicitly reported Medicaid enrollment.
    """

    field = "is_medicaid_eligible"

    def value(self):
        has_medicaid = self.member.has_insurance_types(("medicaid",), strict=False)
        if has_medicaid:
            return True
        return None


class FosterCareDependency(Member):
    """Foster care history, from either the self-reported tile or the relationship.

    The `fosterChild` relationship only catches a foster child listed as a household
    member under that exact value; it misses a child whose caregiver picked `child`, and
    every young adult who is themselves the head of household. `was_in_foster_care` is the
    Special Circumstances tile ("Ever in foster care, even briefly"), which catches both.

    Returns None rather than False when neither holds, so PolicyEngine computes its own
    default instead of us asserting a negative we never asked about.
    """

    field = "was_in_foster_care"
    dependencies = ("relationship", "was_in_foster_care")

    def value(self):
        if self.member.relationship == "fosterChild" or self.member.was_in_foster_care:
            return True
        return None


class EmploymentIncomeBeforeLsrDependency(IncomeDependency):
    field = "employment_income_before_lsr"
    income_types = ["wages"]


class SelfEmploymentIncomeBeforeLsrDependency(IncomeDependency):
    field = "self_employment_income_before_lsr"
    income_types = ["selfEmployment"]


class WaAppleHealthKidsEligible(Member):
    field = "wa_apple_health_kids_eligible"


class InSecondarySchoolDependency(Member):
    """
    PolicyEngine's ``is_in_secondary_school`` — secondary school, or an equivalent level of
    vocational or technical training.

    The variable has no formula and no default, so PolicyEngine reads False for everyone
    unless it is sent. Its consumers all use it as
    ``where(is_in_secondary_school, student_age_limit, non_student_age_limit)``, so an
    unsent input silently applies the lower limit.

    Means high school or equivalent vocational training — distinct from PolicyEngine's
    ``is_in_k12_school``, which covers all of K-12 and imputes ages 5–17.

    The screener has no secondary-enrollment field: ``student`` and ``student_full_time``
    ask about college, and a False there does not disprove high-school attendance. So this
    is an imputation from age alone.

    Age alone, deliberately: attendance does not depend on tax-dependency status, and gating
    on it would route this through ``HouseholdMember.is_dependent()``, whose support test
    drops exactly the 18-year-olds this input exists to keep in the assistance unit
    (MFB-1693).
    """

    field = "is_in_secondary_school"
    dependencies = ("age",)

    # US high school runs roughly ages 14-18. The upper bound is 18 rather than 17 because a
    # student in their final year is exactly the case the 18-vs-19 age limits distinguish;
    # the lower bound excludes younger K-8 children, for whom the variable is simply false.
    MIN_AGE = 14
    MAX_AGE = 18

    def value(self):
        # calc_age(), not the age column: AgeDependency sends the same reference-date age, and
        # the two disagree by a year for any member with birth_year_month — on the 18/19
        # boundary this input exists to control.
        age = self.member.calc_age()
        return self.MIN_AGE <= age <= self.MAX_AGE
