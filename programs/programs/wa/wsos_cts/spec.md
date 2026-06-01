# Washington State Opportunity Scholarship (WSOS) — CTS Track Implementation Spec

**Program:** `wa_wsos_cts`
**State:** Washington
**White Label:** `wa`
**Research Date:** 2026-05-05

---

## Eligibility Criteria

1. **Applicant is a Washington state resident**
   - Screener fields:
     - `zipcode`
     - `county`
   - Note: CTS requires Washington residency. Verified through ZIP code and county in the screener. WSOS explicitly accepts undocumented applicants — no immigration status restriction applies.
   - Source: https://waopportunityscholarship.org/applicants/career-technical/#eligibility (Residency)

2. **Household income is at or below 125% of Washington State Median Family Income (MFI) for household size**
   - Screener fields:
     - `income_streams` (amount and frequency across all household members)
     - `household_size`
   - Note: CTS uses a single income threshold at 125% MFI. Unlike GRD, there is no expanded eligibility tier above 125% MFI.
     - 2026 MFI thresholds (verified against official 2026 WSOS CTS MFI Chart):
       - Family of 1: $90,500 (125%) / $50,500 (RJI 70%)
       - Family of 2: $118,000 (125%) / $66,500 (RJI 70%)
       - Family of 3: $146,500 (125%) / $82,000 (RJI 70%)
       - Family of 4: $174,500 (125%) / $97,500 (RJI 70%)
       - Family of 5: $202,000 (125%) / $113,000 (RJI 70%)
       - Family of 6: $230,000 (125%) / $128,500 (RJI 70%)
     - The 70% MFI column applies only to the Rural Jobs Initiative (RJI) priority — it does not affect base CTS eligibility (see Priority Criteria).
   - Source: https://waopportunityscholarship.org/applicants/career-technical/#eligibility (Financial Need); https://waopportunityscholarship.org/wp-content/uploads/2025/12/2026_CTS-MFI-Chart-1.pdf (Official 2026 WSOS CTS MFI Chart)

3. **Applicant is currently enrolled (or planning to enroll) in an eligible associate degree, certificate, or apprenticeship program at an eligible community/technical college or apprenticeship sponsor** ⚠️ *partial data gap*
   - Screener fields:
     - `student` (screener asks whether someone is a student — used as a proxy for enrollment intent)
   - Note: CTS funds students pursuing associate degrees, certificates, or apprenticeships at Washington community/technical colleges, plus the apprenticeship sponsors AJAC Advanced Manufacturing Apprenticeships and Evergreen Rural Water. The full list of eligible programs is maintained at https://waopportunityscholarship.org/cts-eligible-programs/.
     - The screener captures student status (`student` field) but not program type, credential level, or institution. Student status is checkable; program type and institution are not.
     - **Inclusivity assumption:** Assume any student respondent is enrolled in (or planning to enroll in) an eligible program at an eligible institution.
     - **Existing screener signal:** The student follow-up question "Is the program that you are enrolled in a job training program?" partially relates to apprenticeships, but is broader than the CTS apprenticeship-sponsor list — not sufficient on its own to confirm CTS apprenticeship eligibility.
     - **Suggested improvement:** Add a field asking which institution the applicant attends or plans to attend, paired with a program field capturing program type (associate degree, certificate, apprenticeship). For CTS, validate the institution against the eligible CTC list and the apprenticeship sponsors (AJAC Advanced Manufacturing Apprenticeships, Evergreen Rural Water).
   - Source: https://waopportunityscholarship.org/applicants/career-technical/#eligibility (Education Plan)

4. **Applicant does not have or intend to immediately pursue a bachelor's degree** ⚠️ *data gap*
   - Screener fields: none
   - Note: CTS does not fund students who have already earned a bachelor's degree, nor those who intend to pursue a bachelor's immediately after their CTS-funded program — applicants in either situation should apply for the Baccalaureate Scholarship instead. Scholars who move into a bachelor's program are withdrawn from CTS. **Already having an associate degree does not disqualify the applicant** — per the WSOS "Common eligibility scenarios," an applicant with an associate degree may pursue another eligible associate degree under CTS. The exclusion is bachelor's-specific. The screener does not currently capture highest-education-completed or future degree intent.
     - **Inclusivity assumption:** Assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested improvement:** Add a dropdown for highest education level completed, with options like "earning high school credential this year," "earned high school credential already," "some college, no degree," "associate degree," and "bachelor's degree," so the screener can directly capture this exclusion rule. If "bachelor's degree" is selected, exclude CTS. Optionally pair with a follow-up asking whether the applicant intends to pursue a bachelor's degree immediately after their CTS program.
     - **Description note:** The description should mention this requirement so applicants know to apply for the Baccalaureate Scholarship instead if they plan to pursue a bachelor's.
   - Source: https://waopportunityscholarship.org/applicants/career-technical/#eligibility (Previous Education; Education Plan)

