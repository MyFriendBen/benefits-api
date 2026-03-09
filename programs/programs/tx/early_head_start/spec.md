# Implement Early Head Start (TX) Program

## Program Details

- **Program**: Early Head Start
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-06

## Eligibility Criteria

1. **Child must be under age 3 (from birth to age 3) OR pregnant woman**
   - Screener fields:
     - `household_member.age`
     - `household_member.pregnant`
     - `household_member.birth_year_month`
   - Logic: `(num_children(age_min=0, age_max=2) > 0) OR (any household_member has pregnant=True)`
   - Source: 45 CFR § 1302.12(c)

2. **Family income at or below 100% of Federal Poverty Level (FPL)**
   - Screener fields:
     - `income (all types)`
     - `household_size`
   - Logic: `calc_gross_income('yearly', ['all']) <= FPL_100_PERCENT[household_size]`
   - Source: 45 CFR § 1302.12(a)(1)

3. **Family income between 100% and 130% FPL (up to 10% of enrollment)**
   - Screener fields:
     - `income (all types)`
     - `household_size`
   - Logic: `(calc_gross_income('yearly', ['all']) > FPL_100_PERCENT[household_size]) AND (calc_gross_income('yearly', ['all']) <= FPL_130_PERCENT[household_size])`
   - Source: 45 CFR § 1302.12(a)(2)

4. **Child receives or is eligible for public assistance (TANF)**
   - Screener fields:
     - `has_tanf`
   - Logic: `has_tanf == True`
   - Source: 45 CFR § 1302.12(b)(1)

5. **Child receives or is eligible for SSI**
   - Screener fields:
     - `has_ssi`
   - Logic: `has_ssi == True`
   - Source: 45 CFR § 1302.12(b)(2)

6. **Child is in foster care**
   - Screener fields:
     - `household_member.relationship`
   - Logic: `any household_member has relationship == 'fosterChild'`
   - Source: 45 CFR § 1302.12(b)(3)

7. **Child is homeless**
   - Screener fields:
     - `housing_situation`
   - Logic: `housing_situation in ['homeless', 'shelter', 'transitional']`
   - Source: 45 CFR § 1302.12(b)(4)

8. **Selection priority: Lowest income families**
   - Screener fields:
     - `income (all types)`
     - `household_size`
   - Logic: `calc_gross_income('yearly', ['all']) / FPL_100_PERCENT[household_size] (lower percentage = higher priority)`
   - Source: 45 CFR § 1302.12(c)(1)

9. **Selection priority: Children with disabilities**
   - Screener fields:
     - `household_member.disabled`
     - `household_member.long_term_disability`
     - `household_member.visually_impaired`
   - Logic: `any child (age 0-2) has disabled=True OR long_term_disability=True OR visually_impaired=True`
   - Source: 45 CFR § 1302.12(c)(2)

## Benefit Value

- Amount varies by household - see test cases

## Data Gaps

⚠️  The following criteria cannot be fully evaluated with current screener fields:

1. **Child is eligible for Medicaid (categorical eligibility)**
   - Note: While we can check if household has_medicaid or if specific member has medicaid, we cannot determine if a specific child (age 0-2) has Medicaid vs. another household member. The household_member.medicaid field exists but we'd need to filter by age.
   - Source: 45 CFR § 1302.12(b)(2) - implied
   - Impact: Medium

2. **Family is experiencing homelessness as defined by McKinney-Vento Act**
   - Note: McKinney-Vento definition includes: lacking fixed/regular/adequate nighttime residence, sharing housing due to economic hardship, living in motels/hotels/camping grounds, living in emergency/transitional shelters, abandoned in hospitals, awaiting foster care. Our housing_situation field may not capture all these nuances (e.g., 'doubled up' families).
   - Source: 45 CFR § 1302.12(b)(4), 42 U.S.C. § 11434a
   - Impact: Medium

3. **Child's family receives or is eligible to receive SNAP**
   - Note: While SNAP receipt is not explicitly listed in 45 CFR 1302.12(b) as categorical eligibility (only TANF and SSI are), some programs may accept it. We have has_snap field but regulation doesn't clearly establish this as categorical eligibility for EHS.
   - Source: 45 CFR § 1302.12(b)(1) - implied parallel to TANF
   - Impact: Low

4. **Selection priority: Families experiencing homelessness**
   - Note: Same issue as homelessness categorical eligibility - housing_situation may not capture full McKinney-Vento definition. Priority criterion, not pass/fail.
   - Source: 45 CFR § 1302.12(c)(3)
   - Impact: Low

