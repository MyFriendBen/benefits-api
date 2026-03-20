# Implement Early Head Start (TX) Program

## Program Details

- **Program**: Early Head Start
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-11

## Eligibility Criteria

1. **Child must be under age 3 (birth to 36 months) OR pregnant woman**
   - Screener fields:
     - `household_member.age`
     - `household_member.pregnant`
     - `household_member.birth_year_month`
   - Source: 45 CFR 1302.12(c) - Early Head Start serves children from birth to age 3 (under 36 months)

2. **Family income at or below 100% of Federal Poverty Level (FPL)**
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR 1302.12(a)(1)(i) and 42 U.S.C. § 9840(a)(1)(B)(i)

3. **Child receives or is eligible for public assistance (TANF, SSI, or SNAP)**
   - Screener fields:
     - `has_tanf`
     - `has_ssi`
     - `has_snap`
   - Source: 45 CFR 1302.12(a)(1)(ii)(A)-(C) - Categorical eligibility for families receiving TANF, SSI, or SNAP

4. **Child is in foster care**
   - Screener fields:
     - `household_member.relationship`
   - Source: 45 CFR 1302.12(a)(1)(iii) - Categorical eligibility for foster children

5. **Child is homeless (McKinney-Vento definition)** ⚠️ *data gap*
   - Note: The housing_situation field exists in the data model but is not collected from users during screening. The needs_housing_help field only indicates whether the user wants housing assistance, not their actual housing status. Cannot determine if child meets McKinney-Vento homeless definition (42 U.S.C. § 11434a). Categorical eligibility under this pathway cannot be evaluated until housing_situation is collected.
   - Source: 45 CFR 1302.12(a)(1)(iv) and 42 U.S.C. § 11434a
   - Impact: Medium

6. **U.S. citizenship or qualified immigration status not required for child** ⚠️ *data gap*
   - Note: Early Head Start does not have citizenship requirements for children. No citizenship field in screener, but this is not a barrier - all children are eligible regardless of immigration status.
   - Source: 45 CFR 1302.12(d) - Children do not need to meet citizenship requirements
   - Impact: Low

7. **Geographic service area requirement** ⚠️ *data gap*
   - Note: Each Early Head Start grantee serves specific geographic areas (counties, cities, neighborhoods). Texas has multiple grantees, each with their own service area boundaries. We have `zipcode` and `county` fields but would need grantee-specific service area data to evaluate which program(s) serve a given location. This is program-specific, not universal eligibility.
   - Source: 45 CFR 1302.11(b) - Programs serve designated geographic areas
   - Impact: High

8. **Family income between 100% and 130% FPL (up to 10% of enrollment)** ⚠️ *data gap*
   - Note: Grantees *may* enroll up to 10% of their slots for families with income between 100–130% FPL (45 CFR 1302.12(a)(2)), but this is discretionary. Whether a specific grantee has chosen to use this pathway and has available over-income slots cannot be determined from the screener data. Cannot evaluate without grantee-specific capacity data.
   - Source: 45 CFR 1302.12(a)(2) - Over-income eligibility for up to 10% of enrollment
   - Impact: High

## Benefit Value

- Amount varies by household - see test cases

## Implementation Coverage

- ✅ Evaluable criteria: 4
- ⚠️  Data gaps: 4

Of 8 identified eligibility criteria, 4 can be fully evaluated with current screener fields and 4 cannot be evaluated. The core evaluable criteria are: age (birth to 36 months / pregnant), income at or below 100% FPL, categorical eligibility through TANF/SSI/SNAP, and foster care status. Major gaps include: (1) over-income slots (100–130% FPL) - discretionary and grantee-specific, cannot evaluate availability; (2) homelessness status - housing_situation field exists but is not collected from users; (3) geographic service area - requires grantee-specific boundary data. The income threshold (100% FPL) and categorical eligibility provisions are well-supported by existing fields.

## Research Sources

