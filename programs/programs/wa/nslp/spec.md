# Implement National School Lunch Program (NSLP) (WA) Program

## Program Details

* **Program**: National School Lunch Program (NSLP)
* **State**: WA
* **White Label**: wa
* **Research Date**: 2026-03-31

## Eligibility Criteria

 1. **Household must contain at least one school-age child (ages 5–17 per PolicyEngine implementation)**
    * Screener fields:
      * `age`
      * `student`
    * Source: 42 U.S.C. § 1758(b)(1); 7 CFR 245.2 definition of 'child'
    * > **PE Note**: PolicyEngine's `is_in_k12_school` variable (used in `school_meal_net_subsidy`) imputes K-12 enrollment as `age >= 5 AND age <= 17`. The statute and regulations allow eligibility through age 18 (and up to 19 if still enrolled), but the PE model caps at 17 as an approximation. Eligible children will be undercounted for 18-year-old high school seniors. See Scenario 14 below.

 2. **Free meals: Household gross income at or below 130% of the Federal Poverty Level (FPL)**
    * Screener fields:
      * `household_size`
      * `incomeStreams (all types)`
    * Source: 42 U.S.C. § 1758(b)(1)(A); 7 CFR 245.6(a); Income Eligibility Guidelines published annually by USDA FNS (e.g., 89 FR 12254 for SY 2024-2025)

 3. **Reduced-price meals: Household gross income above 130% but at or below 185% of the Federal Poverty Level**
    * Screener fields:
      * `household_size`
      * `incomeStreams (all types)`
    * Source: 42 U.S.C. § 1758(b)(1)(A); 7 CFR 245.6(a); Income Eligibility Guidelines published annually by USDA FNS

 4. **Categorical eligibility via SNAP: Children in households receiving SNAP benefits are categorically eligible for free meals**
    * Screener fields:
      * `has_snap`
    * Source: 42 U.S.C. § 1758(b)(12)(A); 7 CFR 245.6(b)

 5. **Categorical eligibility via TANF: Children in households receiving TANF cash assistance are categorically eligible for free meals**
    * Screener fields:
      * `has_tanf`
    * Source: 42 U.S.C. § 1758(b)(12)(A); 7 CFR 245.6(b)
    * > **PE Note**: PE's `categorical_eligibility.yaml` includes TANF but notes it is "currently only available in CA and IL." For WA, TANF categorical eligibility is modeled in PE but may not be active. Verify with PE API before shipping.

 6. **Categorical eligibility via FDPIR: Children in households receiving Food Distribution Program on Indian Reservations benefits are categorically eligible for free meals**
    * Source: 42 U.S.C. § 1758(b)(12)(A); 7 CFR 245.6(b)

 7. **Household size must be determined for income comparison**
    * Screener fields:
      * `household_size`
    * Source: 7 CFR 245.2; 7 CFR 245.6(a)(1)

 8. **Washington state residency (child must attend a school in Washington that participates in NSLP)**
    * Screener fields:
      * `zipcode`
      * `county`
    * Source: 42 U.S.C. § 1751; Washington State OSPI Child Nutrition Programs

 9. **Child must be enrolled in a participating school or residential child care institution** ⚠️ *data gap*
    * Note: The screener does not capture which specific school a child attends or whether that school participates in NSLP. However, in Washington state, nearly all public schools participate, so this is a minor gap. We can approximate by checking for school-age children using the age and student fields.
    * Source: 42 U.S.C. § 1758(b)(1); 7 CFR 245.1(a)
    * Impact: Low

10. **Categorical eligibility for foster children: A child who is the responsibility of a court or foster care agency is categorically eligible for free meals** ⚠️ *data gap*

    * Note: No foster care status field exists in the screener. Foster children are automatically eligible for free meals regardless of household income. PE models this via the `was_in_foster_care` variable in its categorical eligibility list.
    * Source: 42 U.S.C. § 1758(b)(12)(A)(iv); 7 CFR 245.6(b)(4)
    * Impact: Medium

11. **Categorical eligibility for children experiencing homelessness (McKinney-Vento Act)** ⚠️ *data gap*

    * Note: Children identified as homeless under the McKinney-Vento Act are categorically eligible for free meals. The housing_situation field exists in the model but is not collected from users, and needs_housing_help indicates desire for housing assistance, not homelessness status. This criterion cannot be evaluated. PE models this via the `is_homeless` variable.
    * Source: 42 U.S.C. § 1758(b)(12)(A)(vi); 7 CFR 245.6(b)(6); McKinney-Vento Homeless Assistance Act, 42 U.S.C. § 11431 et seq.
    * Impact: Medium

