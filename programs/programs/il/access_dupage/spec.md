# Implement Access DuPage (IL) Program

## Program Details

- **Program**: Access DuPage
- **State**: IL
- **White Label**: il
- **Research Date**: 2026-06-25

## Eligibility Criteria

1. **Must be a permanent DuPage County resident**
   - Screener fields:
     - `county`
   - Note: "Permanent" means residing in DuPage County for at least 30 days with intent to live there year-round. The screener checks county selection but cannot verify duration or intent. ⚠️ *partial data gap* — default to inclusive.
   - Source: [Access DuPage Program Overview – DuPage Health Coalition](https://dupagehealthcoalition.org/access-dupage/): *"Be a permanent DuPage County resident"* / *"This means that you have resided in DuPage County for at least 30 days and intend to live in DuPage County year-round."*

2. **Household income must be at or below 250% of the Federal Poverty Level (FPL)**
   - Screener fields:
     - `household_size`
     - `income (all types via calc_gross_income)`
   - Source: [Access DuPage Program Overview – DuPage Health Coalition](https://dupagehealthcoalition.org/access-dupage/): *"Have income at or below 250% of the current federal poverty line guidelines"*

3. **Must not be eligible for other health insurance**
   - Screener fields:
     - `insurance["none"]` (no health insurance at all)
     - `insurance["medicaid"]` (Medicaid enrollment)
     - `insurance["medicare"]` (Medicare enrollment)
     - `insurance["employer"]` (employer-sponsored insurance)
   - Note: The program excludes anyone eligible for Medicaid, Medicare, ACA marketplace plans, or employer-sponsored insurance. The screener checks current enrollment/coverage, not eligibility for these programs. ⚠️ *partial data gap* — default to inclusive for users who report being uninsured.
   - Source: [Access DuPage Program Overview – DuPage Health Coalition](https://dupagehealthcoalition.org/access-dupage/): *"Eligibility for other health care programs such as Medicaid, Medicare, ACA health insurance, and employer-sponsored insurance, etc. will result in ineligibility for Access DuPage."*

4. **Must be age 19 or older**
   - Screener fields:
     - `birth_year` + `birth_month` (HouseholdMember)
   - Note: No upper age limit is stated. People 65+ are effectively excluded under criterion 3 (Medicare eligibility). Use `birth_year` and `birth_month` — `age` is a deprecated field.
   - Source: [Access DuPage Program Overview – DuPage Health Coalition](https://dupagehealthcoalition.org/access-dupage/): *"Be age 19 or older"*

## Benefit Value

- Access DuPage provides in-kind health care services (doctor visits, lab tests, prescription medicines, specialist care, hospital services). There is no fixed dollar benefit amount. Test scenarios show `$None/year`, which is the correct representation for a non-calculator program — no dollar value will display in the screener.

## Implementation Coverage

- ✅ Evaluable criteria: 4 (all, with partial data gaps on criteria 1 and 3)
- ⚠️ Partial data gaps: 2

All 4 eligibility criteria can be evaluated with current screener fields. Criterion 1 (residency) can be checked by county but not the 30-day duration requirement. Criterion 3 (insurance) can check current enrollment but not full eligibility for Medicaid, ACA, or employer plans. Both default to inclusive per standing rules.

## Research Sources

- [Access DuPage Program Overview – DuPage Health Coalition (Eligibility, Enrollment, and Program Description)](https://dupagehealthcoalition.org/access-dupage/)
- [Access DuPage – Examples of Acceptable Proof Documents for Eligibility Verification](https://dupagehealthcoalition.org/wp-content/uploads/2024/12/2020-Examples-of-proofs-002.pdf)

## Acceptance Criteria

[ ] Scenario 1 (Clearly Eligible Uninsured Adult in DuPage County): User should be **eligible**
[ ] Scenario 2 (Minimally Eligible - Income at Exactly 250% FPL, Age 19): User should be **eligible**
[ ] Scenario 3 (Income Just Below 250% FPL for Household of 3): User should be **eligible**
[ ] Scenario 4 (Income Just Above 250% FPL - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 5 (Non-DuPage County Resident - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 6 (Age Exactly 19 - Minimum Age Threshold): User should be **eligible**
[ ] Scenario 7 (Age 18 - Just Below Minimum Age Threshold - Should NOT Be Eligible): User should be **ineligible**
[ ] Scenario 8 (Excluded Due to Current Medicaid Enrollment): User should be **ineligible**
[ ] Scenario 9 (Excluded Due to Employer-Sponsored Insurance): User should be **ineligible**
[ ] Scenario 10 (Mixed Household - Eligible Adult, Insured Spouse, Minor Child, and Medicare-Enrolled Parent): User should be **eligible**
[ ] Scenario 11 (Two Eligible Uninsured Adults in Same DuPage County Household): User should be **eligible**
[ ] Scenario 12 (Age 64 - Just Before Typical Medicare Age): User should be **eligible**

## Test Scenarios

### Scenario 1: Clearly Eligible Uninsured Adult in DuPage County
**What we're checking**: Baseline happy path — DuPage County resident, uninsured, age 19+, income below 250% FPL, no Medicaid or Medicare
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Sex: `Male`, Relationship: `Head of Household`, Has health insurance: `No`, Has Medicaid: `No`, Has Medicare: `No`, Has income: `Yes`, Employment income: `$1,800` per month

**Why this matters**: Confirms a straightforward eligible applicant is correctly identified. A single adult earning $21,600/year is well below the 2026 250% FPL threshold of $39,900 for a household of 1.

---

### Scenario 2: Minimally Eligible - Income at Exactly 250% FPL, Age 19
**What we're checking**: Applicant at both thresholds simultaneously: just turned 19, income exactly at the 250% FPL ceiling
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 2007` (age 19, just turned 19 this month), Relationship: `headOfHousehold`, Has income: Yes, Employment income: `$3,325` per month ($39,900/year = exactly 250% FPL for household of 1 in 2026: $15,960 × 2.5 = $39,900), Health insurance: None, Not enrolled in or eligible for Medicaid, Not enrolled in Medicare

**Why this matters**: Tests that the income and age boundaries are both inclusive — a person at exactly the minimum age and exactly the income cap should be eligible.

---

### Scenario 3: Income Just Below 250% FPL for Household of 3
**What we're checking**: Multi-person household with income just under the 250% FPL threshold
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: Head of Household, No health insurance coverage, Not enrolled in or eligible for Medicaid, Not enrolled in Medicare
- **Person 2**: Birth month/year: `July 2014` (age 11), Relationship: Child
- **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: Child
- **Income**: Enter employment income for Person 1: `$5,691` per month ($68,292/year, just below the 250% FPL of $68,300 for a household of 3 in 2026: $27,320 × 2.5 = $68,300)

**Why this matters**: Confirms FPL scaling is correctly applied for multi-person households and that the income ceiling is inclusive.

---

### Scenario 4: Income Just Above 250% FPL - Should NOT Be Eligible
**What we're checking**: Single adult with income just over the 250% FPL threshold
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Has income: Yes, Employment income: `$3,326` per month ($39,912/year, above the 250% FPL of $39,900 for household of 1 in 2026: $15,960 × 2.5 = $39,900), No health insurance coverage, Not enrolled in or eligible for Medicaid, Not enrolled in Medicare

**Why this matters**: Confirms the income cap is enforced precisely.

---

### Scenario 5: Non-DuPage County Resident - Should NOT Be Eligible
**What we're checking**: An otherwise-eligible adult who lives in a different county is correctly denied
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `60601`, Select county `Cook`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Has health insurance: `No`, Has Medicaid: `No`, Has Medicare: `No`, Has income: `Yes`, Employment income: `$1,800` per month

**Why this matters**: Directly tests the county residency criterion. This applicant meets all other criteria but lives in Cook County, not DuPage County, and should not be shown as eligible.

---

### Scenario 6: Age Exactly 19 - Minimum Age Threshold - Should Be Eligible
**What we're checking**: A person who is exactly 19 meets the minimum age requirement
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `June 2007` (age 19, just turned 19), Relationship: `headOfHousehold`, No health insurance coverage, Not enrolled in or eligible for Medicaid, Not enrolled in Medicare, Has income: Yes, Employment income: `$1,200` per month

**Why this matters**: Confirms the lower age boundary (19) is inclusive, in isolation from other boundary conditions.

---

### Scenario 7: Age 18 - Just Below Minimum Age Threshold - Should NOT Be Eligible
**What we're checking**: An 18-year-old is correctly rejected (minimum age is 19; 18-year-olds are directed to AllKids)
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Relationship: `headOfHousehold`, Birth month/year: `March 2008` (age 18), Has income: Yes, Employment income: `$1,200` per month, No health insurance coverage, Not enrolled in or eligible for Medicaid, Not enrolled in Medicare

**Why this matters**: Confirms the minimum age of 19 is enforced at the boundary. Single-person household to isolate the age criterion — a second eligible adult would contaminate the expected result.

---

### Scenario 8: Excluded Due to Current Medicaid Enrollment
**What we're checking**: An adult enrolled in Medicaid is excluded, since Medicaid eligibility disqualifies from Access DuPage
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Sex: `Female`, Has income: `Yes`, Employment income: `$1,200` per month, Health insurance: Select `Medicaid` (currently enrolled in Medicaid)

**Why this matters**: Tests the Medicaid branch of the insurance criterion. Medicaid enrollment is a direct disqualifying factor.

---

### Scenario 9: Excluded Due to Employer-Sponsored Insurance
**What we're checking**: An adult with employer-sponsored health insurance is excluded, since having other health coverage disqualifies from Access DuPage
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Has income: `Yes`, Employment income: `$1,800` per month, Has employer-sponsored health insurance: `Yes`

**Why this matters**: Tests the employer insurance branch of the insurance criterion. Access DuPage is specifically for people with no other insurance option. This is a distinct screener path from the Medicaid exclusion (Scenario 8).

---

### Scenario 10: Mixed Household - Eligible Adult, Insured Spouse, Minor Child, and Medicare-Enrolled Parent
**What we're checking**: In a multi-member household, only the uninsured adult without Medicaid/Medicare is flagged as potentially eligible
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `4`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `March 1988` (age 38), No health insurance coverage, Not enrolled in Medicaid, Not enrolled in Medicare
- **Person 2**: Relationship: `Spouse`, Birth month/year: `September 1990` (age 35), Has employer-sponsored health insurance, Not enrolled in Medicaid, Not enrolled in Medicare
- **Person 3**: Relationship: `Child`, Birth month/year: `January 2016` (age 10), Has health insurance (covered under spouse's employer plan), Not enrolled in Medicaid, Not enrolled in Medicare
- **Person 4**: Relationship: `Parent`, Birth month/year: `November 1958` (age 67), Has Medicare coverage, Not enrolled in Medicaid
- **Income**: Person 1: `$2,000` per month, Person 2: `$2,000` per month, Person 4 Social Security: `$1,110` per month, Total: `$5,110`/month ($61,320/year). Note: 250% FPL for household of 4 in 2026 = $33,000 × 2.5 = $82,500/year — this household is within the limit.

**Why this matters**: Confirms the screener evaluates each household member individually and correctly identifies the one eligible adult among a mixed household.

---

### Scenario 11: Two Eligible Uninsured Adults in Same DuPage County Household
**What we're checking**: Multiple eligible adults within the same household are both identified as eligible
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `3`
- **Person 1**: Relationship: `Head of Household`, Birth month/year: `February 1988` (age 38), Employment income: `$1,400` per month, Health insurance: `None`, Not enrolled in or eligible for Medicaid, Not enrolled in Medicare
- **Person 2**: Relationship: `Spouse`, Birth month/year: `September 1991` (age 34), Employment income: `$1,100` per month, Health insurance: `None`, Not enrolled in or eligible for Medicaid, Not enrolled in Medicare
- **Person 3**: Relationship: `Child`, Birth month/year: `March 2018` (age 8), No income, Health insurance: `None`

**Why this matters**: Confirms the screener identifies multiple eligible adults in the same household, not just one.

---

### Scenario 12: Age 64 - Just Before Typical Medicare Age
**What we're checking**: A 64-year-old without Medicare is eligible. The program has no stated upper age limit — people 65+ are excluded under the insurance criterion (Medicare eligibility), not an age cutoff.
**Expected**: Eligible

**Steps**:
- **Location**: Enter ZIP code `60137`, Select county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1962` (age 64), Sex: `Male`, Relationship: `Head of Household`, Has health insurance: `No`, Not enrolled in Medicaid, Not enrolled in Medicare, Has income: `Yes`, Employment income: `$1,500` per month ($18,000/year)

**Why this matters**: Confirms a 64-year-old without Medicare qualifies. Once they turn 65 and become Medicare-eligible, they would be excluded under criterion 3, not a separate age rule.

---

## Source Documentation

- https://dupagehealthcoalition.org/access-dupage/
- https://dupagehealthcoalition.org/wp-content/uploads/2024/12/2020-Examples-of-proofs-002.pdf
