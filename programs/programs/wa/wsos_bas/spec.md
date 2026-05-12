# Washington State Opportunity Scholarship (WSOS) — BaS Track Implementation Spec

**Program:** `wa_wsos_bas`  
**State:** Washington  
**White Label:** `wa`  
**Research Date:** 2026-05-05  
**Self-review update:** 2026-05-06

---

## Eligibility Criteria

1. **Applicant is a Washington state resident** ⚠️ *partial data gap*
   - Screener fields:
     - `zipcode`
     - `county`
   - Note: BaS requires Washington residency, and the screener can verify current Washington location through ZIP code and county. The screener cannot verify any residency-duration requirement, such as living in Washington for one year before starting college.
     - **Proxy assumption:** Use current Washington ZIP/county as the calculator proxy for residency.
     - **Application-stage verification:** Any longer residency-duration requirement is verified during the WSOS application process.
     - WSOS explicitly accepts undocumented applicants — no immigration status restriction applies.
     - **Suggested screener refinement:** Only ask this as a BaS-specific follow-up after the user indicates they are pursuing or planning to pursue a STEM or health care program at a Washington college or university.
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Residency)

2. **Household income is at or below 125% of Washington State Median Family Income (MFI) for household size** ⚠️ *partial data gap*
   - Screener fields:
     - `income_streams` (amount and frequency across all household members)
     - `household_size`
   - Note: BaS uses a single income threshold of 125% MFI — no expanded/hardship-based tier like the GRD track.
   - The official MFI chart is based on 2024 family income for the 2026 cycle. The screener uses current pre-tax household income as a proxy for this income test.
   - **Proxy assumption:** Use current MFB household income as an approximate proxy for WSOS family income. This may over- or under-estimate eligibility if the applicant’s 2024 family income differs from their current income.
     - **Implementation note:** Use the official WSOS MFI chart for all household sizes published in the chart. Do not silently extrapolate or “correct” the family-of-11 value without WSOS confirmation.
     - 2026 MFI thresholds (verified against official WSOS Baccalaureate MFI Chart, applies to 2024 family income):
       - Family of 1: $90,500
       - Family of 2: $118,000
       - Family of 3: $146,500
       - Family of 4: $174,500
       - Family of 5: $202,000
       - Family of 6: $230,000
     - ⚠️ **Note:** Family of 11 shows $156,500 in the official table — this appears to be a typo (out of sequence with surrounding values). Same typo appears in the GRD MFI chart. Worth flagging to WSOS once across all WSOS programs rather than per-program.
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Financial Need); https://waopportunityscholarship.org/wp-content/uploads/2025/10/Baccalaureate-C15-MFI-Chart.pdf (Official 2026 WSOS Baccalaureate MFI Chart)

3. **Applicant is currently a student or planning to enroll as a student in an eligible STEM or health care major at an eligible Washington college/university** ⚠️ *partial data gap*
   - Screener fields:
     - `student` (screener asks whether someone is a student — use as a proxy for current/intended enrollment)
   - Note: BaS is limited to specific STEM and health care majors at eligible WA institutions. The screener captures student status but not intended enrollment, major, or institution.
     - Eligible majors list: https://waopportunityscholarship.org/baccalaureate-eligible-majors-list/
     - Eligible institutions list: https://waopportunityscholarship.org/baccalaureate-eligible-institutions-list/
     - **Inclusivity assumption:** Assume any student respondent is enrolled in (or planning to enroll in) an eligible major at an eligible institution.
     - BaS is open to applicants who have not yet started college, so `student` alone is an imperfect proxy. A student who plans to enroll but does not currently consider themselves a student could be missed.
     - **Suggested screener refinement:** Add education-plan questions for scholarship programs:
       - “Are you currently enrolled, admitted, or planning to enroll in college?”
       - “Which college or university do you attend or plan to attend?” using the BaS eligible-institutions list.
       - “What is your intended or declared major / field of study?” using the BaS eligible-majors list.
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Education plan)

4. **Applicant has not yet earned a bachelor's degree** ⚠️ *data gap*
   - Screener fields: none
   - Note: BaS funds students working toward their *first* bachelor's degree. Not captured in screener.
     - **Inclusivity assumption:** Assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested screener refinement:** Add a “highest education level completed” dropdown with options such as “high school credential/GED,” “some college, no degree,” “associate degree,” and “bachelor's degree or higher.” This would also help CTS/BaS-style scholarship programs.
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Previous education)

