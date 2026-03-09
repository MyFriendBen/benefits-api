# Implement Head Start (TX) Program

## Program Details

- **Program**: Head Start
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-09

## Eligibility Criteria

1. **Child must be age 3-5 years old (not yet in kindergarten)**
   - Screener fields:
     - `household_member.age`
     - `household_member.birth_year_month`
   - Logic: `num_children(age_min=3, age_max=5) > 0`
   - Source: 45 CFR 1302.12(c)(1)

2. **Household income at or below 100% of Federal Poverty Level**
   - Screener fields:
     - `income (all types)`
     - `household_size`
   - Logic: `calc_gross_income('yearly', types=['all']) <= FPL_100_PERCENT[household_size]`
   - Source: 45 CFR 1302.12(a)(1)(i)

3. **Child is eligible if family receives TANF assistance**
   - Screener fields:
     - `has_tanf`
   - Logic: `has_tanf == True`
   - Source: 45 CFR 1302.12(a)(1)(ii)

4. **Child is eligible if family receives SSI**
   - Screener fields:
     - `has_ssi`
   - Logic: `has_ssi == True`
   - Source: 45 CFR 1302.12(a)(1)(ii)

5. **Child is eligible if family receives SNAP**
   - Screener fields:
     - `has_snap`
   - Logic: `has_snap == True`
   - Source: 45 CFR 1302.12(a)(1)(ii) - public assistance

6. **Preference for children from families with incomes below poverty line**
   - Screener fields:
     - `income (all types)`
     - `household_size`
   - Logic: `calc_gross_income('yearly', types=['all']) <= FPL_100_PERCENT[household_size]`
   - Source: 45 CFR 1302.14(a)(1)

7. **Preference for children who are 4 years old**
   - Screener fields:
     - `household_member.age`
   - Logic: `num_children(age_min=4, age_max=4) > 0`
   - Source: 45 CFR 1302.14(a)(3)

8. **Preference for children who are 3 years old**
   - Screener fields:
     - `household_member.age`
   - Logic: `num_children(age_min=3, age_max=3) > 0`
   - Source: 45 CFR 1302.14(a)(4)

9. **Child with disability is eligible regardless of income (within 10% enrollment cap)**
   - Screener fields:
     - `household_member.disabled`
     - `household_member.age`
   - Logic: `any(member.disabled == True and 3 <= member.age <= 5 for member in household_members)`
   - Source: 45 CFR 1302.12(a)(1)(iii)

10. **Preference for children with disabilities**
   - Screener fields:
     - `household_member.disabled`
   - Logic: `any(member.disabled == True for member in household_members)`
   - Source: 45 CFR 1302.14(a)(2)

## Benefit Value

- Amount varies by household - see test cases

## Data Gaps

⚠️  The following criteria cannot be fully evaluated with current screener fields:

1. **Child is homeless**
   - Note: Homeless children are categorically eligible. The housing_situation field exists but we need to verify if it captures homelessness status specifically. If housing_situation includes 'homeless' as a valid value, this can be evaluated.
   - Source: 45 CFR 1302.12(a)(1)(iv)
   - Impact: High

2. **Child is in foster care**
   - Note: Children in foster care are categorically eligible. No field exists to capture foster care status.
   - Source: 45 CFR 1302.12(a)(1)(v)
   - Impact: High

3. **Over-income families (between 100-130% FPL) may be enrolled up to 10% of enrollment**
   - Note: Programs may enroll up to 10% of children from families with income 100-130% FPL if they meet other criteria. This is a program-level cap, not individual eligibility, so cannot be evaluated at screener level without knowing current program enrollment composition.
   - Source: 45 CFR 1302.12(b)(1)
   - Impact: Medium

4. **Child must reside in program's service area**
   - Note: Head Start programs serve specific geographic areas (counties, cities, neighborhoods). While we have zipcode and county, we would need a database of which Head Start grantees serve which areas in Texas to evaluate this. Each grantee has different service boundaries.
   - Source: 45 CFR 1302.12(d) - geographic area requirement
   - Impact: High

