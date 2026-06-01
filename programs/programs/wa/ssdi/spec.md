# Social Security Disability Insurance (SSDI) — Implementation Spec

**Program:** `wa_ssdi`
**State:** Washington
**White Label:** `wa`
**Research Date:** 2026-04-14

---

## Eligibility Criteria

1. **Applicant must have a disability or blindness — a medical condition expected to last at least 12 months or result in death that prevents substantial gainful activity**
   - Screener fields:
     - `long_term_disability` ("Currently have any disabilities that make you unable to work now or in the future")
     - `medical_condition` ("Any medical or developmental condition that has lasted, or is expected to last, more than 12 months")
   - Note: Both screener fields directly map to SSDI's disability definition. Together they serve as a self-reported proxy for SSA's formal disability determination, which requires medical evidence and a 5-step evaluation process. See criterion 7 for the data gap on the full medical determination.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (What We Mean by Disability); https://www.ssa.gov/pubs/EN-05-10029.pdf (Disability Benefits, February 2025), p. 1; 42 U.S.C. § 423(d)(1)(A)

2. **Applicant's current earnings must not exceed the Substantial Gainful Activity (SGA) threshold — $1,690/month for non-blind individuals, $2,830/month for blind individuals (2026 values)**
   - Screener fields:
     - `income_streams` (amount, frequency) — including wages and self-employment
     - `visually_impaired` ("Blind or visually impaired" in Special Circumstances)
   - Note: The 2026 SGA values are $1,690/month (non-blind) and $2,830/month (blind), confirmed at https://www.ssa.gov/benefits/disability/qualify.html. The earnings check should use the `<=` comparison — income exactly at the threshold is still eligible. The screener captures self-employment as an income type and amount, which is sufficient to apply the standard SGA threshold.
   - ⚠️ **Data gap (self-employment SGA detail):** SSA applies special rules for self-employed applicants — either the Three Tests or the Countable Income Test — which require more detail than the screener captures (e.g. hours worked, services rendered to the business, net earnings breakdown).
     - **Inclusivity assumption:** treat self-employed applicants the same as wage earners using the standard SGA threshold.
     - **Suggested improvement:** Add follow-up questions when self-employment is selected as an income type, such as average hours worked per week and whether the applicant renders significant services to the business. This would allow the calculator to flag self-employed applicants for special SGA evaluation and surface a note that their rules may differ and they should contact SSA directly.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How We Decide if You Have a Qualifying Disability); https://www.ssa.gov/pubs/EN-05-10095.pdf (Social Security Work Incentives at a Glance, 2026); https://www.ssa.gov/redbook/eng/definedisability.htm (What is Substantial Gainful Activity); 42 U.S.C. § 423(d)(4)

3. **Applicant must not already be receiving benefits on their own Social Security record**
   - Screener fields:
     - `has_ssdi` (captured in current benefits section — "Social Security Disability Insurance (SSDI)")
   - Note: The screener's current benefits section includes SSDI. Someone already receiving SSDI should not be shown SSDI as a recommendation. Note that receiving SSI does NOT exclude someone from SSDI — concurrent SSI/SSDI receipt is allowed. Additionally, former SSDI recipients whose benefits stopped because they returned to work may be eligible for Expedited Reinstatement within 5 years — they do not need to file a new application and should contact SSA directly.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How Does Someone Become Eligible)

4. **Applicant must not already be receiving Social Security retirement benefits on the same earnings record** ⚠️ *data gap*
   - Screener fields: none
   - Note: Per SSA, a person cannot receive both SSDI and Social Security retirement benefits on the same earnings record simultaneously. At full retirement age, SSDI automatically converts to retirement benefits — this is not a separate application. Social Security retirement is not currently listed as an option in the screener's current benefits section.
     - **Inclusivity assumption:** assume all screener respondents are not already receiving Social Security retirement benefits.
     - **Suggested improvement:** Add "Social Security Retirement" to the current benefits section of the screener so it can be used to screen out applicants already receiving retirement benefits on the same earnings record.
   - Source: https://www.ssa.gov/faqs/en/questions/KA-01861.html ("The law does not allow a person to receive both retirement and disability benefits on one earnings record at the same time."); 42 U.S.C. § 402(a); 42 U.S.C. § 423