5. **Applicant has earned, or will earn by June of the application year, a Washington state high school credential (or passing GED scores)** ⚠️ *data gap*
   - Screener fields: none
   - Note: BaS requires a Washington HS credential or passing GED. Not captured in screener — and importantly stricter than CTS, which does not require the credential to be from a Washington institution.
     - Passing GED scores: 45 (1988 series), 450 (2002 series), or 145 (2014 series).
     - **Inclusivity assumption:** Assume requirement is met for all student respondents who indicate WA residency. Devs should add a comment in the calculator noting this assumption.
     - **Suggested screener refinement:** Add a student/education follow-up asking whether the applicant has earned, or will earn by June of the application year, a high school diploma or GED, and whether it was earned in Washington State.
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Previous education)

6. **Cumulative GPA of at least 2.75 (on a 4.0 scale) or passing GED score** ⚠️ *data gap*
   - Screener fields: none
   - Note: Verified via transcript at application. Not captured in screener.
     - **Inclusivity assumption:** Assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested screener refinement:** Add an optional scholarship follow-up asking for most recent cumulative GPA, with an option like “I do not have a GPA / GED path.” This may add friction, so use only if scholarship screening becomes a priority.
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Previous education)

7. **Applicant has not earned more than 90 quarter or 60 semester credits since high school graduation (Running Start and other dual-credit high school program credits do NOT count)** ⚠️ *data gap*
   - Screener fields: none
   - Note: BaS is intended for students relatively early in their college path. Credits earned through Running Start or other dual-credit programs are excluded from this count. Not captured in screener.
     - **Inclusivity assumption (silent):** Assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - Per user direction: this constraint is NOT surfaced in the user-facing description. Applicants who have already exceeded the credit ceiling will be incorrectly shown the program; this is acceptable given the dev-only handling pattern chosen here.
     - **Suggested screener refinement:** If MFB later supports education-specific screening, add a credits-completed question that separates college credits earned after high school from Running Start / dual-credit credits earned during high school.
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Previous education)

8. **Applicant plans to enroll in at least three credits every fall, winter, and spring term** ⚠️ *data gap*
   - Screener fields: none
   - Note: Minimum enrollment for BaS funding. Not captured in screener.
     - **Inclusivity assumption:** Assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested screener refinement:** Add a scholarship-program follow-up asking expected credits per fall/winter/spring term, or a simpler yes/no question: “Do you plan to take at least 3 credits each fall, winter, and spring term?”
   - Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Education plan)

---

## Non-Eligibility Items (Administrative / Application Requirements)

These items appear in the program rules but are application requirements, not eligibility criteria. They should be surfaced in the program description, documents list, or application guidance rather than used in eligibility logic:

- **FAFSA or WASFA submission:** Required application step. Already captured in documents list.
- **Federal Education Tax Credits:** Apply if eligible — compliance requirement, not an eligibility factor.
- **Application materials** (essays, unofficial transcript): Application requirements. Already captured in documents list. BaS notably does NOT require recommendation forms or references.
- **Application deadlines:** Timing factor, not eligibility. Should be shown in application guidance or results page. (2026 cycle: opens Jan 14, deadline Feb 26 at 9 p.m. PST; acceptance deadline May 6 at 9 p.m. PST.)

---

## Priority Criteria

These factors affect selection priority but not eligibility:

- The Board of Directors determines final selection criteria, which include factors such as financial need, commitment to STEM or health care, and academic achievement.
- Selection criteria can vary year to year.

---

## Benefit Value

