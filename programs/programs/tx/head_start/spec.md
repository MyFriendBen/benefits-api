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

7. **Child experiencing homelessness** ⚠️ *data gap*
   - Note: Children experiencing homelessness are categorically eligible regardless of income. The screener has 'housing_situation' field in the model but it is not collected from users. The 'needs_housing_help' field indicates desire for housing assistance, not current housing status. Cannot evaluate homelessness status.
   - Source: 45 CFR § 1302.12(c)(1)(i) - Homeless children eligibility
   - Impact: High


## Benefit Value

- ~$10,517/year per eligible child (ages 3–5), based on TX state spending divided by enrollment (PolicyEngine 2022 data: $538,423,499 ÷ 51,195 slots). Value scales with number of eligible children in the household.
- Note: PolicyEngine calculates this as `state_spending / state_enrollment`; actual grantee-level cost may differ.

## Implementation Coverage

- ✅ Evaluable criteria: 5
- ⚠️  Data gaps: 2

Head Start eligibility can be substantially evaluated with current screener fields. Of the core eligibility criteria, we can evaluate: age requirements (3-5 years old), income eligibility (at or below 135% FPL, covering both the primary ≤100% FPL threshold and the 100–130% FPL over-income pathway under 45 CFR § 1302.12(d)), and categorical eligibility through TANF, SSI, SNAP, and foster care. The remaining gaps are: homelessness status (a categorical eligibility factor — the screener does not collect current housing status) and the 10% fully discretionary carve-out (depends entirely on grantee judgment). The homelessness gap is the most significant as homeless children are categorically eligible regardless of income.

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
[ ] Scenario 2 (Foster Child, Income Above 135% FPL - Categorical Override): User should be **eligible**
[ ] Scenario 3 (Single Parent with 4-Year-Old, Income Above 135% FPL, TANF Recipient - Categorical Override): User should be **eligible**
[ ] Scenario 4 (Child Exactly Age 3 - Minimum Age Boundary): User should be **eligible**
[ ] Scenario 5 (Child Age 6 - Above Maximum Age): User should be **ineligible**
[ ] Scenario 6 (Multi-Member Household - One Eligible Child Among Age-Ineligible Siblings): User should be **eligible**
[ ] Scenario 7 (Child Turns 3 Next Month - Month-Level Age Boundary): User should be **ineligible**
[ ] Scenario 8 (Family at 130% FPL - Over-Income Pathway Upper Boundary, No Categorical): User should be **eligible**
[ ] Scenario 9 (SNAP Recipient, Income Above 135% FPL - Categorical Override): User should be **eligible**
[ ] Scenario 10 (Foster Child, Income Above 135% FPL - Foster Care Categorical Override): User should be **eligible**
[ ] Scenario 11 (Family with High Income Above TX BBCE SNAP Threshold, No Categorical Eligibility): User should be **ineligible**

## Test Scenarios

### Scenario 1: Single Parent with 4-Year-Old Child, Income Below 100% FPL
**What we're checking**: Validates that a household with a child in the eligible age range (3-5 years old) and income at or below 100% FPL qualifies for Head Start
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1992` (age 34), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,496` per month (~85% of 2025 FPL for HH of 2: $21,150/yr → $1,762/mo × 0.85 ≈ $1,496/mo), Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2022` (age 3, turning 4 in June), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: This is the most common Head Start eligibility pathway - a low-income family with a preschool-age child. Tests the core income and age requirements per 45 CFR § 1302.12(a)(1)(i) and 45 CFR § 1302.12(c)(1).

---

### Scenario 2: Foster Child, Income Above 135% FPL - Categorical Override
**What we're checking**: Validates that a foster child is eligible regardless of family income — categorical eligibility for foster children overrides the income limit
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,732` per month (~155% of 2025 FPL for HH of 2: $21,150/yr → $1,762/mo × 1.55 ≈ $2,732/mo), Insurance: `None`
- **Person 2 (Foster Child)**: Relationship: `Foster Child`, Birth month/year: `March 2023` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: Tests that foster child categorical eligibility (45 CFR § 1302.12(c)(1)(iii)) independently qualifies a child regardless of family income. This is distinct from scenario 1 — the family is well above the income ceiling, so eligibility must flow solely from foster care status.

---