5. **Selection priority: Children in foster care**
   - Note: Can potentially identify via relationship field, but need to confirm 'fosterChild' is valid value and can filter to children age 0-2.
   - Source: 45 CFR § 1302.12(c)(4)
   - Impact: Low

6. **Selection priority: Other criteria established by program**
   - Note: Programs may establish additional selection priorities (e.g., single parents, teen parents, families with multiple risk factors). These are program-specific and cannot be generically evaluated.
   - Source: 45 CFR § 1302.12(c)(5)
   - Impact: Low

7. **Child must not be currently enrolled in another federally-funded early childhood program**
   - Note: No field captures current enrollment in other programs. This is typically verified during application process.
   - Source: Program operational requirement (implied)
   - Impact: Low

8. **Residency in program service area**
   - Note: Each Early Head Start grantee serves specific geographic areas. We have zipcode and county but would need grantee-specific service area data to evaluate. This is program-location specific.
   - Source: Program operational requirement
   - Impact: High

9. **Age eligibility: Child must be under 3 at time of enrollment**
   - Note: We can identify children currently under 3, but cannot determine if they'll still be under 3 at future enrollment date. Programs have specific enrollment periods. This requires knowing enrollment timeline.
   - Source: 45 CFR § 1302.12(c)
   - Impact: Medium

10. **Pregnant women must be in 2nd or 3rd trimester (some programs)**
   - Note: We can identify pregnant women but not trimester. Some programs only serve women in later pregnancy. This is program-specific.
   - Source: Program-specific requirement
   - Impact: Low

## Implementation Coverage

- ✅ Evaluable criteria: 9
- ⚠️  Data gaps: 10

Of the major eligibility criteria for Early Head Start, we can evaluate 9 core requirements with current screener fields, including income limits (100% and 100-130% FPL), age requirements (children under 3 or pregnant women), and categorical eligibility (TANF, SSI, foster care, homelessness). We can also evaluate several selection priority criteria (lowest income, children with disabilities). The most significant gap is the inability to determine program-specific service areas (high impact), as Early Head Start is administered by local grantees serving specific geographic regions. Other gaps include nuanced homelessness definitions, specific child-level Medicaid enrollment, and program-specific selection priorities. Most gaps are low-medium impact as they represent edge cases or program-specific variations.

## Research Sources

