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

2. **Family income at or below 100% of Federal Poverty Level (FPL)**
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR § 1302.12(a)(1)(i) - Income eligibility

3. **Child receives or family is eligible for TANF**
   - Screener fields:
     - `has_tanf`
   - Source: 45 CFR § 1302.12(a)(1)(ii)(A) - Categorical eligibility

4. **Child receives or family is eligible for SSI**
   - Screener fields:
     - `has_ssi`
   - Source: 45 CFR § 1302.12(a)(1)(ii)(B) - Categorical eligibility

5. **Child is in foster care**
   - Screener fields:
     - `household_member.relationship`
   - Source: 45 CFR § 1302.12(c)(1)(ii) - Foster children eligibility

6. **Family income between 100% and 130% FPL (up to 10% of enrollment)**
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR § 1302.12(a)(1)(iii) - Over-income eligibility

7. **Priority for children from families with incomes below poverty line**
   - Screener fields:
     - `income_stream.amount`
     - `income_stream.frequency`
     - `household_size`
   - Source: 45 CFR § 1302.14(a)(1) - Selection priorities

8. **Priority for children with disabilities**
   - Screener fields:
     - `household_member.disabled`
     - `household_member.long_term_disability`
   - Source: 45 CFR § 1302.14(a)(2) - Selection priorities

9. **Child experiencing homelessness** ⚠️ *data gap*
   - Note: Children experiencing homelessness are categorically eligible regardless of income. The screener has 'housing_situation' field in the model but it is not collected from users. The 'needs_housing_help' field indicates desire for housing assistance, not current housing status. Cannot evaluate homelessness status.
   - Source: 45 CFR § 1302.12(c)(1)(i) - Homeless children eligibility
   - Impact: High

10. **Child must not yet be eligible for kindergarten** ⚠️ *data gap*
   - Note: 5-year-olds are only eligible if not yet eligible for kindergarten. Kindergarten eligibility varies by state/district and depends on birth date cutoffs (e.g., must turn 5 by September 1). The screener captures age but not kindergarten enrollment status or eligibility.
   - Source: 45 CFR § 1302.12(c)(1) - Age eligibility
   - Impact: Medium

11. **Residency in program service area** ⚠️ *data gap*
   - Note: Each Head Start program serves a specific geographic area (may be county, city, neighborhood, or other boundary). The screener captures zipcode and county but cannot determine if these fall within a specific program's service area without program-specific geographic data.
   - Source: 45 CFR § 1302.12(b) - Geographic eligibility
   - Impact: High

12. **Priority for families receiving public assistance** ⚠️ *data gap*
   - Note: Selection priority for families receiving public assistance beyond TANF/SSI/SNAP (e.g., housing assistance, Medicaid). While screener captures some benefits (has_medicaid, has_section_8), 'public assistance' is broader and not fully defined. Partial evaluation possible but incomplete.
   - Source: 45 CFR § 1302.14(a)(3) - Selection priorities
   - Impact: Low

13. **Priority for single-parent families** ⚠️ *data gap*
   - Note: Programs may establish additional selection priorities including single-parent status. The screener captures household member relationships but cannot definitively determine single-parent status (would need to identify one adult guardian with children and no spouse/partner).
   - Source: 45 CFR § 1302.14(b) - Additional selection criteria
   - Impact: Low

14. **Priority for families with lowest incomes** ⚠️ *data gap*
   - Note: Among eligible families, priority given to those with lowest incomes. This requires ranking/comparison across applicants, which cannot be done in a single-screen evaluation context.
   - Source: 45 CFR § 1302.14(a)(1) - Selection priorities
   - Impact: Low

15. **Child's immunization status** ⚠️ *data gap*
   - Note: Children must be up-to-date on immunizations or have exemption. This is a post-enrollment requirement, not an eligibility barrier, but must be addressed within 90 days. Not captured in screener.
   - Source: 45 CFR § 1302.42 - Child health status and care
   - Impact: Low

