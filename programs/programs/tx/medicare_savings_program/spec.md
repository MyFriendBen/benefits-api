# Implement Medicare Savings Program (TX) Program

## Program Details

- **Program**: Medicare Savings Program
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-11

## Eligibility Criteria

1. **QMB: Income at or below 100% of Federal Poverty Level**
   - Screener fields:
     - `household_size`
     - `IncomeStream.amount`
     - `IncomeStream.frequency`
   - Source: Section Q-2000, Appendix IX

2. **SLMB: Income between 100% and 120% of Federal Poverty Level**
   - Screener fields:
     - `household_size`
     - `IncomeStream.amount`
     - `IncomeStream.frequency`
   - Source: Section Q-3000, Appendix IX

3. **QI: Income between 120% and 135% of Federal Poverty Level**
   - Screener fields:
     - `household_size`
     - `IncomeStream.amount`
     - `IncomeStream.frequency`
   - Source: Section Q-5000, Appendix IX

4. **QMB/SLMB/QI: Resources not exceeding $9,430 for individual or $14,130 for couple (2024)**
   - Screener fields:
     - `household_assets`
     - `HouseholdMember.relationship`
   - Note: The resource limit is determined by marital status (individual vs. couple), not by household size — there is no defined limit for households with 3 or more members. The couple limit ($14,130) applies when a spouse is present (use `screen.is_joint()` or check for a spouse relationship); otherwise the individual limit ($9,430) applies. `household_size` is not the right field to select the limit. ⚠️ Data gap: `household_assets` is a household-level total that includes assets of non-eligible members (e.g., adult children). MSP only counts the applicant's and spouse's resources, so passing `household_assets` directly can produce false negatives when non-eligible household members hold significant assets.
   - Note on resource exclusions: Many asset types are excluded from the resource count under MSP rules: homestead, one vehicle, household goods, personal effects, burial funds up to $1,500, and life insurance with face value up to $1,500. The screener collects a single `household_assets` total, so users may unknowingly include excluded items — this can produce false negatives. This is surfaced in the initial program config description to set user expectations.
   - Source: Section Q-1300, Appendix IX, Chapter F - Resources

5. **Must be Texas resident**
   - Note: Handled via white label association — the program is only shown to users of the `tx` white label, so no screener field check is needed.
   - Source: Chapter D - Non-Financial Eligibility Requirements

