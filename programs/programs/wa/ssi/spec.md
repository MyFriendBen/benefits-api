# Implement Supplemental Security Income (SSI) (WA) Program

## Program Details

- **Program**: Supplemental Security Income (SSI)
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-04-27

## Eligibility Criteria

1. **Aged 65 or older**
   - Screener fields: `household_member.age`, `household_member.birth_year_month`
   - Source: 42 U.S.C. § 1382c(a)(1)(A); 20 CFR § 416.202(a). Aged status is one of three categorical entry routes to SSI.

2. **Disability — medically determinable physical or mental impairment expected to last 12+ continuous months or result in death; for adults, the impairment must prevent substantial gainful activity (SGA)**
   - Screener fields: `household_member.long_term_disability`
   - Note: The screener captures the 12-month duration test via `long_term_disability` (true/false). It cannot perform SSA's medical adjudication or vocational analysis (Listings of Impairments, Medical-Vocational Guidelines), so eligibility is treated as a *likely-eligible* signal pending SSA review. The general `disabled` flag without `long_term_disability` is **not** sufficient — see Scenario 10 below.
   - Source: 42 U.S.C. § 1382c(a)(3); 20 CFR §§ 416.905, 416.906; SSA Blue Book.

3. **Statutory blindness — central visual acuity ≤ 20/200 in the better eye with corrective lens, or visual field ≤ 20°**
   - Screener fields: `household_member.visually_impaired`
   - Note: The screener's `visually_impaired` flag is broader than SSA's statutory definition of blindness; it should be treated as a *likely-eligible* signal pending SSA verification of acuity/field measurements.
   - Source: 42 U.S.C. § 1382c(a)(2); 20 CFR §§ 416.981, 416.983.

4. **U.S. citizen, U.S. national, or qualified alien meeting SSI's narrow PRWORA categories**
   - Screener fields: program-level `legal_status_required` (set to `["citizen", "gc_5plus"]` in the program config); post-results citizenship filter chip
   - Note: Most non-citizens face strict SSI alien restrictions: 7-year limits for refugees/asylees/Cuban-Haitian entrants, 40-quarter requirements for LPRs, and U.S.-military-service exemptions. The screener filters at the program-config level and via the citizenship chip on the Results UI; immigration sub-status is not collected as a household-member field.
   - Source: 8 U.S.C. § 1612(a)(2); 42 U.S.C. § 1382c(a)(1)(B).

5. **Resident of one of the 50 states, DC, or the Northern Mariana Islands**
   - Screener fields: `screen.white_label`, `screen.zipcode`
   - Source: 42 U.S.C. § 1382c(a)(1)(B)(i); 20 CFR § 416.1603. WA white label + WA ZIP code satisfies state residency for screener purposes.

6. **Not already receiving SSI**
   - Screener fields: `screen.has_ssi`
   - Note: Captured via the "Current household benefits" step. Households already receiving SSI are filtered out to prevent duplicate-enrollment recommendations.
   - Source: General SSI policy — households cannot be screened into a benefit they already receive.

7. **Countable income below the Federal Benefit Rate (FBR)**
   - Screener fields: `household_member.has_income`, `income_streams (type, amount, frequency)`
   - Note: Income streams are collected, but countable-income computation (general $20 exclusion, earned-income $65 + ½ remaining exclusion, in-kind support and maintenance reductions, deeming) is non-trivial. Detailed math is delegated to PolicyEngine; the screener applies a conservative pre-filter against the 2026 FBR ($994 individual / $1,491 couple).
   - Source: 42 U.S.C. § 1382(a); 20 CFR §§ 416.1100–416.1182.

8. **Countable resources at or below $2,000 (individual) or $3,000 (couple)**
   - Screener fields: `screen.household_assets`
   - Note: `household_assets` is a single conservative number; the screener cannot separate countable from excluded resources (home, one vehicle, household goods, burial space, etc.). Pre-filter on the raw asset value, then defer to PolicyEngine for the precise countable-resource calculation.
   - Source: 42 U.S.C. § 1382(a)(3); 20 CFR §§ 416.1201, 416.1205, 416.1210.

9. **Spousal income/resource deeming — for an eligible individual living with an ineligible spouse**
   - Screener fields: `household_member.relationship`, `income_streams`, `household_assets`
   - Note: Household composition (head + spouse) is captured. The screener does not perform deeming math; it is left to PolicyEngine.
   - Source: 20 CFR §§ 416.1160, 416.1163.

10. **Parental deeming — for child applicants under 18 living with parents**
    - Screener fields: `household_member.relationship`, `household_member.age`, `income_streams`, `household_assets`
    - Note: Household composition (parent/child) is captured. The screener does not perform parent-to-child deeming; it is left to PolicyEngine.
    - Source: 20 CFR §§ 416.1165, 416.1202.