16. **Citizenship or immigration status** ⚠️ *data gap*
   - Note: Head Start does not have citizenship requirements - children are eligible regardless of immigration status. However, this is not captured in screener. No evaluation needed as there is no restriction.
   - Source: Head Start Act Section 645(a)(1)(B)(ii)
   - Impact: Low

17. **Documentation of income eligibility** ⚠️ *data gap*
   - Note: Programs must verify income eligibility through documentation (pay stubs, tax returns, benefit award letters, etc.). The screener collects self-reported income but cannot verify documentation. This is an administrative requirement, not an eligibility criterion.
   - Source: 45 CFR § 1302.12(j) - Verification of eligibility
   - Impact: Low

18. **Priority for children in families with both parents working or in training** ⚠️ *data gap*
   - Note: Programs may prioritize families where parents are working or in job training. The screener captures income streams (which may indicate employment) but not explicit employment status or training program participation for all household members.
   - Source: 45 CFR § 1302.14(b) - Additional selection criteria
   - Impact: Low

## Benefit Value

- Amount varies by household - see test cases

## Implementation Coverage

- ✅ Evaluable criteria: 8
- ⚠️  Data gaps: 10

Head Start eligibility can be substantially evaluated with current screener fields. Of the core eligibility criteria, we can evaluate: age requirements (3-5 years old), income eligibility (at or below 100% FPL, or 100-130% FPL for up to 10% of slots), and categorical eligibility through TANF, SSI, and foster care receipt. We can also evaluate some selection priorities including disability status and income level. However, critical gaps exist: we cannot determine if a child is experiencing homelessness (a categorical eligibility factor), whether a 5-year-old is kindergarten-eligible, or whether the family resides in a specific program's service area. The homelessness gap is particularly significant as homeless children are categorically eligible regardless of income. Most other gaps relate to selection priorities rather than hard eligibility requirements, making them lower impact.

## Research Sources

