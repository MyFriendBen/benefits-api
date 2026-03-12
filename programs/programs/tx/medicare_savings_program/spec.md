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
     - `household_size`
   - Source: Section Q-1300, Appendix IX

6. **QDWI: Resources not exceeding $4,000 for individual or $6,000 for couple**
   - Screener fields:
     - `household_assets`
     - `household_size`
   - Source: Section Q-6000, Q-1300

7. **QDWI: Age under 65**
   - Screener fields:
     - `HouseholdMember.age`
     - `HouseholdMember.relationship`
   - Source: Section Q-6000

8. **QDWI: Must be disabled**
   - Screener fields:
     - `HouseholdMember.disabled`
     - `HouseholdMember.long_term_disability`
   - Source: Section Q-6000

9. **Must be Texas resident**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: Chapter D - Non-Financial Eligibility Requirements

10. **QI: Not eligible for Medicaid**
   - Screener fields:
     - `has_medicaid`
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

13. **Must be U.S. citizen or qualified non-citizen** ⚠️ *data gap*
   - Note: No citizenship/immigration status field in screener. MSP follows Medicaid citizenship requirements. Qualified non-citizens must meet specific immigration status and duration requirements.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: High

14. **Must provide Social Security Number or apply for one** ⚠️ *data gap*
   - Note: No SSN field in screener. Required for all MSP applicants unless good cause exception applies.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Medium

15. **Cannot be an inmate of a public institution** ⚠️ *data gap*
   - Note: No incarceration status field. Inmates of public institutions are ineligible for MSP.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Low

16. **QI: First-come, first-served based on federal funding allocation** ⚠️ *data gap*
   - Note: QI program has limited federal funding and operates on first-come, first-served basis. Cannot determine if funding is available through screener.
   - Source: Section Q-5000
   - Impact: Medium

17. **Must assign rights to medical support and third-party payments** ⚠️ *data gap*
   - Note: Administrative requirement - applicants must assign rights to medical support. Cannot evaluate through screener.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Low

18. **Must cooperate with quality control reviews** ⚠️ *data gap*
   - Note: Administrative requirement - cannot evaluate through screener.
   - Source: Chapter D - Non-Financial Eligibility Requirements
   - Impact: Low

19. **Specific income exclusions and deductions apply** ⚠️ *data gap*
   - Note: MSP uses specific income counting rules including exclusions for certain income types (e.g., $20 general income exclusion, earned income exclusions, etc.). Screener collects gross income but cannot apply all MSP-specific exclusions and deductions.
   - Source: Chapter E - Income Determination
   - Impact: Medium

20. **Specific resource exclusions apply** ⚠️ *data gap*
   - Note: Many resources excluded: homestead, one vehicle, household goods, personal effects, burial funds up to $1,500, life insurance with face value up to $1,500, etc. Screener asks for household_assets but users may not know to exclude these items.
   - Source: Chapter F - Resources, Section Q-1300
   - Impact: Medium

21. **Deeming rules for married couples** ⚠️ *data gap*
   - Note: When one spouse applies for MSP, income and resources of both spouses are considered. Complex deeming calculations apply. Screener can identify couples but cannot apply full deeming methodology.
   - Source: Chapter E - Income Determination, Chapter F - Resources
   - Impact: Medium

## Benefit Value

- Amount varies by household - see test cases

## Implementation Coverage

- ✅ Evaluable criteria: 11
- ⚠️  Data gaps: 10

The Medicare Savings Program in Texas has four sub-programs (QMB, SLMB, QI, QDWI) with varying income and resource limits. Of the major eligibility criteria, 11 can be evaluated with current screener fields, while 10 cannot. The evaluable criteria include all income thresholds (100%, 120%, 135%, 200% FPL), resource limits ($9,430/$14,130 for QMB/SLMB/QI; $4,000/$6,000 for QDWI), Medicare enrollment status (via `insurance.medicare` field), age requirements (QDWI under 65), disability status (QDWI), Texas residency, and Medicaid exclusion (QI only). Critical gaps include citizenship/immigration status, SSN requirement, whether someone lost free Part A due to returning to work (QDWI), and QI funding availability. The screener can effectively pre-screen based on income, assets, and Medicare enrollment status.

## Research Sources

