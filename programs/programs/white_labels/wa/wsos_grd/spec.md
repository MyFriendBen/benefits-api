# Washington State Opportunity Scholarship (WSOS) — GRD Track Implementation Spec

**Program:** `wa_wsos_grd`
**State:** Washington
**White Label:** `wa`
**Research Date:** 2026-04-27

---

## Eligibility Criteria

1. **Applicant is a Washington state resident**
   - Screener fields:
     - `zipcode`
     - `county`
   - Note: GRD requires Washington residency. Verified through ZIP code and county in the screener. WSOS explicitly accepts undocumented applicants — no immigration status restriction applies.
   - Source: https://waopportunityscholarship.org/applicants/grd/#Eligibility (Residency)

2. **Household income is at or below 155% of Washington State Median Family Income (MFI) for household size**
   - Screener fields:
     - `income_streams` (amount and frequency across all household members)
     - `household_size`
   - Note: GRD uses a two-tier income threshold:
     - **Automatic eligibility (125% MFI):** Applicants at or below 125% MFI are automatically income-eligible. This is fully checkable via the screener.
     - **Expanded eligibility (126–155% MFI):** Applicants between 126–155% MFI may qualify only if they can demonstrate financial hardship — specifically, student loan debt exceeding $30K, prior use of income-based programs, or significant economic hardship. The screener cannot verify hardship factors.
     - ⚠️ **Data gap (hardship verification):** The screener cannot check whether an applicant qualifies under the expanded 126–155% MFI path. Hardship factors are not captured.
       - **Inclusivity assumption:** Show the program to all applicants up to 155% MFI. The calculator cannot determine whether those in the 126–155% range will ultimately qualify — eligibility is conditional on hardship evidence provided during the application.
       - **Implementation:** Use 155% MFI as the upper calculator cutoff. Applicants between 126–155% MFI should see the program with a clear note that they will need to demonstrate financial hardship during the application process.
     - 2026 MFI thresholds (verified against official WSOS GRD MFI Chart):
       - Family of 1: $90,500 (125%) / $112,500 (155%)
       - Family of 2: $118,000 (125%) / $146,500 (155%)
       - Family of 3: $146,500 (125%) / $181,500 (155%)
       - Family of 4: $174,500 (125%) / $216,000 (155%)
       - Family of 5: $202,000 (125%) / $250,500 (155%)
       - Family of 6: $230,000 (125%) / $285,000 (155%)
     - ⚠️ **Note:** Family of 11 shows $156,500 at 125% in the official table — this appears to be a typo. Verify with WSOS before implementation.
   - Source: https://waopportunityscholarship.org/applicants/grd/#Eligibility (Financial Need); https://waopportunityscholarship.org/wp-content/uploads/2025/12/GRD-C7-MFI-Chart-1-1.pdf (Official 2026 WSOS GRD MFI Chart)

3. **Applicant is currently enrolled as a student in an eligible nurse practitioner graduate program (DNP or MSN) at an eligible institution** ⚠️ *partial data gap*
   - Screener fields:
     - `student` (screener asks whether someone is a student — use as a proxy for enrollment)
   - Note: GRD is limited to specific nurse practitioner specialties at specific Washington universities:
     - Eligible specialties: AGNP (primary care), FNP, PMHNP, PNP (primary care)
     - Eligible universities: Gonzaga University, Pacific Lutheran University, Seattle University, UW Seattle, Washington State University (WSU Spokane, WSU Tri-Cities, WSU Vancouver, WSU Yakima)
     - The screener captures student status (`student` field) but not program type, specialty, or institution. Student status is checkable; program type and institution are not.
     - **Inclusivity assumption:** Assume any student respondent is enrolled in an eligible program and institution.
     - **Suggested improvement:** Add a field asking what type of program the applicant is in. If they select a graduate health care path, trigger GRD-specific follow-up questions about specialty and institution.
   - Source: https://waopportunityscholarship.org/applicants/grd/#Eligibility (Education Plan)