5. **Applicant has earned or will earn a high school credential by June of the application year** ⚠️ *data gap*
   - Screener fields: none
   - Note: A high school diploma or equivalency is required by June of the year of application. Unlike BaS, the CTS credential does not need to be from a Washington institution. Not captured in the screener.
     - **Inclusivity assumption:** Assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Suggested improvement:** Add a dropdown under Student Information for education status — options like "earning high school credential this year" or "earned high school credential already" — so the screener can confirm the applicant has earned (or will earn by June) a high school credential. (Unlike BaS, no follow-up about Washington-state issuance is needed for CTS.)
   - Source: https://waopportunityscholarship.org/applicants/career-technical/#eligibility (Previous Education)

6. **Applicant plans to enroll in at least 3 credits every fall, winter, and spring term** ⚠️ *data gap*
   - Screener fields: none
   - Note: CTS requires at least 3 credits per term to receive any funding (full-time = 12 credits for 100% funding; part-time 3–11 credits is prorated; <3 credits is not funded). Apprenticeship Scholars may be exempt. Not directly captured in the screener.
     - **Inclusivity assumption:** Assume requirement is met for all student respondents. Devs should add a comment in the calculator noting this assumption.
     - **Existing screener signal:** The student follow-up question "Are you enrolled half-time or more in a university, college, or community college as defined by the educational institution?" partially relates to enrollment intensity. A "Yes" response (half-time or more) is typically ≥6 credits, which exceeds the CTS 3-credit minimum. A "No" response could indicate <3 credits (ineligible) *or* 3–5 credits (eligible but prorated) — so it is not sufficient on its own to exclude. The half-time signal could be used as a positive indicator but should not be used to exclude.
     - **Suggested improvement:** Add a CTS-specific follow-up asking how many credits the applicant plans to take per term, only shown if they indicate they are a student pursuing an associate degree or certificate. Allow apprenticeship respondents to bypass this check.
   - Source: https://waopportunityscholarship.org/applicants/career-technical/#eligibility (Education Plan)

---

## Non-Eligibility Items (Administrative / Application Requirements)

These items appear in the program rules but are application requirements, not eligibility criteria. They should be surfaced in the program description, documents list, or application guidance rather than used in eligibility logic:

- **FAFSA or WASFA submission:** Required application step. Captured in documents list.
- **Federal Education Tax Credits:** Compliance recommendation, not an eligibility factor.
- **Short answer responses:** Application requirement (completed in-app, no separate document upload). Application guide linked in documents list.
- **Application deadlines:** Timing factor, not eligibility. Surface in application guidance or warning message.

---

## Priority Criteria

These factors affect selection priority but not base CTS eligibility:

- **Rural Jobs Initiative (RJI) priority:** All CTS applicants are automatically considered. Selection requires:
  - Income at or below 70% MFI for household size (vs. 125% for base CTS)
  - Resident of a Washington county *other than* King, Pierce, Snohomish, Kitsap, Thurston, Clark, Benton, or Spokane — OR — high school graduate from a school district with fewer than 2,000 students
  - Enrolled at one of the rural community/technical colleges listed on the CTS page
  - RJI funding is higher: up to $3,500 first quarter, $2,500 second quarter, $2,000 per quarter thereafter
- The Board of Directors determines final selection criteria using factors including financial need, likelihood to persist, and academic achievement.
- RJI seats are limited and selection is competitive — applicants meeting RJI criteria are not guaranteed RJI funding.

**Implementation note:** RJI is treated as a priority modifier on CTS, not as a separate program in MFB. Surface RJI in the program description so users in rural counties know they may receive higher funding.

---

## Benefit Value