5. **Applicant must be of working age — under full retirement age (FRA), which ranges from 66 to 67 depending on birth year**
   - Screener fields:
     - `birth_month`
     - `birth_year`
   - Note: FRA is not a fixed age — it depends on birth year. Born 1943–1954: FRA is 66. Born 1955–1959: FRA increases by 2 months per year. Born 1960 or later: FRA is 67. The calculator must use the SSA birth-year FRA schedule rather than a fixed cutoff. At FRA, SSDI benefits automatically convert to retirement benefits. There is no hard minimum age for SSDI — younger workers simply need fewer work credits (see criterion 6). The screener captures birth month and year, so this criterion is fully checkable.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How Does Someone Become Eligible); 42 U.S.C. § 423(a)(1)(B)

6. **Applicant must have earned sufficient work credits through Social Security-covered employment — generally 40 credits (20/40 Rule), with 20 earned in the last 10 years; younger workers need fewer credits** ⚠️ *data gap*
   - Screener fields: none
   - Note: The screener does not collect work history duration or Social Security work credits. In 2026, one credit equals $1,890 in wages or self-employment income, with a maximum of 4 credits per year ($7,560). SSA verifies credit accumulation from their own earnings records. This criterion also covers the insured status requirement — applicants must generally have worked 5 of the last 10 years before disability onset.
     - Age-based work credit requirements (from SSA Publication No. 05-10029):
       - Before age 28: 1.5 years of work
       - Age 30: 2 years
       - Age 34: 3 years
       - Age 38: 4 years
       - Age 42: 5 years
       - Age 44: 5.5 years
       - Age 46: 6 years
       - Age 50: 7 years
       - Age 60: 9.5 years
       - Age 62 or older: 10 years
     - ⚠️ **Data gap (non-covered jobs):** Not all jobs count toward Social Security credits. Examples include most federal employees hired before 1984, railroad employees with 10+ years of service, and some state and local government employees. The screener cannot determine whether an applicant worked in a covered job.
     - **Inclusivity assumption:** assume all screener respondents have sufficient work credits, were insured at disability onset, and worked in Social Security-covered employment. Devs should add a comment in the calculator noting this assumption. This is the most significant data gap for SSDI eligibility.
     - **Suggested improvement:** Add a general question such as "How many years have you worked and paid into Social Security?" with range options (e.g. less than 5 years, 5–10 years, 10–20 years, 20+ years). This would allow the calculator to use 10+ years as a proxy for the 40-credit requirement without being specific to any one program. Additionally, surface a note in the program description directing users to check their own work credits by logging into their my Social Security account at ssa.gov/myaccount before applying.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How Much Work Do You Need); https://www.ssa.gov/pubs/EN-05-10072.pdf (How You Earn Credits, January 2026); https://www.ssa.gov/pubs/EN-05-10029.pdf (Disability Benefits, February 2025), p. 2–4; 42 U.S.C. § 423(c)(1)

7. **The medical condition must meet SSA's specific 5-step disability determination — inability to engage in any substantial gainful activity due to a medically determinable physical or mental impairment** ⚠️ *data gap*
   - Screener fields:
     - `long_term_disability` ("Currently have any disabilities that make you unable to work now or in the future")
     - `medical_condition` ("Any medical or developmental condition that has lasted, or is expected to last, more than 12 months")
     - `income_streams` (captures SGA — step 1 of the 5-step process)
   - Note: SSA uses a formal 5-step sequential evaluation process that considers listed impairments, residual functional capacity, past relevant work, and ability to do other work. The screener partially captures step 1 (SGA via income streams) and the presence of a qualifying disability via the two Special Circumstances fields, but cannot replicate the full 5-step determination.
     - **Inclusivity assumption:** assume all self-reported disabilities meet SSA's full definition.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How We Decide if You Have a Qualifying Disability); https://www.ssa.gov/pubs/EN-05-10029.pdf (How is the Decision Made), p. 7–8; 20 CFR § 404.1520

8. **Applicant must not be involved with the criminal justice system in a disqualifying way** ⚠️ *data gap*
   - Screener fields: none
   - Note: Benefits cannot be paid for any month in which any of the following apply:
     - Applicant is incarcerated or confined to a public institution after conviction
     - Applicant has an outstanding felony arrest warrant for flight to avoid prosecution, escape from custody, or flight-escape
     - Applicant is violating a condition of parole or probation
     - No field in the screener captures any of these statuses. Adding such questions would feel invasive to users and is not recommended.
     - **Inclusivity assumption:** assume all screener respondents are not in a disqualifying criminal justice situation.
   - Source: 42 U.S.C. § 402(x); https://www.ssa.gov/pubs/EN-05-10029.pdf (What do I need to tell Social Security), p. 11