- [Appendix IX - Medicare Savings Program (MSP) Income and Resource Limits Table (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information)
- [Section Q-1000 - Medicare Savings Programs Overview (42 U.S.C. § 1396a, 42 CFR § 435.4)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview)
- [Skip to main content](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information#main-content)
- [Search this Handbook](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/search-handbook)
- [Chapter A - General Information and MEPD Eligibility Groups (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-a-general-information-mepd-groups)
- [Chapter B - Application Process and Redetermination Requirements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-b-applications-redeterminations)
- [Chapter C, Rights and Responsibilities](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-c-rights-responsibilities)
- [Chapter D - Non-Financial Eligibility Requirements (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-d-non-financial)
- [Chapter E - Income Determination and Counting Rules (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-e-general-income)
- [Chapter F - Resource Determination and Exclusions (Texas MEPD Handbook)](https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-f-resources)

## Program Configuration

Django admin import configuration (ready to use):

```json
{
  "white_label": {
    "code": "tx"
  },
  "program_category": {
    "external_name": "tx_healthcare"
  },
  "program": {
    "name_abbreviated": "tx_medicare_savings_program",
    "year": "2025",
    "legal_status_required": [
      "citizen"
    ],
    "name": "Medicare Savings Program (MSP)",
    "description": "The Medicare Savings Program helps pay for Medicare costs. It covers premiums, deductibles, and copays. There are four programs: QMB, SLMB, QI, and QDWI. Each program helps with different Medicare costs. You must have Medicare Part A to qualify.\n\nYou can apply if you have low income and few assets. Income limits range from 100% to 200% of the poverty line. Asset limits are $10,000 for one person or $15,000 for a couple. You must live in Texas. The QDWI program is for disabled workers under age 65.",
    "description_short": "Help paying for Medicare premiums and costs",
    "learn_more_link": "https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview",
    "apply_button_link": "https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/chapter-b-applications-redeterminations",
    "apply_button_description": "Apply for Texas Medicare Savings Program",
    "estimated_application_time": "1 - 2 hours",
    "estimated_delivery_time": "45 days",
    "estimated_value": "Varies by program - QMB covers Part A and B premiums plus cost-sharing; SLMB covers Part B premiums; QI covers Part B premiums; QDWI covers Part A premiums",
    "website_description": "Helps pay Medicare premiums, deductibles, and copays for people with low income"
  },
  "warning_message": null,
  "documents": [
    {
      "external_name": "tx_home",
      "text": "Proof of home address (ex: lease, utility bill)",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "id_proof",
      "text": "Proof of identity",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_ssn",
      "text": "Social Security Number or proof you applied for one",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_medicare_card",
      "text": "Medicare card showing Part A enrollment",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_earned_income",
      "text": "Proof of income (ex: pay stubs, Social Security statement, pension statement)",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_assets",
      "text": "Proof of assets (ex: bank statements, investment accounts). Do not include your home, one vehicle, household goods, or burial funds up to $1,500",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_us_status",
      "text": "Proof of U.S. citizenship or qualified immigration status",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_disability_proof",
      "text": "Proof of disability (for QDWI program only)",
      "link_url": "",
      "link_text": ""
    }
  ],
  "navigators": []
}
```

**Human Review Checklist:**
- [ ] Verify program name and description are accurate
- [ ] Confirm application link is correct
- [ ] Add navigator contacts if available
- [ ] Review required documents list
- [ ] Check legal status requirements

## Research Output

Local path: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Medicare Savings Program_20260311_164059`

Files generated:
- Program config: `{white_label}_{program_name}_initial_config.json`
- Test cases: `{white_label}_{program_name}_test_cases.json`
- Full research data in output directory


## Acceptance Criteria

[ ] Scenario 1 (QMB Eligible - Single Senior with Social Security Income): User should be **eligible** with $None/year
[ ] Scenario 2 (SLMB Eligible - Single Senior at 120% FPL Threshold): User should be **eligible** with $None/year
[ ] Scenario 3 (QI Eligible - Single Senior Just Below 135% FPL Income Threshold): User should be **eligible** with $None/year
[ ] Scenario 4 (QMB Eligible - Single Senior with Income Exactly at 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 5 (Income Just Above 135% FPL - Not Eligible for Any MSP Category): User should be **ineligible**
[ ] Scenario 6 (QDWI Eligible - Person Exactly Age 64 at Disability Threshold): User should be **eligible** with $None/year
[ ] Scenario 7 (QDWI Not Eligible - Person Age 65 Just Above Age Threshold): User should be **ineligible**
[ ] Scenario 8 (QMB Eligible - Senior Age 75 Well Above Minimum Age): User should be **eligible** with $None/year
[ ] Scenario 9 (Eligible Location - Houston ZIP Code in Harris County): User should be **eligible** with $None/year
[ ] Scenario 10 (Already Receiving Medicaid - QI Exclusion Test): User should be **ineligible**
[ ] Scenario 11 (QDWI Excluded - Already Receiving Medicare Part A (Premium-Free)): User should be **ineligible**
[ ] Scenario 12 (Mixed Household - Eligible Senior with Non-Eligible Adult Child): User should be **eligible** with $None/year
[ ] Scenario 13 (Multiple Eligible Members - Married Couple Both Qualifying for QMB): User should be **eligible** with $None/year
[ ] Scenario 14 (QDWI Edge Case - Disabled Person Age 64 with Resources Exactly at $4,000 Limit): User should be **eligible** with $None/year

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
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This is the most common QMB scenario - a single senior on Medicare with Social Security income right at the 100% FPL threshold. QMB is the most comprehensive Medicare Savings Program, and this tests the baseline eligibility for the program's primary target population.

---

### Scenario 2: SLMB Eligible - Single Senior at 120% FPL Threshold
**What we're checking**: Validates SLMB eligibility at the minimum income threshold (just above 100% FPL) with maximum allowable resources
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `75001`, Select county `Collin`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,255`, Frequency: `Monthly`, Has health insurance: `Medicare`, Citizenship: `U.S. Citizen`
- **Assets**: Total household assets: `$10,000`

**Why this matters**: Tests the lower boundary of SLMB eligibility - ensures the system correctly identifies applicants who exceed QMB income limits but qualify for SLMB at the minimum threshold with maximum allowable resources

---

### Scenario 3: QI Eligible - Single Senior Just Below 135% FPL Income Threshold
**What we're checking**: Tests QI eligibility with income just below the 135% FPL threshold to verify the upper income boundary is correctly evaluated
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Has Medicare: `Yes`, Has income: `Yes`, Social Security Retirement: `$1,732` monthly, Income frequency: `Monthly`
- **Assets**: Total household assets: `$8,500`
- **Current Benefits**: Not currently receiving Medicaid

**Why this matters**: This test validates that the income threshold calculation correctly identifies applicants just below the 135% FPL limit for QI eligibility. It ensures the system doesn't incorrectly reject applicants who are within the qualifying range by even a small margin, which is critical for ensuring eligible seniors receive benefits.

---

### Scenario 4: QMB Eligible - Single Senior with Income Exactly at 100% FPL
**What we're checking**: Validates that income exactly at 100% FPL qualifies for QMB (at or below threshold)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `75001`, Select county `Collin`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Has Medicare: `Yes`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$1,255` monthly (exactly $15,060/year = 100% FPL for 1 person), Has assets: `Yes`, Asset amount: `$8,000` (below $10,000 resource limit)

**Why this matters**: Tests boundary condition where income is exactly at the 100% FPL threshold. This validates that the 'at or below' logic is implemented correctly and doesn't incorrectly exclude applicants at the exact threshold.

---

### Scenario 5: Income Just Above 135% FPL - Not Eligible for Any MSP Category
**What we're checking**: Validates that applicants with income exceeding 135% FPL (the highest QI threshold) are correctly denied for all Medicare Savings Program categories
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, U.S. Citizen: `Yes`, Has income: `Yes`, Social Security Retirement: `$1,700` per month, Income frequency: `Monthly`, Has health insurance: `Medicare only`, Not disabled, Not receiving Medicaid
- **Assets**: Total household assets: `$5,000`

**Why this matters**: This test ensures the screener correctly denies applicants whose income exceeds the highest MSP threshold (135% FPL for QI). It validates that the income ceiling is properly enforced and prevents false positives for applicants who earn too much to qualify for any MSP category.

---

### Scenario 6: QDWI Eligible - Person Exactly Age 64 at Disability Threshold
**What we're checking**: Tests that a person exactly at age 64 (under 65) with disability qualifies for QDWI program
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1962` (age 64), Relationship: `Head of Household`, Check `Has a disability`, Income: Social Security Disability Income `$1,500/month` ($18,000/year), Assets: `$3,500`, Insurance: `Medicare Part A only`

**Why this matters**: This test validates that the age threshold for QDWI is correctly implemented as 'under 65' (not 'under 64' or '65 and under'). A person who is exactly 64 years old should qualify, while someone who turns 65 would not qualify for QDWI based on age alone. This is critical because QDWI has different eligibility rules than QMB/SLMB/QI programs.

---

### Scenario 7: QDWI Not Eligible - Person Age 65 Just Above Age Threshold
**What we're checking**: Validates that QDWI has strict age requirement of under 65, and person who just turned 65 is not eligible for QDWI (but may qualify for QMB/SLMB/QI instead)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `February 1961` (age 65, just turned 65 last month), Check `Disabled`, Check `Has income`, Income type: `Social Security Disability`, Amount: `$1,800`, Frequency: `Monthly`, Insurance: `Medicare`, Assets: `$3,500`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: Tests the strict age boundary for QDWI eligibility. QDWI is specifically for disabled individuals under age 65 who are working and paying Medicare Part A premiums. Once a person turns 65, they transition to standard Medicare and would need to qualify under QMB/SLMB/QI categories instead. This validates the system correctly enforces the age < 65 requirement per Section Q-6000.

---

### Scenario 8: QMB Eligible - Senior Age 75 Well Above Minimum Age
**What we're checking**: Validates that seniors well above the typical Medicare eligibility age (65) remain eligible for QMB when meeting income and resource requirements
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1951` (age 75), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Social Security Retirement`, Amount: `$950`, Frequency: `Monthly`, Has health insurance: `Medicare`, Citizenship: `U.S. Citizen`
- **Assets**: Total household assets: `$8,000`

**Why this matters**: This test confirms that the Medicare Savings Program does not have an upper age limit and that seniors significantly older than the minimum Medicare age (65) can still qualify for QMB assistance. This is important because many seniors in their 70s and 80s have limited fixed incomes and need help with Medicare costs.

---

### Scenario 9: Eligible Location - Houston ZIP Code in Harris County
**What we're checking**: Verifies that applicants in a major Texas metropolitan area (Houston) are eligible based on geographic location
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `77002`, Select county `Harris`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Relationship: `Head of Household`, Citizenship: `U.S. Citizen`, Has income: `Yes`, Social Security Retirement: `$950/month`, Insurance: `Medicare only`
- **Assets**: Total household assets: `$5,000`

**Why this matters**: Confirms that the Medicare Savings Program correctly recognizes major Texas metropolitan areas as eligible service locations. Harris County (Houston) is the most populous county in Texas, so this validates that urban areas are properly included in the geographic eligibility criteria.

---

### Scenario 10: Already Receiving Medicaid - QI Exclusion Test
**What we're checking**: Tests that applicants already receiving Medicaid are excluded from QI (Qualifying Individual) program per Section Q-5000 requirement
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Relationship: `Head of Household`, Citizenship: `U.S. Citizen`, Has income: `Yes`, Income type: `Social Security Retirement`, Income amount: `$1,350` per month (approximately 122% FPL - within QI range), Has health insurance: `Yes - Medicaid`
- **Assets**: Total household assets: `$5,000` (well below $10,000 limit)

**Why this matters**: This test validates the critical exclusion rule in Section Q-5000 that prevents dual enrollment in Medicaid and QI programs. QI is specifically designed for Medicare beneficiaries who are NOT eligible for Medicaid, so this exclusion prevents improper benefit stacking and ensures program integrity.

---

### Scenario 11: QDWI Excluded - Already Receiving Medicare Part A (Premium-Free)
**What we're checking**: Tests QDWI exclusion for individuals who already have premium-free Medicare Part A coverage, as QDWI is specifically for those who need to purchase Part A
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1964` (age 62), Relationship: `Head of Household`, Citizenship: `U.S. Citizen`, Disabled: `Yes`, Has income: `Yes`, Income type: `Social Security Disability`, Income amount: `$1,500` per month, Has health insurance: `Yes`, Insurance type: `Medicare Part A (Premium-Free)`
- **Assets**: Total household assets: `$3,000`
- **Current Benefits**: Not receiving Medicaid or other assistance programs

**Why this matters**: QDWI (Qualified Disabled and Working Individuals) program specifically helps disabled individuals under age 65 who have lost premium-free Medicare Part A due to returning to work and need to purchase Part A coverage. Those who already have premium-free Part A are excluded from QDWI but may qualify for other MSP categories (QMB/SLMB/QI). This tests the system correctly identifies this exclusion criterion.

---

### Scenario 12: Mixed Household - Eligible Senior with Non-Eligible Adult Child
**What we're checking**: Tests multi-member household where head of household qualifies for QMB but adult child does not have Medicare, ensuring individual eligibility is properly assessed
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1958` (age 68), Relationship: `Head of Household`, Has Medicare Part A: `Yes`, Has Medicare Part B: `Yes`, Has income: `Yes`, Social Security Retirement: `$1,350` monthly, Citizenship: `U.S. Citizen`
- **Person 2 (Adult Child)**: Birth month/year: `June 1988` (age 37), Relationship: `Child`, Has Medicare: `No`, Has income: `Yes`, Wages: `$2,800` monthly, Citizenship: `U.S. Citizen`
- **Assets**: Total household assets: `$8,500`

**Why this matters**: This test validates that the screener correctly handles mixed households where only some members meet all eligibility criteria. It ensures that MSP eligibility is assessed individually based on Medicare enrollment status, even when household income and assets are within limits. This is critical because MSP requires Medicare enrollment, which typically requires age 65+ or disability.

---

### Scenario 13: Multiple Eligible Members - Married Couple Both Qualifying for QMB
**What we're checking**: Tests that multiple household members can each qualify for MSP benefits independently when both meet QMB eligibility criteria (both 65+, combined income at 100% FPL for household of 2, combined resources under $10,000)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1959` (age 67), Relationship: Head of Household, Has income: Yes, Social Security Retirement: `$1,100` monthly, Insurance: Medicare Part A and Part B, Citizenship: U.S. Citizen
- **Person 2 (Spouse)**: Birth month/year: `March 1960` (age 66), Relationship: Spouse, Has income: Yes, Social Security Retirement: `$900` monthly, Insurance: Medicare Part A and Part B, Citizenship: U.S. Citizen
- **Assets**: Total household assets: `$8,500`
- **Current Benefits**: Not receiving Medicaid or other assistance

**Why this matters**: This test validates that the MSP screening tool correctly handles households where multiple members independently qualify for the same MSP category. It ensures the system can process married couples where both spouses meet QMB criteria, properly aggregates household income and resources, and applies the correct couple thresholds rather than individual thresholds. This is a common real-world scenario since married seniors often both have Medicare and modest Social Security income.

---

### Scenario 14: QDWI Edge Case - Disabled Person Age 64 with Resources Exactly at $4,000 Limit
**What we're checking**: Tests QDWI eligibility when applicant is at the exact resource limit ($4,000 for individual) and just under the age threshold (64 years old)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1962` (age 64), Relationship: `Head of Household`, Citizenship: `U.S. Citizen`, Has disability: `Yes`, Has Medicare Part A (premium-free): `No`, Has Medicare Part B: `No`, Has Medicaid: `No`
- **Income**: Social Security Disability Income: `$1,500` per month, Total monthly income: `$1,500`, Annual income: `$18,000` (exactly 120% FPL for household of 1)
- **Assets**: Total household assets: `$4,000` (exactly at QDWI resource limit)

**Why this matters**: This edge case tests the system's handling of exact threshold values for QDWI resources ($4,000) combined with age boundary (64 years old, just under the 65 age exclusion). It validates that the system correctly applies 'at or below' logic for resource limits and properly evaluates the unique QDWI requirements (disabled, under 65, no premium-free Part A) when multiple boundary conditions are present simultaneously.

---


## Source Documentation

- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/appendix-ix-medicare-savings-program-information
- https://www.hhs.texas.gov/handbooks/medicaid-elderly-people-disabilities-handbook/q-1000-medicare-savings-programs-overview

## JSON Test Cases
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Medicare Savings Program_20260311_164059/ticket_content/tx_Medicare Savings Program_test_cases.json`

## Program Configuration
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Medicare Savings Program_20260311_164059/ticket_content/tx_Medicare Savings Program_initial_config.json`