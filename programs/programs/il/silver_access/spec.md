# Implement Silver Access (IL) Program

## Program Details

- **Program**: Silver Access
- **State**: IL
- **White Label**: il
- **Calculator Type**: MFB Custom
- **Research Date**: 2026-06-22

## Program Summary

Silver Access is a **DuPage Health Coalition** program that helps qualifying low-income DuPage County residents pay their **ACA Marketplace health insurance premiums**. It provides **up to $150 per member per month** toward the monthly premium of a Marketplace plan. Silver Access is **not health insurance itself** — it is premium assistance layered on top of a Marketplace plan purchased through Get Covered Illinois.

> Note: This program is frequently confused with **Access DuPage** (a separate DuPage Health Coalition program that connects uninsured residents to low-cost health *services*). Access DuPage is being handled as an Additional Resource, not a calculator. This spec is for Silver Access (premium assistance) only.

## Eligibility Criteria

1. **Must reside in DuPage County, Illinois**
   - Screener fields:
     - `county` (auto-populated from `zipcode`)
   - Source: Silver Access FAQs ("Live in DuPage County, Illinois"); 211 DuPage listing

2. **Household income must be at or below 250% of the Federal Poverty Level (FPL)**
   - Screener fields:
     - `household_size`
     - `income_streams` (sum all members' streams → gross household income)
   - Note: Use the **2026** FPL (matches the `year` field in the config). 2026 250% FPL: HH1 $39,900; HH2 $54,100; HH3 $68,300; HH4 $82,500 (HH FPL × 2.5). Use the income the applicant reports to the Marketplace (gross/MAGI-style). Use `<=` at the boundary.
   - Source: Silver Access FAQs ("Meet income guidelines (below 250% of Federal Poverty level)"); DuPage income guidelines page; HHS/ASPE 2026 Poverty Guidelines (42 U.S.C. § 9902(2))

3. **Must not be enrolled in or eligible for Medicaid or Medicare**
   - Screener fields:
     - `insurance` (per member: `medicaid`, `medicare`)
     - `medicaid` (per-member Medicaid field)
     - `birth_year` + `birth_month` (for the Medicare age-65 test)
   - Note: The program text is "not *qualify* for," so this uses an eligibility reading, not just current enrollment. Exclude a member if **any** of the following is true: (a) they currently report Medicaid or Medicare coverage; (b) MFB's own Medicaid determination finds them Medicaid-eligible (computed in the same screener run, so no added user burden); or (c) they are **age 65 or older** (Medicare-eligible by age). Rationale: a member with a public-coverage path generally cannot claim Marketplace premium tax credits, so Silver Access cannot help them. **Known edge case (accepted):** a lawfully-present immigrant 65+ who is not actually Medicare-eligible (e.g., insufficient work history or <5 years' residence) would be wrongly excluded by the age-65 rule. This is treated as an acceptable rare miss for simplicity; revisit if it proves material.
   - Source: Silver Access FAQs ("NOT qualify for Medicaid or Medicare")

4. **Must be lawfully present — U.S. citizen, Legal Permanent Resident, or DACA recipient**
   - Screener fields:
     - handled at program level via `legal_status_required` (not a per-criterion screener field)
   - Note: Maps to `legal_status_required = ["citizen", "refugee", "gc_5plus", "gc_5less", "otherWithWorkPermission"]`. `citizen` and LPRs (`gc_5plus`/`gc_5less`) map directly to the program's "U.S. citizen / Legal Permanent Resident"; DACA recipients carry work authorization and fall under `otherWithWorkPermission` (the closest MFB bucket — note it also admits other work-authorized lawfully-present statuses, which is acceptable for an inclusivity tool). `refugee` is included: refugees and asylees are lawfully present, can enroll in ACA Marketplace coverage, and can claim the APTC, so they pass the program's "able to enroll in a Marketplace plan" gate and fall within the FAQ's "U.S citizen or legal resident" language. Undocumented residents (`non_citizen`) are excluded: they cannot enroll in Marketplace coverage or claim the APTC, so the benefit cannot reach them.
   - Source: 211 DuPage listing ("U.S. citizen or a Legal Permanent Resident, or DACA recipient"); Silver Access FAQs ("U.S citizen or legal resident")

