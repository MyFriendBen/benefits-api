# Implement Promise Act (KS) Program

## Program Details

- **Program**: Kansas Promise Scholarship Act
- **State**: KS
- **White Label**: ks
- **Calculator Type**: MFB Custom
- **Linear Ticket**: MFB-1073
- **Research Date**: 2026-06-30

## Eligibility Criteria

1. **Kansas residency**
   - Screener fields: `county`, `zipcode`
   - Source: [Kansas Promise Scholarship Act — Program Overview & Eligibility (KBOR)](https://www.kansasregents.gov/students/student_financial_aid/promise-act-scholarship)

2. **Qualifying educational history** — applicant must meet ONE of the following:
   - Graduated from a Kansas public or private high school within the preceding 12 months, OR
   - Attended a Kansas public or private high school and received a GED or other Kansas
     high school equivalency credential within the preceding 12 months, OR
   - Has been a Kansas resident for three or more consecutive years immediately preceding
     the scholarship application, OR
   - Is a dependent child of a military servicemember **permanently** stationed in another state who,
     within the preceding 12 months, graduated from an out-of-state high school or
     obtained a GED or other high school equivalency credential, OR
   - Has been in the custody of the Secretary for Children and Families at any time while
     enrolled in and attending any of grades 9–12, and is NOT eligible for the waiver
     benefit under the Kansas Foster Child Educational Assistance Act

   ⚠️ **Data gap** — Screener fields: none. The screener does not capture educational
   history, graduation date, length of Kansas residency, military dependent status, or
   foster care history. For the calculator, we assume all households meet the qualifying
   educational history requirement (inclusivity assumption). The program description
   should note that applicants must meet one of these educational history requirements.

   Source: [Kansas Promise Scholarship Act — Program Overview & Eligibility
   (KBOR)](https://www.kansasregents.gov/students/student_financial_aid/promise-act-scholarship);
   [Kansas Promise Scholarship Act FAQ, May 2025 (KBOR), Q1](https://www.kansasregents.gov/resources/PDF/Students/Student_Financial_Aid/Kansas_Promise_Scholarship_Act_FAQ_May_2025.pdf)
   — confirms all 5 pathways verbatim; [KBOR Annual Report to 2026 Legislature](https://www.kansasregents.gov/resources/PDF/Legislative_Reports/2026/KBOR_Promise_Act_Scholarship_Report_to_2026_Legislature.pdf)
   — confirms foster care restriction as "not eligible for the waiver benefit under the
   Kansas Foster Child Educational Assistance Act";
   [K.A.R. 88-9a-1 et seq.](https://www.kansasregents.gov/about/rules-regulations/promise-scholarship-rules-regulations?showall=1)

3. **Household income at or below the income limit**

   | Household size | Income limit |
   |---|---|
   | 1–2 | $100,000 |
   | 3 | $150,000 |
   | 4+ | $150,000 + $4,800 per member beyond 3 |

   - Screener fields: `household_size`, all income streams (employment, self-employment,
     SSI, SSDI, etc.)
   - Note: Per FAQ Q17, the program measures income against **adjusted gross income (AGI)**
     from the FAFSA, not total gross income. The screener uses gross income (pre-deductions),
     which may be higher than AGI — meaning some households shown as over the limit may
     actually qualify. This is a conservative screening gap, not an inclusivity gap; the
     description should note that users near the income limit should apply.
   - Source: [Kansas Promise Scholarship Act — Program Overview & Eligibility
     (KBOR)](https://www.kansasregents.gov/students/student_financial_aid/promise-act-scholarship);
     [K.S.A. 74-32,274](https://www.kslegislature.gov/li/b2025_26/statute/074_000_0000_chapter/074_032_0000_article/074_032_0274_section/074_032_0274_k/):
     "household income of one hundred thousand dollars or less for a family of one or
     two; one hundred fifty thousand dollars or less for a family of three; or for
     household sizes above three, a household income that is equal to or less than the
     family of three amount plus four thousand eight hundred dollars for each additional
     family member"; [Kansas Promise Scholarship Act FAQ, May 2025 (KBOR), Q1 and
     Q17](https://www.kansasregents.gov/resources/PDF/Students/Student_Financial_Aid/Kansas_Promise_Scholarship_Act_FAQ_May_2025.pdf)

4. **Enrolled in a KBOR-approved program at an eligible Kansas institution** — eligible
   institutions are Kansas public community colleges, Kansas technical colleges, Washburn
   Institute of Technology, and certain Kansas private independent institutions that offer
   a promise-eligible program (per [K.S.A. 74-32,271(b)(1)(C)](https://www.kslegislature.gov/li/b2025_26/statute/074_000_0000_chapter/074_032_0000_article/074_032_0271_section/074_032_0271_k/)); the program must be in a
   KBOR-designated high-demand field. Note: Kansas public four-year institutions (state
   universities, Washburn University) are NOT eligible, and no private for-profit institutions
   are eligible.

   ⚠️ **Data gap** — Screener fields: none. The screener does not capture institution
   type, program of study, or KBOR program approval status. For the calculator, we assume
   all households are enrolled in an eligible program at an eligible institution
   (inclusivity assumption). The program description should note that applicants must be
   enrolled in a KBOR-approved program at a Kansas community college, technical college,
   Washburn Institute of Technology, or qualifying private institution.

   Source: [Kansas Promise Scholarship Act — Program Overview & Eligibility
   (KBOR)](https://www.kansasregents.gov/students/student_financial_aid/promise-act-scholarship);
   [Kansas Promise Scholarship Act FAQ, May 2025 (KBOR), Q3](https://www.kansasregents.gov/resources/PDF/Students/Student_Financial_Aid/Kansas_Promise_Scholarship_Act_FAQ_May_2025.pdf);
   [K.A.R. 88-9a-1 et seq.](https://www.kansasregents.gov/about/rules-regulations/promise-scholarship-rules-regulations?showall=1)

**Note on citizenship:** US citizenship is required but is handled at the config level
via `legal_status_required: ["citizen"]`. It is not listed as an eligibility criterion
here because it is enforced before the calculator runs.

**Note on excluded requirements:** FAFSA completion, minimum 6-credit-hour enrollment,
satisfactory academic progress, 36-month completion timeline, and post-graduation service
commitment are administrative or ongoing compliance requirements, not initial eligibility
criteria, and are not listed here.

## Priority Criteria

None identified for this program.

## Benefit Value

**Benefit type:** Last-dollar scholarship

**What it covers:** Tuition, required fees, and required books/materials at an eligible
Kansas 2-year institution, minus all other non-repayable financial aid the student
receives (grants, scholarships, and any other aid that does not require repayment).
Repayable aid such as loans does not reduce the scholarship amount.

**Screener limitation:** The screener does not capture which institution the student
attends, how many credit hours they are enrolled in, or what other financial aid they
receive. For the calculator, we estimate the benefit using the statewide average
in-district tuition + required fees across Kansas community colleges at full-time
enrollment (30 credit hours/year). We do not deduct other aid, as that figure is
unavailable to the screener — this is an inclusivity assumption. The estimated value
represents what a full-time student with no other financial aid would receive.

**Estimated annual benefit: $3,960**

- Derived from: $132/credit hour (statewide average in-district tuition + required fees
  across all 19 Kansas community colleges, AY 2026) × 30 credit hours/year
- Rate range across community colleges: $101/credit hour (Johnson County CC) to
  $175/credit hour (Highland CC)
- Source: KBOR Community College Data Book, January 2026, Table 2.10 — In-District
  Tuition and Required Fees per Credit Hour, AY 2021–2026.
  https://www.kansasregents.gov/resources/PDF/Data/Community_College_Data_Books/Community_College_Data_Book_2026_FINAL.pdf

**Notes:**
- This estimate covers tuition and required fees only. The scholarship also covers
  required books and materials; that component is excluded from this estimate as no
  official systemwide average is available.
- Students at Kansas technical colleges may receive a higher benefit. The AY 2026
  resident average across all 7 technical colleges (including Washburn Institute of
  Technology) is **$198/credit hour** (~$5,940/year at 30 credit hours) — exact average
  $197.71/credit hour across all 7 institutions. Rate range: $135/credit hour (WSU-CAST)
  to $245/credit hour (Manhattan Area Technical College).
  Source: KBOR Technical College Data Book, January 2026, Table 2.10 — Resident Tuition
  and Required Fees per Credit Hour, AY 2021–2026 (verified 2026-07-01).
  https://www.kansasregents.gov/resources/PDF/Data/Technical_College_Data_Books/Technical_College_Data_Book_2026_FINAL.pdf
- Because this is a last-dollar scholarship, a student with other non-repayable aid will
  receive a smaller actual benefit. The $3,960 estimate represents the full tuition +
  fees cost before other aid is applied — the maximum for a student with no other
  assistance.
- The program has a **lifetime cap of $20,000 or 68 credit hours**, whichever is reached
  first (per KBOR program page, verified 2026-07-01). At 30 credit hours/year and
  $132/credit hour, the lifetime dollar cap is reached after approximately $20,000 in
  cumulative awards (~152 credit hours at that rate, so the 68-credit-hour limit binds
  first for most students). The screener cannot capture prior Promise Act receipt, so
  this estimate does not account for remaining lifetime benefit — inclusivity assumption.
- Display as `estimated_annual`.

## Implementation Coverage

- Evaluable criteria: 2 (Kansas residency via location fields; household income via
  income streams + household size)
- Data gaps: 2 (qualifying educational history; enrollment in KBOR-approved program at
  eligible institution)

## Research Sources

1. [Kansas Promise Scholarship Act — Program Overview & Eligibility (KBOR)](https://www.kansasregents.gov/students/student_financial_aid/promise-act-scholarship)
2. [Kansas Promise Scholarship Administrative Rules & Regulations (K.A.R. 88-9a-1 et seq.)](https://www.kansasregents.gov/about/rules-regulations/promise-scholarship-rules-regulations?showall=1)
3. [Kansas Promise Scholarship Act — Frequently Asked Questions (May 2025, KBOR)](https://www.kansasregents.gov/resources/PDF/Students/Student_Financial_Aid/Kansas_Promise_Scholarship_Act_FAQ_May_2025.pdf)
4. [Kansas Promise Act Scholarship — KBOR Annual Report to the 2026 Legislature](https://www.kansasregents.gov/resources/PDF/Legislative_Reports/2026/KBOR_Promise_Act_Scholarship_Report_to_2026_Legislature.pdf)
5. [K.S.A. 74-32,274 — Kansas Promise Scholarship Act income threshold statute](https://www.kslegislature.gov/li/b2025_26/statute/074_000_0000_chapter/074_032_0000_article/074_032_0274_section/074_032_0274_k/)
6. [KBOR Community College Data Book, January 2026, Table 2.10 — In-District Tuition and Required Fees per Credit Hour](https://www.kansasregents.gov/resources/PDF/Data/Community_College_Data_Books/Community_College_Data_Book_2026_FINAL.pdf)

## Acceptance Criteria

- [ ] Scenario 1 (Clearly Eligible — Golden Path): User should be **eligible** with **$3,960/year**
- [ ] Scenario 2 (1-Person Household at $100,000 Income Limit): User should be **eligible** with **$3,960/year**
- [ ] Scenario 3 (1-Person Household Just Over $100,000 Income Limit): User should be **ineligible**
- [ ] Scenario 4 (3-Person Household at $150,000 Income Limit): User should be **eligible** with **$3,960/year**
- [ ] Scenario 5 (3-Person Household Just Over $150,000 Income Limit): User should be **ineligible**
- [ ] Scenario 6 (4-Person Household at Extended Formula Limit — $154,800): User should be **eligible** with **$3,960/year**
- [ ] Scenario 7 (4-Person Household Just Over Extended Formula Limit): User should be **ineligible**

## Test Scenarios

### Scenario 1: Clearly Eligible Kansas Resident — Golden Path
**What we're checking**: A single Kansas adult with income well below the $100,000 limit
is shown as potentially eligible. Primary regression test.
**Expected**: Eligible — $3,960/year

**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `1`
* Person 1: Birth month/year `March 2004` (age 22), `headOfHousehold`, wages: $3,750/month (~$45,000/year)

**Why this matters**: Validates the basic happy path — a typical college-age Kansas
resident with modest income is surfaced as potentially eligible. If this fails, something
is fundamentally broken.

---

### Scenario 2: 1-Person Household at the $100,000 Income Limit
**What we're checking**: A single-adult household at exactly the $100,000 limit is
eligible. Tests that the threshold is "at or below," not "strictly below."
**Expected**: Eligible — $3,960/year

**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `1`
* Person 1: Birth month/year `March 2004` (age 22), `headOfHousehold`, wages: $8,333/month (~$99,996/year, at the $100,000 limit)

**Why this matters**: Confirms the boundary is inclusive. A household at the cap must not
be excluded by an off-by-one implementation.

---

### Scenario 3: 1-Person Household Just Over the $100,000 Income Limit
**What we're checking**: A single-adult household earning just over the $100,000 limit is
ineligible. Primary screen-out case.
**Expected**: Not eligible (no value).

**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `1`
* Person 1: Birth month/year `March 2004` (age 22), `headOfHousehold`, wages: $8,334/month (~$100,008/year, just over the $100,000 limit)

**Why this matters**: Confirms the income cutoff is enforced. Paired with Scenario 2,
this bracket confirms the $100,000 limit is applied precisely for households of 1–2.

---

### Scenario 4: 3-Person Household at the $150,000 Income Limit
**What we're checking**: A 3-person household at exactly the $150,000 limit is eligible.
Tests the second income tier.
**Expected**: Eligible — $3,960/year

**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `3`
* Person 1: Birth month/year `March 1980` (age 46), `headOfHousehold`, wages: $12,499/month (~$149,988/year)
* Person 2: Birth month/year `March 2004` (age 22), `child`, no income
* Person 3: Birth month/year `March 1982` (age 44), `spouse`, no income

**Why this matters**: A developer who hardcodes $100,000 as the flat cap for all
household sizes will fail this scenario.

---

### Scenario 5: 3-Person Household Just Over the $150,000 Income Limit
**What we're checking**: A 3-person household earning just over the $150,000 limit is
ineligible.
**Expected**: Not eligible (no value).

**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `3`
* Person 1: Birth month/year `March 1980` (age 46), `headOfHousehold`, wages: $12,501/month (~$150,012/year)
* Person 2: Birth month/year `March 2004` (age 22), `child`, no income
* Person 3: Birth month/year `March 1982` (age 44), `spouse`, no income

**Why this matters**: Confirms the $150,000 cutoff for 3-person households is enforced.
Paired with Scenario 4.

---

### Scenario 6: 4-Person Household at the Extended Formula Limit ($154,800)
**What we're checking**: A 4-person household at the per-member extended formula limit
($150,000 + $4,800 × 1 additional member = $154,800) is eligible. Tests the formula for
household sizes above 3.
**Expected**: Eligible — $3,960/year

**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `4`
* Person 1: Birth month/year `March 1980` (age 46), `headOfHousehold`, wages: $12,899/month (~$154,788/year, at the $154,800 limit)
* Person 2: Birth month/year `March 2004` (age 22), `child`, no income
* Person 3: Birth month/year `March 1982` (age 44), `spouse`, no income
* Person 4: Birth month/year `March 2006` (age 20), `child`, no income

**Why this matters**: Tests that the $4,800-per-member extension beyond 3 is implemented
correctly. A developer who uses $150,000 as a flat cap for all households of 3+ will fail
this scenario.

---

### Scenario 7: 4-Person Household Just Over the Extended Formula Limit
**What we're checking**: A 4-person household earning just over $154,800 is ineligible.
**Expected**: Not eligible (no value).

**Steps**:

* Location: ZIP `66502`, county `Riley`
* Household size: `4`
* Person 1: Birth month/year `March 1980` (age 46), `headOfHousehold`, wages: $12,901/month (~$154,812/year)
* Person 2: Birth month/year `March 2004` (age 22), `child`, no income
* Person 3: Birth month/year `March 1982` (age 44), `spouse`, no income
* Person 4: Birth month/year `March 2006` (age 20), `child`, no income

**Why this matters**: Confirms the extended formula cutoff is enforced. Paired with
Scenario 6.
