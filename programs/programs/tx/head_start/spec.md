# Implement Head Start (TX) Program

## Program Details

- **Program**: Head Start
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-11

## Eligibility Criteria

1. **Child must be between ages 3 and 5 (not yet in kindergarten)**
   - Screener fields:
     - `household_member.age`
     - `household_member.birth_year_month`
   - Source: 45 CFR § 1302.12(c)(1) - Head Start Program Performance Standards

2. **Family income at or below 135% of Federal Poverty Level (FPL)**
   - Primary eligibility at or below 100% FPL per 45 CFR § 1302.12(a)(1)(i)
   - Over-income eligibility between 100–130% FPL per 45 CFR § 1302.12(d)(1-2) (up to 35% of enrollment; discretionary, grantee-specific slot availability)
   - The screener uses 135% as a conservative ceiling to surface both groups; the program description notes that families between 100–130% FPL depend on grantee slot availability
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR § 1302.12(a)(1)(i) and § 1302.12(d)(1-2)

3. **Child receives or family is eligible for TANF, SSI, or SNAP (categorical eligibility)**
   - Screener fields:
     - `has_tanf`
     - `has_ssi`
     - `has_snap`
   - Source: 45 CFR § 1302.12(a)(1)(ii)(B) - Categorical eligibility; [Head Start FAQ](https://headstart.gov/about-us/article/head-start-faqs) - SNAP listed alongside TANF and SSI as qualifying benefits

4. **Child is in foster care**
   - Screener fields:
     - `household_member.relationship`
   - Source: 45 CFR § 1302.12(c)(1)(iii) - Foster children eligibility

5. **Family income between 100% and 130% FPL (up to 35% of enrollment)** — show as eligible
   - Note: Under 45 CFR § 1302.12(d)(1-2), a program may enroll up to an additional 35% of participants whose family income is between 100–130% FPL, provided specific reporting requirements are met. Because this pathway serves a defined income band with a substantial enrollment allowance, the screener surfaces these families as potentially eligible. The program description notes that enrollment depends on grantee slot availability.
   - Note: Under 45 CFR § 1302.12(a)(1)(ii), a program may adjust a family's gross income downward for eligibility purposes to account for excessive housing costs. If a family spends more than 30% of gross income on housing (as defined in part 1305), the program may subtract the excess amount — potentially reducing a family's effective income for FPL calculation. This is relevant to families near the 100% or 130% FPL thresholds who might qualify once housing costs are factored in. This adjustment cannot be determined from screener data alone — it requires documentation (bills, bank statements) and is applied at the grantee's discretion. The screener does not collect housing cost data. ⚠️ *data gap*
   - Source: 45 CFR § 1302.12(d)(1-2); housing adjustment per 45 CFR § 1302.12(a)(1)(ii)

6. **Fully discretionary enrollment (no income criterion, up to 10% of enrollment)** ⚠️ *data gap*
   - Note: Under 45 CFR § 1302.12(c)(2), if a child does not meet any criterion under (c)(1) (income, public assistance, homelessness, foster care), a program may still enroll that child at its sole discretion, subject to a 10% enrollment cap (counted within the 35% d.1 cap). This carve-out has no income threshold — it cannot be evaluated without grantee-specific capacity data.
   - Source: 45 CFR § 1302.12(c)(2)
   - Impact: Low

7. **Priority for children from families with incomes below poverty line**
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR § 1302.14(a)(1) - Selection priorities

8. **Child experiencing homelessness** ⚠️ *data gap*
   - Note: Children experiencing homelessness are categorically eligible regardless of income. The screener has 'housing_situation' field in the model but it is not collected from users. The 'needs_housing_help' field indicates desire for housing assistance, not current housing status. Cannot evaluate homelessness status.
   - Source: 45 CFR § 1302.12(c)(1)(i) - Homeless children eligibility
   - Impact: High

9. **Child's immunization status** ⚠️ *data gap*
   - Note: Children must be up-to-date on immunizations or have exemption. This is a post-enrollment requirement, not an eligibility barrier, but must be addressed within 90 days. Not captured in screener.
   - Source: 45 CFR § 1302.42 - Child health status and care
   - Impact: Low

## Benefit Value

- ~$10,517/year per eligible child (ages 3–5), based on TX state spending divided by enrollment (PolicyEngine 2022 data: $538,423,499 ÷ 51,195 slots). Value scales with number of eligible children in the household.
- Note: PolicyEngine calculates this as `state_spending / state_enrollment`; actual grantee-level cost may differ.

## Implementation Coverage

- ✅ Evaluable criteria: 6
- ⚠️  Data gaps: 3

Head Start eligibility can be substantially evaluated with current screener fields. Of the core eligibility criteria, we can evaluate: age requirements (3-5 years old), income eligibility (at or below 135% FPL, covering both the primary ≤100% FPL threshold and the 100–130% FPL over-income pathway under 45 CFR § 1302.12(d)), and categorical eligibility through TANF, SSI, SNAP, and foster care. We can also evaluate selection priorities based on income level. The remaining gaps are: homelessness status (a categorical eligibility factor — the screener does not collect current housing status), the 10% fully discretionary carve-out (depends entirely on grantee judgment), and immunization status (a post-enrollment requirement, not an eligibility barrier). The homelessness gap is the most significant as homeless children are categorically eligible regardless of income.

## Research Sources

- [HHS Poverty Guidelines (Annual Update per 42 U.S.C. § 9902)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
- [Texas Early Childhood Education Eligibility Screener - About Page](https://www.earlychildhood.texas.gov/about-eligibility-screener)
- [Historical HHS Poverty Guidelines with Federal Register Citations (1982-Present)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/prior-hhs-poverty-guidelines-federal-register-references)
- [HHS Poverty Guidelines FAQ - Definitions and Program Applications](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/frequently-asked-questions-related-poverty-guidelines-poverty)
- [Further Resources](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/further-resources-poverty-measurement-poverty-lines-their-history)
- [HHS Poverty Guidelines API - Programmatic Access](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/poverty-guidelines-api)
- [Poverty Estimates, Trends, and Analysis](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-estimates-trends-analysis)
- [Marginal Tax Rates/Benefit Cliffs](https://aspe.hhs.gov/topics/poverty-economic-mobility/marginal-tax-rate-series)

## Research Output

Generated via program-researcher tool on 2026-03-11.

Files committed to repo:
- Program config: `programs/management/commands/import_program_config_data/data/tx_head_start_initial_config.json`
- Test cases: `validations/management/commands/import_validations/data/tx_head_start.json`


## Acceptance Criteria

[ ] Scenario 1 (Single Parent with 4-Year-Old Child, Income Below 100% FPL): User should be **eligible**
[ ] Scenario 2 (Foster Child at Age 3, Family Income at Exactly 100% FPL): User should be **eligible**
[ ] Scenario 3 (Two-Parent Household with 5-Year-Old, Income Exactly at 100% FPL): User should be **eligible**
[ ] Scenario 4 (Single Parent with 4-Year-Old, Income Above 135% FPL, No Categorical Eligibility): User should be **ineligible**
[ ] Scenario 5 (Child Exactly Age 3 - Minimum Age Boundary): User should be **eligible**
[ ] Scenario 6 (Child Age 6 - Above Maximum Age): User should be **ineligible**
[ ] Scenario 7 (Multi-Member Household - One Eligible Child Among Age-Ineligible Siblings): User should be **eligible**
[ ] Scenario 8 (Child Turns 3 Next Month - Month-Level Age Boundary): User should be **ineligible**
[ ] Scenario 9 (Family at 130% FPL - Over-Income Pathway Upper Boundary, No Categorical): User should be **eligible**

## Test Scenarios

### Scenario 1: Single Parent with 4-Year-Old Child, Income Below 100% FPL
**What we're checking**: Validates that a household with a child in the eligible age range (3-5 years old) and income at or below 100% FPL qualifies for Head Start
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1992` (age 34), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800` per month, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2022` (age 3, turning 4 in June), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`

**Why this matters**: This is the most common Head Start eligibility pathway - a low-income family with a preschool-age child. Tests the core income and age requirements per 45 CFR § 1302.12(a)(1)(i) and 45 CFR § 1302.12(c)(1).

---

### Scenario 2: Foster Child at Age 3, Family Income at Exactly 100% FPL
**What we're checking**: Validates minimal eligibility: youngest eligible age (3), foster child categorical eligibility, and income at exactly 100% FPL threshold
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `1,580` monthly (exactly $18,960/year = 100% FPL for household of 2), Insurance: `None`
- **Person 2**: Relationship: `Foster Child`, Birth month/year: `March 2023` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: Tests the absolute minimum eligibility boundaries: youngest eligible age, foster child automatic qualification, and income at the exact 100% FPL threshold without any buffer. Ensures the system correctly handles edge cases where all criteria are just barely met.

---

### Scenario 3: Two-Parent Household with 5-Year-Old, Income Exactly at 100% FPL
**What we're checking**: Validates that a family with income exactly at 100% FPL is eligible (testing the upper boundary of the primary income threshold)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `January 1988` (age 38), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salary`, Amount: `$2,100`, Frequency: `Monthly`, Insurance: `None`
- **Person 2**: Birth month/year: `February 1989` (age 37), Relationship: `Spouse`, Has income: `Yes`, Income type: `Wages/Salary`, Amount: `$900`, Frequency: `Monthly`, Insurance: `None`
- **Person 3**: Birth month/year: `April 2021` (age 5), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Person 4**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: Tests the exact upper boundary of the primary income eligibility threshold (100% FPL per 45 CFR § 1302.12(a)(1)(i)). Ensures the system correctly includes families at exactly 100% FPL, not just below it.

---

### Scenario 4: Single Parent with 4-Year-Old, Income Above 135% FPL - Should NOT Be Eligible
**What we're checking**: Verifies that a household with income above 135% FPL is ineligible when not receiving categorical benefits — this is above both the primary 100% FPL threshold and the 100–130% FPL over-income pathway
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,900` per month (~$34,800 annually, ~140% FPL for HH of 2), Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `June 2022` (age 4), Relationship: `Child`, Has income: `No`, Insurance: `None`, Not in foster care
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: This test validates the income ceiling at 135% FPL. At 140% FPL, the family exceeds both the primary 100% FPL threshold (45 CFR § 1302.12(a)(1)(i)) and the 100–130% FPL over-income band (45 CFR § 1302.12(d)(1-2)). With no categorical eligibility, this family should not be shown as eligible.

---

### Scenario 5: Child Exactly Age 3 (Minimum Age), Income Below 100% FPL - Should Be Eligible
**What we're checking**: Validates that a child who is exactly 3 years old (the minimum age requirement) is eligible for Head Start when family income is below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1991` (age 35), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800` per month ($21,600 annually), Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `March 2023` (age exactly 3), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This test validates that the age eligibility logic correctly includes children who are exactly at the minimum age threshold of 3 years old. Per 45 CFR § 1302.12(c)(1), children must be between ages 3 and 5 (not yet in kindergarten). This ensures the system doesn't incorrectly exclude children who just turned 3.

---

### Scenario 6: Child Age 6 (Above Maximum Age), Income Below 100% FPL - Should NOT Be Eligible
**What we're checking**: Verifies that children who are 6 years old (above the maximum age of 5) are excluded from Head Start eligibility, even when family income is well below 100% FPL
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,500` per month ($18,000/year), Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1991` (age 35), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `January 2020` (age 6), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: This test validates that Head Start strictly enforces the maximum age requirement of 5 years old (not yet in kindergarten) per 45 CFR § 1302.12(c)(1). A 6-year-old child would typically be in kindergarten and therefore excluded from Head Start, regardless of how low the family income is. This ensures program resources are directed to the correct age group and prevents enrollment of school-age children who should be in the K-12 system.

---

### Scenario 7: Multi-Member Household - 3 Children (One Eligible Age, Two Ineligible Ages), Income Below 100% FPL
**What we're checking**: Tests that only age-eligible children (3-5 years old) qualify while siblings outside the age range do not, even when household income is well below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `5`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1988` (age 38), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `May 1990` (age 35), Has income: `No`, Insurance: `None`
- **Person 3 (Child - Too Young)**: Relationship: `Child`, Birth month/year: `June 2024` (age 1), Has income: `No`, Insurance: `None`
- **Person 4 (Child - Eligible Age)**: Relationship: `Child`, Birth month/year: `February 2022` (age 4), Has income: `No`, Insurance: `None`
- **Person 5 (Child - Too Old)**: Relationship: `Child`, Birth month/year: `August 2018` (age 7), Has income: `No`, Insurance: `None`

**Why this matters**: This test validates that the screener correctly applies age eligibility criteria (3-5 years old per 45 CFR § 1302.12(c)(1)) on a per-child basis in multi-child households, ensuring that only age-appropriate children are identified as eligible even when the household meets income requirements

---

### Scenario 8: Child Turns 3 Next Month - Testing Age Boundary at Minimum Eligibility
**What we're checking**: Tests the minimum age boundary where a child turns 3 next month (April 2026), meaning they are currently age 2 at the time of screening (March 2026) and will not yet have turned 3. This should make them ineligible.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1991` (age 35), Has income: `Yes`, Income type: `Employment`, Income amount: `$1,200` per month ($14,400/year), Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `April 2023` (age 2 as of March 2026, turns 3 in April 2026), Has income: `No`, Insurance: `None`
- **Current Benefits**: Not receiving any current benefits
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This edge case tests the minimum age boundary using month-year granularity (the precision available in the screener). A child born April 2023 is age 2 when screened in March 2026 and should not be eligible. This validates that the age calculation correctly handles month-boundary cases per 45 CFR § 1302.12(c)(1). Note: day-level precision (e.g., "turns 3 tomorrow") is not testable since the screener captures only birth month and year.

---

### Scenario 9: Family at 130% FPL - Over-Income Pathway Upper Boundary, No Categorical Eligibility
**What we're checking**: Validates that a family with income at exactly 130% FPL and an age-eligible child is shown as potentially eligible at the upper boundary of the over-income enrollment pathway (45 CFR § 1302.12(d)(1-2))
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,797` per month (~$33,564 annually, ~130% FPL for HH of 3), Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1991` (age 35), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2022` (age 4), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: This test validates the upper boundary of the over-income pathway. Under 45 CFR § 1302.12(d)(1-2), families at up to 130% FPL may be enrolled (up to 35% of slots). Testing at exactly 130% — rather than a comfortable 115% — confirms the screener's ceiling is inclusive and correctly placed. Families in this band should see Head Start as a result so they know to contact their local program about availability — the program description notes that enrollment depends on slot availability.

---


## Source Documentation

- https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- https://www.earlychildhood.texas.gov/about-eligibility-screener

## JSON Test Cases
File: `validations/management/commands/import_validations/data/tx_head_start.json`

## Generated Program Configuration
File: `programs/management/commands/import_program_config_data/data/tx_head_start_initial_config.json`
