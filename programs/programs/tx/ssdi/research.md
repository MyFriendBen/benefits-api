# TX: Social Security Disability Insurance (SSDI)

- **Program**: Social Security Disability Insurance (SSDI)
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-03-04

## Eligibility Criteria

| # | Criterion | Screener Fields | Logic | Can Evaluate? | Notes | Source |
|---|-----------|-----------------|-------|---------------|-------|--------|
| 1 | Worked in jobs covered by Social Security | `household_member.worked_in_last_18_mos`, `household_member.has_income`, `incomeStreams (category='wages')` | `worked_in_last_18_mos == True OR (has_income == True AND income category 'wages')` | ⚠️ | Can only capture if currently working; cannot verify past SS-covered employment history | 20 CFR § 404.101, 404.110–404.146 |
| 2 | Medically determinable impairment expected to last 12+ months or result in death | `household_member.long_term_disability` | `long_term_disability == True` | ✅ | | 20 CFR § 404.1505, 42 U.S.C. § 423(d)(1)(A) |
| 3a | Not engaging in SGA — non-blind ($1,690/month in 2026) | `household_member.has_income`, `incomeStreams (amount, frequency)` | `calc_gross_income('monthly', types=['all']) < 1690` | ✅ | Includes wages and self-employment income (20 CFR § 404.1575) | 20 CFR § 404.1574, [SSA SGA Table](https://www.ssa.gov/oact/cola/sga.html) |
| 3b | Not engaging in SGA — blind ($2,830/month in 2026) | `household_member.has_income`, `household_member.visually_impaired`, `incomeStreams (amount, frequency)` | `IF visually_impaired: calc_gross_income('monthly', types=['all']) < 2830` | ✅ | Higher SGA threshold for statutory blindness | 20 CFR § 404.1584, [SSA Red Book 2026](https://www.ssa.gov/redbook/newfor2026.htm) |
| 4 | Under Full Retirement Age (67 for those born 1960+) | `household_member.age`, `household_member.birth_year_month` | `age < 67` | ✅ | FRA varies by birth year (66–67); screener can approximate with age field | 20 CFR § 404.1520, 42 U.S.C. § 423 |
| 5 | Unable to do previous work and cannot adjust to other work | — | SSA vocational assessment | ❌ | Requires SSA's five-step sequential evaluation; screener doesn't have the fields to assess this | 20 CFR § 404.1520(a)(4) |
| 6 | Sufficient work credits (generally 40 credits, 20 in last 10 years for age 31+) | — | SSA earnings record calculation | ❌ | Requires SSA earnings records; `worked_in_last_18_mos` is too limited | 20 CFR § 404.130, 404.140–404.146 |
| 7 | Disability meets SSA Blue Book listings or medical-vocational guidelines | — | SSA medical adjudication | ❌ | Requires specific diagnoses/functional limitations; screener only captures general disability status | 20 CFR Part 404, Subpart P, Appendix 1 |
| 8 | Five-month waiting period from disability onset | — | Disability onset date | ❌ | Screener does not capture disability onset date or duration | 20 CFR § 404.315, 42 U.S.C. § 423(a)(1) |
| 9 | Not already receiving Social Security retirement benefits | `incomeStreams (category='socialSecurity')` | `calc_gross_income('yearly', types=['socialSecurity']) == 0` | ✅ | Can infer SS retirement from income type | 20 CFR § 404.1520 |
| 10 | Insured status — worked in 5 of last 10 years (age 31+) | — | Detailed work history | ❌ | `worked_in_last_18_mos` is insufficient; need quarters of coverage in specific periods | 20 CFR § 404.130, 404.140 |
| 11 | U.S. citizenship or qualified alien with work authorization | `legal_status_required` | `legal_status in ['citizen', 'otherWithWorkPermission']` | ✅ | Captured via program's `legal_status_required` configuration | 42 U.S.C. § 402(y), 20 CFR § 404.1520 |
| 12 | Not incarcerated for felony conviction or confined to public institution | — | — | ❌ | No incarceration status field in screener | 20 CFR § 404.468, 42 U.S.C. § 402(x) |
| 13 | No prior SSDI denial within past 60 days (for reopening) | — | Prior application history | ❌ | Screener does not capture prior SSDI application history | 20 CFR § 404.987–404.989 |
| 14 | Medical evidence from acceptable medical sources | — | Medical documentation | ❌ | Procedural requirement; screener doesn't capture whether applicant has treating physicians | 20 CFR § 404.1513 |
| 15 | Blindness exception: higher SGA limit (see 3b) | `household_member.visually_impaired` | See criterion 3b | ⚠️ | SSA statutory blindness (20/200 or less, or visual field ≤20°) is more specific than `visually_impaired` field; handled via separate SGA threshold in 3b | 20 CFR § 404.1584, 404.1585 |
| 16 | Not already receiving SSDI | `current_benefits` | `'tx_ssdi' not in current_benefits` | ✅ | | — |

## Coverage

- **Evaluable**: 7 of 17 criteria (41%)
- **Partially evaluable**: 2 of 17 (12%)
- **Summary**: The screener can evaluate long-term disability status, earnings relative to blind/non-blind SGA limits, age relative to Full Retirement Age, SS retirement income, citizenship/work authorization, and duplicate enrollment. Work history can be partially assessed (current employment only). Critical gaps include the specific work credit calculation (requires SSA earnings records), SSA medical adjudication under Blue Book listings, vocational assessment, insured status based on detailed work history, the five-month waiting period, and incarceration status. The screener can identify potentially eligible individuals but cannot definitively determine SSDI eligibility given its reliance on SSA administrative records and medical adjudication.

## Benefit Value

Amount varies by individual based on lifetime Social Security-covered earnings. Calculated using the Primary Insurance Amount (PIA) formula applied to Average Indexed Monthly Earnings (AIME). Average benefit was approximately $1,537/month in 2024. No fixed amount can be calculated by the screener.

## Sources

- [SSDI Application Portal](https://www.ssa.gov/apply?benefits=disability&age=adult)
- [Social Security Disability Insurance Overview](https://www.ssa.gov/disability)
- [SSDI Eligibility Requirements](https://www.ssa.gov/disability/eligibility)
- [SSDI Benefit Calculation](https://www.ssa.gov/disability/amount)
- [SSA SGA Table](https://www.ssa.gov/oact/cola/sga.html)
- [SSA Red Book — What's New in 2026](https://www.ssa.gov/redbook/newfor2026.htm)
- [20 CFR Part 404 — Federal Old-Age, Survivors, and Disability Insurance](https://www.ecfr.gov/current/title-20/chapter-III/part-404?toc=1)
- [SSA Benefits Estimate Tool](https://www.ssa.gov/prepare/get-benefits-estimate)

## Test Scenarios

### Scenario 1: Disabled Worker Under FRA with Work History and No SGA

**Checks**: Core happy path — disabled, under FRA, recent work history, not earning SGA
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `January 1976` (age 50), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$0`, no insurance

**Why this matters**: Most straightforward SSDI profile — working-age adult who became disabled, has recent work history, is below SGA, and is under FRA. Tests all five evaluable criteria simultaneously.

---

### Scenario 2: Disabled Worker Near Full Retirement Age, Just Below SGA Threshold

**Checks**: Upper age boundary (just under 67) combined with income just below SGA
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `April 1959` (age 66), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, wages: `$1,619/month`, no insurance

**Why this matters**: Tests minimum threshold boundaries simultaneously — age just under FRA and earnings just below SGA. Ensures the screener doesn't incorrectly exclude marginally eligible applicants.

---

### Scenario 3: Monthly Income Just Below SGA Threshold

**Checks**: Income just under $1,620/month is permitted
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `January 1972` (age 54), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, wages: `$1,600/month`, no insurance

**Why this matters**: Validates the SGA threshold — disabled individuals earning just under the limit must not be incorrectly excluded.

---

### Scenario 4: Monthly Income Exactly at SGA Threshold

**Checks**: Income at exactly $1,620/month should still qualify ("less than or equal to")
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `March 1976` (age 50), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, wages: `$1,620/month`, no insurance

**Why this matters**: Confirms the boundary is inclusive — ensures the system uses `<=` not `<` for the SGA check.

---

### Scenario 5: Monthly Income Above SGA Threshold

**Checks**: Income exceeding $1,620/month disqualifies the applicant
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `March 1972` (age 54), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, wages: `$1,750/month`, no insurance

**Why this matters**: Ensures SGA enforcement works — earnings above the threshold must disqualify regardless of disability status.

---

### Scenario 6: Minimum Age (18) with Disability

**Checks**: Age 18 is the minimum; eligible if all other criteria met
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `March 2008` (age 18), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, wages: `$500/month`, no insurance

**Why this matters**: Validates no off-by-one error at minimum age. Young workers who become disabled shortly after entering the workforce should qualify.

---

### Scenario 7: Age 17 — Below Minimum Age

**Checks**: Under-18 applicants are ineligible even with disability and work history
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `April 2008` (age 17), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, wages: `$500/month`, no insurance

**Why this matters**: SSDI is for adult workers; minors with disabilities are directed to SSI instead.

---

### Scenario 8: Age 50 — Mid-Career Disabled Worker

**Checks**: No unintended upper age restriction below FRA
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `March 1976` (age 50), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$0`, no insurance

**Why this matters**: Confirms eligibility is maintained for mid-career workers and no unintended age caps exist below FRA.

---

### Scenario 9: Valid Texas Resident

**Checks**: Texas residency — SSDI is a federal program available statewide
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `January 1981` (age 45), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$800/month` Social Security, no insurance

**Why this matters**: Confirms geographic location within Texas poses no barrier to eligibility for this federal program.

---

### Scenario 10: Already Receiving SSDI

**Checks**: Current SSDI beneficiaries are not shown as newly eligible
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `March 1976` (age 50), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$1,537/month SSDI`, Medicare, **current benefits: SSDI**

**Why this matters**: Prevents duplicate benefit display for current recipients.

---

### Scenario 11: Already Receiving SSI (Concurrent Benefits Allowed)

**Checks**: Current SSI recipients can also receive SSDI (concurrent benefits)
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 1 person
- **Person 1**: DOB `January 1978` (age 48), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$943/month SSI`, Medicaid, **current benefits: SSI**

**Why this matters**: SSI and SSDI can be received concurrently ([SSA Red Book](https://www.ssa.gov/redbook/eng/supportsexample.htm)). Current SSI recipients should still be shown as potentially eligible for SSDI.

---

### Scenario 12: Mixed Household — Eligible Disabled Worker, Non-Disabled Spouse, Child

**Checks**: SSDI eligibility is per-individual; spousal income does not affect eligibility
**Expected**: Eligible (for the disabled worker)

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 3 people
- **Person 1 (Head)**: DOB `January 1972` (age 54), U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$0`, no insurance
- **Person 2 (Spouse)**: DOB `May 1974` (age 51), U.S. Citizen, no disability, worked in last 18 months, wages: `$2,800/month`, employer insurance
- **Person 3 (Child)**: DOB `September 2010` (age 15), U.S. Citizen, no disability, no income, on parent's plan

**Why this matters**: SSDI is an individual entitlement; spousal income has no effect. Confirms per-member evaluation.

---

### Scenario 13: Two Disabled Workers in Same Household

**Checks**: Both household members independently qualify
**Expected**: Eligible (both members)

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1971` (age 55), U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$1,200/month SSDI`, no insurance
- **Person 2 (Spouse)**: DOB `June 1973` (age 52), U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$1,050/month SSDI`, no insurance

**Why this matters**: Validates that multiple household members can independently qualify and are each evaluated on their own work history and disability status.

---

### Scenario 14: Exactly at Full Retirement Age (67)

**Checks**: At FRA, SSDI eligibility ends and transitions to retirement benefits
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `March 1959` (age 67 — exactly at FRA), Head of Household, U.S. Citizen, has disability, long-term disability, worked in last 18 months, income: `$0`, no insurance, no current benefits

**Why this matters**: At FRA, disability benefits convert to retirement benefits. Confirms the age cutoff is correctly enforced and no SSDI eligibility is shown at 67.

---

### Scenario 15: Blind Individual — Income Below Blind SGA Threshold

**Checks**: Visually impaired applicant with income under blind SGA ($2,830/month in 2026)
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `January 1976` (age 50), Head of Household, U.S. Citizen, has disability, long-term disability, visually impaired, worked in last 18 months, wages: `$2,500/month`, no insurance

**Why this matters**: Validates the higher blind SGA threshold. A blind individual earning $2,500/month is above the non-blind SGA ($1,690) but below the blind SGA ($2,830), so they should still qualify.

---

### Scenario 16: Blind Individual — Income Above Blind SGA Threshold

**Checks**: Visually impaired applicant with income above blind SGA ($2,830/month in 2026)
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `January 1976` (age 50), Head of Household, U.S. Citizen, has disability, long-term disability, visually impaired, worked in last 18 months, wages: `$3,000/month`, no insurance

**Why this matters**: Confirms the blind SGA threshold is enforced — even blind applicants earning above $2,830/month are ineligible.

---

### Scenario 17: Long-Term Disability Only (No General Disability Flag)

**Checks**: Applicant has `long_term_disability` but not `disabled` — should still qualify
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `January 1976` (age 50), Head of Household, U.S. Citizen, long-term disability (no general disability flag), worked in last 18 months, income: `$0`, no insurance

**Why this matters**: Eligibility should key off `long_term_disability` alone. Ensures the screener doesn't require both flags.

---

### Scenario 18: General Disability Only (No Long-Term Disability)

**Checks**: Applicant has `disabled` but not `long_term_disability` — should not qualify
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75001`, County `Collin County`
- **Household**: 1 person
- **Person 1**: DOB `January 1976` (age 50), Head of Household, U.S. Citizen, has disability (no long-term disability), worked in last 18 months, income: `$0`, no insurance

**Why this matters**: SSDI requires a long-term disability (12+ months). A general disability flag without the long-term qualifier should not be sufficient.