5. **Preference for children experiencing homelessness**
   - Note: Priority criterion - homeless children receive highest priority. Depends on whether housing_situation captures homelessness.
   - Source: 45 CFR 1302.14(b)(1)
   - Impact: Medium

6. **Preference for children in foster care**
   - Note: Priority criterion - foster children receive highest priority. No foster care field exists.
   - Source: 45 CFR 1302.14(b)(2)
   - Impact: Medium

7. **Preference for children from families receiving public assistance**
   - Note: Priority criterion - already captured through categorical eligibility fields, but this is about prioritization within eligible pool. Can be partially evaluated.
   - Source: 45 CFR 1302.14(b)(3)
   - Impact: Low

8. **No citizenship or immigration status requirement**
   - Note: Head Start does not require children or families to be U.S. citizens or have specific immigration status. This is a non-requirement (no barrier), so no field needed.
   - Source: Head Start Act Section 645(a)(1)(B)(ii) - no citizenship requirement
   - Impact: Low

9. **Preference based on family circumstances (single parent, teen parent, etc.)**
   - Note: Programs may establish additional local selection criteria. Could partially evaluate single parent status using relationship fields and num_guardians(), but teen parent status would require checking if guardian age < 20. Complex logic needed.
   - Source: 45 CFR 1302.14(c) - additional selection criteria
   - Impact: Low

10. **Child's parent is a veteran (preference in some programs)**
   - Note: Some programs give preference to children of veterans. Can be evaluated if veteran field is populated for parents/guardians.
   - Source: 45 CFR 1302.14(c) - local selection criteria
   - Impact: Low

## Implementation Coverage

- ✅ Evaluable criteria: 10
- ⚠️  Data gaps: 10

10 of 20 identified criteria can be fully evaluated with current screener fields. The core eligibility criteria (age 3-5, income at/below 100% FPL, categorical eligibility through TANF/SSI/SNAP, disability status) are all evaluable. Major gaps include: foster care status (high impact), homelessness status (high impact - depends on housing_situation field values), geographic service area matching (high impact - requires external grantee database), and over-income enrollment cap (medium impact - requires program-level data). Priority/preference criteria are partially evaluable but less critical for initial screening.

## Research Sources

