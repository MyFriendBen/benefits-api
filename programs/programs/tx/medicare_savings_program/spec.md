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

4. **QDWI: Income at or below 200% of Federal Poverty Level**
   - Screener fields:
     - `household_size`
     - `IncomeStream.amount`
     - `IncomeStream.frequency`
   - Source: Section Q-6000

5. **QMB/SLMB/QI: Resources not exceeding $9,430 for individual or $14,130 for couple (2024)**
   - Screener fields:
     - `household_assets`
     - `HouseholdMember.relationship`
   - Note: The resource limit is determined by marital status (individual vs. couple), not by household size — there is no defined limit for households with 3 or more members. The couple limit ($14,130) applies when a spouse is present (use `screen.is_joint()` or check for a spouse relationship); otherwise the individual limit ($9,430) applies. `household_size` is not the right field to select the limit. ⚠️ Partial gap for households > 2: `household_assets` is a household-level total that includes assets of non-eligible members (e.g., adult children). MSP resource counting applies only to the applicant and their spouse — other household members' assets should be excluded. Using `household_assets` as a proxy may produce false negatives for 3+ person households where non-eligible members hold significant assets.
   - Note on resource exclusions: Many asset types are excluded from the resource count under MSP rules: homestead, one vehicle, household goods, personal effects, burial funds up to $1,500, and life insurance with face value up to $1,500. The screener collects a single `household_assets` total, so users may unknowingly include excluded items — this can produce false negatives. This is surfaced in the initial program config description to set user expectations.
   - Source: Section Q-1300, Appendix IX, Chapter F - Resources

6. **QDWI: Resources not exceeding $4,000 for individual or $6,000 for couple**
   - Screener fields:
     - `household_assets`
     - `HouseholdMember.relationship`
   - Note: Same household-size caveat as criterion 5. The couple limit ($6,000) applies when a spouse is present; otherwise the individual limit ($4,000) applies. ⚠️ Partial gap for households > 2: `household_assets` overcounts by including non-eligible members' assets, risking false negatives.
   - Source: Section Q-6000, Q-1300

7. **QDWI: Age under 65**
   - Screener fields:
     - `HouseholdMember.age`
     - `HouseholdMember.relationship`
   - Source: Section Q-6000

8. **QDWI: Must be disabled**
   - Screener fields:
     - `HouseholdMember.disabled`
     - `HouseholdMember.visually_impaired`
     - `HouseholdMember.long_term_disability`
   - Source: Section Q-6000

9. **Must be Texas resident**
   - Note: Handled via white label association — the program is only shown to users of the `tx` white label, so no screener field check is needed.
   - Source: Chapter D - Non-Financial Eligibility Requirements