9. **Disabled Adult Child (DAC) — adults whose disability began before age 22 may qualify on a parent's earnings record** ⚠️ *data gap*
   - Screener fields: none
   - Note: An adult whose disability began before age 22 may be eligible for SSDI on a parent's Social Security earnings record if the parent is deceased or receiving retirement or disability benefits. The DAC must be unmarried, age 18 or older, and have a qualifying disability. The screener does not capture whether a parent is receiving Social Security benefits or whether the applicant's disability began before age 22.
     - **Inclusivity assumption:** this path is not checked in the calculator. The program description notes that some people may qualify through special paths and directs them to contact SSA.
     - **Suggested improvement:** Add a question such as "Do you have a parent who is deceased or currently receiving Social Security benefits?" to flag potential DAC eligibility and direct users to contact SSA directly.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (Adults with a Disability That Began Before Age 22); https://www.ssa.gov/pubs/EN-05-10029.pdf (Can my family get benefits), p. 10

10. **Surviving spouse — surviving spouses ages 50–60 with a disability may qualify on a deceased worker's earnings record** ⚠️ *data gap*
    - Screener fields: none
    - Note: A surviving spouse or surviving divorced spouse between ages 50 and 60 with a qualifying disability that began before or within 7 years of the worker's death may be eligible. The screener does not capture survivor status or the relationship between a disability onset and a spouse's death.
      - **Inclusivity assumption:** this path is not checked in the calculator. The program description notes that some people may qualify through special paths and directs them to contact SSA.
      - **Suggested improvement:** Add a question such as "Are you a surviving spouse of someone who worked and paid into Social Security?" to flag potential surviving spouse eligibility and direct users to contact SSA directly.
    - Source: https://www.ssa.gov/benefits/disability/qualify.html (Benefits for Surviving Spouses With Disabilities); https://www.ssa.gov/pubs/EN-05-10029.pdf (Benefits for Surviving Spouses With Disabilities), p. 5

---

## Priority Criteria

SSDI has no priority criteria — eligibility is an all-or-nothing determination based on the criteria above. There are no tiers, priority groups, or waitlists. All applicants who meet the eligibility criteria receive benefits.

---

## Benefit Value

SSDI benefit amounts are variable — they are based on the applicant's lifetime earnings history, specifically the Average Indexed Monthly Earnings (AIME) calculated from the highest-earning 35 years of covered work. There is no fixed benefit amount.

- SSDI is **not means-tested** — there are no household income limits or asset limits.
- **Average monthly benefit (March 2026):** approximately **$1,634/month** for disabled workers in current payment status — this is a citable figure from SSA's Disabled Worker Average Benefits table.
- **This is the value the calculator will return for eligible households.** Individual benefit amounts vary based on earnings history, so this figure serves as an illustrative estimate with appropriate caveats in the UI.
- Applicants can estimate their individual benefit amount using the SSA's online benefits calculator at https://www.ssa.gov/benefits/retirement/planner/AnypiaApplet.html.

**Recommended calculator methodology:** Return the average monthly benefit of **$1,634** as the estimated value for eligible scenarios. `value_format` is `null` (monthly). The UI should include a caveat that actual amounts vary based on individual earnings history.

Source: https://www.ssa.gov/oact/STATS/dib-g3.html (Disabled Worker Average Benefits table, March 2026 current payment status: $1,634.51)

---

## Test Scenarios

### Scenario 1: Clearly Eligible — Standard Case
**What's being tested:** Baseline eligibility — working-age adult with a qualifying long-term disability, earnings well below 2026 SGA threshold, not currently receiving SSDI or Social Security retirement.
**Expected:** Eligible, value: $1,634

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `June 1981` (age 44), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `Wages`, Income amount: `$500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Primary regression test confirming the standard eligible case.

---

### Scenario 2: Clearly Ineligible — No Qualifying Long-Term Disability
**What's being tested:** Applicant does not have a qualifying long-term disability. Disability is the core requirement of SSDI — without it the applicant should be screened out regardless of income or age.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `June 1981` (age 44), Special Circumstances: select `None`, Has income: `Yes`, Income type: `Wages`, Income amount: `$500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms that disability is the primary gate — all other criteria are irrelevant without it.

---

