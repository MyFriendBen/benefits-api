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

2. **Family income at or below 135% of Federal Poverty Level (FPL)**
   - Primary eligibility at or below 100% FPL per 45 CFR 1302.12(a)(1)(i) and 42 U.S.C. § 9840(a)(1)(B)(i)
   - Over-income eligibility between 100–130% FPL per 45 CFR 1302.12(d)(1-2) (up to 35% of enrollment; discretionary, grantee-specific slot availability)
   - The screener uses 135% as a conservative ceiling to surface both groups; the program description notes that families between 100–130% FPL depend on grantee slot availability
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`

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

6. **Geographic service area requirement** ⚠️ *data gap*
   - Note: Each Early Head Start grantee serves specific geographic areas (counties, cities, neighborhoods). Texas has multiple grantees, each with their own service area boundaries. We have `zipcode` and `county` fields but would need grantee-specific service area data to evaluate which program(s) serve a given location. This is program-specific, not universal eligibility.
   - Source: 45 CFR 1302.11(b) - Programs serve designated geographic areas
   - Impact: High

7. **Family income between 100% and 130% FPL (up to 35% of enrollment)** — show as eligible
   - Note: Under 45 CFR 1302.12(d)(1-2), a program may enroll up to an additional 35% of participants whose family income is between 100–130% FPL, provided specific reporting requirements are met. Because this pathway serves a defined income band with a substantial enrollment allowance, the screener surfaces these families as potentially eligible. The program description notes that enrollment depends on grantee slot availability.
   - Source: 45 CFR 1302.12(d)(1-2)

8. **Fully discretionary enrollment (no income criterion, up to 10% of enrollment)** ⚠️ *data gap*
   - Note: Under 45 CFR 1302.12(c)(2), if a child does not meet any criterion under (c)(1) (income, public assistance, homelessness, foster care), a program may still enroll that child at its sole discretion, subject to a 10% enrollment cap. This carve-out has no income threshold — it cannot be evaluated without grantee-specific capacity data.
   - Source: 45 CFR 1302.12(c)(2)
   - Impact: Low

9. **Tribal program eligibility (income waived for tribal service area)** ⚠️ *data gap*
    - Note: A Tribal program may determine any pregnant woman or child in the approved tribal service area to be eligible regardless of income, provided they meet the age requirement (birth to 36 months or pregnant, per 45 CFR 1302.12(b)). Cannot evaluate without knowing whether the grantee is a Tribal program and whether the user's location falls within the tribal service area. Capturing this would require grantee-type data and tribal service area boundaries.
    - Source: 45 CFR 1302.12(e)
    - Impact: Low (applies only to Tribal grantees)

10. **Small community eligibility (program-defined criteria)** ⚠️ *data gap*
    - Note: In communities with 1,000 or fewer individuals, a program may establish its own eligibility criteria provided they satisfy the requirements of section 645(a)(2) of the Act. Cannot evaluate without community population data and the specific criteria a given small-community grantee has established.
    - Source: 45 CFR 1302.12(g)
    - Impact: Low (applies only to very small communities)

## Benefit Value

- Amount varies by household - see test cases

## Implementation Coverage

- ✅ Evaluable criteria: 5
- ⚠️  Data gaps: 5

Of 10 identified eligibility criteria, 5 can be fully evaluated and 5 cannot. Note: Early Head Start has no citizenship or immigration requirement — all children qualify regardless of status. The evaluable criteria are: age (birth to 36 months / pregnant), income at or below 135% FPL (covering primary 100% FPL threshold and the 100–130% FPL over-income pathway under 45 CFR 1302.12(d)), categorical eligibility through TANF/SSI/SNAP, and foster care status. Major gaps include: (1) fully discretionary 10% enrollment carve-out (45 CFR 1302.12(c)(2)) — no income threshold, grantee discretion only; (2) homelessness status — housing_situation field exists but is not collected from users; (3) geographic service area — requires grantee-specific boundary data; (4) tribal program eligibility (45 CFR 1302.12(e)) — requires knowing whether grantee is a Tribal program and tribal service area boundaries; (5) small community eligibility (45 CFR 1302.12(g)) — requires community population data and grantee-specific criteria for communities of 1,000 or fewer. The income threshold (135% FPL ceiling) and categorical eligibility provisions are well-supported by existing fields.

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
[ ] Scenario 3 (Family with toddler at 134% FPL - just below income ceiling): User should be **eligible** with $None/year
[ ] Scenario 16 (Family at 140% FPL - above all income thresholds, no categorical eligibility): User should be **ineligible**
[ ] Scenario 6 (Newborn at exactly 0 months old - minimum age requirement): User should be **eligible** with $None/year
[ ] Scenario 7 (Child age 3 years old - just above maximum age threshold): User should be **ineligible**
[ ] Scenario 8 (Child age 2 years 11 months - approaching upper age limit): User should be **eligible** with $None/year
[ ] Scenario 10 (Family already enrolled in Early Head Start - duplicate enrollment check): User should be **ineligible**
[ ] Scenario 12 (Mixed household - eligible toddler, ineligible older sibling, working parent at 95% FPL): User should be **eligible** with $None/year
[ ] Scenario 13 (Multi-generational household - pregnant teen, infant sibling, and working parent at 92% FPL): User should be **eligible** with $None/year
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

### Scenario 3: Family with toddler at 134% FPL - just below income ceiling
**What we're checking**: Validates income eligibility when family income is just below the 135% FPL screener ceiling (134% FPL)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `June 1995` (age 30), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$2,976` monthly (~134% FPL for household of 3), Insurance: `None`
- **Person 2**: Birth month/year: `August 1997` (age 28), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3**: Birth month/year: `January 2025` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Select `U.S. Citizen` for all household members