10. **QI: Not eligible for Medicaid**
   - Screener fields:
     - `HouseholdMember.insurance.medicaid`
   - PolicyEngine calculation:
     - `medicaid_eligible` (used when `HouseholdMember.insurance.medicaid` is not indicated)
   - Note: If the person has indicated they currently have Medicaid, they are immediately disqualified from QI. If they have not indicated Medicaid coverage, `medicaid_eligible` (derived from PolicyEngine's calculation) is used to determine whether they would be eligible for Medicaid — if so, they are also disqualified from QI.
   - Source: Section Q-5000

11. **Must be entitled to Medicare Part A (hospital insurance)**
   - Screener fields:
     - `HouseholdMember.insurance.medicare`
   - Note: The screener `medicare` insurance field is used as a proxy for Medicare Part A enrollment. QMB/SLMB/QI require Part A entitlement. QDWI has a different requirement (lost free Part A due to returning to work — see data gap below).
   - Source: Section Q-1000, Q-2000, Q-3000, Q-5000

12. **QDWI: Must be working and paying Medicare Part A premiums** ⚠️ *data gap*
   - Note: No field captures whether someone is paying Medicare Part A premiums or lost free Part A due to returning to work. QDWI specifically helps disabled workers who lost free Part A.
   - Source: Section Q-6000
   - Impact: High

13. **Must be U.S. citizen or qualified non-citizen**
   - Screener fields: `legal_status_required` (program config)
   - Note: Handled at the program level via `legal_status_required`. MSP follows Medicaid citizenship requirements; the program config restricts results to citizens and qualified non-citizens.
   - Source: Chapter D - Non-Financial Eligibility Requirements

14. **Must provide Social Security Number or apply for one** ⚠️ *data gap*
   - Note: No SSN field in screener. Required for all MSP applicants unless good cause exception applies.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Medium

15. **Cannot be an inmate of a public institution** ⚠️ *data gap*
   - Note: No incarceration status field. Inmates of public institutions are ineligible for MSP.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Low

16. **Must assign rights to medical support and third-party payments** ⚠️ *data gap*
   - Note: Administrative requirement - applicants must assign rights to medical support. Cannot evaluate through screener.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Low

17. **Must cooperate with quality control reviews** ⚠️ *data gap*
   - Note: Administrative requirement - cannot evaluate through screener.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Low

18. **Deeming rules for married couples** ⚠️ *data gap*
   - Note: When one spouse applies for MSP, income and resources of both spouses are considered. Complex deeming calculations apply. Screener can identify couples but cannot apply full deeming methodology.
   - Source: Chapter E - Income Determination, Chapter F - Resources
   - Impact: Medium

## Benefit Value

- Amount varies by household - see test cases

## Implementation Coverage

- ✅ Evaluable criteria: 12
- ⚠️  Data gaps: 6

The Medicare Savings Program in Texas has four sub-programs (QMB, SLMB, QI, QDWI) with varying income and resource limits. Of the major eligibility criteria, 12 can be evaluated with current screener fields or program config, while 6 cannot. The evaluable criteria include all income thresholds (100%, 120%, 135%, 200% FPL), resource limits ($9,430/$14,130 for QMB/SLMB/QI; $4,000/$6,000 for QDWI), Medicare enrollment status (via `insurance.medicare` field), age requirements (QDWI under 65), disability status (QDWI), Texas residency, Medicaid exclusion (QI only), and citizenship/immigration status (via `legal_status_required` program config). Critical gaps include SSN requirement and whether someone lost free Part A due to returning to work (QDWI). Resource limit checks are accurate for households of 1–2 (the vast majority of MSP cases) but partially limited for households > 2: `household_assets` captures the whole household including non-eligible members, and the individual/couple limits are selected by spouse presence rather than household size. The screener can effectively pre-screen based on income, assets, Medicare enrollment status, and immigration status. The QI Medicaid exclusion is evaluated in two steps: first by checking `insurance.medicaid` directly, then by falling back to PolicyEngine's `medicaid_eligible` calculation when not indicated — ensuring that applicants who would qualify for Medicaid are also excluded from QI even if they haven't explicitly reported Medicaid enrollment.

## Research Sources

- [Appendix IX - Medicare Savings Program (MSP) Income and Resource Limits Table (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information)
- [Section Q-1000 - Medicare Savings Programs Overview (42 U.S.C. § 1396a, 42 CFR § 435.4)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview)
- [Chapter A - General Information and MEPD Eligibility Groups (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-a-general-information-mepd-groups)
- [Chapter B - Application Process and Redetermination Requirements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-b-applications-redeterminations)
- [Chapter C, Rights and Responsibilities](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-c-rights-responsibilities)
- [Chapter D - Non-Financial Eligibility Requirements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-d-non-financial)
- [Chapter E - Income Determination and Counting Rules (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-e-general-income)
- [Chapter F - Resource Determination and Exclusions (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-f-resources)

## Acceptance Criteria

[ ] Scenario 1 (QMB Eligible - Single Senior with Social Security Income): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 2 (SLMB Eligible - Single Senior with Income in 100-120% FPL Range): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 3 (QI Eligible - Single Senior with Income in 120-135% FPL Range): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 4 (QMB Eligible - Single Senior with Income Exactly at 100% FPL): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 5 (Ineligible - Income Above 135% FPL Disqualifies All MSP Categories): User should be **ineligible**
[ ] Scenario 6 (QDWI Eligible - Person Exactly Age 64 at Disability Threshold): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 7 (QDWI Not Eligible - Person Age 65 With Income in SLMB Range): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 8 (QMB Eligible - Senior Age 75 Well Above Minimum Age): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 10 (Already Receiving Medicaid - QI Exclusion Test): User should be **ineligible**
[ ] Scenario 11 (QDWI Excluded - Already Receiving Medicare Part A (Premium-Free)): User should be **eligible** (for SLMB; ineligible for QDWI)
[ ] Scenario 12 (Mixed Household - Eligible Senior with Non-Eligible Adult Child): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 13 (Multiple Eligible Members - Married Couple Both Qualifying for SLMB): User should be **eligible** (benefit amount: N/A)
[ ] Scenario 14 (QDWI Edge Case - Disabled Person Age 64 with Resources Exactly at $4,000 Limit): User should be **eligible** (benefit amount: N/A)

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

**Why this matters**: Income of $1,700/mo exceeds 135% FPL ($1,694/mo), ruling out QMB/SLMB/QI. Age 65 rules out QDWI. This single case validates all income ceiling logic across the program.

---

### Scenario 6: QDWI Eligible - Person Exactly Age 64 at Disability Threshold
**What we're checking**: Tests that a person exactly at age 64 (under 65) with disability qualifies for QDWI program
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1962` (age 64), Relationship: `Head of Household`, Check `Has a disability` (`disabled`, `visually_impaired`, or `long_term_disability`), Has income: `Yes`, Income type: `Social Security Disability`, Amount: `$1,500/month`, Has Medicare: `No`, Has Medicaid: `No`
- **Assets**: Total household assets: `$3,500`

**Why this matters**: Validates that the age threshold for QDWI is correctly implemented as 'under 65'. A person exactly 64 should qualify. Note: QDWI technically requires the person to be paying Medicare Part A premiums (having lost premium-free coverage by returning to work), but this is a known data gap (#12). The screener uses `Has Medicare: No` as a proxy for this requirement — this scenario tests the proxy behavior only, not exact QDWI eligibility.

---

### Scenario 7: QDWI Not Eligible - Person Age 65 With Income in SLMB Range
**What we're checking**: Validates that QDWI has a strict age requirement of under 65, and a person who just turned 65 is denied QDWI but correctly qualifies for SLMB instead
**Expected**: Eligible (for SLMB; ineligible for QDWI)

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `February 1961` (age 65), Check `Has a disability` (`disabled`, `visually_impaired`, or `long_term_disability`), Has income: `Yes`, Income type: `Social Security Disability`, Amount: `$1,500`, Frequency: `Monthly`, Has Medicare: `Yes`, Assets: `$3,500`
- **Current Benefits**: Select `None`

**Why this matters**: Tests the strict age boundary for QDWI (age < 65). At age 65 with income of $1,500/mo (~119.5% FPL, in SLMB range), the person is denied QDWI due to age but correctly qualifies for SLMB. This validates that (a) QDWI correctly enforces the age < 65 requirement per Section Q-6000, and (b) the system falls through to SLMB eligibility rather than returning a blanket denial.

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

### Scenario 11: QDWI Excluded - Already Receiving Medicare Part A (Premium-Free)
**What we're checking**: Tests QDWI exclusion for individuals who already have premium-free Medicare Part A coverage, while confirming they still qualify for SLMB
**Expected**: Eligible (for SLMB; ineligible for QDWI)

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1964` (age 62), Relationship: `Head of Household`, Check `Has a disability` (`disabled`, `visually_impaired`, or `long_term_disability`), Has Medicare: `Yes`, Has Medicaid: `No`, Has income: `Yes`, Income type: `Social Security Disability`, Amount: `$1,500` per month
- **Assets**: Total household assets: `$3,000`

**Why this matters**: QDWI specifically helps disabled workers who lost premium-free Medicare Part A due to returning to work. Those who already have Medicare (premium-free Part A) are excluded from QDWI. Note: the screener uses the `medicare` field as a proxy — this scenario tests that Medicare enrollment correctly disqualifies a QDWI candidate. However, having Medicare is a *prerequisite* (not a disqualification) for SLMB. With income of $1,500/month (~115% FPL, within the 100–120% SLMB range) and assets of $3,000 (below the $9,430 individual limit), this person qualifies for SLMB. The system should fall through to SLMB eligibility rather than returning a blanket denial.

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

### Scenario 14: QDWI Edge Case - Disabled Person Age 64 with Resources Exactly at $4,000 Limit
**What we're checking**: Tests QDWI eligibility when applicant is at the exact resource limit ($4,000 for individual) and just under the age threshold (64 years old)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1962` (age 64), Relationship: `Head of Household`, Check `Has a disability` (`disabled`, `visually_impaired`, or `long_term_disability`), Has Medicare: `No`, Has Medicaid: `No`
- **Income**: Income type: `Social Security Disability`, Amount: `$1,500` per month
- **Assets**: Total household assets: `$4,000` (exactly at QDWI resource limit)

**Why this matters**: Tests the system's handling of exact threshold values for QDWI resources ($4,000 at or below) combined with the age boundary (64, just under the 65 exclusion). Validates that 'at or below' logic is correctly applied for resource limits. Note: Like Scenario 6, this uses `Has Medicare: No` as a proxy for the QDWI Part A premium-payment requirement (data gap #12) — this tests proxy behavior only.

---


## Source Documentation

- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information
- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview

## JSON Test Cases
File: `validations/management/commands/import_validations/data/tx_medicare_savings_program.json`

## Program Configuration
File: `programs/management/commands/import_program_config_data/data/tx_medicare_savings_program_initial_config.json`
