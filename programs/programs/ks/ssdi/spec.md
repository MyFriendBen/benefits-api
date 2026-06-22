# Social Security Disability Insurance (SSDI) — Implementation Spec

**Program:** `ks_ssdi`
**State:** Kansas
**White Label:** `ks`
**Research Date:** 2026-06-15

> SSDI is a federal program with no state variance in eligibility or benefit value.
> This calculator mirrors the federal SSDI rules already implemented for other states
> (e.g. `wa_ssdi`). The criteria below are reproduced from that federal research for reference.

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
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How We Decide if You Have a Qualifying Disability); https://www.ssa.gov/redbook/eng/definedisability.htm (What is Substantial Gainful Activity); 42 U.S.C. § 423(d)(4)

3. **Applicant must not already be receiving benefits on their own Social Security record**
   - Screener fields:
     - `has_ssdi` (captured in current benefits section — "Social Security Disability Insurance (SSDI)")
   - Note: Someone already receiving SSDI should not be shown SSDI as a recommendation. Receiving SSI does NOT exclude someone from SSDI — concurrent SSI/SSDI receipt is allowed.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How Does Someone Become Eligible)

4. **Applicant must not already be receiving Social Security retirement benefits on the same earnings record** ⚠️ *data gap*
   - Screener fields: none (Social Security retirement is not currently listed in the screener's current benefits section)
   - Note: A person cannot receive both SSDI and Social Security retirement benefits on the same earnings record simultaneously. At full retirement age, SSDI automatically converts to retirement benefits.
     - **Inclusivity assumption:** assume all screener respondents are not already receiving Social Security retirement benefits. The calculator additionally screens out applicants reporting `sSRetirement` income.
   - Source: https://www.ssa.gov/faqs/en/questions/KA-01861.html; 42 U.S.C. § 402(a); 42 U.S.C. § 423

5. **Applicant must be of working age — under full retirement age (FRA), which ranges from 66 to 67 depending on birth year**
   - Screener fields:
     - `birth_month`
     - `birth_year`
   - Note: FRA depends on birth year. Born 1943–1954: FRA is 66. Born 1955–1959: FRA increases by 2 months per year. Born 1960 or later: FRA is 67. The calculator uses the SSA birth-year FRA schedule rather than a fixed cutoff.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html; 42 U.S.C. § 423(a)(1)(B)

6. **Applicant must have earned sufficient work credits through Social Security-covered employment — generally 40 credits (20/40 Rule); younger workers need fewer credits** ⚠️ *data gap*
   - Screener fields: none
   - Note: The screener does not collect work history duration or Social Security work credits. SSA verifies credit accumulation from their own earnings records.
     - **Inclusivity assumption:** assume all screener respondents have sufficient work credits, were insured at disability onset, and worked in Social Security-covered employment. This is the most significant data gap for SSDI eligibility.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html (How Much Work Do You Need); 42 U.S.C. § 423(c)(1)

7. **The medical condition must meet SSA's specific 5-step disability determination** ⚠️ *data gap*
   - Screener fields: `long_term_disability`, `medical_condition`, `income_streams`
   - Note: SSA uses a formal 5-step sequential evaluation that the screener cannot replicate.
     - **Inclusivity assumption:** assume all self-reported disabilities meet SSA's full definition.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html; 20 CFR § 404.1520

8. **Applicant must not be involved with the criminal justice system in a disqualifying way** ⚠️ *data gap*
   - Screener fields: none
   - Note: Benefits cannot be paid for any month of disqualifying incarceration, outstanding felony warrant, or parole/probation violation. No field captures these statuses.
     - **Inclusivity assumption:** assume all screener respondents are not in a disqualifying criminal justice situation.
   - Source: 42 U.S.C. § 402(x)

9. **Disabled Adult Child (DAC) and Surviving Spouse special paths** ⚠️ *data gap*
   - Screener fields: none
   - Note: Adults disabled before age 22 may qualify on a parent's record; surviving spouses ages 50–60 with a disability may qualify on a deceased worker's record. The screener does not capture these statuses.
     - **Inclusivity assumption:** these paths are not checked in the calculator. The program description directs users to contact SSA.
   - Source: https://www.ssa.gov/benefits/disability/qualify.html

---

## Priority Criteria

SSDI has no priority criteria — eligibility is an all-or-nothing determination. There are no tiers, priority groups, or waitlists.

---

## Benefit Value

SSDI benefit amounts are variable, based on the applicant's lifetime earnings history (AIME). There is no fixed amount.

- SSDI is **not means-tested** — there are no household income or asset limits.
- **Average monthly benefit (March 2026):** approximately **$1,634/month** for disabled workers in current payment status.
- **This is the value the calculator returns for eligible households**, as an illustrative estimate; actual amounts vary by earnings history.

**Recommended calculator methodology:** Return the average monthly benefit of **$1,634** as the estimated value for eligible scenarios. `value_format` is `null` (monthly).

Source: https://www.ssa.gov/oact/STATS/dib-g3.html (Disabled Worker Average Benefits table, March 2026: $1,634.51)

---

## Test Scenarios

Test scenarios mirror the federal SSDI cases, using Kansas locations.

### Scenario 1: Clearly Eligible — Standard Case
**Expected:** Eligible, value: $1,634
- **Location:** ZIP `67202`, county `Sedgwick`
- **Household:** 1 person
- **Person 1 (Head):** Born `June 1981` (age 44), Special Circumstances: long-term disability + medical condition, Income: Wages `$500/month`, Insurance: None
- **Current Benefits:** None

### Scenario 2: Ineligible — No Qualifying Long-Term Disability
**Expected:** Ineligible
- Same as Scenario 1 but Special Circumstances: None

### Scenario 3: Ineligible — Income Above 2026 SGA Threshold
**Expected:** Ineligible
- Disability met, Wages `$1,700/month` (above $1,690 non-blind SGA)

### Scenario 4: Ineligible — Already Receiving Social Security Retirement
**Expected:** Ineligible
- Born `June 1959` (age 66), disability met, Income type: Social Security Retirement `$1,500/month`

### Scenario 5: Edge — Income Exactly at 2026 SGA Boundary
**Expected:** Eligible, value: $1,634
- Disability met, Wages `$1,690/month` (confirms `<=` comparison)

### Scenario 6: Ineligible — Applicant Over Full Retirement Age
**Expected:** Ineligible
- Born `January 1957` (age 68, FRA 66y6m reached mid-2023)

### Scenario 7: Edge — Blind Applicant Below Higher 2026 SGA Threshold
**Expected:** Eligible, value: $1,634
- Disability + blind, Wages `$2,500/month` (above $1,690 but below $2,830 blind SGA)

### Scenario 8: Edge — FRA Boundary (Born 1960, Turning 66 in 2026)
**Expected:** Eligible, value: $1,634
- Born `November 1960` (age 65, FRA = 67), disability met, Wages `$500/month`

### Scenario 9: Edge — Multi-Member Household, One Eligible Member
**Expected:** Eligible, value: $1,634
- **Location:** ZIP `66603`, county `Shawnee`
- Head eligible (disability, Wages `$800/month`); Spouse already receives SSDI; Adult child (age 24) no disability, Wages `$2,500/month`