5. **Must be able to enroll in an ACA Marketplace plan — specifically a Silver or Gold-level plan, using the full Advance Premium Tax Credit (APTC)** ⚠️ *data gap*
   - Screener fields:
     - `none`
   - Note: This is partly an **enrollment action** (choose a Silver or Gold plan, apply your full APTC, enroll through Get Covered Illinois) that a screener cannot verify, and partly a coverage test (the person must not already have other minimum essential coverage such as affordable employer-sponsored insurance, which would make them ineligible for Marketplace premium tax credits). **Handling assumption for the calculator:** treat any household member who is lawfully present (criterion 4), within the income limit (criterion 2), and not excluded under criteria 3 (Medicaid/Medicare) or 6 (employer/VA coverage) as *able to enroll*, and count them toward the benefit. The Silver/Gold-plan + full-APTC requirements are surfaced to the user in the program **description** rather than gated in the screener.
   - Screener improvement considered: **None viable.** Whether someone will enroll in a Marketplace plan, choose a Silver/Gold metal level, and apply their full APTC is a *future enrollment action* the screener cannot observe — there is no question that reliably captures a not-yet-taken action pre-application. No new screener field is recommended; the requirement is handled by the inclusivity assumption above plus description surfacing.
   - Source: Silver Access FAQs ("Be able to enroll in health insurance from The Health Insurance Marketplace", "Have selected a Silver or Gold level plan", "Selected to use ALL of your Advanced Premium Tax Credit")
   - Impact: Medium