11. **Filed for / receiving any other applicable benefits the applicant is entitled to (Social Security retirement, SSDI, pensions, etc.)**
    - Screener fields: `income_streams (sSRetirement, sSDisability, sSSurvivor, sSDependent, pension, veteran)`
    - Note: This is enforced as an income offset (counts as unearned income against the FBR), not a hard disqualifier. SSA requires SSI applicants to apply for any other benefits they may be entitled to before/while receiving SSI.
    - Source: 20 CFR § 416.210; 42 U.S.C. § 1382(e)(2).

12. **Not absent from the United States for 30+ consecutive days** ⚠️ *data gap*
    - Note: The screener does not collect U.S.-presence/absence data. This is a procedural verification at the application stage; affects a small subset of applicants.
    - Source: 42 U.S.C. § 1382(f); 20 CFR § 416.1327.
    - Impact: Low

13. **Not a resident of a public institution (jail, prison, hospital, nursing facility, etc.) — with limited exceptions** ⚠️ *data gap*
    - Note: The screener does not collect institutional-residence status. SSI is generally suspended during institutional residence longer than a calendar month.
    - Source: 42 U.S.C. § 1382(e)(1); 20 CFR § 416.211.
    - Impact: Low

14. **Not a fugitive felon, parole or probation violator, or in confinement for a felony** ⚠️ *data gap*
    - Note: The screener does not collect criminal-justice status. Disqualification under this rule affects a small population.
    - Source: 42 U.S.C. § 1382(e)(4)–(5); 20 CFR § 416.1339.
    - Impact: Low

15. **Procedural: applicant assigns rights to other federal benefits when applicable** ⚠️ *not evaluable*
    - Note: Procedural; happens at the application stage, not pre-screening. Out of scope for the screener.
    - Source: 20 CFR § 416.210.
    - Impact: Low

## Benefit Value

SSI benefits equal the **Federal Benefit Rate (FBR) minus countable income**. As of January 2026 (after the 2.8% COLA):

| Recipient Type | Monthly FBR | Annual Value |
|---|---|---|
| Eligible individual | $994 | $11,928 |
| Eligible couple | $1,491 | $17,892 |

Washington does **not** pay a state supplement to SSI for most aged, blind, or disabled adults living independently. Some narrow categories — e.g., individuals in certain residential care facilities — receive a small state supplement administered by Washington DSHS, but those programs are out of scope for the screener at launch. The estimated benefit value should be the federal SSI amount as computed by PolicyEngine for the household, reduced by countable income via the SSA exclusions (general $20 + earned $65 + ½ remaining earned).

