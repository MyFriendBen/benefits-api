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
   - Note: The resource limit is determined by marital status (individual vs. couple), not by household size — there is no defined limit for households with 3 or more members. The couple limit ($14,130) applies when a spouse is present (use `screen.is_joint()` or check for a spouse relationship); otherwise the individual limit ($9,430) applies. `household_size` is not the right field to select the limit. ⚠️ Partial gap for households > 2: `household_assets` is a household-level total that includes assets of non-eligible members (e.g., adult children). MSP resource counting applies only to the applicant and their spouse — other household members' assets should be excluded. Using `household_assets` as a proxy may produce false negatives for 3+ person households where non-eligible members hold significant assets.
   - Note on resource exclusions: Many asset types are excluded from the resource count under MSP rules: homestead, one vehicle, household goods, personal effects, burial funds up to $1,500, and life insurance with face value up to $1,500. The screener collects a single `household_assets` total, so users may unknowingly include excluded items — this can produce false negatives. This is surfaced in the initial program config description to set user expectations.
   - Source: Section Q-1300, Appendix IX, Chapter F - Resources

5. **Must be Texas resident**
   - Note: Handled via white label association — the program is only shown to users of the `tx` white label, so no screener field check is needed.
   - Source: Chapter D - Non-Financial Eligibility Requirements

6. **QI: Not eligible for Medicaid**
   - Screener fields:
     - `HouseholdMember.insurance.medicaid`
   - PolicyEngine calculation:
     - `medicaid_eligible` (used when `HouseholdMember.insurance.medicaid` is not indicated)
   - Note: If the person has indicated they currently have Medicaid, they are immediately disqualified from QI. If they have not indicated Medicaid coverage, `medicaid_eligible` (derived from PolicyEngine's calculation) is used to determine whether they would be eligible for Medicaid — if so, they are also disqualified from QI.
   - Source: Section Q-5000

7. **Must be entitled to Medicare Part A (hospital insurance)**
   - Screener fields:
     - `HouseholdMember.insurance.medicare`
   - Note: The screener `medicare` insurance field is used as a proxy for Medicare Part A enrollment. QMB/SLMB/QI all require Part A entitlement.
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
- ⚠️  Data gaps: 2

> **Note on QDWI:** The QDWI (Qualified Disabled and Working Individuals) sub-program is not surfaced by this implementation. PolicyEngine does not model the QDWI benefit value (`msp_benefit_value` has no QDWI branch), and the program's primary eligibility requirement — that the applicant lost premium-free Medicare Part A by returning to work — cannot be evaluated with current screener fields. Given these limitations, QDWI is excluded from the screener results.

This implementation covers the three remaining MSP sub-programs: QMB, SLMB, and QI. Of the 11 major eligibility criteria for these programs, 9 can be evaluated with current screener fields or program config, while 2 cannot. The evaluable criteria include all income thresholds (100%, 120%, 135% FPL), resource limits ($9,430/$14,130 for individual/couple), Medicare enrollment status (via `insurance.medicare` field), Texas residency, Medicaid exclusion (QI only), citizenship/immigration status (via `legal_status_required` program config), and deeming rules (spouse-to-spouse and parent-to-child). Resource limit checks are accurate for households of 1–2 (the vast majority of MSP cases) but partially limited for households > 2: `household_assets` captures the whole household including non-eligible members, and the individual/couple limits are selected by spouse presence rather than household size. The screener can effectively pre-screen based on income, assets, Medicare enrollment status, immigration status, and deeming. The QI Medicaid exclusion is evaluated in two steps: first by checking `insurance.medicaid` directly, then by falling back to PolicyEngine's `medicaid_eligible` calculation when not indicated — ensuring that applicants who would qualify for Medicaid are also excluded from QI even if they haven't explicitly reported Medicaid enrollment.

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
**What we're checking**: Validates that income exactly at 100% FPL qualifies for QMB (at or below threshold)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `75001`, Select county `Collin`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,255` monthly (exactly $15,060/year = 100% FPL for 1 person), Assets: `$8,000` (below $9,430 resource limit)

**Why this matters**: Tests the boundary condition where income is exactly at the 100% FPL threshold. Validates that the 'at or below' logic is implemented correctly and does not exclude applicants at the exact threshold.

---

### Scenario 5: Ineligible - Income Above 135% FPL Disqualifies All MSP Categories
**What we're checking**: Validates that applicants with income exceeding 135% FPL are correctly denied for all Medicare Savings Program categories
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,700` per month, Not disabled, Not receiving Medicaid
- **Assets**: Total household assets: `$5,000`

**Why this matters**: Income of $1,700/mo exceeds 135% FPL ($1,694/mo), ruling out all three sub-programs (QMB/SLMB/QI). This single case validates all income ceiling logic across the program.

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
**What we're checking**: Tests multi-member household where head of household qualifies for QMB but adult child does not have Medicare, ensuring individual eligibility is properly assessed
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
- **Assets**: Total household assets: `$8,500`
- **Current Benefits**: Not receiving Medicaid or other assistance

**Why this matters**: Validates that the system correctly handles households where multiple members independently qualify. Combined income of $2,000/mo for a household of 2 is ~117.5% of the 2-person FPL, placing them in the SLMB range (100–120% FPL). The couple resource limit ($14,130) applies rather than the individual limit ($9,430).

---

### Scenario 15: Spouse-to-Spouse Deeming - Ineligible Due to Deemed Spouse Income
**What we're checking**: Tests that an ineligible (non-applying) spouse's income is deemed to the applicant, making them ineligible for all MSP sub-programs even though their own income would qualify them for QMB
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1959` (age 67), Relationship: `Head of Household`, Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$800` monthly
- **Person 2 (Spouse)**: Birth month/year: `March 1962` (age 64), Relationship: `Spouse`, Has Medicare: `No`, Has income: `Yes`, Income type: `Wages`, Amount: `$1,500` monthly
- **Assets**: Total household assets: `$8,000`
- **Current Benefits**: Not receiving Medicaid or other assistance

**Why this matters**: The applicant's own income ($800/mo) is well below the QMB threshold for a single person (~$1,255/mo at 100% FPL). Without deeming, they would qualify for QMB. But with the ineligible spouse's income deemed in, the combined household income is $2,300/mo — just above the 135% FPL ceiling for a 2-person household (~$2,299/mo), disqualifying them from all MSP sub-programs. This directly validates that spouse-to-spouse deeming is applied and can change eligibility outcomes.

---

## Source Documentation

- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information
- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview

## JSON Test Cases
File: `validations/management/commands/import_validations/data/tx_medicare_savings_program.json`

## Program Configuration
File: `programs/management/commands/import_program_config_data/data/tx_medicare_savings_program_initial_config.json`