6. **Members currently covered by employer or VA health insurance are not counted** ⚠️ *data gap*
   - Screener fields:
     - `insurance` (per member: `employer`, `va`)
   - Note: A member with employer or VA coverage already has minimum essential coverage, generally cannot claim Marketplace premium tax credits, and is almost certainly not buying a Marketplace plan — so showing them as eligible would be a false positive. **Handling assumption:** exclude members who currently report `employer` or `va` coverage from the benefit count. Do **not** try to infer *unenrolled* employer offers — those are unobservable and guessing would over-exclude. Members reporting `none` (about to enroll) or `private` (most likely the Marketplace plan itself) are counted.
   - Screener improvement considered: **None added.** The screenable part — *current* employer/VA coverage — is already captured by the `insurance` field and is used directly to exclude. The only unscreenable piece is whether a member has an *available but unenrolled* employer offer that is affordable minimum essential coverage; a new screener question for this was rejected because households cannot reliably self-report MEC/affordability, it would be invasive, and it would over-exclude. Inclusivity assumption applied (count members who do not currently report employer/VA coverage).
   - Source: This exclusion is **derived** from federal premium-tax-credit rules, not stated verbatim in the Silver Access FAQ (which requires applicants to "Be able to enroll in health insurance from The Health Insurance Marketplace"). Per the IRS, a person enrolled in an employer-sponsored plan that is minimum essential coverage is **not eligible for the Premium Tax Credit, even if the employer plan is unaffordable** — see [IRS, Eligibility for the Premium Tax Credit](https://www.irs.gov/affordable-care-act/individuals-and-families/eligibility-for-the-premium-tax-credit) and [26 CFR § 1.36B-2(c)(3)](https://www.law.cornell.edu/cfr/text/26/1.36B-2). Because Silver Access only assists Marketplace premiums (which require PTC use), members with current employer/VA MEC cannot benefit.
   - Impact: Low

## Priority Criteria

None identified. Silver Access does not rank eligible applicants by any characteristic — enrollment is first-come until member capacity is reached. (Operational details — limited capacity, Open Enrollment timing, enroll-through-Marketplace-first, and the member cost share — are carried in the program `description` in the config, not as eligibility or priority criteria.)

## Benefit Value

- **Shape**: Variable, per-member.
- **Stored/calculated value is ANNUAL.** MFB calculators store and assert an **annual** value; `value_format = null` makes the frontend divide by 12 for monthly display. Silver Access pays **up to $150 per eligible member per month**, so the calculator value is **$1,800 per eligible member per year** ($150 × 12).
- **Methodology**: Household annual benefit = **$1,800 × (number of eligible members)**. The frontend displays this as ~$150 per eligible member per month.
  - "Eligible member" = a household member who satisfies criteria 2–6: within the income limit, lawfully present (citizen/LPR/DACA), not enrolled in/eligible for Medicaid or Medicare, and not covered by employer/VA insurance.
- **Real-world cap (data gap):** actual assistance is capped at the residual premium after APTC (premium minus the member's APTC). The screener does not collect the plan premium or APTC amount, so the calculator **estimates at the $150/member/month cap → $1,800/member/year**. This may overstate the benefit for members whose residual premium is below $150/month. Surface the "up to $150" framing in the description.
- **Display: monthly** via `value_format = null`. The annual value ($1,800/eligible member) is divided by 12 by the frontend and shown as ~$150/member/month. **All scenario expected values below are stated as annual dollar amounts** (the unit the calculator returns and the validation suite asserts).
- Source: Silver Access FAQs ("up to $150 per member per month"); 2026 Silver Access application (JotForm) terms ("assistance of up to $150 per member every month").

## Implementation Coverage

- ✅ Fully evaluable criteria: 4 (county, income ≤250% FPL, Medicaid/Medicare, legal status)
- ⚠️ Data gaps (handled by assumption + description): 2 (able to enroll in Marketplace / Silver or Gold plan + full APTC; current employer/VA coverage)

The core eligibility (geography, income, public-coverage exclusion, lawful presence) is screener-evaluable. The two gaps relate to Marketplace enrollment *actions* and unobservable offers of other coverage. A screener improvement was assessed for each (see the "Screener improvement considered" lines under criteria 5 and 6) and judged non-viable — an unscreenable future action, and an invasive/unreliable self-report of unenrolled MEC, respectively. Both are therefore handled with inclusivity-leaning assumptions, and the Silver/Gold-plan/APTC requirements are communicated to the user in the description.

## Research Sources

- [Silver Access FAQs – DuPage Health Coalition](https://dupagehealthcoalition.org/silver-access/silver-access-faqs/)
- [Silver Access Program Overview – DuPage Health Coalition](https://dupagehealthcoalition.org/silver-access/)
- [211 DuPage County Resource Listing – Silver Access](https://search.211dupage.gov/search/9ccddb8b-3331-5518-a753-7ce6fc864799)
- [Silver Access Income Eligibility Guidelines – DuPage Health Coalition](https://dupagehealthcoalition.org/income-guidelines/)
- [2026 Silver Access Application (JotForm)](https://form.jotform.com/253016629905156) — confirms "$150 per member every month," Silver-or-Gold, full-APTC requirement, DACA/LPR
- [IRS – Eligibility for the Premium Tax Credit](https://www.irs.gov/affordable-care-act/individuals-and-families/eligibility-for-the-premium-tax-credit); [26 CFR § 1.36B-2](https://www.law.cornell.edu/cfr/text/26/1.36B-2) — basis for criteria 3 and 6
- [HHS/ASPE 2026 Federal Poverty Guidelines (42 U.S.C. § 9902(2))](https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines)
- [Get Covered Illinois (state ACA Marketplace)](https://getcovered.illinois.gov/) — enrollment context

## Acceptance Criteria

[ ] Scenario 1 (Eligible single adult, DuPage County): **eligible**, $1,800/year ($150/month)
[ ] Scenario 2 (Income above 250% FPL): **ineligible**
[ ] Scenario 3 (Income exactly at 250% FPL): **eligible**, $1,800/year ($150/month)
[ ] Scenario 4 (Currently enrolled in Medicaid): **ineligible**
[ ] Scenario 5 (Age 67 with Medicare): **ineligible**
[ ] Scenario 6 (Lives outside DuPage County): **ineligible**
[ ] Scenario 7 (Married couple, both eligible): **eligible**, $3,600/year ($300/month)
[ ] Scenario 8 (Mixed household — one eligible adult, others on Medicaid): **eligible**, $1,800/year ($150/month)
[ ] Scenario 9 (Undocumented adult — excluded by legal status): **ineligible**
[ ] Scenario 10 (Adult with employer insurance): **ineligible**
[ ] Scenario 11 (Age 66, no Medicare reported — excluded by age-65 rule): **ineligible**
[ ] Scenario 12 (Medicaid-eligible but not enrolled — excluded by eligibility reading): **ineligible**
[ ] Scenario 13 (Eligible Legal Permanent Resident): **eligible**, $1,800/year ($150/month)
[ ] Scenario 14 (Adult with VA health coverage): **ineligible**

## Test Scenarios

### Scenario 1: Eligible Single Adult in DuPage County (Golden Path)
**What we're checking**: A typical applicant who meets all criteria — DuPage County, income below 250% FPL, lawfully present, no Medicaid/Medicare, planning to enroll in a Marketplace Silver or Gold plan.
**Expected**: Eligible — $1,800/year ($150/month displayed)

**Steps**:
- **Location**: ZIP `60137` (Glen Ellyn), county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: Head of Household, Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$2,500`/month ($30,000/yr ≈ 188% FPL), Health insurance: None (about to enroll in Marketplace), Not enrolled in/eligible for Medicaid, Not eligible for Medicare

**Why this matters**: Baseline happy-path test. One eligible member → $1,800/year ($150/month displayed). (At $30,000/yr the member is above the HH1 Medicaid threshold of $22,025, so criterion 3(b) does not exclude them.)

---

### Scenario 2: Income Above 250% FPL — Ineligible
**What we're checking**: Income test enforced for a single-person household.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$3,500`/month ($42,000/yr), Health insurance: None, Not Medicaid/Medicare

**Why this matters**: $42,000 exceeds the 2026 250% FPL for HH1 ($39,900). Confirms the income ceiling screens the household out.

---

### Scenario 3: Income Exactly at 250% FPL — Eligible
**What we're checking**: Boundary condition; eligibility uses `<=`.
**Expected**: Eligible — $1,800/year ($150/month displayed)

**Steps**:
- **Location**: ZIP `60515` (Downers Grove), county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `September 1981` (age 44), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$3,325`/month ($39,900/yr = exactly 250% FPL HH1), Health insurance: None, Not Medicaid/Medicare

**Why this matters**: Income exactly at the limit must remain eligible (`<=`, not `<`).

---

### Scenario 4: Currently Enrolled in Medicaid — Ineligible
**What we're checking**: Medicaid exclusion.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `September 1988` (age 37), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$1,500`/month ($18,000/yr), Health insurance: Medicaid

**Why this matters**: Silver Access requires applicants not qualify for Medicaid/Medicare; a Medicaid enrollee is excluded even though income and county qualify.

---

### Scenario 5: Age 67 with Medicare — Ineligible
**What we're checking**: Medicare exclusion (no upper age cut-off, but Medicare disqualifies).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `January 1959` (age 67), Citizenship: U.S. Citizen, Has income: Yes, Social Security Retirement income: `$1,400`/month, Health insurance: Medicare

**Why this matters**: A Medicare beneficiary cannot use Marketplace premium assistance; confirms the Medicare exclusion fires.

---

### Scenario 6: Lives Outside DuPage County — Ineligible
**What we're checking**: Geographic restriction to DuPage County.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60601` (Chicago, Cook County), county `Cook`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$2,000`/month, Health insurance: None, Not Medicaid/Medicare

**Why this matters**: Despite meeting income and all other tests, a Cook County resident is outside the service area and must be screened out.

---

### Scenario 7: Married Couple, Both Eligible — Per-Member Value
**What we're checking**: Multi-member value stacking ($1,800/year per eligible member).
**Expected**: Eligible — $3,600/year ($300/month displayed)

**Steps**:
- **Location**: ZIP `60540` (Naperville), county `DuPage`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: Head of Household, Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$2,500`/month, Health insurance: None, Not Medicaid/Medicare
- **Person 2**: Birth month/year: `July 1982` (age 43), Relationship: Spouse, Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$1,500`/month, Health insurance: None, Not Medicaid/Medicare

**Why this matters**: Combined $48,000/yr is below HH2 250% FPL ($54,100) and above the HH2 Medicaid threshold ($29,863), so neither spouse is Medicaid-eligible. Two eligible members → 2 × $1,800 = $3,600/year ($300/month displayed). Confirms per-member stacking.

---

### Scenario 8: Mixed Household — Only Eligible Member Counted
**What we're checking**: Per-member evaluation; household income test uses full household size.
**Expected**: Eligible — $1,800/year ($150/month displayed; one eligible member)

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1985` (age 41), Relationship: Head of Household, Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$4,500`/month ($54,000/yr), Health insurance: None, Not Medicaid/Medicare
- **Person 2**: Birth month/year: `September 1987` (age 38), Relationship: Spouse, Citizenship: U.S. Citizen, Has income: No, Health insurance: Medicaid
- **Person 3**: Birth month/year: `January 2014` (age 12), Relationship: Child, Health insurance: Medicaid

**Why this matters**: Household income ($54,000/yr) is below HH3 250% FPL ($68,300) **and above the HH3 Medicaid threshold ($37,702)**, so Person 1 is not Medicaid-eligible and is counted. Persons 2 and 3 are excluded (on Medicaid). Benefit = 1 × $1,800/year ($150/month displayed). Confirms ineligible members are excluded from the value while still counting toward household size/income. (Note: the original $3,000/month figure put the household *below* the HH3 Medicaid threshold, which would have made Person 1 Medicaid-eligible and the household ineligible — income raised so the scenario tests what it intends.)

---

### Scenario 9: Undocumented Adult — Excluded by Legal Status
**What we're checking**: Program-level `legal_status_required` filter.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1990` (age 36), Citizenship/immigration status: Undocumented / none of the listed statuses, Has income: Yes, Employment income: `$1,800`/month, Health insurance: None

**Why this matters**: Undocumented residents cannot enroll in Marketplace coverage and are excluded by `legal_status_required`. The program should not display as eligible.

---

### Scenario 10: Adult with Employer Insurance — Ineligible
**What we're checking**: Other-coverage exclusion (criterion 6 handling assumption).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$2,800`/month, Health insurance: Employer

**Why this matters**: A member already covered by employer insurance generally cannot claim Marketplace premium tax credits and is not counted for Silver Access. Validates the criterion-6 assumption (confirmed: exclude members currently reporting `employer`/`va` coverage).

---

### Scenario 11: Age 66, No Medicare Reported — Excluded by Age-65 Rule
**What we're checking**: Isolates criterion 3(c) — a member 65+ is treated as Medicare-eligible and excluded **even when they do not report Medicare coverage**. (Distinct from Scenario 5, where age and Medicare coverage both apply.)
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1960` (age 66), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$2,000`/month ($24,000/yr), Health insurance: None (no Medicare reported), Not enrolled in Medicaid

**Why this matters**: Confirms the age-65 Medicare-eligibility rule fires on age alone, without requiring reported Medicare coverage. All other criteria (DuPage, income below 250% FPL, citizen, uninsured, and income above the $22,025 Medicaid threshold) are met, so age is the sole disqualifier.

---

### Scenario 12: Medicaid-Eligible but Not Enrolled — Excluded by Eligibility Reading
**What we're checking**: Isolates criterion 3(b) — a member MFB determines Medicaid-eligible is excluded even though they report no current coverage.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1992` (age 34), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$800`/month ($9,600/yr), Health insurance: None (no Medicaid reported), Not eligible for Medicare

**Why this matters**: At $9,600/yr the member is below Illinois Medicaid's ~138% FPL adult threshold ($22,025/yr for HH1 in 2026), so MFB's own Medicaid determination finds them eligible. Criterion 3 excludes them on the "not *qualify* for Medicaid" reading, even though they report no current coverage. Confirms rule 3(b) fires off MFB's Medicaid result, not just reported enrollment.

---

### Scenario 13: Eligible Legal Permanent Resident — Non-Citizen Lawful Status Counted
**What we're checking**: Confirms a lawfully-present non-citizen (LPR) passes the `legal_status_required` filter and is counted for the benefit.
**Expected**: Eligible — $1,800/year ($150/month displayed)

**Steps**:
- **Location**: ZIP `60515` (Downers Grove), county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1984` (age 42), Immigration status: Legal Permanent Resident (green card, 5+ years), Has income: Yes, Employment income: `$2,200`/month ($26,400/yr), Health insurance: None (about to enroll in Marketplace), Not Medicaid/Medicare

**Why this matters**: $26,400/yr is above Illinois Medicaid's adult threshold ($22,025, so not excluded by criterion 3) and below 250% FPL ($39,900). A green-card holder maps to `gc_5plus`, which is in `legal_status_required`, so the program displays and the member is counted → $1,800/year ($150/month displayed). Proves the non-citizen lawful statuses — not just citizens — are admitted and valued.

---

### Scenario 14: Adult with VA Health Coverage — Ineligible
**What we're checking**: Other-coverage exclusion (criterion 6), **VA branch** — companion to Scenario 10 (employer), confirming the exclusion fires on `va` coverage too, not only `employer`.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `60137`, county `DuPage`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 1986` (age 40), Citizenship: U.S. Citizen, Has income: Yes, Employment income: `$2,800`/month ($33,600/yr), Health insurance: VA

**Why this matters**: At $33,600/yr the member is above the HH1 Medicaid threshold ($22,025) and below 250% FPL ($39,900), and is a citizen in DuPage — so VA coverage is the *sole* disqualifier. A member with VA health coverage already has minimum essential coverage and generally cannot claim Marketplace premium tax credits, so they are not counted for Silver Access. Validates the criterion-6 `va` exclusion in isolation.

---

## Source Documentation

- https://dupagehealthcoalition.org/silver-access/silver-access-faqs/
- https://dupagehealthcoalition.org/silver-access/
- https://search.211dupage.gov/search/9ccddb8b-3331-5518-a753-7ce6fc864799
- https://dupagehealthcoalition.org/income-guidelines/
- https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- https://getcovered.illinois.gov/
