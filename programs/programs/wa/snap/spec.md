# Implement Basic Food - Supplemental Nutrition Assistance Program (SNAP) (WA) Program

## Program Details

- **Program**: Basic Food - Supplemental Nutrition Assistance Program (SNAP)
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-03-23
- **Spec Revision**: 2026-04-07 (incorporating feedback from patmanson)

## Eligibility Criteria

1. **Gross monthly income must be at or below 200% of the Federal Poverty Level (Washington uses Broad-Based Categorical Eligibility)**
   - Screener fields: `household_size`, `calc_gross_income`
   - Source: WAC 388-414-0001; DSHS Basic Food overview page states households must meet income guidelines. Washington's BBCE raises the gross income limit to 200% FPL.

2. **Net monthly income must be at or below 100% of the Federal Poverty Level**
   - Screener fields: `household_size`, `calc_net_income`
   - Note: For most households, both the gross income test AND the net income test must be passed. However, for households with a member aged 60+ or with a disability, the net income test applies **only if the household did not pass the gross income test** (see criterion 7).
   - Source: 7 CFR 273.9(b)(2); 7 U.S.C. § 2014(c)(2); WAC 388-450-0001. The net income test applies to all SNAP households regardless of BBCE status.

3. **No asset/resource limit applies under Washington's Broad-Based Categorical Eligibility (BBCE)**
   - Screener fields: `household_assets`
   - Note: No asset limit applies for most households. **Exception**: if the household contains a member who is 60+ or has a disability AND the household fails the gross income test, a maximum resource limit of **$4,500** applies.
   - Source: WAC 388-470-0005; Washington DSHS eliminated the asset test for Basic Food under BBCE. Per USDA FNS BBCE policy, states that provide BBCE can eliminate the asset test.

4. **Household size determination**
   - Screener fields: `household_size`
   - Source: 7 CFR 273.1(a)-(b); WAC 388-408-0015. People who live together and customarily purchase and prepare meals together are considered one SNAP household.

5. **Must not already be receiving SNAP/Basic Food benefits**
   - Screener fields: `has_snap`
   - Source: General SNAP policy — households cannot receive duplicate benefits.

6. **Student eligibility: College students aged 18–49 enrolled at least half-time in an institution of higher education must meet an exemption to be eligible**
   - Screener fields: `student`, `student_full_time`, `student_works_20_plus_hrs`, `student_has_work_study`, `student_job_training_program`, `age`
   - Source: 7 CFR 273.5; 7 U.S.C. § 2015(e); WAC 388-482-0005. Students enrolled at least half-time in higher education are ineligible unless they meet an exemption (working 20+ hours/week, participating in work-study, in a job training program, caring for a dependent child under 6, etc.).

7. **Elderly or disabled household member — alternative eligibility path** ⚠️ *complex edge case — recommend disclaimer rather than evaluating in screener*
   - Screener fields: `age`, `disabled`
   - Note: Households with a member aged 60+ or with a disability have **two paths** to eligibility:
     - **Option A (pass gross income test)**: Gross income ≤ 200% FPL → eligible; net income test is not required.
     - **Option B (fail gross income test)**: Gross income > 200% FPL → can still be eligible if net income ≤ 100% FPL. A $4,500 asset limit also applies under this path.
   - **Recommendation**: Ignore this edge case in the screener logic and surface a disclaimer for any result returned to a household where a member is 60+ or has a disability:
     > *"If you got an ineligible result for SNAP and your household includes a person over the age of 60 or with a disability, there is an alternate path to qualify, so consider applying."*
   - The same disclaimer can be extended if a user did not submit citizenship status:
     > *"If you did not provide citizenship status, your result may not reflect your full eligibility. Meet citizenship or immigration status requirements to qualify."*
   - Source: 7 CFR 273.9(b)(1); 7 U.S.C. § 2014(c)(1); WAC 388-470-0005.
   - Impact: Medium

8. **Household must include at least one member who is a U.S. citizen or qualified non-citizen**
   - Source: 7 U.S.C. § 2015(f); 7 CFR 273.4; WAC 388-424-0001. Only U.S. citizens and certain qualified non-citizens are eligible for SNAP. However, Washington has a state-funded Food Assistance Program (FAP) for legal immigrants who don't qualify for federal SNAP.