**Why this matters**: Tests the screener's 135% FPL income ceiling boundary. A family at 134% FPL falls within the 100–130% FPL over-income band (45 CFR 1302.12(d)) and should be shown as potentially eligible. This validates the screener correctly includes families just below its upper income ceiling without rounding errors that might incorrectly exclude them.

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

### Scenario 8: Child age 2 years 11 months - approaching upper age limit
**What we're checking**: Validates that a child who is 2 years and 11 months old (35 months) is eligible, just one month before the 36-month age cutoff
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `You (head of household)`, Birth month/year: `January 1998` (age 28), Has income: `Yes`, Income type: `Job (wages/salary)`, Income amount: `$2,100`, Income frequency: `Monthly`, Health insurance: `None`
- **Person 2**: Relationship: `Spouse`, Birth month/year: `March 1997` (age 29), Has income: `No`, Health insurance: `None`
- **Person 3**: Relationship: `Child`, Birth month/year: `April 2023` (age 2 years 11 months), Has income: `No`, Health insurance: `None`
- **Current Benefits**: Select `None of these`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: This is a near-boundary threshold check. A child at 35 months is just one month before the age cutoff, validating that the screener correctly includes children right at the upper edge of eligibility rather than treating this as a comfortable mid-range case. Combined with income eligibility at 95% FPL.

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

### Scenario 16: Family at 140% FPL - above all income thresholds, no categorical eligibility
**What we're checking**: Verifies that a family with income above 130% FPL and no categorical eligibility (no TANF/SNAP/SSI, not foster care) is NOT eligible
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `January 1992` (age 34), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$3,015` monthly (~140% FPL for household of 3), Frequency: `Monthly`, Insurance: `None`
- **Person 2**: Birth month/year: `March 1993` (age 33), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Select `U.S. Citizen` for all household members

**Why this matters**: This test validates the upper income boundary of the screener's 135% FPL ceiling. At 140% FPL, the family exceeds both the primary 100% FPL threshold and the 100–130% FPL over-income band under 45 CFR 1302.12(d). With no categorical eligibility pathway (TANF, SNAP, SSI, foster care), this family should not be shown as eligible.

---


## Source Documentation

- https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- https://www.earlychildhood.texas.gov/about-eligibility-screener