**Award structure (citable figures from program page):**
- Up to **$22,500** total in scholarship dollars (lifetime maximum across the program).
- Funding is applied to the applicant's Cost of Attendance (COA) *after* all other financial aid (e.g., Pell Grant, Washington College Grant).
- Can cover tuition, housing, transportation, food, and other eligible costs beyond tuition.
- Per-term/year cap is not specified on the program page (unlike GRD's $6,250 per-term cap).
- If other financial aid covers part or all of COA, some or all of the scholarship funding may be returned to WSOS.

**Recommended methodology:**
- Return **$22,500** as a lump sum value (`value_format: "lump_sum"`).
- This is a citable figure directly from the program page.
- Actual award depends on cost of attendance, remaining program duration, and other financial aid already applied.
- Source: https://waopportunityscholarship.org/applicants/baccalaureate/ (Baccalaureate Scholarship 101; “This program provides up to a total of $22,500 in scholarship dollars...”)

---

## Test Scenarios

### Scenario 1: Clearly Eligible — WA Student Below 125% MFI
**What's being tested:** Baseline eligibility — WA student with income well below the 125% MFI threshold for 1 person ($90,500/year). All screener-checkable criteria met.
**Expected:** Eligible, value: $22,500

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 2006` (age 20), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,000`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Primary regression test confirming the standard eligible case for an undergraduate.

---

### Scenario 2: Clearly Ineligible — Income Above 125% MFI (Single Person)
**What's being tested:** Single-person household with income above the 125% MFI cutoff ($90,500/year ≈ $7,541/month). Should be screened out — BaS has no expanded/hardship path.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `March 2005` (age 21), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$8,000`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms applicants above the 125% MFI cutoff are correctly screened out. This is a stronger validation scenario than a “not a student” case because BaS also covers students planning to enroll.

---

### Scenario 3: Edge Case — 4-Person Household Just Below the 125% MFI Boundary Due to Monthly Rounding
**What's being tested:** 4-person household with income just below the 4-person 125% MFI threshold ($174,500/year). The validation uses `$14,541/month`, which annualizes to `$174,492/year`. This tests household-size scaling and near-boundary eligibility, but not exact equality.
**Expected:** Eligible, value: $22,500

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `4`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1980` (age 46, parent), Has income: `Yes`, Income type: `Wages`, Income amount: `$14,541`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1982` (age 44, parent), Has income: `No`, Insurance: `None`
- **Person 3 (Child — applicant):** Relationship: `Child`, Birth month/year: `September 2008` (age 17), Student: `Yes`, Has income: `No`, Insurance: `None`
- **Person 4 (Child):** Relationship: `Child`, Birth month/year: `June 2012` (age 13), Student: `No`, Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the 125% MFI threshold scales correctly with household size and reflects a typical BaS applicant scenario (high school senior in a family of 4). If the validation system supports annual income frequency, a separate exact-boundary test could use `$174,500/year`.

---

### Scenario 4: Clearly Ineligible — Large Household, Income Above Scaled 125% MFI
**What's being tested:** 4-person household with income above the 4-person 125% MFI threshold ($174,500/year = about $14,541.67/month). `$16,000/month` exceeds this threshold.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `4`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1980` (age 46, parent), Has income: `Yes`, Income type: `Wages`, Income amount: `$16,000`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1982` (age 44, parent), Has income: `No`, Insurance: `None`
- **Person 3 (Child — applicant):** Relationship: `Child`, Birth month/year: `September 2008` (age 17), Student: `Yes`, Has income: `No`, Insurance: `None`
- **Person 4 (Child):** Relationship: `Child`, Birth month/year: `June 2012` (age 13), Student: `No`, Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms a multi-member household above its scaled 125% threshold is correctly screened out.

---

### Scenario 5: Eligible — Mixed Household, Student-as-Head with Non-Student Spouse and Child
**What's being tested:** Returning adult learner (age 28) is the head of household and the BaS applicant. Non-student spouse and young child still count toward household size and income but are not evaluated as the applicant. Income `$4,000/month` (`$48,000/year`) is well below the 3-person 125% MFI cap of `$146,500/year`.
**Expected:** Eligible, value: $22,500

**Steps:**
- **Location:** Enter ZIP code `99201`, Select county `Spokane`
- **Household:** Number of people: `3`
- **Person 1 (Head of Household — applicant):** Relationship: `Head of Household`, Birth month/year: `May 1998` (age 28), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$4,000`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `February 1996` (age 30), Student: `No`, Has income: `No`, Insurance: `None`
- **Person 3 (Child):** Relationship: `Child`, Birth month/year: `October 2021` (age 4), Student: `No`, Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Tests household logic — only the student-as-HoH should be evaluated as the BaS applicant, while the non-student spouse and child still count toward household size and income. Reflects a realistic returning-adult-learner persona pursuing a first bachelor's degree.