12. **Categorical eligibility for migrant children (children of migrant workers as defined by the Migrant Education Program)** ⚠️ *data gap*

    * Note: No migrant worker status field in the screener. Relevant in Washington state given agricultural workforce. These children would likely qualify via income thresholds as well. PE models this via the `is_migratory_child` variable.
    * Source: 42 U.S.C. § 1758(b)(12)(A)(v); 7 CFR 245.6(b)(5)
    * Impact: Low

13. **Categorical eligibility for runaway children (receiving assistance from a program under the Runaway and Homeless Youth Act)** ⚠️ *data gap*

    * Note: No field to capture runaway youth status. Very narrow population. PE models this via the `is_runaway_child` variable.
    * Source: 42 U.S.C. § 1758(b)(12)(A)(vii); 7 CFR 245.6(b)(7)
    * Impact: Low

14. **Categorical eligibility for children enrolled in Head Start or Even Start programs** ⚠️ *data gap*

    * Note: The has_head_start field can partially address this. Head Start children are categorically eligible for free meals. Even Start is a separate program not captured in the screener but is very small. PE models this via the `is_head_start_eligible` variable.
    * Source: 42 U.S.C. § 1758(b)(12)(A)(ii); 7 CFR 245.6(b)(2)
    * Impact: Low

15. **Community Eligibility Provision (CEP): Schools with high poverty rates may provide free meals to ALL students regardless of individual household income** ⚠️ *data gap*

    * Note: Many Washington schools participate in CEP, meaning ALL enrolled students receive free meals regardless of income. The screener cannot determine if a child's specific school is a CEP school. In WA, a significant number of schools use CEP. This means some children we might screen as 'not eligible for free meals' based on income may actually receive free meals at their school.
    * Source: 42 U.S.C. § 1759a(a)(1)(F); 7 CFR 245.9(f); Washington OSPI CEP schools list
    * Impact: Medium

16. **Provision 2 or Provision 3 schools: Some schools operate under special provisions that provide free meals to all students** ⚠️ *data gap*

    * Note: Similar to CEP, some schools operate under Provision 2 or 3 where all students eat free. Cannot determine from screener data.
    * Source: 7 CFR 245.9(b)-(e)
    * Impact: Low

17. **FDPIR (Food Distribution Program on Indian Reservations) categorical eligibility** ⚠️ *data gap*

    * Note: No FDPIR field in screener. Relevant for Washington's tribal communities but participants would likely also qualify via income.
    * Source: 42 U.S.C. § 1758(b)(12)(A)(iii); 7 CFR 245.6(b)(3)
    * Impact: Low

18. **Citizenship/immigration status is NOT a barrier - all children regardless of immigration status are eligible** ⚠️ *data gap*

    * Note: NSLP does not require citizenship or immigration documentation. All children enrolled in participating schools are eligible. This is a non-barrier that should be noted - the screener does not need to check immigration status for NSLP.
    * Source: USDA FNS Policy Memo SP 46-2016; 7 CFR 245.6(a) - no citizenship requirement
    * Impact: Low

19. **Washington state: Reduced-price copay elimination - WA state funds the copay for reduced-price eligible students, making meals effectively free** ⚠️ *data gap*

    * Note: Washington state has eliminated copays for reduced-price meal eligible students through state funding. This means students qualifying at 185% FPL effectively receive free meals. This is a state policy enhancement that affects the benefit amount but not eligibility determination. The screener can note this in the benefit description.
    * **PE Note**: PolicyEngine does NOT model this WA-specific enhancement. PE will calculate the REDUCED tier benefit at reduced-price reimbursement rates rather than free-meal rates for households between 130%–185% FPL. The actual benefit to WA families is higher than PE estimates for this income band.
    * Source: RCW 28A.235.160; Washington State Legislature budget provisos; OSPI Bulletin No. 062-22
    * Impact: Low

## Benefit Value