- [HHS Poverty Guidelines (Federal Poverty Level) - Annual Updates](https://aspe.hhs.gov/topics/poverty-economic-mobility/po;5Dverty-guidelines)
- [Texas Early Childhood Education Eligibility Screener - About Page](https://www.earlychildhood.texas.gov/about-eligibility-screener)
- [Skip to main content](https://aspe.hhs.gov/topics/poverty-economic-mobility/po;5Dverty-guidelines#main-content)
- [Skip to main content](https://www.earlychildhood.texas.gov/about-eligibility-screener#main-content)
- [Texas Early Childhood Education Eligibility Screener - Interactive Tool](https://www.earlychildhood.texas.gov/ece-screener)
- [Texas ECE Screener - Frequently Asked Questions](https://www.earlychildhood.texas.gov/ece-screener/faqs)
- [Texas Early Childhood Programs At a Glance - Program Comparison](https://www.earlychildhood.texas.gov/early-childhood-programs-glance)

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
    "name_abbreviated": "tx_head start",
    "year": "2025",
    "legal_status_required": [],
    "name": "Head Start",
    "description": "Head Start provides free early childhood education and development services for children ages 3-5 from low-income families. The program offers classroom learning, health screenings, meals, and support services to help children prepare for kindergarten.\n\nFamilies with income at or below the federal poverty level qualify, as well as families receiving TANF, SSI, or SNAP benefits. Children with disabilities and children in foster care or experiencing homelessness are also eligible. Priority is given to 4-year-olds and families with the lowest incomes.",
    "description_short": "Free preschool for low-income families",
    "learn_more_link": "https://www.earlychildhood.texas.gov/about-eligibility-screener",
    "apply_button_link": "https://www.earlychildhood.texas.gov/about-eligibility-screener",
    "apply_button_description": "Apply for Texas Head Start",
    "estimated_application_time": "1 - 2 hours",
    "estimated_delivery_time": "Varies by program availability",
    "estimated_value": "Varies - free preschool services valued at several thousand dollars per year",
    "website_description": "Free early childhood education and development services for children ages 3-5 from low-income families"
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
      "text": "Proof of household income (ex: pay stubs, tax returns)",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_ssn",
      "text": "Social Security Number for child",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_immunization",
      "text": "Child's immunization records",
      "link_url": "",
      "link_text": ""
    },
    {
      "external_name": "tx_health_records",
      "text": "Child's health screening or physical exam records",
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

Local path: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Head Start_20260309_093911`

Files generated:
- Program config: `{white_label}_{program_name}_initial_config.json`
- Test cases: `{white_label}_{program_name}_test_cases.json`
- Full research data in output directory


## Acceptance Criteria

[ ] Scenario 1 (Single Parent with 4-Year-Old, Income Below 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 2 (3-Year-Old Child at Exactly 100% FPL with No Public Assistance): User should be **eligible** with $None/year
[ ] Scenario 3 (Two-Parent Household with 5-Year-Old, Income Just Below 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 4 (Family of Four with Income Exactly at 100% FPL - Should Be Eligible): User should be **eligible** with $None/year
[ ] Scenario 5 (Single Parent with 4-Year-Old, Income Just Above 100% FPL - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 6 (Child Exactly 3 Years Old (Minimum Age) - Should Be Eligible): User should be **eligible** with $None/year
[ ] Scenario 7 (Child Age 2 (Just Below Minimum Age of 3) - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 8 (Child Age 5 (Maximum Age) - Should Be Eligible): User should be **eligible** with $None/year
[ ] Scenario 9 (Eligible Location Within Service Area - Travis County, TX): User should be **eligible** with $None/year
[ ] Scenario 10 (Family Already Enrolled in Head Start - Duplicate Application): User should be **ineligible**
[ ] Scenario 11 (Child Age 6 (Kindergarten Age) - Should NOT Be Eligible Due to Age Exclusion): User should be **ineligible**
[ ] Scenario 12 (Multi-Child Household - One Eligible Child (Age 4), One Too Young (Age 2), One Too Old (Age 6)): User should be **eligible** with $None/year
[ ] Scenario 13 (Two Eligible Children (Ages 3 and 4) with Working Parent Below 100% FPL): User should be **eligible** with $None/year
[ ] Scenario 14 (Child Turning 3 Years Old Tomorrow - Age Boundary Edge Case): User should be **ineligible**

## Test Scenarios

### Scenario 1: Single Parent with 4-Year-Old, Income Below 100% FPL
**What we're checking**: Validates that a household with a 4-year-old child and income at or below 100% FPL qualifies for Head Start
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,000` per month, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `June 2021` (age 4), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Not receiving TANF, SSI, or SNAP
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This is the most common Head Start scenario - a low-income family with a preschool-aged child who meets both the age requirement (3-5 years old) and income threshold (at or below 100% FPL). This validates the core eligibility pathway under 45 CFR 1302.12(a)(1)(i) and 45 CFR 1302.12(c)(1).

---

### Scenario 2: 3-Year-Old Child at Exactly 100% FPL with No Public Assistance
**What we're checking**: Validates minimal eligibility: youngest eligible age (3 years old) with household income at exactly 100% Federal Poverty Level without categorical eligibility through public assistance programs
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `2,510`, Income frequency: `Monthly`, Insurance: `None`, Not receiving TANF, SSI, or SNAP
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `March 2023` (age 3), Has income: `No`, Insurance: `None`, Not disabled, Not in kindergarten
- **Current Benefits**: Not receiving TANF: `No`, Not receiving SSI: `No`, Not receiving SNAP: `No`

**Why this matters**: Tests the absolute minimum eligibility threshold: youngest eligible child (3 years old) with income at exactly 100% FPL without relying on categorical eligibility through TANF, SSI, or SNAP. Ensures the screener correctly identifies eligibility at the precise income limit.

---

### Scenario 3: Two-Parent Household with 5-Year-Old, Income Just Below 100% FPL
**What we're checking**: Validates eligibility when household income is slightly below the 100% FPL threshold with a 5-year-old child
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Birth month/year: `January 1988` (age 38), Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$2,400`, Frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `March 1989` (age 37), Relationship: `Spouse`, Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `$600`, Frequency: `Monthly`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `April 2021` (age 5), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Person 4 (Child)**: Birth month/year: `June 2023` (age 2), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs

**Why this matters**: This test validates that the screener correctly identifies eligibility when household income is just below (but not at) the 100% FPL threshold, ensuring the income calculation and comparison logic works properly for families near the poverty line with multiple children of varying ages.

---

### Scenario 4: Family of Four with Income Exactly at 100% FPL - Should Be Eligible
**What we're checking**: Validates that a household with income exactly at the 100% Federal Poverty Level threshold qualifies for Head Start (testing the 'at or below' language in 45 CFR 1302.12(a)(1)(i))
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `4`
- **Person 1 (Parent)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,417` monthly (exactly $29,000 annually = 100% FPL for family of 4), Insurance: `None`
- **Person 2 (Parent)**: Birth month/year: `May 1991` (age 34), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `June 2022` (age 3), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Person 4 (Child)**: Birth month/year: `September 2024` (age 1), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Not receiving TANF, SSI, or SNAP

**Why this matters**: This test confirms that the 'at or below' language in the regulation is correctly implemented - families at exactly 100% FPL should qualify, not just those below it. This is a critical boundary condition that ensures no eligible families are incorrectly denied.

---

### Scenario 5: Single Parent with 4-Year-Old, Income Just Above 100% FPL - Should NOT Be Eligible
**What we're checking**: Verifies that household income exceeding 100% FPL without categorical eligibility (TANF/SSI/SNAP) results in ineligibility
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,300` per month ($27,600 annually), Insurance: `None`
- **Person 2 (Child)**: Birth month/year: `June 2022` (age 4), Relationship: `Child`, Has income: `No`, Has disability: `No`, Insurance: `None`
- **Current Benefits**: TANF: `No`, SSI: `No`, SNAP: `No`
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This test validates that the income threshold at 100% FPL is strictly enforced when families lack categorical eligibility. For 2026, 100% FPL for a household of 2 is approximately $20,440 annually. Income of $27,600 exceeds this by roughly $7,160 (35% over limit), confirming the family does not meet the income requirement under 45 CFR 1302.12(a)(1)(i) and has no alternative categorical eligibility pathway.

---

### Scenario 6: Child Exactly 3 Years Old (Minimum Age) - Should Be Eligible
**What we're checking**: Validates that a child who is exactly 3 years old (the minimum age requirement) is eligible for Head Start
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1991` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `March 2023` (age exactly 3), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None`
- **Citizenship**: Select `U.S. Citizen` for all household members

**Why this matters**: This test validates that the age eligibility logic correctly includes children who are exactly at the minimum age threshold of 3 years old, per 45 CFR 1302.12(c)(1). It ensures the system doesn't incorrectly exclude children who just turned 3.

---

### Scenario 7: Child Age 2 (Just Below Minimum Age of 3) - Should NOT Be Eligible
**What we're checking**: Validates that children under age 3 are not eligible for Head Start, testing the minimum age threshold of 3 years old per 45 CFR 1302.12(c)(1)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salary`, Income amount: `$1,800` per month ($21,600 annually - below 100% FPL for household of 2), Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `April 2024` (age 2 - just below minimum age), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This test validates the minimum age threshold enforcement. Head Start serves children ages 3-5 who are not yet in kindergarten (45 CFR 1302.12(c)(1)). A 2-year-old child, even with qualifying income, should be ineligible. This ensures the program correctly identifies age-based ineligibility and prevents enrollment of children who should be served by Early Head Start instead.

---

### Scenario 8: Child Age 5 (Maximum Age) - Should Be Eligible
**What we're checking**: Validates that a 5-year-old child (at the upper age limit) is eligible for Head Start, testing the maximum age threshold of the 3-5 year range
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Employment income: `$2,100` per month, Insurance: `None`
- **Person 2 (Child - 5 years old)**: Relationship: `Child`, Birth month/year: `February 2021` (age 5), Has income: `No`, Insurance: `None`
- **Person 3 (Child - 7 years old)**: Relationship: `Child`, Birth month/year: `January 2019` (age 7), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select: `None`

**Why this matters**: This test validates the upper boundary of the age eligibility range. Head Start serves children ages 3-5 who are not yet in kindergarten. Testing a 5-year-old ensures the system correctly includes children at the maximum age threshold, which is critical since many 5-year-olds may be transitioning to kindergarten soon.

---

### Scenario 9: Eligible Location Within Service Area - Travis County, TX
**What we're checking**: Verifies that a family residing in an eligible Texas county (Travis County) with a qualifying child can access Head Start services
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,000` per month, Insurance: `None`
- **Person 2 (Spouse)**: Birth month/year: `February 1991` (age 35), Relationship: `Spouse`, Has income: `No`, Insurance: `None`
- **Person 3 (Child)**: Birth month/year: `April 2022` (age 3), Relationship: `Child`, Has income: `No`, Insurance: `None`
- **Current Benefits**: Select `None` for all benefit programs
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This test validates that Head Start correctly identifies eligible families within Texas service areas. Travis County (Austin area) is a major metropolitan area with established Head Start programs, making it a representative test case for geographic eligibility in Texas.

---

### Scenario 10: Family Already Enrolled in Head Start - Duplicate Application
**What we're checking**: Tests that the system properly handles cases where a child is already enrolled in Head Start and prevents duplicate enrollment or shows appropriate messaging
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Birth month/year: `January 1990` (age 36), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$2,000` per month, Insurance: `None`
- **Person 2 (Child - Already Enrolled)**: Birth month/year: `June 2022` (age 3), Relationship: `Child`, No income, Insurance: `None`
- **Person 3 (Younger Child)**: Birth month/year: `September 2024` (age 1), Relationship: `Child`, No income, Insurance: `None`
- **Current Benefits**: Select `Head Start` as a current benefit being received, Indicate that Person 2 (the 3-year-old) is the recipient
- **Citizenship**: All household members: `U.S. Citizen`

**Why this matters**: This test validates that the system prevents duplicate enrollments and properly tracks children already receiving Head Start services. This is important for program integrity, accurate enrollment counts, and ensuring that limited Head Start slots are available to children not currently served. It also tests whether the system can distinguish between multiple children in a household where one is already enrolled.

---

### Scenario 11: Child Age 6 (Kindergarten Age) - Should NOT Be Eligible Due to Age Exclusion
**What we're checking**: Validates that children who are 6 years old or already in kindergarten are excluded from Head Start eligibility, even if income-qualified
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Employment`, Income amount: `$1,200` per month ($14,400/year - well below 100% FPL for household of 2), Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `January 2020` (age 6), Has income: `No`, Insurance: `None`, Note: Child is 6 years old, which exceeds the maximum age of 5 for Head Start eligibility
- **Current Benefits**: Select `None` for all current benefits
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This test validates the upper age boundary exclusion for Head Start. Per 45 CFR 1302.12(c)(1), Head Start serves children ages 3-5 who are not yet in kindergarten. Children who turn 6 or enter kindergarten are excluded regardless of income or other qualifying factors. This ensures the program serves its intended pre-kindergarten population.

---

### Scenario 12: Multi-Child Household - One Eligible Child (Age 4), One Too Young (Age 2), One Too Old (Age 6)
**What we're checking**: Tests that Head Start correctly identifies eligible children in a mixed-age household where only some children meet the age criteria (3-5 years old, not yet in kindergarten)
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `5`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1988` (age 38), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `2,100`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Parent)**: Relationship: `Spouse`, Birth month/year: `March 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `1,800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 3 (Child - Too Old)**: Relationship: `Child`, Birth month/year: `January 2020` (age 6), Has income: `No`, Insurance: `None`
- **Person 4 (Child - ELIGIBLE)**: Relationship: `Child`, Birth month/year: `May 2022` (age 4), Has income: `No`, Insurance: `None`
- **Person 5 (Child - Too Young)**: Relationship: `Child`, Birth month/year: `June 2024` (age 2), Has income: `No`, Insurance: `None`
- **Current Benefits**: Select: `None`
- **Citizenship**: All members: `U.S. Citizen`

**Why this matters**: This test validates that Head Start correctly evaluates households with multiple children of varying ages, ensuring only children aged 3-5 (not yet in kindergarten) are identified as eligible. This is critical because families often have children spanning different age ranges, and the system must accurately determine which specific children qualify for services per 45 CFR 1302.12(c)(1).

---

### Scenario 13: Two Eligible Children (Ages 3 and 4) with Working Parent Below 100% FPL
**What we're checking**: Multiple children in the same household who are both eligible for Head Start based on age (3 and 4 years old) and household income below 100% FPL
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `3`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,900`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (First Child)**: Relationship: `Child`, Birth month/year: `June 2022` (age 3), Has income: `No`, Insurance: `None`, Has disability: `No`
- **Person 3 (Second Child)**: Relationship: `Child`, Birth month/year: `September 2021` (age 4), Has income: `No`, Insurance: `None`, Has disability: `No`
- **Current Benefits**: Not receiving TANF, SSI, or SNAP

**Why this matters**: This tests the system's ability to correctly identify multiple eligible children within the same household and apply both income-based eligibility (45 CFR 1302.12(a)(1)(i)) and age-based eligibility (45 CFR 1302.12(c)(1)) to each child independently. It also validates that preference criteria are properly applied when multiple children qualify.

---

### Scenario 14: Child Turning 3 Years Old Tomorrow - Age Boundary Edge Case
**What we're checking**: Tests the exact age boundary when a child is 2 years and 364 days old (turns 3 tomorrow) - should NOT be eligible until they actually turn 3
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `78701`, Select county `Travis`
- **Household**: Number of people: `2`
- **Person 1 (Parent)**: Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Has income: `Yes`, Income type: `Wages/Salaries`, Amount: `1,255`, Frequency: `Monthly` (equals $15,060/year, below 100% FPL for household of 2), Insurance: `None`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `March 2023` (will turn 3 tomorrow on March 10, 2026), Currently age 2 years, 364 days old, Insurance: `None`
- **Current Benefits**: No current benefits selected
- **Citizenship**: Citizenship status: `U.S. Citizen`

**Why this matters**: This edge case tests whether the system correctly enforces the exact age boundary of 3 years old per 45 CFR 1302.12(c)(1). Children must be at least 3 years old, not 'almost 3'. This prevents premature enrollment and ensures compliance with federal regulations. The child would become eligible the very next day (March 10, 2026).

---


## Source Documentation

- https://aspe.hhs.gov/topics/poverty-economic-mobility/po;5Dverty-guidelines
- https://www.earlychildhood.texas.gov/about-eligibility-screener

## JSON Test Cases
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Head Start_20260309_093911/ticket_content/tx_Head Start_test_cases.json`

## Program Configuration
File: `/Users/patrickwey/code/mfb/program-researcher/output/tx_Head Start_20260309_093911/ticket_content/tx_Head Start_initial_config.json`