# Implement Commodity Supplemental Food Program (CSFP) (WA) Program

## Program Details

* **Program**: Commodity Supplemental Food Program (CSFP)
* **State**: WA
* **White Label**: wa
* **Research Date**: 2026-04-02

## Eligibility Criteria

1. **Applicant must be at least 60 years of age**
   * Screener fields:
     * `age (HouseholdMember level)`
   * Source: 7 CFR 247.2 (definition of 'elderly person'); 7 CFR 247.9(a); WA CSFP State Plan Section 2
2. **Household income must be at or below 150% of the Federal Poverty Level (FPL)**
   * Note: Effective January 1, 2025, USDA revised the federal CSFP income limit from 130% FPL to 150% FPL. All scenarios use the 150% threshold applicable for 2025+. (Source for change: USDA CSFP Revised Income Guidelines 2024.)
   * Screener fields:
     * `household_size`
     * `income_streams`
   * Source: 7 CFR 247.9(a)(1); 7 CFR 247.9(d); WA CSFP State Plan Section 2; USDA CSFP Revised Income Guidelines 2024
3. **Applicant must reside in Washington State**
   * Screener fields:
     * `zipcode`
     * `county`
   * Source: 7 CFR 247.9(a); WA CSFP State Plan Section 2
4. **Applicant must reside within an approved CSFP service area (not all areas of Washington may be served)** ⚠️ *data gap*
   * Note: While we have zipcode and county, we do not have a maintained list of which specific areas in Washington are approved CSFP service areas. CSFP operates through local agencies in designated areas, and not all counties may be served. The WA CSFP State Plan Section 1 defines caseload and service areas, but this data would need to be maintained as a lookup table. Without this mapping, we can confirm WA residency but not service area eligibility.
   * Source: 7 CFR 247.6; WA CSFP State Plan Section 1 (Caseload and Service Areas)
   * Impact: Medium
5. **Applicant must not simultaneously participate in the Food Distribution Program on Indian Reservations (FDPIR)** ⚠️ *data gap*
   * Note: There is no screener field for FDPIR participation. FDPIR is a relatively small program and dual participation would be uncommon, but it is a federal regulatory prohibition. This would be verified at the point of application/certification by the local CSFP agency.
   * Source: 7 CFR 247.9(c)
   * Impact: Low

## Benefit Value

* The benefit value is estimated as roughly $50/month per eligible household member 60+. Benefits are provided as monthly food commodity packages, not cash.
* Source: https://www.feedingamerica.org/advocate/federal-hunger-relief-programs/csfp#:~:text=The%20%2427%20cost%20to%20USDA,pick%20up%20their%20food%20package.

## Implementation Coverage

* ✅ Evaluable criteria: 3
* ⚠️  Data gaps: 2

3 of 5 total criteria can be evaluated (fully or substantially) with current screener fields. The two core eligibility requirements - age (60+) and income (at or below 150% FPL) - are fully evaluable and represent the primary screening criteria. State residency can be confirmed via zipcode/county. The criteria that cannot be evaluated are primarily administrative (service area specifics, caseload availability, identity verification) or rare edge cases (institutionalization, FDPIR dual participation). The screener can effectively identify likely-eligible individuals for CSFP in Washington State.

## Research Sources