### Scenario 3: Clearly Ineligible — Income Above 2026 SGA Threshold
**What's being tested:** Earned income above the 2026 SGA threshold ($1,700/month vs $1,690/month limit) correctly screens out the applicant.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `March 1978` (age 47), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `Wages`, Income amount: `$1,700`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms income above SGA correctly screens out applicants even when disability criterion is met.

---

### Scenario 4: Clearly Ineligible — Already Receiving Social Security Retirement Benefits
**What's being tested:** Applicant already receiving Social Security retirement benefits on the same earnings record cannot simultaneously receive SSDI.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `June 1959` (age 66), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `Social Security Retirement`, Income amount: `$1,500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `Social Security Retirement`

**Why this matters:** Confirms that current retirement benefit recipients are correctly screened out.

---

### Scenario 5: Edge Case — Income Exactly at 2026 SGA Boundary
**What's being tested:** Income exactly at the 2026 SGA threshold ($1,690/month) should still qualify — confirms `<=` not `<` comparison.
**Expected:** Eligible, value: $1,634

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `March 1978` (age 47), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `Wages`, Income amount: `$1,690`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the SGA threshold is inclusive — income at exactly the limit should not disqualify the applicant.

---

### Scenario 6: Clearly Ineligible — Applicant Over Full Retirement Age
**What's being tested:** Applicant born in 1957 has an FRA of 66 years 6 months, meaning they reached FRA in mid-2023. At age 68 in 2026 they are over FRA and SSDI is no longer applicable — benefits would have converted to retirement.
**Expected:** Ineligible

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1957` (age 68), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `Wages`, Income amount: `$500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the FRA upper age cutoff is correctly applied using the birth-year FRA schedule.

---

### Scenario 7: Edge Case — Blind Applicant Below Higher 2026 SGA Threshold
**What's being tested:** Confirms the higher 2026 SGA threshold ($2,830/month) applies correctly for blind applicants. Income is above the standard $1,690/month threshold but below the blind threshold — confirms the applicant is correctly shown as eligible.
**Expected:** Eligible, value: $1,634

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `June 1981` (age 44), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future`, `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, and `Blind or visually impaired`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Confirms the higher blind SGA threshold is applied correctly — without it this applicant would be incorrectly screened out.

---

### Scenario 8: Edge Case — FRA Boundary (Born 1960, Turning 66 in 2026)
**What's being tested:** FRA boundary for the 1960 birth cohort (FRA = 67). Person is currently 65, turning 66 in November 2026 — still under FRA and should be eligible.
**Expected:** Eligible, value: $1,634

**Steps:**
- **Location:** Enter ZIP code `98103`, Select county `King`
- **Household:** Number of people: `1`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `November 1960` (age 65), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `Wages`, Income amount: `$500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** Select `None`

**Why this matters:** Validates that the calculator uses the SSA birth-year FRA schedule rather than a fixed age cutoff — a 65-year-old born in 1960 is still under FRA.

---

### Scenario 9: Edge Case — Multi-Member Household, One Eligible Member
**What's being tested:** Per-member SSDI evaluation in a 3-person household. Head is eligible (disability, income $800, not receiving SSDI); spouse already receives SSDI; adult child has no disability and earns $2,500/month. Overall household result: eligible (for head only).
**Expected:** Eligible, value: $1,634

**Steps:**
- **Location:** Enter ZIP code `98501`, Select county `Thurston`
- **Household:** Number of people: `3`
- **Person 1 (Head of Household):** Relationship: `Head of Household`, Birth month/year: `January 1976` (age 49), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `Wages`, Income amount: `$800`, Income frequency: `Monthly`, Insurance: `None`
- **Person 2 (Spouse):** Relationship: `Spouse`, Birth month/year: `March 1978` (age 47), Special Circumstances: select `Currently have any disabilities that make you unable to work now or in the future` and `Any medical or developmental condition that has lasted, or is expected to last, more than 12 months`, Has income: `Yes`, Income type: `SSDI`, Income amount: `$1,200`, Income frequency: `Monthly`, Insurance: `None`
- **Person 3 (Adult Child):** Relationship: `Dependent`, Birth month/year: `May 2001` (age 24), Special Circumstances: select `None`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,500`, Income frequency: `Monthly`, Insurance: `None`
- **Current Benefits:** `None` for head; `SSDI` for spouse

**Why this matters:** Confirms per-member eligibility evaluation — the household is eligible for the head even though the spouse already receives SSDI and the child has no disability.