- [HHS Poverty Guidelines (Annual Updates per 42 U.S.C. § 9902)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
- [Texas Early Childhood Education Eligibility Screener - About Page](https://www.earlychildhood.texas.gov/about-eligibility-screener)
- [Prior HHS Poverty Guidelines - Federal Register Citations (Historical Archive)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/prior-hhs-poverty-guidelines-federal-register-references)
- [HHS Poverty Guidelines - Frequently Asked Questions](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/frequently-asked-questions-related-poverty-guidelines-poverty)
- [Further Resources](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/further-resources-poverty-measurement-poverty-lines-their-history)
- [Mollie Orshansky](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/mollie-orshansky-her-career-achievements-publications)
- [HHS Poverty Guidelines API - Programmatic Access](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/poverty-guidelines-api)
- [Poverty Estimates, Trends, and Analysis](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-estimates-trends-analysis)
- [Marginal Tax Rates/Benefit Cliffs](https://aspe.hhs.gov/topics/poverty-economic-mobility/marginal-tax-rate-series)

## Acceptance Criteria

[ ] Scenario 1 (Young mother with infant - income eligible at 85% FPL): User should be **eligible** with $None/year
[ ] Scenario 2 (Pregnant woman at exactly 100% FPL - minimal income eligibility): User should be **eligible** with $None/year
[ ] Scenario 3 (Family with toddler at 99% FPL - just below income threshold): User should be **eligible** with $None/year
[ ] Scenario 4 (Family with toddler at exactly 100% FPL - income at exact threshold): User should be **eligible** with $None/year
[ ] Scenario 5 (Family with toddler at 101% FPL - income just above threshold): User should be **ineligible**
[ ] Scenario 6 (Newborn at exactly 0 months old - minimum age requirement): User should be **eligible** with $None/year
[ ] Scenario 7 (Child age 3 years old - just above maximum age threshold): User should be **ineligible**
[ ] Scenario 8 (Child age 2 years 11 months - well within age eligibility range): User should be **eligible** with $None/year
[ ] Scenario 9 (Family at 94% FPL with infant - income and age eligible): User should be **eligible** with $None/year
[ ] Scenario 10 (Family already enrolled in Early Head Start - duplicate enrollment check): User should be **ineligible**
[ ] Scenario 11 (Household with only an over-age child - no EHS-eligible children): User should be **ineligible**
[ ] Scenario 12 (Mixed household - eligible toddler, ineligible older sibling, working parent at 95% FPL): User should be **eligible** with $None/year
[ ] Scenario 13 (Multi-generational household - pregnant teen, infant sibling, and working parent at 92% FPL): User should be **eligible** with $None/year
[ ] Scenario 14 (Child turning 3 years old next month - age boundary edge case): User should be **eligible** with $None/year
[ ] Scenario 15 (Family with SNAP benefits - categorical eligibility overrides high income): User should be **eligible** with $None/year

## Test Scenarios

### Scenario 1: Young mother with infant - income eligible at 85% FPL
**What we're checking**: Validates basic income eligibility for a household with an infant under age 3 at 85% of Federal Poverty Level
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `June 1998` (age 27), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,448`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `January 2025` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Select `U.S. Citizen` for all household members

**Why this matters**: This is the most common eligibility pathway for Early Head Start - a low-income family with a young child under age 3. Testing this scenario validates the core income-based eligibility criterion (45 CFR 1302.12(a)(1)(i)) and age requirement (45 CFR 1302.12(c)).

---

### Scenario 2: Pregnant woman at exactly 100% FPL - minimal income eligibility
**What we're checking**: Validates eligibility at the exact 100% FPL threshold with pregnant woman (no children yet)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1998` (age 27), Relationship: `Head of Household`, Pregnant: `Yes`, Has income: `Yes`, Income type: `Wages/Salary`, Income amount: `1255` monthly (exactly 100% FPL for household of 1), Insurance: `None`
- **Current Benefits**: No current benefits selected
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: Tests the minimum threshold for income eligibility at exactly 100% FPL with a pregnant woman, confirming that pregnant women qualify even without existing children under age 3

---

### Scenario 3: Family with toddler at 99% FPL - just below income threshold
**What we're checking**: Validates income eligibility when family income is just below the 100% FPL threshold (99% FPL)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1995` (age 30), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$2,130` monthly (99% of FPL for household of 3), Insurance: `None`
- **Person 2**: Birth month/year: `August 1997` (age 28), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3**: Birth month/year: `January 2025` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Select `U.S. Citizen` for all household members

**Why this matters**: Tests the income threshold boundary to ensure families just below 100% FPL are correctly identified as eligible under 45 CFR 1302.12(a)(1)(i). This validates the screener properly calculates and compares income against FPL without rounding errors that might incorrectly exclude eligible families.

---

### Scenario 4: Family with toddler at exactly 100% FPL - income at exact threshold
**What we're checking**: Validates that a family with income exactly at 100% FPL is eligible (testing the 'at or below' boundary condition per 45 CFR 1302.12(a)(1)(i))
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1995` (age 31), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `2,152` (monthly), Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1996` (age 30), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select: `None`
- **Citizenship**: All household members are U.S. citizens

**Why this matters**: This test validates the upper boundary of the primary income eligibility criterion. Per 45 CFR 1302.12(a)(1)(i), families 'at or below' 100% FPL are eligible. This ensures the system correctly interprets 'at or below' to include families at exactly 100% FPL, not just below it. This is a critical boundary test since many families may be right at the threshold.

---

### Scenario 5: Family with toddler at 101% FPL - income just above threshold
**What we're checking**: Verifies that families with income just above 100% FPL (at 101%) are NOT eligible for Early Head Start under standard income criteria
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `January 1992` (age 34), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$2,173`, Frequency: `Monthly`, Insurance: `None`
- **Person 2**: Birth month/year: `March 1993` (age 33), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Select `U.S. Citizen` for all household members

**Why this matters**: This test validates that the screener correctly enforces the 100% FPL income limit per 45 CFR 1302.12(a)(1)(i) and 42 U.S.C. § 9840(a)(1)(B)(i). Families just above this threshold should not qualify under standard income criteria, though they might qualify for the 10% over-income slots (100-130% FPL) which are discretionary and not guaranteed.

---

### Scenario 6: Newborn at exactly 0 months old - minimum age requirement
**What we're checking**: Child at exactly the minimum age (birth/0 months) qualifies for Early Head Start
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1998` (age 28), Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$1,800`, Frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `March 2026` (age 0 - newborn born this month), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: Validates that the absolute minimum age (newborn at 0 months) is correctly included in the birth-to-36-months eligibility range per 45 CFR 1302.12(c). This ensures the screener doesn't incorrectly exclude newborns.

---

### Scenario 7: Child age 3 years old - just above maximum age threshold
**What we're checking**: Validates that a child who has turned 3 years old (36 months) is NOT eligible for Early Head Start, which serves children birth to 36 months
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `January 1998` (age 28), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2**: Relationship: `Child`, Birth month/year: `February 2023` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: This test validates the upper age boundary for Early Head Start eligibility. Per 45 CFR 1302.12(c), Early Head Start serves children from birth to age 3 (under 36 months). A child who has reached their 3rd birthday should transition to Head Start, not Early Head Start. This ensures proper program placement and resource allocation.

---

### Scenario 8: Child age 2 years 11 months - well within age eligibility range
**What we're checking**: Validates that a child who is 2 years and 11 months old (35 months) is eligible, being well within the birth to 36 months age range but approaching the upper limit
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `You (head of household)`, Birth month/year: `January 1998` (age 28), Has income: `Yes`, Income type: `Job (wages/salary)`, Income amount: `$2,100`, Income frequency: `Monthly`, Health insurance: `None`
- **Person 2**: Relationship: `Spouse`, Birth month/year: `March 1997` (age 29), Has income: `No`, Health insurance: `None`
- **Person 3**: Relationship: `Child`, Birth month/year: `April 2023` (age 2 years 11 months), Has income: `No`, Health insurance: `None`
- **Current Benefits**: Select `None of these`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: This test validates that children who are well within the age range (but not at the extremes) are properly identified as eligible. A child at 35 months is clearly under the 36-month threshold and should qualify based on age, combined with income eligibility at 95% FPL.

---

### Scenario 9: Family at 94% FPL with infant - income and age eligible
**What we're checking**: Validates that a family with income at 94% FPL and an age-eligible infant is correctly identified as eligible. Note: geographic service area eligibility is a high-impact data gap (each grantee has specific service area boundaries not available in the screener) and is not evaluated here.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `January 1998` (age 28), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,600`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2**: Birth month/year: `January 2025` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: This test confirms income and age eligibility for a household of 2 at 94% FPL ($1,600/month ≈ $19,200/year, below the $20,440 threshold for household of 2). Geographic service area validation requires grantee-specific boundary data that is not available in the screener and therefore cannot be used as an eligibility signal.

---

### Scenario 10: Family already enrolled in Early Head Start - duplicate enrollment check
**What we're checking**: Tests that families already receiving Early Head Start benefits are properly identified and handled (may show different messaging or prevent duplicate enrollment)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `March 1998` (age 28), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child 1)**: Relationship: `Child`, Birth month/year: `January 2025` (age 1 year 2 months), Has income: `No`, Insurance: `None`, Current benefits: `Early Head Start`
- **Person 3 (Child 2)**: Relationship: `Child`, Birth month/year: `November 2024` (age 1 year 4 months), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `Early Head Start` as a current benefit (marks the household as already enrolled)

**Why this matters**: Prevents duplicate enrollment and ensures accurate tracking of program participation. Families already receiving Early Head Start should not be screened as newly eligible, as they are already being served. This tests the system's ability to identify and handle existing beneficiaries appropriately.

---

### Scenario 11: Household with only an over-age child - no EHS-eligible children
**What we're checking**: Verifies that a household with no children under age 3 is NOT eligible for Early Head Start, even when income is below 100% FPL
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `You (Head of Household)`, Birth month/year: `January 1992` (age 34), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,100`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2**: Relationship: `Child`, Birth month/year: `June 2022` (age 3 years 9 months), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`

**Why this matters**: Early Head Start specifically serves children birth to age 3 (36 months) per 45 CFR 1302.12(c). A household with no age-eligible children should be ineligible regardless of income level. This ensures the age criterion is correctly applied as a prerequisite for all other eligibility pathways.

---

### Scenario 12: Mixed household - eligible toddler, ineligible older sibling, working parent at 95% FPL
**What we're checking**: Tests that eligibility is correctly determined when household contains both age-eligible (under 3) and age-ineligible (over 3) children, with income below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1992` (age 34), Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$2,470`, Frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `May 1993` (age 32), Has income: `No`, Insurance: `None`
- **Person 3 (Eligible Child)**: Relationship: `Child`, Birth month/year: `June 2024` (age 1 year 9 months), Has income: `No`, Insurance: `None`
- **Person 4 (Ineligible Child)**: Relationship: `Child`, Birth month/year: `February 2021` (age 5), Has income: `No`, Insurance: `None`
- **Current Benefits**: Not receiving any current benefits

**Why this matters**: This test validates that the screener correctly handles mixed-age households where some children meet age requirements and others don't. Early Head Start serves children birth to age 3, while Head Start serves ages 3-5. A household can have children in both age ranges, and the presence of older children should not disqualify younger eligible children. This is a common real-world scenario for families with multiple children.

---

### Scenario 13: Multi-generational household - pregnant teen, infant sibling, and working parent at 92% FPL
**What we're checking**: Multiple eligible children (pregnant teen + infant) in same household with working parent below income threshold
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1988` (age 38), Has income: `Yes`, Income type: `Wages/Salary`, Amount: `$2,392`, Frequency: `Monthly`, Insurance: `None`
- **Person 2 (Pregnant Teen)**: Relationship: `Child`, Birth month/year: `June 2009` (age 16), Pregnant: `Yes`, Has income: `No`, Insurance: `None`
- **Person 3 (Infant)**: Relationship: `Child`, Birth month/year: `December 2025` (age 0 - 3 months old), Has income: `No`, Insurance: `None`
- **Person 4 (School-Age Child)**: Relationship: `Child`, Birth month/year: `March 2018` (age 8), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` or skip if no current benefits

**Why this matters**: Tests complex household with multiple eligible members through different pathways (pregnancy + age-eligible infant) while including an ineligible older child, ensuring the screener correctly identifies all eligible household members and doesn't incorrectly exclude based on presence of older children

---

### Scenario 14: Child turning 3 years old next month - age boundary edge case
**What we're checking**: Tests the age cutoff at 36 months (under age 3) when child will age out next month
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `January 1998` (age 28), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `2,100`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2**: Relationship: `Child`, Birth month/year: `April 2023` (age 2 years, 11 months - turns 3 next month), Insurance: `None`
- **Current Benefits**: Select: `None`
- **Citizenship**: Select: `U.S. Citizen`

**Why this matters**: Tests the age boundary interpretation - whether the system correctly evaluates 'under age 3' as the child's current age on the application date. With a birth month of April 2023 and research date of March 2026, the child is 2 years 11 months old and turns 3 next month. This edge case is critical because families applying just before a child's 3rd birthday need clarity on eligibility timing.

---

### Scenario 15: Family with SNAP benefits - categorical eligibility overrides high income
**What we're checking**: Verifies that a family receiving SNAP is categorically eligible for Early Head Start regardless of income exceeding 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,500`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `SNAP (Food Stamps)`: `Yes`
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: Per 45 CFR 1302.12(a)(1)(ii)(C), families receiving SNAP have categorical eligibility for Early Head Start regardless of income level. This test validates that SNAP participation is a pathway IN (not an exclusion), and that high-income families who receive SNAP still qualify. Unlike CSFP, Early Head Start treats other benefit participation as a categorical eligibility pathway.

---


## Source Documentation

- https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- https://www.earlychildhood.texas.gov/about-eligibility-screener