* [Washington State CSFP Program Overview – WA Department of Agriculture](https://agr.wa.gov/services/food-access/programs-and-services/commodity-supplemental-food-program-(csfp))
* [Washington CSFP State Plan – Section 2: Applicant Eligibility and Certification (7 CFR 247)](https://agr.wa.gov/services/food-access/hunger-relief-agency-hub/csfp/csfp-plan/section-2)
* [WA Department of Agriculture – Public Records Request Portal](https://agr.wa.gov/contact-us/public-disclosure)
* [WA Department of Agriculture – Food Access Programs and Services Directory](https://agr.wa.gov/services/food-access/programs-and-services)
* [Washington State Department of Agriculture – Homepage](https://agr.wa.gov/)
* [Services](https://agr.wa.gov/Services)
* [WA Department of Agriculture – Food Access Division](https://agr.wa.gov/Services/Food-Access)
* [Programs and Services](https://agr.wa.gov/Services/Food-Access/Programs-and-Services)
* [Washington State CSFP Program Overview – WA Department of Agriculture (Duplicate/Canonical URL)](https://agr.wa.gov/Services/Food-Access/Programs-and-Services/Commodity-Supplemental-Food-Program-(CSFP))

---

## Test Scenarios

### Scenario 1: Clearly Eligible Senior - Single 68-Year-Old with Low Income

**What we're checking**: Typical happy path: a single elderly applicant aged 60+ with income well below 150% FPL residing in Washington State

**Expected**: Eligible, value: `$50`

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 1957` (age 68), Relationship: Head of Household, Has income: Yes, Social Security Retirement income: `$950` per month, No other income sources, Insurance: None, Citizenship: US Citizen
* **Current Benefits**: Do not select any current benefits (no FDPIR, no CSFP)

**Why this matters**: This is the most straightforward eligible scenario: a single senior citizen with modest Social Security income living in Washington State. It validates that the screener correctly identifies a clearly qualifying applicant across all four eligibility criteria (age, income, residency, and no FDPIR conflict).

---

### Scenario 2: Minimally Eligible - Just Turned 60 with Income at Exactly 150% FPL

**What we're checking**: Applicant who barely meets all eligibility thresholds: exactly age 60 and income right at the 150% FPL limit

**Expected**: Eligible, value: `$50`

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1966` (age 60, just turned 60 this month), Relationship: `Head of Household`, Has income: Yes, Social Security Retirement income: `$1,956` per month (approximately $23,475/year, which is right at 150% FPL for a household of 1 using 2026 HHS guidelines)
* **Current Benefits**: Do not select any current benefits (no FDPIR)

**Why this matters**: Tests the boundary conditions for CSFP eligibility - someone who just barely qualifies by age (exactly 60) and has income right at the 150% FPL threshold (the federal limit effective January 2026). This ensures the screener correctly handles edge cases where applicants minimally meet all criteria rather than clearly exceeding them.

---

### Scenario 3: Income Well Below 150% FPL - Two-Person Household Senior

**What we're checking**: Validates that a two-person household with combined income comfortably below the 150% FPL threshold is correctly identified as eligible

**Expected**: Eligible, value: `$100`

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `June 1953` (age 72), Relationship: Head of Household, Has income: Yes, Social Security Retirement: `$1,100` per month
* **Person 2**: Birth month/year: `September 1955` (age 70), Relationship: Spouse, Has income: Yes, Social Security Retirement: `$470` per month
* **Current Benefits**: Do not select any current benefits

**Why this matters**: Tests a two-person senior household where combined income ($1,570/month, ~$18,840/year) is well below the 150% FPL threshold for a 2-person household (~$2,705/month), ensuring the screener correctly evaluates household-level income aggregation for multi-member households.

---

### Scenario 5: Income Just Above 150% FPL - Single Senior Should Be Ineligible

**What we're checking**: Verifies that a single 65-year-old senior with income just above the 150% FPL threshold for a 1-person household is correctly determined ineligible

**Expected**: Not eligible, value: `$0`

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1961` (age 65), This person is the head of household, Has income: Yes, Social Security Retirement income: `$1,999` per month (approximately $23,988/year, just above the 150% FPL limit of ~$23,475/year for a 1-person household using 2025 HHS guidelines), No other income sources
* **Current Benefits**: Do not select any current benefits

**Why this matters**: This test ensures the screener correctly rejects applicants whose income is just barely above the 150% FPL threshold (the federal limit effective January 2026), validating that the income boundary is enforced precisely rather than allowing a margin of error. N

---

### Scenario 7: Age 59 - One Year Below Minimum Age Threshold

**What we're checking**: Validates that a person aged 59 (one year below the minimum age of 60) is correctly identified as NOT eligible for CSFP

**Expected**: Not eligible, value: `$0`

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 1966` (age 59), This person is 59 years old, which is below the minimum age of 60 required for CSFP
* **Income**: Enter Social Security Retirement income of `$800` per month, This is well below the 150% FPL threshold for a single-person household, so income is not the disqualifying factor
* **Current Benefits**: Do not select any current benefits (no FDPIR)

**Why this matters**: This test ensures the age boundary is strictly enforced. A 59-year-old is just one year below the minimum age of 60 required by 7 CFR 247.2 and 7 CFR 247.9(a). Even though all other criteria (income, residency, no FDPIR) are met, the applicant must be denied. This is a critical boundary test to prevent false positives for near-eligible individuals.

---

### Scenario 10: Already Receiving CSFP Benefits - Current Participant Should See Exclusion Message

**What we're checking**: Whether a person who already receives CSFP benefits is flagged as ineligible or shown a different message indicating they already participate in the program

**Expected**: Not eligible, value: `$0`

**Steps**:

* **Location**: Enter ZIP code `98902`, Select county `Yakima`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 1956` (age 69), Indicate this person is the head of household, Indicate US citizen
* **Income**: Enter Social Security Retirement income of `$900` per month, No other income sources
* **Current Benefits**: Select or indicate that the applicant currently receives **CSFP** (Commodity Supplemental Food Program) benefits, If there is a checkbox or question about currently receiving CSFP, mark it as **Yes**

**Why this matters**: Per 7 CFR 247.9(c), participants cannot be enrolled in CSFP if they are already receiving benefits. This test validates that the screener correctly handles the exclusion for current CSFP recipients, preventing duplicate enrollment and ensuring program integrity.

---

### Scenario 11: Excluded Due to SNAP Participation - Senior Otherwise Eligible for CSFP

**What we're checking**: Whether current SNAP participation triggers an exclusion or informational note, since CSFP historically had restrictions related to other food assistance programs (FDPIR). While SNAP itself does not disqualify from CSFP, this tests how the screener handles other program participation flags and ensures CSFP eligibility is still correctly evaluated when a person receives SNAP benefits.

**Expected**: Eligible, value: `$50`

**Steps**:

* **Location**: Enter ZIP code `99201`, Select county `Spokane`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 1960` (age 65), Relationship: Head of Household, Has income: Yes, Social Security Retirement income: `$900` per month, No other income sources
* **Current Benefits**: Select that the household currently receives **SNAP** (food stamps/EBT) benefits.

**Why this matters**: 7 CFR 247.9(c) specifically prohibits individuals from receiving CSFP benefits while simultaneously participating in FDPIR. SNAP participation does NOT disqualify someone from CSFP. This test validates that the screener correctly handles other program participation flags and does not incorrectly exclude SNAP recipients from CSFP eligibility. It also tests whether the FDPIR exclusion is properly enforced if that field exists in the screener.

---

### Scenario 12: Mixed Household - Eligible Senior with Younger Spouse and Child

**What we're checking**: Validates that in a multi-member household, CSFP eligibility is determined by the presence of at least one member aged 60+ while other members are below the age threshold, and that household income is evaluated against the correct household size FPL

**Expected**: Eligible, value: `$50`

**Steps**:

* **Location**: Enter ZIP code `98201`, Select county `Snohomish`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1962` (age 63), Relationship: Head of Household, Has income: Yes, Social Security Retirement: `$950` per month
* **Person 2**: Birth month/year: `September 1975` (age 50), Relationship: Spouse, Has income: Yes, Wages/Salary: `$1,200` per month
* **Person 3**: Birth month/year: `January 2008` (age 18), Relationship: Child, Has income: No
* **Current Benefits**: Do not select CSFP or FDPIR as current benefits

**Why this matters**: This tests a realistic mixed-age household where only one member meets the age requirement for CSFP. It verifies that the screener correctly identifies eligibility based on the qualifying senior member while using the full household size for income calculations, which results in a higher income threshold that benefits the household.

---

### Scenario 13: Multiple Eligible Seniors - Two Elderly Spouses Both Over 60 in Same Household

**What we're checking**: Validates that when a household contains two members who both independently meet the age requirement (60+), the screener correctly identifies CSFP eligibility for the household

**Expected**: Eligible, value: `$100`

**Steps**:

* **Location**: Enter ZIP code `99201`, Select county `Spokane`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `June 1954` (age 71), Relationship: Head of Household, Has income: Yes, Social Security Retirement income: `$950` per month
* **Person 2**: Birth month/year: `September 1958` (age 67), Relationship: Spouse, Has income: Yes, Social Security Retirement income: `$750` per month
* **Current Benefits**: Do not select CSFP or FDPIR as current benefits

**Why this matters**: This test verifies that the screener correctly handles a household where multiple members each independently qualify by age. Unlike Scenario 12 which tested a mixed household with only one eligible senior, this scenario ensures the system properly processes two qualifying seniors and does not produce duplicate or conflicting eligibility results.

---

### Scenario 14: Large Household (8 People) with Senior with Income Below FPL Limit

**What we're checking**: Edge case testing a large household size (8 members) where combined income is below the 150% FPL threshold, verifying correct FPL scaling for larger households

**Expected**: Eligible, value: `$50`

**Steps**:

* **Location**: Enter ZIP code `99362`, Select county `Walla Walla`
* **Household**: Number of people: `8`
* **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: Head of Household, Has income: Yes, Social Security Retirement: `$2,500` monthly
* **Person 2**: Birth month/year: `June 1968` (age 57), Relationship: Spouse, Has income: Yes, Employment income: `$2,000` monthly
* **Person 3**: Birth month/year: `March 2000` (age 26), Relationship: Child, Has income: No
* **Person 4**: Birth month/year: `September 2002` (age 23), Relationship: Child, Has income: No
* **Person 5**: Birth month/year: `December 2004` (age 21), Relationship: Child, Has income: No
* **Person 6**: Birth month/year: `February 2007` (age 19), Relationship: Child, Has income: No
* **Person 7**: Birth month/year: `July 2010` (age 15), Relationship: Child, Has income: No
* **Person 8**: Birth month/year: `November 2013` (age 12), Relationship: Child, Has income: No

**Why this matters**: Tests the system's ability to correctly calculate FPL thresholds for large households (8 members). Combined income of $4,500/month ($54,000/year) is well below the 150% FPL threshold for an 8-person household (~$6,769/month using 2025 HHS guidelines). Validates that the screener correctly identifies the eligible senior in a large mixed-age household and applies the per-additional-person FPL increment beyond the base household size.

---

### Scenario 15: Non-Washington Resident — Out-of-State Senior Should Be Ineligible

**What we're checking**: Verifies that an applicant who otherwise meets all CSFP criteria (age 60+, income below 150% FPL, no FDPIR participation) but resides outside Washington State is correctly identified as ineligible due to the state residency requirement

**Expected**: Not eligible, value: `$0`

**Steps**:

* Location: Enter ZIP code `97201`, Select county `Multnomah`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 1957` (age 68), Relationship: Head of Household, Has income: Yes, Social Security Retirement income: `$950` per month, No other income sources, Insurance: None, Citizenship: US Citizen

**Why this matters**: This test isolates the Washington State residency requirement (7 CFR 247.9(a); WA CSFP State Plan Section 2). The applicant clearly satisfies every other eligibility criterion — age well above 60, income well below 150% FPL, no disqualifying program participation — so the only factor that should drive ineligibility is the out-of-state ZIP and county.

---

## Source Documentation

* [https://agr.wa.gov/services/food-access/programs-and-services/commodity-supplemental-food-program-(csfp)](https://agr.wa.gov/services/food-access/programs-and-services/commodity-supplemental-food-program-(csfp))
* [https://agr.wa.gov/services/food-access/hunger-relief-agency-hub/csfp/csfp-plan/section-2](https://agr.wa.gov/services/food-access/hunger-relief-agency-hub/csfp/csfp-plan/section-2)