9. **State residency — must reside in Washington State**
   - Screener fields: `zipcode`, `county`
   - Source: 7 CFR 273.3; WAC 388-468-0005. Applicants must reside in the state where they apply.

10. **TANF/SSI categorical eligibility — households where all members receive TANF or SSI are categorically eligible**
    - Screener fields: `has_tanf`, `has_ssi`
    - Note: Categorical eligibility bypasses the financial eligibility tests (income and asset), but non-financial eligibility rules (student status, citizenship, residency, etc.) still apply. The key phrase is *all members* — if even one household member does not receive TANF or SSI, this specific pathway does not apply.
    - Source: 7 CFR 273.2(j); 7 U.S.C. § 2014(a). *Statutory language — 7 U.S.C. § 2014(a): households in which each member receives benefits under a State program funded under part A of title IV of the Social Security Act (TANF), supplemental security income benefits under title XVI of the Social Security Act, or aid to the aged, blind, or disabled, shall be eligible to participate in the supplemental nutrition assistance program.*

11. **Pregnant women count as one household member for Basic Food (SNAP)** *(corrected — original spec was incorrect)*
    - Note: A pregnant woman counts as **one** person for household size purposes under WA SNAP. Federal SNAP rules and Washington's WAC 388-408-0015 do not count unborn children as household members for Basic Food. The `pregnant` screener field is relevant for the work requirement exemption only — a pregnant woman is exempt from the ABAWD work requirement, but pregnancy does **not** change household size for FPL threshold calculations.
    - Screener fields: `pregnant` (work requirement exemption only; does not affect `household_size`)
    - Source: WAC 388-408-0034; WAC 388-408-0035; WAC 388-400-0040; federal SNAP rules.

12. **U.S. citizenship or qualified non-citizen status** ⚠️ *data gap*
    - Note: The screener does not collect citizenship or immigration status. This is a federal requirement for SNAP. Qualified non-citizens include lawful permanent residents (with 5-year bar or exemptions), refugees, asylees, etc. Washington's state-funded FAP covers some legal immigrants who don't qualify for federal SNAP. Without this field, we cannot distinguish between citizens, qualified non-citizens, and ineligible non-citizens.
    - Source: 7 U.S.C. § 2015(f); 7 CFR 273.4; WAC 388-424-0001 through 388-424-0025
    - Impact: Medium

13. **Social Security Number requirement — must provide SSN or apply for one** ⚠️ *data gap*
    - Note: The screener does not collect SSN information (nor should it for a screening tool). This is an application-stage requirement, not a pre-screening criterion. Individuals who refuse to provide or apply for an SSN are ineligible, but this is verified during the application process.
    - Source: 7 CFR 273.6; 7 U.S.C. § 2015(e)(1).
    - Impact: Low

14. **Must not be a fleeing felon or in violation of parole/probation** ⚠️ *data gap*
    - Note: Individuals who are fleeing felons or violating conditions of parole or probation are ineligible for SNAP. The screener does not collect criminal justice status. This affects a small subset of applicants.
    - Source: 7 U.S.C. § 2015(k); 7 CFR 273.11(n); WAC 388-442-0010
    - Impact: Low

15. **Must not be residing in an institutional setting (unless exempt)** ⚠️ *data gap*
    - Note: The screener does not collect information about institutional residence. Homeless individuals ARE eligible for SNAP; this criterion specifically excludes those in institutions like prisons, hospitals (long-term), or nursing homes.
    - Source: 7 CFR 273.1(b)(7); WAC 388-408-0040.
    - Impact: Low

16. **ABAWD (Able-Bodied Adults Without Dependents) work requirement — adults aged 18–52 without dependents must work or participate in qualifying activities for at least 80 hours/month** ⚠️ *data gap*
    - Note: Cannot be fully evaluated because: (1) the screener doesn't track months of prior SNAP receipt, (2) Washington's ABAWD waiver status changes frequently by county and year, and (3) the 80 hours/month work requirement is more specific than the screener's employment fields capture. Washington has frequently obtained statewide or partial ABAWD waivers. A pregnant woman is exempt from this requirement.
    - Source: 7 U.S.C. § 2015(o); 7 CFR 273.24; WAC 388-444-0030.
    - Impact: Medium