- [HHS Poverty Guidelines (Annual Update per 42 U.S.C. § 9902)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
- [Texas Early Childhood Education Eligibility Screener - About Page](https://www.earlychildhood.texas.gov/about-eligibility-screener)
- [Skip to main content](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines#main-content)
- [Historical HHS Poverty Guidelines - Federal Register Citations (1982-Present)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/prior-hhs-poverty-guidelines-federal-register-references)
- [HHS Poverty Guidelines FAQ - Difference Between Guidelines and Thresholds](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/frequently-asked-questions-related-poverty-guidelines-poverty)
- [Further Resources](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/further-resources-poverty-measurement-poverty-lines-their-history)
- [Mollie Orshansky](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/mollie-orshansky-her-career-achievements-publications)
- [HHS Poverty Guidelines API - Programmatic Access](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/poverty-guidelines-api)
- [Poverty Estimates, Trends, and Analysis](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-estimates-trends-analysis)
- [Marginal Tax Rates/Benefit Cliffs](https://aspe.hhs.gov/topics/poverty-economic-mobility/marginal-tax-rate-series)

## Program Configuration

Django admin import configuration (ready to use):

```json
{
  "white_label": {
    "code": "tx"
  },
  "program_category": {
    "external_name": "tx_childcare"
  },
  "program": {
    "name_abbreviated": "tx_early head start",
    "year": "2025",
    "legal_status_required": [
      "citizen",
      "gc_5plus",
      "gc_5less",
      "refugee",
      "otherWithWorkPermission"
    ],
    "name": "Early Head Start",
    "description": "Early Head Start provides free early learning and development services for infants, toddlers, and pregnant women. The program offers child care, health screenings, meals, parent education, and support services to help young children grow and learn. Services are provided through local programs in your community.\n\nFamilies with children from birth to age 3 can qualify if their income is at or below the federal poverty level. Pregnant women are also eligible for prenatal services. Families receiving TANF or SSI, children in foster care, and homeless families may qualify regardless of income. Priority is given to families with the lowest income and children with disabilities.",
    "description_short": "Free early learning and care for infants and toddlers",
    "learn_more_link": "https://www.earlychildhood.texas.gov/about-eligibility-screener",
    "apply_button_link": "https://www.earlychildhood.texas.gov/about-eligibility-screener",
    "apply_button_description": "Apply for Texas Early Head Start",
    "estimated_application_time": "1 - 2 hours",
    "estimated_delivery_time": "Varies based on program availability",
    "estimated_value": "Varies by program and services provided",
    "website_description": "Free early learning, child care, and family support services for infants, toddlers, and pregnant women"
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
      "text": "Proof of identity for parent/guardian",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_earned_income",
      "text": "Proof of household income (ex: pay stubs, tax returns, benefit statements)",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_ssn",
      "text": "Social Security Number or proof of application for SSN",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "child_birth_certificate",
      "text": "Child's birth certificate or proof of age",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "immunization_records",
      "text": "Child's immunization records and health information",
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

Local path: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Early Head Start_20260306_205147`

Files generated:
- Program config: `{white_label}_{program_name}_initial_config.json`
- Test cases: `{white_label}_{program_name}_test_cases.json`
- Full research data in output directory


## Acceptance Criteria

[ ] Scenario 1 (Low-income family with infant - clearly eligible): User should be **eligible** with $None/year
[ ] Scenario 2 (Minimally eligible - pregnant woman at exactly 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 3 (Family income just below 100% FPL - should be eligible): User should be **eligible** with $None/year
[ ] Scenario 4 (Family with toddler at exactly 100% FPL - should be eligible): User should be **eligible** with $None/year
[ ] Scenario 5 (Family income just above 130% FPL - should NOT be eligible): User should be **ineligible**
[ ] Scenario 6 (Newborn at exactly age 0 (birth) - minimum age requirement): User should be **eligible** with $None/year
[ ] Scenario 7 (Child age 3 (just above maximum age) - should NOT be eligible): User should be **ineligible**
[ ] Scenario 8 (Child age 2 years 11 months - well within eligible age range): User should be **eligible** with $None/year
[ ] Scenario 9 (Eligible location within service area - Travis County, TX): User should be **eligible** with $None/year
[ ] Scenario 10 (Family already enrolled in Early Head Start - exclusion test): User should be **ineligible**
[ ] Scenario 11 (Child enrolled in Head Start (age 3+) - excluded from Early Head Start): User should be **ineligible**
[ ] Scenario 12 (Mixed household - eligible infant with older ineligible sibling and working parent): User should be **eligible** with $None/year
[ ] Scenario 13 (Multiple eligible children (infant and toddler) with categorical eligibility through TANF): User should be **eligible** with $None/year
[ ] Scenario 14 (Child turning 3 years old tomorrow - last day of eligibility): User should be **eligible** with $None/year

## Test Scenarios

### Scenario 1: Low-income family with infant - clearly eligible
**What we're checking**: Validates eligibility for a typical low-income family with an infant under age 3 and income at or below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1995` (age 31), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,800` per month, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1996` (age 30), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `December 2025` (age 0 - 3 months old), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: This is the most common eligibility pathway for Early Head Start - a low-income family with an infant. Tests the core income and age requirements under 45 CFR § 1302.12(a)(1) and (c).

---

### Scenario 2: Minimally eligible - pregnant woman at exactly 100% FPL
**What we're checking**: Tests minimum eligibility threshold: pregnant woman (satisfies age requirement via pregnancy) with income at exactly 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 1998` (age 27), Relationship: `Head of Household`, Select `Pregnant`, Citizenship: `U.S. Citizen`, Has income: `Yes`, Income type: `Wages/Salary`, Income amount: `1255` (monthly), Income frequency: `Monthly`, Insurance: `None`

**Why this matters**: Validates that the screener correctly identifies minimum eligibility: pregnant women qualify even without an existing child under 3, and income at exactly 100% FPL (not below) meets the threshold. This tests the boundary condition of the income limit.

---

### Scenario 3: Family income just below 100% FPL - should be eligible
**What we're checking**: Tests that a family with income slightly below the 100% FPL threshold qualifies under 45 CFR § 1302.12(a)(1)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Birth month/year: `January 1995` (age 31), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,400` per month ($28,800 annually), Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Person 3 (Infant)**: Birth month/year: `January 2026` (age 0, 2 months old), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Benefits**: Current benefits: `None selected`

**Why this matters**: This test validates that the screener correctly identifies families with income just below the 100% FPL threshold as eligible. It's critical to ensure the income calculation and FPL comparison work accurately at the boundary, as families slightly below the limit should qualify without needing categorical eligibility.

---

### Scenario 4: Family with toddler at exactly 100% FPL - should be eligible
**What we're checking**: Tests that a family with income exactly at 100% FPL threshold qualifies under 45 CFR § 1302.12(a)(1)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `75201`, Select county `Dallas`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,510` per month ($30,120 annually), Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `May 1992` (age 33), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`

**Why this matters**: This test validates the upper boundary of the primary income eligibility threshold. Families at exactly 100% FPL must be accepted, as the regulation states 'at or below' 100% FPL. This is distinct from the 100-130% FPL range which has enrollment caps.

---

### Scenario 5: Family income just above 130% FPL - should NOT be eligible
**What we're checking**: Validates that families with income exceeding 130% FPL are ineligible, even with a qualifying child under age 3
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$4,200` monthly ($50,400 annually), Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1991` (age 35), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Select `U.S. Citizen` for all household members

**Why this matters**: This test ensures the screener correctly enforces the 130% FPL upper income limit per 45 CFR § 1302.12(a)(2). Families above this threshold cannot qualify even through the 10% enrollment exception, as that exception only applies to families between 100-130% FPL. This prevents ineligible families from receiving incorrect eligibility determinations.

---

### Scenario 6: Newborn at exactly age 0 (birth) - minimum age requirement
**What we're checking**: Tests that a child at the absolute minimum age (newborn, age 0) qualifies for Early Head Start under the age requirement
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1995` (age 31), Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$2,100`, Frequency: `Monthly`, Insurance: `None`
- **Person 2 (Parent)**: Relationship: `Spouse`, Birth month/year: `March 1994` (age 32), Has income: `No`, Insurance: `None`
- **Person 3 (Newborn)**: Relationship: `Child`, Birth month/year: `February 2026` (age 0, born 1 month ago), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: This test validates that the age eligibility criterion correctly includes children from birth (age 0), not just children age 1 and older. Per 45 CFR § 1302.12(c), Early Head Start serves children 'from birth to age 3', and this tests the lower boundary of that range.

---

### Scenario 7: Child age 3 (just above maximum age) - should NOT be eligible
**What we're checking**: Validates that children who have reached age 3 are NOT eligible for Early Head Start (age maximum boundary)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `You (head of household)`, Birth month/year: `January 1995` (age 31), Has income: `Yes`, Income type: `Wages/salary`, Amount: `$1,200`, Frequency: `Monthly`, Insurance: `None`
- **Person 2**: Relationship: `Child`, Birth month/year: `February 2023` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select: `None`
- **Citizenship**: Select: `U.S. Citizen`

**Why this matters**: Early Head Start serves children from birth through age 2 (under age 3). This test confirms the upper age boundary is enforced correctly - a child who has turned 3 is no longer eligible, even if all other criteria are met. This distinguishes Early Head Start from regular Head Start which serves ages 3-5.

---

### Scenario 8: Child age 2 years 11 months - well within eligible age range
**What we're checking**: Validates that children who are well within the eligible age range (under 3) but not at the minimum threshold are correctly identified as eligible
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `You (Head of Household)`, Birth month/year: `January 1992` (age 34), Has income: `Yes`, Income type: `Wages/Salary`, Income amount: `$1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2**: Relationship: `Spouse`, Birth month/year: `June 1993` (age 32), Has income: `No`, Insurance: `None`
- **Person 3**: Relationship: `Child`, Birth month/year: `April 2023` (age 2 years 11 months), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen`

**Why this matters**: This test validates that the age eligibility logic correctly identifies children who are well within the eligible age range (birth to age 3) but not at the boundary thresholds. A child at 2 years 11 months is clearly under age 3 and should be eligible, testing that the system doesn't have off-by-one errors or incorrectly restrictive age calculations.

---

### Scenario 9: Eligible location within service area - Travis County, TX
**What we're checking**: Verifies that a family in an eligible geographic service area (Travis County, TX) with qualifying income and age criteria is correctly identified as eligible
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1995` (age 31), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,100` per month, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1996` (age 30), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2024` (age 1 year 9 months), Relationship: `Child`, Has income: `No`, Insurance: `None`

**Why this matters**: This test validates that the geographic eligibility check correctly identifies families within the Texas service area. Early Head Start programs are locally administered, and confirming that valid Texas counties are recognized ensures families in eligible locations can access services. Travis County (Austin area) is a major metropolitan area with established Early Head Start programs.

---

### Scenario 10: Family already enrolled in Early Head Start - exclusion test
**What we're checking**: Tests that families already receiving Early Head Start benefits are properly identified and handled (should show as already enrolled or ineligible for duplicate enrollment)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1995` (age 31), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child 1)**: Relationship: `Child`, Birth month/year: `May 2024` (age 1), Has income: `No`, Insurance: `None`
- **Person 3 (Child 2)**: Relationship: `Child`, Birth month/year: `August 2025` (age 0), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `Early Head Start` as a current benefit being received

**Why this matters**: Prevents duplicate enrollment and ensures accurate screening results. Families already enrolled should be directed to their current program rather than applying again. This tests the system's ability to identify and handle existing beneficiaries appropriately.

---

### Scenario 11: Child enrolled in Head Start (age 3+) - excluded from Early Head Start
**What we're checking**: Validates that children already enrolled in Head Start (regular program for ages 3-5) are excluded from Early Head Start, which serves birth to age 3
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,000` monthly, Insurance: `None`
- **Person 2 (Infant - eligible age)**: Birth month/year: `January 2025` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Person 3 (Older child in Head Start)**: Birth month/year: `January 2022` (age 4), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select that household receives `Head Start` for the 4-year-old child

**Why this matters**: This tests whether the system properly distinguishes between Head Start (ages 3-5) and Early Head Start (birth to 3), and whether it correctly handles households with children in both age ranges. It validates that the screener doesn't incorrectly exclude families from Early Head Start simply because an older sibling is in Head Start, as these are complementary programs serving different age groups.

---

### Scenario 12: Mixed household - eligible infant with older ineligible sibling and working parent
**What we're checking**: Tests that eligibility is determined by presence of at least one eligible child (under age 3), even when household includes older ineligible children
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Employment income: `$2,400` monthly, Insurance: `None`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `June 1992` (age 33), Has income: `Yes`, Employment income: `$1,200` monthly, Insurance: `None`
- **Person 3 (Eligible Child - Infant)**: Relationship: `Child`, Birth month/year: `December 2025` (age 0 - 3 months old), Has income: `No`, Insurance: `None`
- **Person 4 (Ineligible Child - Too Old)**: Relationship: `Child`, Birth month/year: `May 2020` (age 5), Has income: `No`, Insurance: `None`

**Why this matters**: Validates that Early Head Start correctly evaluates mixed-age households where only some children meet the age criteria. This is critical because many families have multiple children of different ages, and the program should serve eligible younger children even when older siblings are present. Tests criterion #1 (child under age 3) in a multi-member context.

---

### Scenario 13: Multiple eligible children (infant and toddler) with categorical eligibility through TANF
**What we're checking**: Household with multiple eligible children under age 3, one receiving TANF, testing that all eligible children are identified and categorical eligibility applies
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `4`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1998` (age 28), Has income: `Yes`, Income type: `Wages/Salary`, Amount: `$1,800`, Frequency: `Monthly`, Insurance: `Medicaid`
- **Person 2 (Infant)**: Relationship: `Child`, Birth month/year: `October 2025` (age 0, 4 months old), Has income: `No`, Receives TANF: `Yes`, Insurance: `Medicaid`
- **Person 3 (Toddler)**: Relationship: `Child`, Birth month/year: `May 2024` (age 1, 10 months old), Has income: `No`, Insurance: `Medicaid`
- **Person 4 (Older Child)**: Relationship: `Child`, Birth month/year: `March 2021` (age 5), Has income: `No`, Insurance: `Medicaid`
- **Current Benefits**: Select `TANF` for Person 2 (infant)

**Why this matters**: Tests the system's ability to correctly identify multiple eligible children in the same household while excluding ineligible siblings, and validates that categorical eligibility through TANF applies to qualifying children regardless of income level

---

### Scenario 14: Child turning 3 years old tomorrow - last day of eligibility
**What we're checking**: Tests the exact upper age boundary where child is still 2 years old today but will age out tomorrow
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `You`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$2,100`, Frequency: `Monthly`, Insurance: `None`
- **Person 2**: Relationship: `Child`, Birth month/year: `March 2023` (age 2, turns 3 tomorrow on March 7, 2026), Insurance: `None`
- **Current Benefits**: Select: `None`
- **Citizenship**: All household members are U.S. citizens

**Why this matters**: This edge case validates that the age eligibility check uses the current date (application date) rather than a future date. Children who are still within the eligible age range on the day of application should qualify, even if they will age out imminently. This ensures families aren't incorrectly denied due to timing issues in age calculation logic.

---


## Source Documentation

- https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- https://www.earlychildhood.texas.gov/about-eligibility-screener

## JSON Test Cases
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Early Head Start_20260306_205147/ticket_content/tx_Early Head Start_test_cases.json`

## Program Configuration
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Early Head Start_20260306_205147/ticket_content/tx_Early Head Start_initial_config.json`