MFB's `SchoolLunch` base class (and all state NSLP subclasses) use `pe_name = "school_meal_daily_subsidy"` — the per-day combined NSLP+SBP reimbursement rate from PolicyEngine. `household_value()` then multiplies by 180 school days × number of qualifying children, returning zero if the tier is `PAID`. Washington falls in the **CONTIGUOUS_US** state group. The net annual benefit per child equals:

```
(daily_nslp_rate[tier] + daily_sbp_rate[tier] - daily_nslp_rate[PAID] - daily_sbp_rate[PAID])
  × school_days (180)
  × children_in_k12 (ages 5–17 per is_in_k12_school)
```

> Note: `free_school_meals` and `reduced_price_school_meals` are PE annual-dollar variables split by tier, but MFB does not request these — it uses `school_meal_daily_subsidy` directly.

**2025 per-child annual estimates (CONTIGUOUS_US):**

| Tier     | NSLP/day | SBP/day | Combined | Less PAID ($0.86) | × 180 days | Annual benefit |
|----------|----------|---------|----------|-------------------|------------|----------------|
| FREE     | $4.60    | $2.46   | $7.06    | $6.20             | 180        | **~$1,116**    |
| REDUCED  | $4.20    | $2.16   | $6.36    | $5.50             | 180        | **~$990**      |
| PAID     | $0.46    | $0.40   | $0.86    | $0.00             | 180        | $0 (no subsidy)|

> **WA policy note**: Due to RCW 28A.235.160, REDUCED-tier families in WA receive free meals in practice (~$1,116/year per child), but PE will calculate ~$990/year for them.

## Implementation Coverage

* ✅ Evaluable criteria: 8
* ⚠️  Data gaps: 11

7 of approximately 15 total eligibility criteria/pathways can be evaluated with current screener fields. The core eligibility determination — income-based eligibility at 130% FPL (free) and 185% FPL (reduced-price), plus categorical eligibility via SNAP and TANF — can be fully evaluated. The primary gaps are: (1) inability to determine if a child's specific school participates in NSLP or CEP (though nearly all WA public schools participate), (2) foster care status, (3) homelessness status, and (4) migrant worker status. These gaps primarily affect categorical eligibility pathways; most affected children would also qualify through income-based criteria. The screener can reliably identify the vast majority of NSLP-eligible households in Washington state.

## Research Sources