4. **Applicant has completed at least one semester or two quarters in their program** ⚠️ *data gap*
   - Screener fields: none
   - Note: Ensures applicants are already progressing through their program. Not captured in screener.
     - **Inclusivity assumption:** assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested improvement:** Add a GRD-specific follow-up question asking how many semesters or quarters the applicant has completed, only shown if they indicate they are a student in a graduate health care program.
   - Source: https://waopportunityscholarship.org/applicants/grd/#Eligibility (Education Plan)

5. **Applicant has at least 75% of required clinical hours remaining** ⚠️ *data gap*
   - Screener fields: none
   - Note: Ensures funding is used during the majority of training. Not captured in screener.
     - **Inclusivity assumption:** assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested improvement:** Add a GRD-specific follow-up question on clinical hours remaining, only shown if they indicate they are a student in a graduate health care program.
   - Source: https://waopportunityscholarship.org/applicants/grd/#Eligibility (Education Plan)

6. **Applicant is enrolled full-time (DNP) or part-time (MSN) and in good academic standing** ⚠️ *data gap*
   - Screener fields: none
   - Note: Academic standing and enrollment intensity are required but not captured in screener.
     - **Inclusivity assumption:** assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested improvement:** Add GRD-specific follow-up questions on enrollment status and academic standing, only shown if they indicate they are a student in a graduate health care program.
   - Source: https://waopportunityscholarship.org/applicants/grd/#Eligibility (Education Plan)

7. **Applicant intends to practice in a Washington MUA or HPSA for at least 2 years after graduation** ⚠️ *data gap*
   - Screener fields: none
   - Note: Key service commitment requirement. Not captured in screener.
     - **Inclusivity assumption:** assume intent is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Description note:** The current config description says "After graduation, you must plan to work in an underserved area in Washington" but does not mention the 2-year minimum. Consider updating to "After graduation, you must plan to work in an underserved area in Washington for at least two years" to ensure applicants are fully aware of the commitment before applying.
     - **Suggested improvement:** Add a GRD-specific follow-up asking whether the applicant plans to practice in a Washington MUA or HPSA for at least two years after graduation, only shown if they indicate they are a student in a graduate health care program.
   - Source: https://waopportunityscholarship.org/applicants/grd/#Eligibility (Post-Degree Plan; "Intend to practice in a Washington state MUA or HPSA for at least two years after program completion.")

---

## Non-Eligibility Items (Administrative / Application Requirements)

These items appear in the program rules but are application requirements, not eligibility criteria. They should be surfaced in the program description, documents list, or application guidance rather than used in eligibility logic:

- **FAFSA or WASFA submission:** Required application step. Already captured in documents list.
- **Federal Education Tax Credits:** Compliance requirement, not an eligibility factor.
- **Application materials** (essays, unofficial transcript, recommendation form): Application requirements. Already captured in documents list.
- **Application deadlines:** Timing factor, not eligibility. Should be shown in application guidance or results page.

---

## Priority Criteria

These factors affect selection priority but not eligibility:

- Applicants at or below 125% MFI receive automatic consideration; applicants between 126–155% MFI must demonstrate financial hardship
- The Board of Directors determines final selection criteria, which vary year to year
- Demonstrated commitment to practicing in Washington state underserved areas is valued in selection

---

## Benefit Value

**Award structure (citable figures from program page):**
- Up to $25,000 total over 3 years
- Maximum $6,250 per term (citable figure from program page)
- Funding is divided evenly across remaining academic terms starting the fall after selection
- Award is applied after other financial aid, up to Cost of Attendance (COA)
- Can cover tuition, fees, housing, transportation, and other eligible costs

**Travel stipend:**
- Additional $500 per term if training at a remote MUA or HPSA site
- Not included in the lump sum benefit value estimate

**Recommended methodology:**
- Return **$25,000** as a lump sum value (`value_format: "lump_sum"`)
- This is a citable figure directly from the program page
- Actual award depends on cost of attendance, remaining program duration, and other financial aid already applied
- Source: https://waopportunityscholarship.org/applicants/grd/ (Graduate Scholarship 101; "The scholarship provides up to $25,000, up to Cost of Attendance (COA)...Funding does not exceed $6,250 per term.")