17. **Drug felony compliance** ⚠️ *data gap*
    - Note: Washington does not impose a lifetime ban on SNAP for drug felons (RCW 74.04.805), but there may be compliance conditions. The screener does not collect criminal history. This affects a small population.
    - Source: 7 U.S.C. § 2015(k)(1).
    - Impact: Low

18. **Identity verification and interview requirement** ⚠️ *data gap*
    - Note: This is a procedural/administrative requirement during the application process, not a pre-screening criterion.
    - Source: 7 CFR 273.2(e); WAC 388-452-0005.
    - Impact: Low

19. **Voluntary quit — individuals who voluntarily quit a job or reduce work hours below 30/week without good cause within 60 days prior to application may be disqualified** ⚠️ *data gap*
    - Note: The screener captures `unemployed` and `worked_in_last_18_mos` but does not capture the reason for job separation or whether hours were voluntarily reduced.
    - Source: 7 CFR 273.7(j); WAC 388-444-0055
    - Impact: Low

20. **Intentional Program Violation (IPV) disqualification** ⚠️ *data gap*
    - Note: The screener cannot and should not attempt to evaluate prior fraud disqualifications. This is verified through state databases during the application process.
    - Source: 7 CFR 273.16; 7 U.S.C. § 2015(b); WAC 388-446-0001
    - Impact: Low

21. **Precise SNAP net income deduction calculations** ⚠️ *data gap*
    - Note: The screener can approximate but not precisely replicate SNAP deduction methodology: (1) standard deduction amounts change annually and vary by household size, (2) Washington uses a Standard Utility Allowance (SUA) rather than actual utility costs, (3) excess shelter deduction has a cap ($672/month for FFY 2025) unless household has elderly/disabled member, (4) medical expense deduction only applies to elderly/disabled members for amounts exceeding $35/month.
    - Source: 7 CFR 273.9(d); WAC 388-450-0185 through 388-450-0230.
    - Impact: Medium


## Benefit Value

- The maximum monthly benefit depends on household size and is only paid to households with no income at all. Benefits are calculated as:
  **Maximum for household size MINUS 30% of household's net monthly income**
  (where net income = gross income after deductions for rent, utilities, childcare, and medical expenses)
- The estimated average benefit per person in FY 2026 is **$188 per month** ($6.17 per day).
- Maximum monthly benefit amounts (as of October 2025):

| Household Size | Maximum Monthly Benefit | Annual Value |
|---|---|---|
| 1 person | $298 | $3,576 |
| 2 people | $546 | $6,552 |
| 3 people | $785 | $9,420 |
| 4 people | $994 | $11,928 |