6. **QI: Not eligible for Medicaid**
   - Screener fields:
     - `HouseholdMember.insurance.medicaid` (direct check — definitionally Medicaid-eligible)
     - `HouseholdMember` birth month/year (age, for PE fallback calculation)
     - `HouseholdMember.pregnant` (for PE fallback calculation)
     - `HouseholdMember.disabled` / `long_term_disability` (for PE fallback calculation)
     - `IncomeStream.amount`, `IncomeStream.frequency` (for PE fallback calculation — covered by criteria #1–3)
     - `household_assets` (for PE fallback calculation via `ssi_countable_resources` — covered by criteria #4)
   - PolicyEngine dependency: `IsMedicaidEligibleDependency` (`is_medicaid_eligible`)
   - Note: Two-step evaluation. Step 1: If `insurance.medicaid` is True, `IsMedicaidEligibleDependency` returns `True` — PolicyEngine sees the member as Medicaid-eligible and disqualifies them from QI. Step 2: If `insurance.medicaid` is not indicated, the dependency returns `None` and PolicyEngine calculates `is_medicaid_eligible` from age, income, disability, and pregnancy (`medicaid_category`). If PolicyEngine finds them eligible, they are still disqualified from QI. This mirrors `IsMedicareEligibleDependency` and prevents PolicyEngine from reaching a different Medicaid eligibility conclusion than what the user has reported.
   - Source: Section Q-5000

7. **Must be entitled to Medicare Part A (hospital insurance)**
   - Screener fields:
     - `HouseholdMember.insurance.medicare` (direct check — definitionally Medicare-eligible)
     - `HouseholdMember` birth month/year (age, for PE fallback — age pathway: `age >= 65`)
     - `IncomeStream.type = sSDisability`, `IncomeStream.amount`, `IncomeStream.frequency` (for PE fallback — disability pathway: `social_security_disability > 0`)
     - `months_receiving_social_security_disability` ⚠️ *not collected* — see data gap below
   - PolicyEngine dependency: `IsMedicareEligibleDependency` (`is_medicare_eligible`)
   - Note: Two-step evaluation. Step 1: If `insurance.medicare` is True, `IsMedicareEligibleDependency` returns `True` — definitionally Medicare-eligible, bypassing PolicyEngine's calculation entirely. Step 2: If `insurance.medicare` is not indicated, the dependency returns `None` and PolicyEngine calculates via two pathways: age (`age >= 65`, reliable) or SSDI duration (`social_security_disability > 0` AND `months_receiving_social_security_disability >= 24`). The disability pathway is unreliable because `months_receiving_social_security_disability` is not collected — disabled users under 65 who have Medicare but haven't indicated it will produce a false negative on this criterion. QMB/SLMB/QI all require Part A entitlement.
   - Data gap ⚠️: `months_receiving_social_security_disability` is not collected. Disabled individuals under 65 with Medicare who do not indicate `insurance.medicare` may be incorrectly found ineligible via the disability pathway. Impact: Low — the direct `insurance.medicare` check covers the vast majority of Medicare beneficiaries.
   - Source: Section Q-1000, Q-2000, Q-3000, Q-5000

8. **Must be U.S. citizen or qualified non-citizen**
   - Screener fields: `legal_status_required` (program config)
   - Note: Handled at the program level via `legal_status_required`. MSP follows Medicaid citizenship requirements; the program config restricts results to citizens and qualified non-citizens.
   - Source: Chapter D - Non-Financial Eligibility Requirements

9. **Must provide Social Security Number or apply for one** ⚠️ *data gap*
   - Note: No SSN field in screener. Required for all MSP applicants unless good cause exception applies.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Medium

10. **Cannot be an inmate of a public institution** ⚠️ *data gap*
   - Note: No incarceration status field. Inmates of public institutions are ineligible for MSP.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Low

11. **Deeming rules (spouse-to-spouse and parent-to-child)**
   - Spouse-to-spouse: If the applicant lives with an ineligible (non-applying) spouse, that spouse's income and resources are factored into the eligibility determination.
   - Parent-to-child: For an eligible child under 18 who lives with one or both parents, is not married, and is eligible for Medicaid, a parent's income (even if earned) is treated as unearned income when deemed to the child. Deeming stops the month after the child turns 18.
   - Deeming does not apply when the ineligible spouse or parent is in an institutional setting.
   - Source: [E-7100 Living Arrangement (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/e-7100-living-arrangement), [D-4200 Living Arrangements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/d-4200-living-arrangements), Chapter E - Income Determination, Chapter F - Resources
   - Impact: Medium

## Benefit Value

MSP covers Medicare premium costs per eligible person per month. The benefit value is the sum across all eligible household members, expressed as an annual total.

| Sub-program | Covers | 2025 Monthly Value | 2025 Annual Value |
|---|---|---|---|
| QMB | Part A + Part B premiums | $0–$185+ (most enrollees have free Part A) | $0–$2,220+ |
| SLMB | Part B premium only | $185/month | $2,220/year |
| QI | Part B premium only | $185/month | $2,220/year |

**Notes:**
- Part B premium is set annually by CMS ($174.70/month in 2024, $185/month in 2025).
- Most enrollees 65+ have 40+ work quarters → premium-free Part A → QMB benefit equals the Part B premium ($2,220/year in 2025).
- For multi-member households, the annual value is the sum across all eligible members (e.g., two SLMB-eligible spouses = $4,440/year in 2025).

## Implementation Coverage

- ✅ Evaluable criteria: 9
- ⚠️  Data gaps: 3 (SSN requirement, incarceration status, `months_receiving_social_security_disability` for disabled Medicare beneficiaries under 65)

> **Note on QDWI:** The QDWI (Qualified Disabled and Working Individuals) sub-program is not surfaced by this implementation. PolicyEngine does not model the QDWI benefit value (`msp_benefit_value` has no QDWI branch), and the program's primary eligibility requirement — that the applicant lost premium-free Medicare Part A by returning to work — cannot be evaluated with current screener fields. Given these limitations, QDWI is excluded from the screener results.

This implementation covers the three remaining MSP sub-programs: QMB, SLMB, and QI. Of the 11 major eligibility criteria for these programs, 9 can be evaluated with current screener fields or program config, while 3 cannot (SSN requirement, incarceration status, and SSDI duration for disabled Medicare beneficiaries under 65). The evaluable criteria include all income thresholds (100%, 120%, 135% FPL), resource limits ($9,430/$14,130 for individual/couple), Medicare enrollment status, Texas residency, Medicaid exclusion (QI only), citizenship/immigration status (via `legal_status_required` program config), and deeming rules (spouse-to-spouse and parent-to-child). Resource limit checks are accurate for households of 1–2 (the vast majority of MSP cases); for households > 2, a custom dependency zeroes out `household_assets` before passing it to PolicyEngine (since `household_assets` includes non-eligible members' assets and MSP only counts the applicant's and spouse's resources), treating the resource test as passing rather than risk a false negative. Medicare eligibility (criteria #7) is evaluated via `IsMedicareEligibleDependency`: if `insurance.medicare` is True it returns `True` directly, bypassing PolicyEngine's SSDI-duration check (which would fail for disabled users under 65 since we don't collect `months_receiving_social_security_disability`); otherwise it returns `None` and PolicyEngine falls back to the age pathway (`age >= 65`). The QI Medicaid exclusion (criteria #6) is evaluated via a parallel `IsMedicaidEligibleDependency`: if `insurance.medicaid` is True it returns `True` directly; otherwise PolicyEngine calculates Medicaid eligibility from age, income, disability, and pregnancy — ensuring applicants who would qualify for Medicaid are excluded from QI even if they haven't explicitly reported Medicaid enrollment.

## Research Sources

- [Appendix IX - Medicare Savings Program (MSP) Income and Resource Limits Table (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information)
- [Section Q-1000 - Medicare Savings Programs Overview (42 U.S.C. § 1396a, 42 CFR § 435.4)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview)
- [Chapter A - General Information and MEPD Eligibility Groups (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-a-general-information-mepd-groups)
- [Chapter B - Application Process and Redetermination Requirements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-b-applications-redeterminations)
- [Chapter C, Rights and Responsibilities](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-c-rights-responsibilities)
- [Chapter D - Non-Financial Eligibility Requirements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-d-non-financial)
- [Chapter E - Income Determination and Counting Rules (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-e-general-income)
- [Chapter F - Resource Determination and Exclusions (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-f-resources)
- [E-7100 Living Arrangement (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/e-7100-living-arrangement)
- [D-4200 Living Arrangements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/d-4200-living-arrangements)

## Acceptance Criteria

[ ] Scenario 1 (QMB Eligible - Single Senior with Social Security Income): User should be **eligible** (benefit amount: $2,220/year)
[ ] Scenario 2 (SLMB Eligible - Single Senior with Income in 100-120% FPL Range): User should be **eligible** (benefit amount: $2,220/year)
[ ] Scenario 3 (QI Eligible - Single Senior with Income in 120-135% FPL Range): User should be **eligible** (benefit amount: $2,220/year)
[ ] Scenario 4 (QMB Eligible - Single Senior with Income Exactly at 100% FPL): User should be **eligible** (benefit amount: $2,220/year)
[ ] Scenario 5 (Ineligible - Income Above 135% FPL Disqualifies All MSP Categories): User should be **ineligible**
[ ] Scenario 8 (QMB Eligible - Senior Age 75 Well Above Minimum Age): User should be **eligible** (benefit amount: $2,220/year)
[ ] Scenario 10 (Already Receiving Medicaid - QI Exclusion Test): User should be **ineligible**
[ ] Scenario 12 (Mixed Household - Eligible Senior with Non-Eligible Adult Child): User should be **eligible** (benefit amount: $2,220/year — 1 eligible member)
[ ] Scenario 13 (Multiple Eligible Members - Married Couple Both Qualifying for SLMB): User should be **eligible** (benefit amount: $4,440/year — 2 eligible members × $2,220)
[ ] Scenario 15 (Spouse-to-Spouse Deeming - Ineligible Due to Deemed Spouse Income): User should be **ineligible**
[ ] Scenario 16 (Resource Boundary - Assets Exactly at Individual Limit): User should be **eligible** (benefit amount: $2,220/year)
[ ] Scenario 17 (Earned Income Exclusion - Wages Exceeding Gross Income Limits): User should be **eligible** (benefit amount: $2,220/year)
[ ] Scenario 18 (3+ Person Household - Assets Above Individual Limit, Data Gap): User should be **ineligible** (household_assets exceeds individual resource limit; non-eligible member's assets cannot be separated — known false negative)
[ ] Scenario 19 (Single Individual - Assets Above Individual Limit, Below Couple Limit): User should be **ineligible**

## Test Scenarios

### Scenario 1: QMB Eligible - Single Senior with Social Security Income
**What we're checking**: Validates that a single 65-year-old Medicare beneficiary with income at 100% FPL and minimal assets qualifies for QMB (Qualified Medicare Beneficiary) program
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `January 1961` (age 65), Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Income amount: `$1,255` per month, Has other insurance: `No`
- **Assets**: Total household assets: `$5,000`
- **Current Benefits**: Not currently receiving Medicaid or other assistance

**Why this matters**: The most common QMB scenario — a single senior on Medicare with Social Security income at the 100% FPL threshold. QMB is the most comprehensive sub-program and tests the baseline eligibility for the program's primary target population.

---

### Scenario 2: SLMB Eligible - Single Senior with Income in 100-120% FPL Range
**What we're checking**: Validates SLMB eligibility for a Medicare beneficiary whose income exceeds the QMB limit but falls below 120% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,380`, Frequency: `Monthly`
- **Assets**: Total household assets: `$8,000`

**Why this matters**: Tests SLMB eligibility with income clearly between 100% ($1,255/mo) and 120% ($1,506/mo) FPL, confirming the system routes correctly to the SLMB sub-program when income exceeds the QMB threshold.

---

### Scenario 3: QI Eligible - Single Senior with Income in 120-135% FPL Range
**What we're checking**: Tests QI eligibility with income between 120% and 135% FPL, verifying the upper income tier is correctly evaluated
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `75001`, Select county `Collin`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,632`, Frequency: `Monthly`, Citizenship: `U.S. Citizen`
- **Assets**: Total household assets: `$9,400`
- **Current Benefits**: Not currently receiving Medicaid

**Why this matters**: Tests that the QI income tier (120-135% FPL) is correctly identified. Income of $1,632/mo falls between the SLMB ceiling ($1,506/mo at 120% FPL) and QI ceiling ($1,694/mo at 135% FPL).

---

### Scenario 4: QMB Eligible - Single Senior with Income Exactly at 100% FPL
**What we're checking**: Validates that countable income exactly at 100% FPL qualifies for QMB (at or below threshold)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `75001`, Select county `Collin`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,275` monthly, Assets: `$8,000` (below $9,430 resource limit)

**Why this matters**: Tests the boundary condition where countable income is exactly at the 100% FPL threshold ($1,255/mo). Gross SS of $1,275 minus the $20 general exclusion yields countable income of exactly $1,255 — the QMB ceiling. Validates that the 'at or below' logic is implemented correctly (≤, not <) and does not exclude applicants at the exact threshold.

---

### Scenario 5: Ineligible - Income Above 135% FPL Disqualifies All MSP Categories
**What we're checking**: Validates that applicants with income exceeding 135% FPL are correctly denied for all Medicare Savings Program categories
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,800` per month, Not disabled, Not receiving Medicaid
- **Assets**: Total household assets: `$5,000`

**Why this matters**: MSP uses SSI income methodology, which applies a $20 general exclusion to unearned income before comparing to the FPL threshold. Countable income is $1,800 − $20 = $1,780/mo, which exceeds the 135% FPL ceiling ($1,760.63/mo at 2025 FPL), ruling out all three sub-programs (QMB/SLMB/QI). This single case validates all income ceiling logic across the program.

---

### Scenario 8: QMB Eligible - Senior Age 75 Well Above Minimum Age
**What we're checking**: Validates that seniors well above the typical Medicare eligibility age (65) remain eligible for QMB when meeting income and resource requirements
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1951` (age 75), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$950`, Frequency: `Monthly`
- **Assets**: Total household assets: `$8,000`

**Why this matters**: Confirms that MSP does not have an upper age limit and that seniors significantly older than 65 can still qualify for QMB. Important because many seniors in their 70s and 80s have limited fixed incomes.

---

### Scenario 10: Already Receiving Medicaid - QI Exclusion Test
**What we're checking**: Tests that applicants already receiving Medicaid are excluded from QI (Qualifying Individual) program per Section Q-5000
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Relationship: `Head of Household`, Has Medicare: `Yes`, Has Medicaid: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,600` per month (within QI range at ~127.5% FPL)
- **Assets**: Total household assets: `$5,000`

**Why this matters**: Validates the critical exclusion rule in Section Q-5000 — QI is specifically designed for Medicare beneficiaries who are NOT eligible for Medicaid. The Medicaid exclusion prevents improper benefit stacking. Income of $1,600/mo is in the QI range (~127.5% FPL, between 120% and 135% FPL), so Medicaid is the only disqualifying factor.

---

### Scenario 12: Mixed Household - Eligible Senior with Non-Eligible Adult Child
**What we're checking**: Tests multi-member household where head of household qualifies for SLMB but adult child does not have Medicare, ensuring individual eligibility is properly assessed
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1958` (age 68), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,350` monthly
- **Person 2 (Adult Child)**: Birth month/year: `June 1988` (age 37), Relationship: `Child`, Has Medicare: `No`, Has income: `Yes`, Income type: `Wages`, Amount: `$2,800` monthly
- **Assets**: Total household assets: `$8,500`

**Why this matters**: Validates that MSP eligibility is assessed per member — the senior with Medicare qualifies even though the adult child does not. Ensures the system doesn't incorrectly deny the senior due to the child's presence or income.

---

### Scenario 13: Multiple Eligible Members - Married Couple Both Qualifying for SLMB
**What we're checking**: Tests that multiple household members can each qualify for MSP benefits when both meet SLMB eligibility criteria
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1959` (age 67), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,100` monthly
- **Person 2 (Spouse)**: Birth month/year: `March 1960` (age 66), Relationship: `Spouse`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$900` monthly
- **Assets**: Total household assets: `$12,000`
- **Current Benefits**: Not receiving Medicaid or other assistance

**Why this matters**: Validates that the system correctly handles households where multiple members independently qualify. Combined income of $2,000/mo for a household of 2 is ~117.5% of the 2-person FPL, placing them in the SLMB range (100–120% FPL). Assets of $12,000 exceed the individual resource limit ($9,430) but fall below the couple limit ($14,130), so this test only passes if the system correctly applies the couple limit.

---

### Scenario 15: Spouse-to-Spouse Deeming - Ineligible Due to Deemed Spouse Income
**What we're checking**: Tests that an ineligible (non-applying) spouse's income is deemed to the applicant, making them ineligible for all MSP sub-programs even though their own income would qualify them for QMB
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1959` (age 67), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$800` monthly
- **Person 2 (Spouse)**: Birth month/year: `March 1962` (age 64), Relationship: `Spouse`, Has Medicare: `No`, Has income: `Yes`, Income type: `Wages`, Amount: `$3,200` monthly
- **Assets**: Total household assets: `$8,000`
- **Current Benefits**: Not receiving Medicaid or other assistance

**Why this matters**: MSP uses SSI income methodology, which applies exclusions before comparing to the FPL threshold: (1) $20 general exclusion applied to unearned income first, (2) $65 earned income exclusion, (3) 50% of remaining earned income excluded. The applicant's own SS income ($800/mo) counts as $780 after the $20 exclusion. Without deeming, $780 is well below the 1-person QMB threshold (~$1,255/mo), so they would qualify. With the spouse's wages deemed in: ($3,200 − $20 − $65) × 0.50 = $1,557.50 countable, for a combined countable income of $2,337.50/mo — above the 135% FPL ceiling for a 2-person household ($2,299.50/mo). This disqualifies them from all sub-programs and directly validates that spouse-to-spouse deeming is applied and can change eligibility outcomes.

---

### Scenario 16: Resource Boundary - Assets Exactly at Individual Limit
**What we're checking**: Validates that assets exactly equal to the individual resource limit ($9,430) do not disqualify the applicant — the rule is "not exceeding," meaning the limit is inclusive
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,000` monthly
- **Assets**: Total household assets: `$9,430`
- **Current Benefits**: Not currently receiving Medicaid or other assistance

**Why this matters**: Tests the boundary condition on the resource limit. Income of $1,000/mo is comfortably within the QMB range (below the $1,255/mo threshold), so the only variable being tested here is the asset limit. Assets at exactly $9,430 should result in eligibility because the rule is "not exceeding $9,430" (≤), not "below $9,430" (<). This validates the comparison operator is implemented correctly and that applicants at the exact threshold are not incorrectly denied.

---

### Scenario 17: Earned Income Exclusion - Wages Exceeding Gross Income Limits
**What we're checking**: Validates that the SSI earned income methodology — $20 general exclusion, $65 earned income exclusion, and 50% of remaining earned income excluded — is applied to wages, making someone with high gross wages eligible for QMB
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Wages`, Amount: `$2,400` monthly
- **Assets**: Total household assets: `$5,000`
- **Current Benefits**: Not currently receiving Medicaid or other assistance

**Why this matters**: Gross wages of $2,400/mo greatly exceed the QMB income ceiling of $1,255/mo. Under SSI income methodology, the earned income exclusions reduce countable income significantly: $2,400 − $20 (general exclusion) − $65 (earned income exclusion) = $2,315; $2,315 × 0.50 = $1,157.50 countable income/mo — well below the QMB threshold. Without these exclusions, the system would incorrectly deny the applicant for all three sub-programs. This test validates that the system applies the 50% earned income exclusion rather than using gross wages directly.

---

### Scenario 18: 3+ Person Household — Assets Above Individual Limit (Known False Negative)
**What we're checking**: A senior living with an adult child where `household_assets` exceeds the individual resource limit. The implementation passes `household_assets` directly to PolicyEngine for all household sizes, so the resource check fails even though the excess assets may belong entirely to the non-eligible adult child (MSP only counts the applicant's and spouse's resources). This is a known false negative caused by the data gap.
**Expected**: Not eligible (known false negative — user should be advised to apply regardless)

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,000` monthly
- **Person 2 (Adult Child)**: Birth month/year: `June 1988` (age ~37), Relationship: `Child`, Has Medicare: `No`, Has income: `Yes`, Income type: `Wages`, Amount: `$2,000` monthly
- **Assets**: Total household assets: `$12,000`
- **Current Benefits**: Not receiving Medicaid or other assistance

**Why this matters**: Validates the known data gap behavior — `household_assets` of $12,000 exceeds the individual resource limit ($9,430), so the screener returns not eligible even though the excess may belong entirely to the adult child. Documents that this is an expected false negative so future developers understand the behavior is intentional, not a bug.

---

### Scenario 19: Single Individual — Assets Between Individual and Couple Limits
**What we're checking**: A single person whose assets exceed the individual resource limit ($9,430) but fall below the couple resource limit ($14,130). The individual limit must apply — this would catch a bug where the couple limit was incorrectly applied to a single-person household.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,000` monthly
- **Assets**: Total household assets: `$10,000`
- **Current Benefits**: Not currently receiving Medicaid or other assistance

**Why this matters**: Assets of $10,000 are above the individual limit ($9,430) but below the couple limit ($14,130). Income of $1,000/mo is comfortably within the QMB range, so the resource limit is the sole disqualifying factor. This scenario would catch a PE bug where `spm_unit_cash_assets` caused the couple limit to be applied to a single-person household — under that bug, assets of $10,000 would pass the (incorrect) $14,130 couple threshold and the applicant would be incorrectly deemed eligible. The correct result is ineligible.

---

## Source Documentation

- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information
- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview

## JSON Test Cases
File: `validations/management/commands/import_validations/data/tx_medicare_savings_program.json`

## Program Configuration
File: `programs/management/commands/import_program_config_data/data/tx_medicare_savings_program_initial_config.json`