**Award structure (citable figures from program page):**
- Up to **$1,500 per quarter, every quarter**, for the duration of the program (up to 18 terms of state financial aid total)
- Full-time enrollment (12 credits): 100% of funding
- Part-time enrollment (3–11 credits): prorated funding
- Less than 3 credits: not eligible for funding
- Award is applied after other financial aid, up to Cost of Attendance (COA)
- Can cover tuition, fees, housing, transportation, food, and other eligible costs

**RJI award structure (priority — not base CTS):**
- $3,500 first quarter, $2,500 second quarter, $2,000 per quarter thereafter
- Not used in base CTS value since RJI selection is competitive

**Note:** WSOS does not publish a methodology for calculating a per-applicant benefit value. The published figures above are the only citable values; actual award depends on enrollment intensity, cost of attendance, remaining program duration, and other financial aid already applied. The calculator should return `eligible: true/false` without a specific dollar value.

Source: https://waopportunityscholarship.org/applicants/career-technical/ (Career & Technical Scholarship 101; FAQs — "How many terms of funding am I eligible for?")

---

## Test Scenarios

### Scenario 1: Clearly Eligible — WA Student Below 125% MFI
**What's being tested:** Baseline eligibility — WA student with income well below the 125% MFI threshold for 1 person ($90,500/year). All screener-checkable criteria met.
**Expected:** Eligible

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 2002` (age 24), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Primary regression test confirming the standard eligible case for a young CTC student.

---

### Scenario 2: Clearly Ineligible — Not a Student
**What's being tested:** Applicant is not a student. CTS requires current/intended enrollment in an eligible associate, certificate, or apprenticeship program — this is the primary screener-checkable gate after residency.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `No`, Has income: `Yes`, Income type: `Wages`, Income amount: `$3,000`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms student status is a required gate for CTS eligibility.

---

### Scenario 3: Clearly Ineligible — Income Above 125% MFI
**What's being tested:** Single-person household with income above the 125% MFI cutoff ($90,500/year = $7,542/month). Unlike GRD, there is no hardship/expanded path — over 125% MFI means ineligible.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98101`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 2002` (age 24), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$8,000`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the single 125% MFI cap is enforced (no expanded eligibility path like GRD).

---

### Scenario 4: Edge Case — 3-Person Household at Exactly the 125% MFI Boundary
**What's being tested:** 3-person household with income exactly at the 3-person 125% MFI threshold ($146,500/year = $12,208/month, rounded). Tests both the `<=` inclusive comparison and household size scaling together. Note: $146,500 ÷ 12 = $12,208.33, rounded down to $12,208.
**Expected:** Eligible

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `3`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1995` (age 31), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$12,208`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1996` (age 30), Has income: `No`, Insurance: `None`
- **Person 3 (Child):** Relationship: `Child`, Birth month/year: `June 2022` (age 3), Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the 125% MFI threshold is inclusive and scales correctly with household size.

---

### Scenario 5: Eligible — RJI-Likely Candidate (Rural County, Below 70% MFI)
**What's being tested:** A 2-person household with income below the 70% MFI RJI threshold ($66,500/year = $5,541/month) in a rural county (Whatcom). Base CTS eligibility is unchanged from Scenario 1. RJI is a priority/bonus, not a separate eligibility result, so the screener treats this scenario the same as Scenario 1 from a calculator standpoint.
**Expected:** Eligible

**Steps:**
- **Location:** Enter ZIP code `98225`, Select county `Whatcom`
- **Household:** Number of people: `2`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 2003` (age 23), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$3,500`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Parent):** Relationship: `Parent`, Birth month/year: `April 1975` (age 51), Has income: `Yes`, Income type: `Wages`, Income amount: `$1,500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms that base CTS eligibility holds for an RJI-likely candidate. The RJI priority modifier surfaces in the description but does not change the calculator output.

---

### Scenario 6: Clearly Ineligible — Large Household, Income Above Scaled 125% MFI
**What's being tested:** 4-person household with income above the 4-person 125% MFI threshold ($174,500/year = $14,541/month).
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `4`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1990` (age 36), Student: `Yes`, Has income: `Yes`, Income type: `Wages`, Income amount: `$15,000`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1992` (age 34), Has income: `No`, Insurance: `None`
- **Person 3 (Child):** Relationship: `Child`, Birth month/year: `June 2018` (age 7), Has income: `No`, Insurance: `None`
- **Person 4 (Child):** Relationship: `Child`, Birth month/year: `September 2020` (age 5), Has income: `No`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms household size scaling works correctly above the 125% MFI cap for larger households.