- Note: Calculating an exact benefit per scenario requires net income (post-deduction), which the screener can only approximate. `estimated_value` will use PolicyEngine's calculation.
- Source: [Center on Budget and Policy Priorities](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits); [Snap Benefit Calculator](https://snapbenefitcalculator.com/washington-snap-calculator/)


## Implementation Coverage

- ✅ Evaluable criteria: 10
- ⚠️  Data gaps: 10
- ⚠️  Complex edge case (recommend disclaimer): 1 (criterion 7 — elderly/disabled alternative path)

10 of 21 total eligibility criteria can be evaluated with current screener fields. The most critical evaluable criteria are: gross income test (200% FPL under WA BBCE), net income test (100% FPL), household size, state residency, current SNAP receipt status, and student eligibility exemptions. Washington's BBCE significantly simplifies screening by eliminating the asset test for most households and raising the gross income limit to 200% FPL. Key corrections from original spec: (1) pregnant women count as **one** household member for Basic Food — pregnancy only affects the work requirement exemption, not household size; (2) the elderly/disabled alternative path (criterion 7) is too complex to reliably evaluate in the screener — recommend a disclaimer instead. Primary gaps are citizenship/immigration status (medium impact), ABAWD work requirements (medium impact, frequently waived in WA), and precise net income deduction calculations (medium impact, approximated).



## Acceptance Criteria

- [ ] Scenario 1 (Single Adult Worker — Clearly Eligible): User should be **eligible**
- [ ] Scenario 2 (Family of Four — Income Just Under 200% FPL Gross and 100% FPL Net): User should be **eligible**
- [ ] Scenario 3 (Single Parent with Child — Gross Income $1 Below 200% FPL): User should be **eligible**
- [ ] Scenario 4 (Couple Household — Gross Income Exactly at 200% FPL): User should be **eligible**
- [ ] Scenario 5 (Single Adult — Gross Income $1 Above 200% FPL): User should be **ineligible**
- [ ] Scenario 6 (Person Exactly Age 18 — Minimum Adult Age): User should be **eligible**
- [ ] Scenario 7 (17-Year-Old Living Alone — Half-Time Student, No Exemption): User should be **ineligible**
- [ ] Scenario 8 (75-Year-Old Elderly Individual — Elderly Exemption): User should be **eligible**
- [ ] Scenario 9 (Washington State Resident in Seattle — Valid Location): User should be **eligible**
- [ ] Scenario 10 (Already Receiving Basic Food/SNAP — Duplicate Benefit Exclusion): User should be **ineligible**
- [ ] Scenario 11 (Household Already Receiving SNAP — Duplicate Benefit Exclusion): User should be **ineligible**
- [ ] Scenario 12 (Mixed Household — Elderly Member, College Student with Exemption, Working Adult): User should be **eligible**
- [ ] Scenario 13 (Family of Five — Two Working Adults, Pregnant Member, Two Children): User should be **eligible**


## Test Scenarios

### Scenario 1: Single Adult Worker — Clearly Eligible for Basic Food

**What we're checking**: Typical single adult with low wage income who clearly meets both gross and net income tests under Washington's BBCE program.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Male, Not a student enrolled in higher education, Not pregnant, No disability, U.S. citizen
- **Income**: Employment income: `$1,500` per month, No other income sources
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI
- **Assets**: No asset information needed (WA BBCE eliminates asset test)

**Why this matters**: This is the most common Basic Food applicant profile — a single working adult with modest earnings. It validates that the screener correctly identifies a clearly eligible household that passes both the gross income test (200% FPL under WA BBCE) and the net income test (100% FPL), with no complicating factors like student status, disability, or elderly exemptions.

---

### Scenario 2: Family of Four — Income Just Under 200% FPL Gross and 100% FPL Net

**What we're checking**: Household that barely meets both the gross income test (200% FPL) and net income test (100% FPL) thresholds, validating edge-case eligibility at the income ceiling.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, Not disabled, US citizen, Employment income: `$4,800` per month
- **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: Spouse, Sex: Female, Not a student, Not pregnant, Not disabled, US citizen, No income
- **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, Sex: Female, US citizen, No income
- **Person 4**: Birth month/year: `April 2019` (age 6), Relationship: Child, Sex: Male, US citizen, No income
- **Expenses**: Monthly rent/mortgage: `$2,200`, Monthly dependent care costs: `$400`
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: This scenario tests the boundary condition where a family's gross income is just barely under the 200% FPL limit and their net income, after all applicable deductions, falls just under the 100% FPL threshold. It validates that the screener correctly applies Washington's BBCE gross income limit, the standard SNAP net income test, and all relevant deductions for a household with children and shelter costs.

---

### Scenario 3: Single Parent with Child — Gross Income $1 Below 200% FPL Threshold

**What we're checking**: Validates that a household of 2 with gross monthly income exactly $1 below the 2026 200% FPL threshold for a household of 2 ($3,607/mo) is correctly found eligible.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Female, Not a student, Not pregnant, No disability, U.S. citizen, Employment income: `$3,606` per month (~$1 below 200% FPL for HH of 2 in 2026: 200% FPL = $3,607/mo)
- **Person 2**: Birth month/year: `September 2020` (age 5), Relationship: Child, Sex: Male, No income, U.S. citizen
- **Expenses**: Rent/housing cost: `$1,200` per month, Child care costs: `$400` per month
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: This test validates the critical boundary condition where gross income is exactly $1 below the 200% FPL threshold under Washington's BBCE policy. It ensures the screener correctly applies the 200% gross income limit (not the standard 130% SNAP limit) and that households just barely meeting the threshold are correctly identified as eligible. Note: income updated from original spec to reflect 2026 FPL values (200% FPL for HH of 2 = $3,607/mo).

---

### Scenario 4: Couple Household — Gross Income Exactly at 200% FPL Threshold

**What we're checking**: Validates that a 2-person household with gross monthly income exactly equal to the 200% FPL threshold for 2026 ($3,607/month for HH of 2) is eligible under Washington's BBCE gross income test, and net income after standard deduction passes 100% FPL.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, Not disabled, US citizen, Employment income: `$2,000` per month
- **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: Spouse, Sex: Female, Not a student, Not pregnant, Not disabled, US citizen, Employment income: `$1,607` per month
- **Combined gross income**: `$3,607/month` (exactly 200% FPL for HH of 2 in 2026). Net income at exactly 100% FPL = `$1,803/month`.
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Testing the exact boundary of the 200% FPL gross income threshold for a 2-person household ensures the screener correctly handles the 'at or below' condition. This is a critical edge case — being $1 over would make the household ineligible for the gross income test. Note: income updated from original spec to reflect 2026 FPL values (200% FPL for HH of 2 = $3,607/mo).

---

### Scenario 5: Single Adult — Gross Income $1 Above 200% FPL, Should Be Ineligible

**What we're checking**: Validates that a single-person household with gross monthly income just $1 above the 2026 200% FPL threshold for a household of 1 ($2,660/mo) is correctly denied Basic Food benefits.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Male, Not a student, Not pregnant, No disability, US citizen, Employment income: `$2,661` per month ($1 above 200% FPL for HH of 1 in 2026: 200% FPL = $2,660/mo)
- **Expenses**: Rent/mortgage: `$900` per month, No other deductions or expenses
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: This tests the upper boundary of the gross income test under Washington's BBCE policy. A household exceeding this threshold by even $1 should be denied, confirming the screener correctly enforces the boundary rather than rounding or allowing a tolerance. Note: income updated from original spec to reflect 2026 FPL values (200% FPL for HH of 1 = $2,660/mo; use $2,661 to be $1 above).

---

### Scenario 6: Person Exactly Age 18 — Minimum Age for Adult SNAP Eligibility

**What we're checking**: Validates that a person who just turned 18 is eligible for Basic Food when all other criteria are met, and that this person is not incorrectly subject to the student eligibility restriction since they are not enrolled in higher education.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 2008` (age 18), Relationship: Head of Household, Not a student enrolled in higher education, Not pregnant, No disability, Employment income: `$800/month`, No other income sources
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Age 18 is the minimum threshold at which a person can independently apply for SNAP as an adult head of household. This test verifies the system correctly handles someone at exactly the minimum adult age boundary. It also confirms that an 18-year-old who is NOT enrolled in higher education is not incorrectly flagged by the student eligibility restriction (which only applies to students aged 18–49 enrolled at least half-time).

---

### Scenario 7: 17-Year-Old Living Alone — Half-Time Student, No Exemption, Ineligible

**What we're checking**: Validates that a 17-year-old (just below age 18) who is a college student enrolled half-time with no student exemption does NOT qualify independently.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 2008` (age 17 — will turn 18 in June 2026), Relationship: Head of Household, Student status: enrolled in higher education at least half-time, Working: No (does not meet any student exemption), No disability, Not pregnant
- **Income**: No earned income, No unearned income, Total gross monthly income: `$0`
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Tests the age boundary just below 18. A 17-year-old applying independently as a half-time college student with no student exemptions should not be eligible. This tests the interaction between age thresholds and student eligibility rules. Note: age 18 is not explicitly a threshold in WA SNAP rules, but the combination of being a minor and a half-time student without exemption makes this an edge case scenario.

---

### Scenario 8: 75-Year-Old Elderly Individual — Eligible with Elderly Exemption

**What we're checking**: Validates that a person aged 75 is eligible for Basic Food and that the elderly exemption (age 60+) correctly applies — in this scenario the person passes the gross income test directly.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1951` (age 75), Relationship: Head of Household, Not a student, Not pregnant, Not disabled (using age 60+ exemption, not disability)
- **Income**: Social Security Retirement income: `$1,200` per month, No other income sources
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF, Not receiving SSI

**Why this matters**: Confirms that a person well above the minimum age threshold is correctly recognized as eligible. Also validates the critical elderly exemption (age 60+) pathway. At $1,200/mo income for HH of 1, this household is well below 200% FPL ($2,660/mo), so it qualifies directly via the gross income test without needing the alternative net-income-only path.

---

### Scenario 9: Washington State Resident in Seattle — Eligible Location Within Service Area

**What we're checking**: Validates that a household residing within Washington State (valid WA ZIP code) is recognized as within the Basic Food service area and can proceed with eligibility determination.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98101`, Select county `King`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, No disability, Not pregnant, Not a student enrolled in higher education, U.S. citizen
- **Income**: Employment income: `$1,200` per month, No other income sources
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF or SSI

**Why this matters**: Confirms that a valid Washington State ZIP code (98101 — downtown Seattle, King County) is properly recognized as within the Basic Food service area. Geographic validation is essential because SNAP is state-administered and applicants must reside in the state where they apply (7 CFR 273.3; WAC 388-468-0005).

---

### Scenario 10: Already Receiving Basic Food/SNAP — Duplicate Benefit Exclusion

**What we're checking**: Validates that a household already receiving SNAP/Basic Food benefits is flagged as ineligible, preventing duplicate benefit enrollment.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: Head of Household, Sex: Female, Not a student, Not pregnant, Not disabled, U.S. citizen, Employment income: `$1,800` per month
- **Person 2**: Birth month/year: `September 2018` (age 7), Relationship: Child, Sex: Male, Not a student, Not disabled, U.S. citizen
- **Current Benefits**: Select that the household **already receives SNAP/Basic Food** benefits (`has_snap` = Yes)

**Why this matters**: Preventing duplicate SNAP benefit enrollment is critical for program integrity. Households already receiving Basic Food should not be screened as eligible for a second enrollment.

---

### Scenario 11: Household Already Receiving SNAP — Duplicate Benefit Exclusion (Parent-Child Household)

**What we're checking**: Whether a parent-child household that is already receiving SNAP/Basic Food benefits is correctly excluded, confirming the exclusion applies regardless of household composition.

**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, No disability, Not pregnant, Not a student, Employment income: `$1,800` per month
- **Person 2**: Birth month/year: `September 2018` (age 7), Relationship: Child, No disability
- **Current Benefits**: Indicate that the household is currently receiving SNAP/Basic Food (`has_snap` = Yes)

**Why this matters**: This scenario differs from Scenario 10 by using a parent-child household rather than a single adult, ensuring the duplicate benefit exclusion applies regardless of household composition.

---

### Scenario 12: Mixed Household — Elderly Exempt Member, College Student with Work Exemption, Working Adult

**What we're checking**: Validates a mixed household where one member is elderly (age 65), one is a college student aged 22 enrolled half-time who qualifies via the 20+ hours/week work exemption, and one is a working adult. Tests interaction of elderly gross income exemption (criterion 7), student eligibility rules (criterion 6), household size determination (criterion 4), and net income test (criterion 2).

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1960` (age 65), Relationship: Head of Household, Not a student, Social Security Retirement income: `$1,200` per month, Not currently receiving SNAP/Basic Food
- **Person 2**: Birth month/year: `September 1996` (age 29), Relationship: Child/Dependent adult, Not a student, No disability, Employment income: `$2,400` per month
- **Person 3**: Birth month/year: `January 2004` (age 22), Relationship: Grandchild, Student: Yes (enrolled at least half-time in higher education), Works 20+ hours per week (qualifies for student exemption), Employment income: `$900` per month, No disability
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF or SSI

**Why this matters**: Validates that the screener correctly applies the elderly/disabled gross income exemption while still enforcing the net income test, and properly handles student eligibility rules within a multi-member household.

---

### Scenario 13: Family of Five — Two Working Adults, Pregnant Member, and Two Children

**What we're checking**: Validates that a multi-member household with two working adults (one pregnant), and two children correctly determines eligibility for a household of 5. Pregnancy does NOT change household size for SNAP — the household remains 5 members.

**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `98103`, Select county `King`
- **Household**: Number of people: `5`
- **Person 1**: Birth month/year: `June 1991` (age 34), Relationship: Head of Household, Sex: Male, US citizen, Employment income: `$2,000` per month, Not a student, No disability
- **Person 2**: Birth month/year: `September 1993` (age 32), Relationship: Spouse, Sex: Female, US citizen, Employment income: `$1,500` per month, Not a student, **Pregnant: Yes** (note: counts as 1 household member, not 2; pregnancy is relevant for work requirement exemption only), No disability
- **Person 3**: Birth month/year: `January 2014` (age 12), Relationship: Child, Sex: Female, US citizen, No income
- **Person 4**: Birth month/year: `July 2017` (age 8), Relationship: Child, Sex: Male, US citizen, No income
- **Person 5**: Birth month/year: `November 2021` (age 4), Relationship: Child, Sex: Male, US citizen, No income
- **Current Benefits**: Not currently receiving SNAP/Basic Food, Not receiving TANF or SSI

**Why this matters**: Tests multiple interacting eligibility criteria simultaneously — household size determination with multiple members, combined income from two earners evaluated against the correct FPL thresholds, and verification that children are included without issue. Confirms that pregnancy does NOT increase household size from 5 to 6 for SNAP (federal SNAP rules and WAC 388-408-0015 do not count unborn children as household members for Basic Food).


## Research Sources

- [DSHS Basic Food (SNAP) Program Overview — Washington State](https://www.dshs.wa.gov/esa/community-services-offices/basic-food)
- [Help Me Grow WA — Basic Food (SNAP) Eligibility Guide](https://helpmegrowwa.org/basic-food-snap)
- [Washington Connection — Online Benefits Application Portal (DSHS)](https://www.washingtonconnection.org/home/)
- [DSHS Food Assistance Program for Legal Immigrants (FAP)](https://www.dshs.wa.gov/esa/program-summary/food-assistance-program-legal-immigrants-fap)
- [Center on Budget and Policy Priorities — A Quick Guide to SNAP Eligibility and Benefits](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits)
- [USDA Food and Nutrition Service — SNAP Recipient Eligibility](https://www.fns.usda.gov/snap/recipient/eligibility)
- [Legal Information Institute — 7 U.S.C. § 2014](https://www.law.cornell.edu/uscode/text/7/2014)
- [Washington State Legislature — WAC 388-400-0040](https://app.leg.wa.gov/wac/default.aspx?cite=388-400-0040)
- [SNAP Benefit Calculator — Washington](https://snapbenefitcalculator.com/washington-snap-calculator/)


## JSON Test Cases

File: `validations/management/commands/import_validations/data/wa_snap.json`

Scenarios 1–13 (scenario 14 removed — the premise that a pregnant woman's unborn child counts as a second household member is incorrect for WA SNAP under federal rules and WAC 388-408-0015).

Updated `eligible` values:
- Scenarios 1, 2, 3, 4, 6, 8, 9, 12, 13: `true`
- Scenarios 5, 7, 10, 11: `false`

Updated income amounts for 2026 FPL:
- Scenario 3 (HH=2, $1 below 200% FPL): `$3,606/mo` (was $2,429)
- Scenario 4 (HH=2, exactly 200% FPL): `$3,607/mo` total combined wages (was $2,510); net income at exactly 100% FPL = `$1,803/mo`
- Scenario 5 (HH=1, $1 above 200% FPL): `$2,661/mo` (was $2,431)


## Generated Program Configuration

File: `programs/management/commands/import_program_config_data/data/wa_snap_initial_config.json`


## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-03-23 | Josh Mejia | Initial research and spec |
| 2026-04-07 | patmanson | Corrections: pregnant women count as 1 HH member (not 2); updated 2026 FPL thresholds in scenarios 3/4/5; clarified elderly/disabled alternative path (criteria 2, 3, 7); recommended disclaimer for 60+/disabled edge case; removed scenario 14; estimated_value deferred to PolicyEngine |