* [Feeding America - National School Lunch Program (NSLP) Overview & Advocacy (Richard B. Russell National School Lunch Act, 42 U.S.C. § 1751 et seq.)](https://www.feedingamerica.org/advocate/federal-hunger-relief-programs/national-school-lunch-program)
* [FRAC - Federal Reimbursement Rates for NSLP, SBP, CACFP, and SFSP (July 2022) (7 CFR 210.4, 7 CFR 220.4)](https://frac.org/wp-content/uploads/FedRates_0722.pdf)
* [Feeding America - Summer Food Service Program (SFSP) Overview (42 U.S.C. § 1761)](https://www.feedingamerica.org/our-work/hunger-relief-programs/summer-food-service-program)
* [USDA FNS - National School Lunch Program (NSLP) Official Program Page (42 U.S.C. § 1751 et seq.; 7 CFR Part 210)](https://www.fns.usda.gov/nslp)

---

## Test Scenarios

### Scenario 1: Low-Income Family with School-Age Child Qualifies for Free Meals

**What we're checking**: Clearly eligible household with income well below 130% FPL and a school-age child in Washington state qualifies for free meals

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Relationship: `Head of Household`, Birth month/year: `June 1991` (age 34), Has income: Yes, Employment income: `$1,800` per month
* **Person 2**: Relationship: `Spouse`, Birth month/year: `September 1993` (age 32), Has income: No
* **Person 3**: Relationship: `Child`, Birth month/year: `January 2018` (age 8), Has income: No
* **Current Benefits**: No current benefits selected

**Why this matters**: This is the most common happy-path scenario: a small family in Washington state with one school-age child and gross income clearly below the 130% FPL threshold for free meals. It validates that the screener correctly identifies straightforward free-meal eligibility based on income and the presence of a qualifying child.

---

### Scenario 2: Household Income Just at 130% FPL Threshold - Barely Qualifies for Free Meals

**What we're checking**: Validates that a household with gross income exactly at 130% FPL qualifies for free meals (boundary test at the upper edge of free meal eligibility)

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98001`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$2,017` per month, No other income sources, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: Spouse, Has income: No, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2021` (age 5), Relationship: Child, Has income: No, Citizenship: US Citizen
* **Current Benefits**: No current benefits selected (no SNAP, no TANF)

**Why this matters**: Tests the boundary condition where household income is exactly at the 130% FPL threshold for a household of 3. For SY 2025-2026, 130% FPL for a household of 3 is approximately $24,204/year ($2,017/month). This ensures the system correctly includes households at the exact cutoff rather than excluding them. The child is exactly age 5 (minimum school age), making this a minimally eligible scenario across multiple criteria.

---

### Scenario 3: Household Income Just Below 185% FPL - Qualifies for Reduced-Price Meals

**What we're checking**: Validates that a household with gross income just below the 185% FPL threshold qualifies for reduced-price meals under NSLP

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `4`
* **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Has income: Yes, Employment income: `$4,400` per month
* **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, Has income: No
* **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, Has income: No
* **Person 4**: Birth month/year: `August 2018` (age 7), Relationship: Child, Has income: No
* **Current Benefits**: Do not select SNAP, TANF, or any other categorical benefits

**Why this matters**: This tests the upper boundary of reduced-price meal eligibility. A family earning just under 185% FPL should still qualify for reduced-price meals. This is distinct from Scenarios 1 and 2 which tested free meal eligibility at or below 130% FPL. Verifying this boundary ensures the screener correctly distinguishes between free meals, reduced-price meals, and ineligibility.

---

### Scenario 4: Household Income Exactly at 185% FPL - Boundary for Reduced-Price Meals

**What we're checking**: Validates that a household with gross income exactly at 185% of the Federal Poverty Level qualifies for reduced-price meals (the upper boundary of eligibility)

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `4`
* **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Has income: Yes, Employment income: `$4,622` per month, No other income sources, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, Has income: No, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, Has income: No, Citizenship: US Citizen
* **Person 4**: Birth month/year: `August 2018` (age 7), Relationship: Child, Has income: No, Citizenship: US Citizen
* **Current Benefits**: No current benefits selected (no SNAP, TANF, or other programs)

**Why this matters**: Testing the exact upper boundary of the 185% FPL income threshold is critical because households at exactly this limit should still qualify for reduced-price meals. Even a dollar over would make them ineligible. This boundary test ensures the screener uses a less-than-or-equal-to comparison rather than strictly less-than.

---

### Scenario 5: Household Income Just Above 185% FPL - Not Eligible for Any Meal Benefit

**What we're checking**: Validates that a household with gross income slightly above 185% FPL is denied both free and reduced-price meal eligibility

**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `4`
* **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Has income: Yes, Employment income: `$4,200` per month
* **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, Has income: Yes, Employment income: `$700` per month
* **Person 3**: Birth month/year: `January 2016` (age 10), Relationship: Child, Has income: No
* **Person 4**: Birth month/year: `August 2018` (age 7), Relationship: Child, Has income: No
* **Current Benefits**: Do not select SNAP, TANF, or any categorically qualifying benefits

**Why this matters**: This test confirms that the income ceiling for reduced-price meals (185% FPL) is enforced correctly. A family earning just over the 185% threshold must be excluded from both free and reduced-price meal categories, ensuring the program does not over-enroll ineligible households.

---

### Scenario 6: Child Exactly Age 5 (Minimum School Age) - Eligible for Free Meals

**What we're checking**: Validates that a child who is exactly 5 years old (the minimum age threshold for school-age children) qualifies for NSLP when income criteria are also met

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800` per month, No current benefits
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: Spouse, Has income: No
* **Person 3**: Birth month/year: `March 2021` (age exactly 5), Relationship: Child, Has income: No
* **Current Benefits**: No current benefits selected

**Why this matters**: This test validates the minimum age boundary for NSLP eligibility. A child who is exactly 5 years old is at the lower edge of the school-age requirement (ages 5–17 per PolicyEngine). If the screener incorrectly requires age 6 or older, this child would be wrongly excluded.

---

### Scenario 7: Child Age 4 (Just Below Minimum School Age) - Not Eligible

**What we're checking**: Validates that a household with only a child aged 4 (below the minimum school age of 5) is NOT eligible for NSLP benefits, even with qualifying income

**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Has income: Yes, Employment income: `$1,500` per month
* **Person 2**: Birth month/year: `August 1992` (age 33), Relationship: Spouse, Has income: No
* **Person 3**: Birth month/year: `July 2021` (age 4), Relationship: Child, Has income: No
* **Current Benefits**: Do not select SNAP, TANF, or any other categorical benefit

**Why this matters**: This test ensures the screener correctly enforces the minimum age boundary of 5 for NSLP eligibility. A child who is 4 years old is not yet school-age per 7 CFR 245.2 and should not qualify the household for free or reduced-price school meals, regardless of income.

---

### Scenario 8: Child Age 14 (Well Above Minimum School Age) - Eligible for Free Meals

**What we're checking**: Validates that a child well above the minimum school age of 5 (age 14, a typical high school student) is recognized as an eligible school-age child for NSLP

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Relationship: `Head of Household`, Birth month/year: `June 1985` (age 40), Has income: Yes, Employment income: `$1,800` per month
* **Person 2**: Relationship: `Child`, Birth month/year: `September 2011` (age 14), Has income: No
* **Person 3**: Relationship: `Child`, Birth month/year: `January 2015` (age 11), Has income: No
* **Current Benefits**: Select: No current benefits

**Why this matters**: Confirms that children well above the minimum age threshold of 5 are correctly identified as eligible school-age children.

---

### Scenario 9: Washington State Resident (Seattle ZIP Code) - Eligible Location Within Service Area

**What we're checking**: Validates that a household located within Washington state (using a valid WA ZIP code and county) is recognized as being within the NSLP service area

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: Head of Household, Has income: Yes, Employment income: `$1,800` per month
* **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, Has income: No
* **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: Child, Has income: No
* **Current Benefits**: Select no current benefits

**Why this matters**: Confirms that a valid Washington state ZIP code and county are properly recognized as being within the NSLP service area.

---

### Scenario 10: Family Already Receiving NSLP Free Meals - Exclusion Check

**What we're checking**: Whether a household that already receives NSLP free/reduced-price meals is flagged differently or shown as already enrolled

**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Relationship: `Head of Household`, Birth month/year: `June 1988` (age 37), Has income: Yes, Employment income: `$1,800` per month
* **Person 2**: Relationship: `Child`, Birth month/year: `September 2016` (age 9), Has income: No
* **Person 3**: Relationship: `Child`, Birth month/year: `January 2019` (age 7), Has income: No
* **Current Benefits**: Select that the household currently receives `National School Lunch Program (NSLP)` / free or reduced-price school meals

**Why this matters**: Households that already receive NSLP free or reduced-price meals should not be directed to apply again.

---

### Scenario 11: Household with No School-Age Children - Only Adult and Toddler Present

**What we're checking**: Validates that a household without any school-age children (ages 5–17) is excluded from NSLP eligibility, even if income would otherwise qualify

**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`, Number of children: `1`
* **Person 1**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: Yes, Employment income: `$1,500` per month
* **Person 2**: Relationship: `Spouse`, Birth month/year: `September 1992` (age 33), Has income: No
* **Person 3**: Relationship: `Child`, Birth month/year: `October 2023` (age 2), Has income: No
* **Current Benefits**: Select that the household currently receives SNAP benefits

**Why this matters**: This test validates that categorical requirements (having a school-age child) cannot be bypassed by other qualifying factors like SNAP participation or low income. NSLP is specifically for school-age children, and a household with only a toddler should be excluded regardless of how many other eligibility criteria they meet.

---

### Scenario 12: Mixed Household - Adults, School-Age Children, and Toddler with Income Between 130%–185% FPL

**What we're checking**: Validates that in a multi-member household with a mix of school-age children (eligible) and non-school-age members (toddler and adults), the program correctly identifies eligibility based on the school-age children while using the full household size for income determination

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98201`, Select county `Snohomish`
* **Household**: Number of people: `6`
* **Person 1**: Relationship: `Head of Household`, Birth month/year: `June 1986` (age 39), Has income: Yes, Employment income: `$2,200` per month
* **Person 2**: Relationship: `Spouse`, Birth month/year: `September 1988` (age 37), Has income: Yes, Employment income: `$1,800` per month
* **Person 3**: Relationship: `Child`, Birth month/year: `January 2014` (age 12), Has income: No
* **Person 4**: Relationship: `Child`, Birth month/year: `August 2019` (age 6), Has income: No
* **Person 5**: Relationship: `Child`, Birth month/year: `November 2023` (age 2), Has income: No
* **Person 6**: Relationship: `Parent (Grandparent)`, Birth month/year: `February 1956` (age 70), Has income: Yes, Social Security Retirement income: `$950` per month

**Why this matters**: This tests a realistic mixed household where not all children are school-age. The program must correctly identify which children qualify (ages 5–17 per PE) while still counting ALL household members (including the toddler and elderly grandparent) for the income threshold lookup. The gross annual income of approximately $59,400 for a 6-person household falls between 130% FPL (~$43,862) and 185% FPL (~$62,400) for SY 2025-2026, placing them in the reduced-price meal tier.

---

### Scenario 13: Large Family with Three School-Age Children and SNAP Benefits - All Children Eligible for Free Meals

**What we're checking**: Validates that multiple school-age children (ages 6, 10, and 16) in the same household all qualify for free meals through categorical eligibility via SNAP, regardless of income level

**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98502`, Select county `Thurston`
* **Household**: Number of people: `6`
* **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Has income: Yes, Employment income: `$3,200` per month, No other income sources
* **Person 2**: Birth month/year: `September 1988` (age 37), Relationship: Spouse, Has income: Yes, Employment income: `$2,400` per month, No other income sources
* **Person 3**: Birth month/year: `November 2019` (age 6), Relationship: Child, Has income: No
* **Person 4**: Birth month/year: `January 2016` (age 10), Relationship: Child, Has income: No
* **Person 5**: Birth month/year: `August 2009` (age 16), Relationship: Child, Has income: No
* **Person 6**: Birth month/year: `February 2023` (age 3), Relationship: Child, Has income: No
* **Current Benefits**: Select SNAP/Food Stamps as a currently received benefit

**Why this matters**: This test verifies that the screener correctly identifies ALL school-age children in a household as eligible when categorical eligibility via SNAP applies, while correctly excluding non-school-age children (ages below 5 per PE's `is_in_k12_school`). The household gross income of $67,200/year exceeds 185% FPL for a family of 6 (approximately $62,400 for SY 2025-2026), so without SNAP categorical eligibility these children would not qualify at all.

---

### Scenario 14: Child Exactly Age 18 - Upper Boundary of School-Age Eligibility

**What we're checking**: Whether a child who is exactly 18 years old (the upper boundary of school-age, still potentially enrolled in high school) qualifies for NSLP benefits

> ⚠️ **PE Implementation Discrepancy**: PolicyEngine's `is_in_k12_school` caps the eligible age range at **17** (`MAX_AGE = 17`), treating this as an imputation rather than a policy rule. A child who is 18 will NOT be counted by PE even though the statute (7 CFR 245.2) allows eligibility through age 18. This is a known PE limitation. The screener result for this scenario will show **Not eligible** because PE does not count the 18-year-old as a K-12 student. If our implementation extends the age range to 18 (overriding PE's imputation), the expected result would flip to Eligible.

**Expected (per PE as-is)**: Not eligible — PE's `is_in_k12_school` caps at age 17, so this child is not counted

**Expected (per statute / intended policy)**: Eligible — 18-year-olds may still be in high school and are within the regulatory definition of a "child" under 7 CFR 245.2

**Steps**:

* **Location**: Enter ZIP code `99362`, Select county `Walla Walla`
* **Household**: Number of people: `2`
* **Person 1**: Relationship: `headOfHousehold`, Birth month/year: `June 1980` (age 45), Has income: Yes, Employment income: `$1,800` per month
* **Person 2**: Relationship: `child`, Birth month/year: `March 2008` (age 18, just turned 18 this month), Has income: No
* **Current Benefits**: No current benefits selected

**Decision needed**: Determine whether to (a) accept PE's age-17 cap and mark this as Not eligible, (b) extend `is_in_k12_school` max age to 18 in a PE override, or (c) note it as a known gap in program copy.

---

## Source Documentation

* [https://www.feedingamerica.org/advocate/federal-hunger-relief-programs/national-school-lunch-program](https://www.feedingamerica.org/advocate/federal-hunger-relief-programs/national-school-lunch-program)
* [https://frac.org/wp-content/uploads/FedRates_0722.pdf](https://frac.org/wp-content/uploads/FedRates_0722.pdf)
