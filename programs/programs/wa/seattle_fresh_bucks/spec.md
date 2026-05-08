# Seattle Fresh Bucks — Implementation Spec

**Program:** `wa_seattle_fresh_bucks`
**State:** Washington
**White Label:** `wa`
**Research Date:** 2026-04-15

---

## Eligibility Criteria

1. **Household income must be at or below 80% Area Median Income (AMI) of the Seattle/King County Area**
   - Screener fields: `household_size`, income streams across all household members
   - Note: AMI thresholds are updated annually. Approximate 2025 80% AMI values for King County: 1-person: $84,850/yr ($7,071/mo) | 2-person: $96,950/yr ($8,079/mo) | 3-person: $109,050/yr ($9,088/mo) | 4-person: $121,150/yr ($10,096/mo) | 5-person: $130,850/yr ($10,904/mo). Priority is given to households at the lowest income tiers (see Priority Criteria).
   - Source: [Seattle Fresh Bucks Eligibility](https://www.seattlefreshbucks.org/apply/)

2. **Applicant must reside within Seattle city limits**
   - Screener fields: `zipcode`
   - Note: The screener uses ZIP code as a proxy for Seattle residency. Exact address verification (city limits boundary) is confirmed during enrollment, not by the screener. Applicants near city limits may be prompted to verify their address using the [Seattle district tool](https://www.seattle.gov/council/members/find-your-district-and-councilmembers). Inclusivity assumption: we assume all ZIPs that fall within Seattle are sufficient for screening purposes.
   - Source: [Seattle Fresh Bucks Eligibility](https://www.seattlefreshbucks.org/apply/)

3. **Applicant must be 18 years or older**
- Screener fields: `age`
- Source: [Seattle Fresh Bucks Eligibility](https://www.seattlefreshbucks.org/apply/)

---

## Priority Criteria

The following affect lottery weighting within the eligible pool — they do not determine eligibility itself:

- **Lowest income households** — Households in lower AMI tiers receive additional lottery entries.
- **Non-English language preference** — Applicants who prefer a language other than English may receive additional lottery weighting.
- **Waitlist duration** — Length of time on the waitlist may factor into selection.

---

## Benefit Value

- **Fixed monthly benefit: $60 per household per month**
- Benefit is loaded monthly onto an EBT card and can be used at any participating Seattle farmers market or grocery store vendor.
- Citable value. Source: [Seattle Fresh Bucks FAQ](https://www.seattlefreshbucks.org/faq/)

**Calculator methodology:** The calculator should return a fixed value of **60** (monthly). `value_format` is `null` (monthly). `estimated_value` is `""` (blank — defers to calculator output).

---

## Test Scenarios

All 12 scenarios below were approved (KEEP or KEEP BUT REVISE).  

---

**Scenario 1: Clearly Eligible Single Adult in Seattle**
- What we're checking: Golden-path eligible case. Single adult, WA resident in Seattle, income well below 80% AMI for 1 person.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98103`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1996` (age 30), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,500`, Income frequency: `Monthly`
- **Citizenship**: All household members are `U.S. Citizens`

**Why this matters**: Confirms standard eligibility for a single-person household in the target geography.

---

**Scenario 2: Minimally Eligible — Large Household at 80% AMI Threshold**
- What we're checking: A 5-person household with combined income exactly at the 5-person 80% AMI limit.
- Expected: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98118`
- **Household**: Number of people: `5`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$9,904`, Income frequency: `Monthly`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,000`, Income frequency: `Monthly`
- **Person 3 (Child)**: Relationship: `Child`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`
- **Person 4 (Child)**: Relationship: `Child`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`
- **Person 5 (Child)**: Relationship: `Child`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`

**Why this matters**: Validates the upper boundary of the 5-person income limit.

---

**Scenario 3: Income Just Below 3-Person 80% AMI Limit**
- What's being tested: Household of 3 with income just under the 3-person threshold.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98103`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$6,588`, Income frequency: `Monthly`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,500`, Income frequency: `Monthly`
- **Person 3 (Child)**: Relationship: `Child`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`

**Why this matters**: Confirms the threshold logic handles values immediately below the cutoff.

---

**Scenario 4: Income Exactly at 2-Person 80% AMI Threshold**
- What's being tested: Income exactly at the 2-person AMI limit confirms the threshold uses a ≤ comparison.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98103`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$4,219`, Income frequency: `Monthly`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,860`, Income frequency: `Monthly`

**Why this matters**: Verifies that the inclusive inequality operator (≤) is implemented correctly.

---

**Scenario 5: Income Just Above 1-Person 80% AMI Limit — Ineligible**
- What's being tested: Income just $1/month above the 1-person 80% AMI limit correctly screens out the applicant.
- Expected result: Ineligible

**Steps**:
- **Location**: Enter ZIP code `98103`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$7,072`, Income frequency: `Monthly`

**Why this matters**: Verifies that the screener correctly identifies the "over-income" cutoff.

---

**Scenario 6: Applicant Age Exactly 18 — Eligible**
- What's being tested: Minimum adult age for application; an 18-year-old is not excluded by age.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98118`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 2008` (age 18), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,500`, Income frequency: `Monthly`

**Why this matters**: Confirms the floor for adult primary applicants.

---

**Scenario 7: Applicant Age 17 — Below Minimum Age — Ineligible**
- What's being tested: A 17-year-old is below the minimum age and should be screened out as a primary applicant.
- Expected result: Ineligible

**Steps**:
- **Location**: Enter ZIP code `98118`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `July 2008` (age 17), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,200`, Income frequency: `Monthly`

**Why this matters**: Verifies age-gating for the application process.

---

**Scenario 8: Senior Applicant Age 72 — Eligible**
- What's being tested: Confirms there is no upper age limit for eligibility.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98144`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `March 1954` (age 72), Has income: `Yes`, Income type: `SSRetirement`, Income amount: `$1,400`, Income frequency: `Monthly`

**Why this matters**: Ensures the screener is inclusive of seniors.

---

**Scenario 9: Eligible Location — Seattle ZIP 98103**
- What's being tested: Confirms that a central Seattle ZIP code is correctly identified as within the service area.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98103`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$2,300`, Income frequency: `Monthly`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Has income: `Yes`, Income type: `Yes`, Income amount: `$2,200`, Income frequency: `Monthly`

**Why this matters**: Validates geographic boundary logic.

---

**Scenario 10: Mixed Household — Eligible at 4-Person Threshold**
- What's being tested: A 4-person household with combined income above the 2-person limit but below the 4-person limit.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98118`
- **Household**: Number of people: `4`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$8,000`, Income frequency: `Monthly`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Has income: `Yes`, Income type: `Yes`, Income amount: `$300`, Income frequency: `Monthly`
- **Person 3 (Child)**: Relationship: `Child`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`
- **Person 4 (Dependent)**: Relationship: `Senior`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`

**Why this matters**: Tests that household size correctly expands the income threshold.

---

**Scenario 11: Multiple Eligible Adults — One Benefit per Household**
- What's being tested: Confirms one benefit is awarded per household regardless of individual eligibility of members.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98122`
- **Household**: Number of people: `5`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$4,032`, Income frequency: `Monthly`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$1,368`, Income frequency: `Monthly`
- **Person 3 (Child)**: Relationship: `Child`, Has income: `Yes`, Income type: `Yes`, Income amount: `1,000`, Income frequency: `Monthly`
- **Person 4 (Child)**: Relationship: `Child`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`
- **Person 5 (Child)**: Relationship: `Child`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`

**Why this matters**: Ensures the calculator returns the household benefit value rather than multiplying by eligible members.

---

**Scenario 12: Household of 1 with Zero Income — Edge Case**
- What's being tested: A household with zero income is still eligible — no minimum income floor.
- Expected result: Eligible, value: 60

**Steps**:
- **Location**: Enter ZIP code `98122`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `No`, Income type: `None`, Income amount: `$0`, Income frequency: `Null`

**Why this matters**: Confirms accessibility for the lowest income tier.

---

**Scenario 13: Ineligible Location — Surrounding Area**
- What's being tested: A household with zero income is still eligible — no minimum income floor.
- Expected result: Not eligible, value: 0

**Steps**:
- **Location**: Enter ZIP code `98004`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$892`, Income frequency: `Monthly`

**Why this matters**: Validates screener flags ineligible zipcodes and marks as Not elible.