- [HHS Poverty Guidelines (Annual Update per 42 U.S.C. § 9902)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
- [Texas Early Childhood Education Eligibility Screener - About Page](https://www.earlychildhood.texas.gov/about-eligibility-screener)
- [Historical HHS Poverty Guidelines with Federal Register Citations (1982-Present)](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/prior-hhs-poverty-guidelines-federal-register-references)
- [HHS Poverty Guidelines FAQ - Definitions and Program Applications](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines/frequently-asked-questions-related-poverty-guidelines-poverty)
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
    "name_abbreviated": "tx_head_start",
    "year": "2025",
    "legal_status_required": [],
    "name": "Head Start",
    "description": "Head Start is a free program for young children ages 3 to 5. It offers preschool classes, meals, and health checkups. Your child also gets help learning and growing. Families pay nothing to join.\n\nFamilies with low income can apply. Children who get TANF (cash help) or SSI (disability benefits) qualify right away. Children in foster care also qualify. Children without a stable home qualify too.",
    "description_short": "Free preschool for children ages 3 to 5",
    "learn_more_link": "https://www.earlychildhood.texas.gov/about-eligibility-screener",
    "apply_button_link": "https://www.earlychildhood.texas.gov/about-eligibility-screener",
    "apply_button_description": "Apply for TX Head Start",
    "estimated_application_time": "1 - 2 hours",
    "estimated_delivery_time": "Varies by program availability",
    "estimated_value": "Free preschool services valued at approximately $10,000 per year",
    "website_description": "Free preschool, meals, and health services for children ages 3 to 5 from low-income families"
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
      "text": "Proof of identity for child (ex: birth certificate)",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_earned_income",
      "text": "Proof of income (ex: pay stubs, tax returns, benefit award letters)",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_immunization",
      "text": "Child's immunization records (can be provided within 90 days of enrollment)",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_benefit_proof",
      "text": "Proof of TANF, SSI, or SNAP benefits if applicable",
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

Local path: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Head Start_20260311_111721`

Files generated:
- Program config: `{white_label}_{program_name}_initial_config.json`
- Test cases: `{white_label}_{program_name}_test_cases.json`
- Full research data in output directory


## Acceptance Criteria

[ ] Scenario 1 (Single Parent with 4-Year-Old Child, Income Below 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 2 (Foster Child at Age 3, Family Income at Exactly 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 3 (Two-Parent Household with 3-Year-Old, Income Just Below 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 4 (Two-Parent Household with 5-Year-Old, Income Exactly at 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 5 (Single Parent with 4-Year-Old, Income Just Above 100% FPL - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 6 (Child Exactly Age 3 (Minimum Age), Income Below 100% FPL - Should Be Eligible): User should be **eligible** with $None/year
[ ] Scenario 7 (Child Age 1 (Just Below Minimum Age 3), Income Below 100% FPL - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 8 (Child Age 5 (Maximum Age), Income Below 100% FPL - Should Be Eligible): User should be **eligible** with $None/year
[ ] Scenario 9 (Eligible Location Within Service Area - Travis County, TX): User should be **eligible** with $None/year
[ ] Scenario 10 (Family Already Enrolled in Head Start - Duplicate Application): User should be **ineligible**
[ ] Scenario 11 (Child Age 6 (Above Maximum Age), Income Below 100% FPL - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 12 (Multi-Member Household - 3 Children (One Eligible Age, Two Ineligible Ages), Income Below 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 13 (Multi-Member Household - Two Eligible Children (Ages 3 and 5), One Parent, Income Below 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 14 (Child Turns 3 Years Old Tomorrow - Testing Age Boundary at Minimum Eligibility): User should be **ineligible**

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

### Scenario 3: Two-Parent Household with 3-Year-Old, Income Just Below 100% FPL
**What we're checking**: Validates income eligibility when household income is just below the 100% FPL threshold for a family of 3
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$1,950`, Frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1991` (age 35), Relationship: `Spouse`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$800`, Frequency: `Monthly`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2022` (age 3), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: Tests the income threshold boundary at just below 100% FPL (45 CFR § 1302.12(a)(1)(i)). This validates that families with income slightly under the poverty line are correctly identified as eligible, ensuring the screener accurately calculates and compares household income against FPL thresholds for different household sizes.

---

### Scenario 4: Two-Parent Household with 5-Year-Old, Income Exactly at 100% FPL
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

### Scenario 5: Single Parent with 4-Year-Old, Income Just Above 100% FPL - Should NOT Be Eligible
**What we're checking**: Verifies that a household with income slightly above 100% FPL is correctly determined ineligible when not receiving categorical benefits (TANF/SSI/SNAP)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,200` per month ($26,400 annually), Income frequency: `Monthly`, Insurance: `None`, Not receiving TANF, SSI, or SNAP
- **Person 2 (Child)**: Birth month/year: `June 2022` (age 4), Relationship: `Child`, Has income: `No`, Insurance: `None`, Not in foster care, No disabilities

**Why this matters**: This test validates the income threshold enforcement at 100% FPL per 45 CFR § 1302.12(a)(1)(i). It ensures the system correctly rejects applicants who exceed the primary income limit and don't qualify through categorical eligibility, preventing over-enrollment of families above the poverty threshold.

---

### Scenario 6: Child Exactly Age 3 (Minimum Age), Income Below 100% FPL - Should Be Eligible
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

### Scenario 7: Child Age 1 (Just Below Minimum Age 3), Income Below 100% FPL - Should NOT Be Eligible
**What we're checking**: Validates that children under age 3 are not eligible for Head Start, even when family income qualifies
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1**: Relationship: `You (Head of Household)`, Birth month/year: `January 1992` (age 34), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,200`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2**: Relationship: `Child`, Birth month/year: `May 2024` (age 1), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select: `None`
- **Citizenship**: Select: `U.S. Citizen`

**Why this matters**: This test ensures the age floor is properly enforced. Head Start serves children ages 3-5 per 45 CFR § 1302.12(c)(1). Children under 3 should be directed to Early Head Start instead. This prevents inappropriate enrollment and ensures families are referred to the correct program.

---

### Scenario 8: Child Age 5 (Maximum Age), Income Below 100% FPL - Should Be Eligible
**What we're checking**: Validates that a child at the maximum eligible age (5 years old, not yet in kindergarten) qualifies for Head Start when family income is below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1996` (age 30), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `February 2021` (age 5), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This test validates the upper age boundary for Head Start eligibility. Children must be between ages 3 and 5 and not yet enrolled in kindergarten. Testing the maximum age (5) ensures the screener correctly includes children at this threshold, as they are still eligible if not yet in kindergarten.

---

### Scenario 9: Eligible Location Within Service Area - Travis County, TX
**What we're checking**: Verifies that a family in an eligible geographic location (Travis County, TX) with a qualifying child and income below 100% FPL is eligible for Head Start services
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,100`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1991` (age 35), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2022` (age 3), Relationship: `Child`, Has income: `No`, Insurance: `None`

**Why this matters**: Head Start programs are administered by local grantees that serve specific geographic areas. This test confirms that the screener correctly identifies eligible locations within Texas and processes applications for families in those service areas. Geographic eligibility is a foundational requirement that must be validated before other eligibility criteria.

---

### Scenario 10: Family Already Enrolled in Head Start - Duplicate Application
**What we're checking**: Validates that the system properly handles cases where a child is already enrolled in Head Start, preventing duplicate enrollment or showing appropriate messaging
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1992` (age 34), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800` per month ($21,600 annually), Insurance: `None`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `March 1993` (age 33), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,500` per month ($18,000 annually), Insurance: `None`
- **Person 3 (Child)**: Relationship: `Child`, Birth month/year: `June 2022` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `Head Start` as a current benefit, Indicate child is already enrolled in Head Start program

**Why this matters**: This test ensures the system prevents duplicate enrollments and properly handles cases where families are already receiving the benefit. It validates data integrity and prevents administrative errors that could waste program resources or create confusion for families already being served.

---

### Scenario 11: Child Age 6 (Above Maximum Age), Income Below 100% FPL - Should NOT Be Eligible
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

### Scenario 12: Multi-Member Household - 3 Children (One Eligible Age, Two Ineligible Ages), Income Below 100% FPL
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

### Scenario 13: Multi-Member Household - Two Eligible Children (Ages 3 and 5), One Parent, Income Below 100% FPL
**What we're checking**: Validates that multiple children in the same household who meet age eligibility (ages 3-5) are both identified as eligible when family income is below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1992` (age 34), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,800` per month ($21,600 annually), Insurance: `None`
- **Person 2 (First Child)**: Birth month/year: `March 2023` (age 3), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Person 3 (Second Child)**: Birth month/year: `September 2020` (age 5, turning 6 in September 2026), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Not currently receiving TANF, SSI, or SNAP

**Why this matters**: This test validates that the screener correctly identifies multiple eligible children within the same household, which is a common real-world scenario. Head Start programs must be able to serve multiple children from the same family when they meet eligibility criteria, and the system should properly account for all eligible household members rather than just one.

---

### Scenario 14: Child Turns 3 Years Old Tomorrow - Testing Age Boundary at Minimum Eligibility
**What we're checking**: Tests the exact minimum age boundary where a child is currently 2 years and 364 days old (turns 3 tomorrow), which should make them ineligible today but eligible tomorrow. This validates strict age enforcement at the lower boundary.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1991` (age 35), Has income: `Yes`, Income type: `Employment`, Income amount: `$1,200` per month ($14,400/year), Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `April 2023` (age 2, turns 3 in April 2026), Has income: `No`, Insurance: `None`
- **Current Benefits**: Not receiving any current benefits
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This edge case tests whether the system correctly enforces the minimum age requirement down to the day level. A child who is 2 years and 364 days old is technically still 2 years old and should not be eligible, even though they will be eligible the next day. This validates that the age calculation is precise and not rounded or approximated, which is critical for program integrity and compliance with 45 CFR § 1302.12(c)(1).

---


## Source Documentation

- https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- https://www.earlychildhood.texas.gov/about-eligibility-screener

## JSON Test Cases
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Head Start_20260311_111721/ticket_content/tx_Head Start_test_cases.json`

## Program Configuration
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Head Start_20260311_111721/ticket_content/tx_Head Start_initial_config.json`