---

## Test Scenarios

### Scenario 1: Clearly Eligible — WA Student Below 125% MFI
**What's being tested:** Baseline eligibility — WA student with income well below the 125% MFI threshold for 1 person ($90,500/year). All screener-checkable criteria met.
**Expected:** Eligible, value: $25,000

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$4,000`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Primary regression test confirming the standard eligible case.

---

### Scenario 2: Clearly Ineligible — Not a Student
**What's being tested:** Applicant is not a student. GRD requires current enrollment in an eligible graduate program — this is the primary screener-checkable gate after residency.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `No`, Has income: `Yes`, Income type: `Wages`, Income amount: `$4,000`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms student status is a required gate for GRD eligibility.

---

### Scenario 3: Clearly Ineligible — Income Above 155% MFI
**What's being tested:** Single-person household with income above the 155% MFI upper cutoff ($112,500/year = $9,375/month). Should be screened out entirely regardless of hardship.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$10,000`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms applicants above the 155% MFI upper cutoff are correctly screened out.

---

### Scenario 4: Edge Case — 3-Person Household at Exactly the 125% MFI Boundary
**What's being tested:** 3-person household with income exactly at the 3-person 125% MFI threshold ($146,500/year = $12,208/month, rounded). Tests both the `<=` inclusive comparison and household size scaling together. Note: $146,500 ÷ 12 = $12,208.33, rounded down to $12,208.
**Expected:** Eligible, value: $25,000

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `3`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$12,208`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1992` (age 34), Has income: `No`, Insurance: `None`
- **Person 3 (Child):** Relationship: `Child`, Birth month/year: `June 2022` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the 125% MFI threshold is inclusive and scales correctly with household size — two dimensions tested in one scenario. Matches the JSON validation edge case.

---

### Scenario 5: Eligible (Conditional) — Income in Expanded 126–155% MFI Range, Single Person
**What's being tested:** Single-person household with income above 125% MFI ($7,542/month) but below 155% MFI ($9,375/month). Since the screener cannot verify hardship, the program is shown — but eligibility is conditional on the applicant demonstrating financial hardship during the application.
**Expected:** Eligible, value: $25,000 (calculator returns `eligible: true` — UI must surface hardship caveat clearly)

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$8,500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms applicants in the expanded eligibility range see the program rather than being incorrectly screened out at 125%. The UI must surface the hardship caveat clearly — the screener cannot verify actual eligibility for this group.

---

### Scenario 6: Eligible (Conditional) — 3-Person Household in Expanded 126–155% MFI Range
**What's being tested:** 3-person household with income above the 3-person 125% MFI threshold ($12,208/month, $146,500/year) but below the 3-person 155% MFI threshold ($15,125/month, $181,500/year). Eligibility is conditional on demonstrating hardship. Income $13,000/month ($156,000/year) lands inside the 126–155% MFI band for a 3-person household.
**Expected:** Eligible, value: $25,000 (calculator returns `eligible: true` — UI must surface hardship caveat clearly)

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `3`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$13,000`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1992` (age 34), Has income: `No`, Insurance: `None`
- **Person 3 (Child):** Relationship: `Child`, Birth month/year: `June 2022` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the hardship path applies correctly for multi-member households — the screener shows the program but cannot confirm final eligibility. The UI must surface the hardship caveat.

---

### Scenario 7: Clearly Ineligible — Large Household, Income Above Scaled 155% MFI
**What's being tested:** 3-person household with income above the 3-person 155% MFI threshold ($181,500/year = $15,125/month).
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `3`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$16,000`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1992` (age 34), Has income: `No`, Insurance: `None`
- **Person 3 (Child):** Relationship: `Child`, Birth month/year: `June 2022` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms that a large household above their scaled 155% threshold is correctly screened out — no hardship path applies above 155% MFI.