### Scenario 3: Single Parent with 4-Year-Old, Income Above 135% FPL, TANF Recipient - Categorical Override
**What we're checking**: Validates that a family receiving TANF is eligible for Head Start regardless of income, because TANF receipt confers categorical eligibility
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,467` per month (~140% of 2025 FPL for HH of 2: $21,150/yr → $1,762/mo × 1.40 ≈ $2,467/mo), Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `June 2022` (age 3), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `TANF`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: Tests that TANF categorical eligibility (45 CFR § 1302.12(a)(1)(ii)(B)) independently qualifies a family regardless of income. The family is above the 135% FPL ceiling, so eligibility must flow solely from TANF receipt. This explicitly covers the TANF pathway; Scenario 9 covers SNAP and Scenario 2/10 cover foster care.

---

### Scenario 4: Child Exactly Age 3 (Minimum Age Boundary), Income Below 100% FPL
**What we're checking**: Validates that a child who is exactly 3 years old (the minimum age requirement) is eligible when family income is below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1991` (age 35), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,496` per month (~85% of 2025 FPL for HH of 2: $21,150/yr → $1,762/mo × 0.85 ≈ $1,496/mo), Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `March 2023` (age exactly 3), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: Validates that the age eligibility logic correctly includes children who are exactly at the minimum age threshold of 3 years old per 45 CFR § 1302.12(c)(1). Ensures the system doesn't incorrectly exclude children who just turned 3.

---

### Scenario 5: Child Age 6 (Above Maximum Age), Income Below 100% FPL
**What we're checking**: Verifies that children who are 6 years old are excluded from Head Start eligibility, even when family income is well below 100% FPL
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,500` per month ($18,000/year), Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1991` (age 35), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `January 2020` (age 6), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: Validates that Head Start strictly enforces the maximum age requirement of 5 years old (not yet in kindergarten) per 45 CFR § 1302.12(c)(1). A 6-year-old is typically in kindergarten and excluded regardless of income.

---

### Scenario 6: Multi-Member Household - One Eligible-Age Child Among Age-Ineligible Siblings
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
- **Current Benefits**: Select `None`
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: Validates that the screener applies age eligibility criteria (45 CFR § 1302.12(c)(1)) on a per-child basis in multi-child households, ensuring only age-appropriate children are flagged as eligible.

---

### Scenario 7: Child Turns 3 Next Month - Month-Level Age Boundary
**What we're checking**: Tests that a child born April 2023 (age 2 as of March 2026, turns 3 in April 2026) is ineligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1991` (age 35), Has income: `Yes`, Income type: `Employment`, Income amount: `$1,200` per month ($14,400/year), Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `April 2023` (age 2 as of March 2026, turns 3 in April 2026), Has income: `No`, Insurance: `None`
- **Current Benefits**: Not receiving any current benefits
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: Tests the minimum age boundary at month-year granularity (the precision available in the screener). Validates that the age calculation correctly handles month-boundary cases per 45 CFR § 1302.12(c)(1). Note: day-level precision is not testable since the screener captures only birth month and year.

---

### Scenario 8: Family at Exactly 130% FPL - Over-Income Pathway Upper Boundary
**What we're checking**: Validates that a family at exactly 130% FPL with an age-eligible child is shown as potentially eligible at the upper boundary of the over-income enrollment pathway
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,887` per month (~130% of 2025 FPL for HH of 3: $26,650/yr → $2,221/mo × 1.30 ≈ $2,887/mo), Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1991` (age 35), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2022` (age 4), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: Validates the upper boundary of the over-income pathway (45 CFR § 1302.12(d)(1-2)). Testing at exactly 130% confirms the screener's ceiling is inclusive. Families in this band should see Head Start as a result so they know to contact their local program about slot availability.

---

### Scenario 9: SNAP Recipient at 150% FPL - Categorical Override
**What we're checking**: Validates that a family receiving SNAP is eligible for Head Start regardless of income, because SNAP receipt confers categorical eligibility
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1988` (age 38), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,331` per month (~150% of 2025 FPL for HH of 3: $26,650/yr → $2,221/mo × 1.50 ≈ $3,331/mo), Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1990` (age 36), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2022` (age 4), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `SNAP`
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: Tests that SNAP categorical eligibility (45 CFR § 1302.12(a)(1)(ii)(B)) independently qualifies a family regardless of income. The family is well above the income ceiling, so eligibility must flow solely from SNAP receipt. The same logic applies to TANF and SSI — this scenario covers the categorical override pathway for all three benefits.

---

### Scenario 10: Foster Child, Income Above 135% FPL - Foster Care Categorical Override
**What we're checking**: Validates that a foster child is categorically eligible for Head Start regardless of family income, with no other qualifying factors (no SNAP/TANF/SSI)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1985` (age 41), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,435` per month (~195% of 2025 FPL for HH of 2: $21,150/yr → $1,762/mo × 1.95 ≈ $3,437/mo), Income frequency: `Monthly`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Foster Child)**: Relationship: `Foster Child`, Birth month/year: `August 2022` (age 3), Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Tests that foster care status (45 CFR § 1302.12(c)(1)(iii)) independently qualifies a child regardless of family income, with no other categorical benefit (SNAP/TANF/SSI) present. The household income is nearly double the 100% FPL threshold, so eligibility must flow solely from foster care status. This isolates the foster care override pathway from the income and SNAP/TANF/SSI pathways.

---

### Scenario 11: Family with High Income Above TX BBCE SNAP Threshold, No Categorical Eligibility
**What we're checking**: Validates that a family with income well above 135% FPL is ineligible for Head Start when there is no categorical eligibility (no SNAP, TANF, SSI, or foster care), and income is high enough to also be above the TX BBCE SNAP threshold so PolicyEngine does not compute SNAP eligibility internally
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1988` (age 38), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,775` per month (~170% of 2025 FPL for HH of 3: $26,650/yr → $2,221/mo × 1.70 ≈ $3,775/mo), Income frequency: `Monthly`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 2 (Spouse)**: Birth month/year: `March 1990` (age 36), Relationship: `Spouse`, Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Person 3 (Child)**: Birth month/year: `June 2022` (age 3–4), Relationship: `Child`, Has income: `No`, Insurance: `None`, Citizenship: `U.S. Citizen`
- **Current Benefits**: Select `None`

**Why this matters**: Validates the income ceiling for Head Start (135% FPL) with no categorical override. The household income of $3,775/mo is ~170% FPL for a 3-person household — well above the 135% ceiling. The child is age-eligible and no categorical benefits are selected, so the only remaining eligibility question is income. The income also exceeds the TX BBCE SNAP gross income threshold (~$3,664/mo for a 3-person household, 165% of the SPM poverty threshold), ensuring PolicyEngine does not internally compute SNAP eligibility via categorical eligibility — which could otherwise incorrectly trigger Head Start eligibility through the `snap: null` pathway.

---


## Source Documentation

- https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- https://www.earlychildhood.texas.gov/about-eligibility-screener

## JSON Test Cases
File: `validations/management/commands/import_validations/data/tx_head_start.json`

## Generated Program Configuration
File: `programs/management/commands/import_program_config_data/data/tx_head_start_initial_config.json`