- Source: [SSA — 2026 SSI Federal Payment Amounts](https://www.ssa.gov/oact/cola/SSI.html); [SSA — 2026 COLA Fact Sheet](https://www.ssa.gov/news/en/cola/factsheets/2026.html).

## Implementation Coverage

- ✅ Evaluable criteria: 11
- ⚠️  Data gaps: 4

11 of 15 total eligibility criteria can be evaluated with current screener fields. The screener confidently identifies applicants who are demographically and categorically in scope (aged 65+, long-term disabled, visually impaired) with WA residence and a qualifying citizenship status, who are not already receiving SSI, and whose income/asset profile pre-filters within the 2026 FBR and resource ceilings. Spousal and parental deeming household composition is captured for PolicyEngine to evaluate. Income and resource feasibility are conservative pre-filters; the precise countable-income calculation, asset exclusions, and deeming math are delegated to PolicyEngine. Primary gaps are SSA's medical/vocational disability adjudication (handled at application), U.S. absence (Low impact), institutional-residence status (Low impact), and fugitive/incarceration status (Low impact) — all handled procedurally at the SSA application stage.

## Acceptance Criteria

- [ ] Scenario 1 (Aged 65+ — No Income, No Resources): User should be **eligible** with $11,928/year
- [ ] Scenario 2 (Long-Term Disabled Adult Under 65 — No Income): User should be **eligible** with $11,928/year
- [ ] Scenario 3 (Visually Impaired Adult — No Income): User should be **eligible** with $11,928/year
- [ ] Scenario 4 (Aged 65+ with Unearned Income Above FBR): User should be **ineligible**
- [ ] Scenario 5 (Aged 65+ with Countable Resources Above $2,000): User should be **ineligible**
- [ ] Scenario 6 (Eligible Aged Couple — Both 65+, No Income): User should be **eligible** with $17,892/year
- [ ] Scenario 7 (Adult Under 65 Without Disability or Visual Impairment): User should be **ineligible**
- [ ] Scenario 8 (Already Receiving SSI — Duplicate Enrollment): User should be **ineligible**
- [ ] Scenario 9 (Long-Term Disabled Child — Parental Deeming Under Limits): User should be **eligible**
- [ ] Scenario 10 (General Disability Flag Only — Long-Term Disability Not Set): User should be **ineligible**
- [ ] Scenario 11 (Aged 65+ with Partial SS Retirement Income — Reduced Benefit): User should be **eligible** with ~$6,168/year ($514/month)

## Test Scenarios

### Scenario 1: Aged 65+, No Income, No Resources

**What we're checking**: Cleanest aged-only path — confirms the screener treats age 65+ as a sufficient categorical entry into SSI when income and resources are clearly under thresholds.

**Expected**: Eligible (full federal individual FBR — $994/month, $11,928/year)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70` (born 1956), Head of Household, U.S. Citizen, no disability, no visual impairment, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: This is the canonical aged-only happy path. Validates that age alone (with zero income and resources) is treated as sufficient categorical entry into SSI, independent of disability or blindness flags.

---

### Scenario 2: Long-Term Disabled Adult Under 65, No Income

**What we're checking**: Disability path via the `long_term_disability` flag for an adult well below retirement age, with no income or resources.

**Expected**: Eligible (full federal individual FBR — $994/month, $11,928/year)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `45` (born 1981), Head of Household, U.S. Citizen, **long-term disability: true**, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates the disability route is honored independently of age, and that `long_term_disability` (not the general `disabled`) is the field used to satisfy SSI's 12-month duration requirement.

---

### Scenario 3: Visually Impaired Adult, No Income

**What we're checking**: Blindness path via the `visually_impaired` flag for a working-age adult with no income or resources.

**Expected**: Eligible (full federal individual FBR — $994/month, $11,928/year)

**Steps**:
- **Location**: ZIP `98052`, County `King`
- **Household**: 1 person
- **Person 1**: Age `40` (born 1986), Head of Household, U.S. Citizen, **visually impaired: true**, no other disability, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms the blind path is enabled. The screener's `visually_impaired` field is broader than SSA's statutory blindness, but should still surface SSI as a likely-eligible match for SSA review.

---

### Scenario 4: Aged 65+ with Unearned Income Above FBR

**What we're checking**: Income disqualification — Social Security retirement income that exceeds the FBR for an individual after the $20 general exclusion.

**Expected**: Not eligible (countable unearned income > FBR)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `68` (born 1958), Head of Household, U.S. Citizen, no disability, Social Security retirement income: `$1,200/month`
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms the income test enforces the FBR ceiling. $1,200 SS retirement minus the $20 general exclusion = $1,180 countable, which is above the 2026 individual FBR of $994.

---

### Scenario 5: Aged 65+ with Countable Resources Above $2,000

**What we're checking**: Resource disqualification — household assets above the individual SSI resource limit.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70` (born 1956), Head of Household, U.S. Citizen, no disability, no income
- **Insurance**: None
- **Household assets**: `$5,000`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms the resource ceiling is enforced. Note: the screener's `household_assets` is a single conservative number; downstream calculation must apply SSA's resource exclusions (home, one vehicle, burial space) when integrated with PolicyEngine. This pre-filter accepts that some applicants with excludable wealth may be incorrectly denied at the screener stage.

---

### Scenario 6: Eligible Aged Couple — Both 65+, No Income

**What we're checking**: Couple FBR path — both spouses age-eligible, no income or assets.

**Expected**: Eligible (couple benefit at $1,491/month FBR for 2026, $17,892/year, shared between members)

**Steps**:
- **Location**: ZIP `98109`, County `King`
- **Household**: 2 people
- **Person 1 (Head)**: Age `70` (born 1956), U.S. Citizen, no disability, no income
- **Person 2 (Spouse)**: Age `68` (born 1958), U.S. Citizen, no disability, no income
- **Insurance**: None for both
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates couple FBR application and that household composition is correctly evaluated for two-person eligibility under SSI's eligible-couple rules.

---

### Scenario 7: Adult Under 65 Without Disability or Visual Impairment

**What we're checking**: Categorical disqualification — fails all three categorical entry prongs (age, blindness, disability).

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `35` (born 1991), Head of Household, U.S. Citizen, no disability, no visual impairment, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms an adult who fails all three categorical entry routes is correctly filtered out, even with zero income and assets. Without satisfying age, blindness, or disability, SSI is unavailable regardless of financial need.

---

### Scenario 8: Already Receiving SSI — Duplicate Enrollment

**What we're checking**: Duplicate enrollment — current SSI recipient should not be shown as a new recommendation.

**Expected**: Not eligible (already has)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70` (born 1956), Head of Household, U.S. Citizen, no disability, SSI income: `$994/month`
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: **Currently receiving SSI** (`has_ssi = true`)

**Why this matters**: Validates the "already has" path so existing recipients aren't redundantly listed under "Programs Found".

---

### Scenario 9: Long-Term Disabled Child — Parental Deeming Under Limits

**What we're checking**: Child applicant — parental deeming math left to PolicyEngine; the screener should still surface SSI as a candidate for the household with a long-term disabled minor.

**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 3 people
- **Person 1 (Head)**: Age `40` (born 1986), U.S. Citizen, no disability, wages: `$1,500/month`
- **Person 2 (Spouse)**: Age `38` (born 1988), U.S. Citizen, no disability, no income
- **Person 3 (Child)**: Age `8` (born 2018), U.S. Citizen, **long-term disability: true**, no income
- **Insurance**: Employer for all three
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms child-SSI eligibility is surfaced when the disabled minor lives with low-income parents. Exact benefit value depends on PolicyEngine's parent-to-child deeming computation; the screener's job is to identify the household as a candidate.

---

### Scenario 10: General Disability Flag Only — Long-Term Disability Not Set

**What we're checking**: SSI requires a disability of 12+ months. A short-term `disabled` flag without `long_term_disability` should not qualify, mirroring the TX SSDI guidance that the long-term flag is the correct field for the duration test.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `45` (born 1981), Head of Household, U.S. Citizen, **disabled: true**, **long_term_disability: false**, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates that the implementation reads `long_term_disability` (not the general `disabled` flag) as the field satisfying SSI's 12-month duration test. A general "disabled" flag without the long-term qualifier is not sufficient on its own.

---

### Scenario 11: Aged 65+ with Partial SS Retirement Income — Reduced Benefit

**What we're checking**: Partial offset — eligible with reduced SSI when unearned income is below FBR. Confirms that some unearned income reduces, but does not eliminate, the SSI benefit.

**Expected**: Eligible (reduced benefit; approximately $514/month, $6,168/year)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `72` (born 1954), Head of Household, U.S. Citizen, no disability, Social Security retirement income: `$500/month`
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates that some unearned income reduces, but does not eliminate, the SSI benefit. Expected approximate value: $994 (2026 FBR) − ($500 − $20 general exclusion) = `$514/month`. The screener should flag eligibility; PolicyEngine performs the precise math.

---

### Out-of-band: Non-citizen without qualified status

The SSI alien restriction (8 U.S.C. § 1612(a)(2)) is enforced through the program's `legal_status_required` configuration (`["citizen", "gc_5plus"]`) and the post-results citizenship filter chip on the Results UI, not via a household-member field on the screen. As a result, this case is not represented in the JSON validation suite — it is verified manually by toggling the citizenship filter and confirming that `wa_ssi` disappears for users who do not select an SSI-qualifying status.

## Research Sources

- [SSA — Supplemental Security Income (SSI) Home](https://www.ssa.gov/ssi/)
- [SSA — Apply for SSI](https://www.ssa.gov/apply/ssi)
- [SSA — Understanding SSI](https://www.ssa.gov/ssi/text-understanding-ssi.htm)
- [SSA — 2026 SSI Federal Payment Amounts](https://www.ssa.gov/oact/cola/SSI.html)
- [SSA — 2026 Cost-of-Living Adjustment Fact Sheet](https://www.ssa.gov/news/en/cola/factsheets/2026.html)
- [Washington DSHS — Cash Assistance Programs](https://www.dshs.wa.gov/esa/community-services-offices/cash-assistance)
- [Legal Information Institute — 42 U.S.C. Chapter 7, Subchapter XVI (SSI)](https://www.law.cornell.edu/uscode/text/42/chapter-7/subchapter-XVI)
- [eCFR — 20 CFR Part 416 (SSI for the Aged, Blind, and Disabled)](https://www.ecfr.gov/current/title-20/chapter-III/part-416)

## JSON Test Cases

File: `validations/management/commands/import_validations/data/wa_ssi.json`

Scenarios 1–11. Updated `eligible` values:
- Scenarios 1, 2, 3, 6, 9, 11: `true`
- Scenarios 4, 5, 7, 8, 10: `false`

## Generated Program Configuration

File: `programs/management/commands/import_program_config_data/data/wa_ssi_initial_config.json`

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-04-27 | cdadams | Initial discovery spec — 11 evaluable criteria, 4 data gaps, 11 test scenarios, 2026 FBR amounts ($994 individual / $1,491 couple). |
