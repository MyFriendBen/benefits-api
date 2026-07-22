# Implement YouthWorks (MA) Program

## Program Details

- **Program**: YouthWorks
- **State**: MA
- **White Label**: ma
- **Research Date**: 2026-06-30

## Eligibility Criteria

### 1. Age
- **Requirement**: The applicant must be 14–25 years old at the start of programming.
- **Screener fields**: `birth_year`, `birth_month`
- **Source**: YouthWorks RFP 2026–27, Table E2 (p.21); FAQs for Young People

### 2. Income
- **Requirement**: Family gross income must not exceed 200% of the Calendar Year Federal Poverty Guidelines.
  - **"Income"** = gross income.
  - **"Family"** = two or more individuals related by blood, marriage, or decree of court, living in a single residence: (a) a married couple and dependent children, (b) a parent or guardian and dependent children, or (c) a married couple.
- **Screener fields**: Income fields across all household members; `household_size`
- **Notes**:
  - For households with irregular income (overtime, seasonal bonuses), regions may use a combined hourly wage measure instead of annualized income. MFB uses annualized gross income; this is a known simplification.
  - For youth who are housing insecure or in foster care, self-attestation is an acceptable primary income verification. MFB cannot verify documentation type — inclusivity assumption applies.
  - ⚠️ **Edge case**: The "family" definition requires 2+ people, but RFP Appendix 1 includes a family-size-1 FPL row ($31,300 at 200% FPL). We treat household size 1 as eligible and apply the 1-person threshold.
- **Source**: YouthWorks RFP 2026–27, Table E2 (p.21); RFP Appendix 1 (p.32); FAQs for Young People

### 3. Massachusetts Residency
- **Requirement**: The participant must reside within Massachusetts and within the MassHire workforce region where they will work.
- **Screener fields**: `zipcode`
- **Notes**: MFB verifies MA residency via ZIP code but cannot verify specific MassHire region. Since YouthWorks operates statewide through all 16 MassHire regions and every MA municipality falls within a covered region, all MA residents are assumed geographically eligible. Low-risk inclusivity assumption.
- **Source**: YouthWorks RFP 2026–27, Table E2 (p.21)

### 4. Risk/Demographic Factor
- **Requirement**: Must meet at least one of: LGBTQ+ community member; Person of Color; single-income household; housing insecurity; disability; justice-involved (DYS-committed, juvenile probation, gang-involved, CRS, juvenile arrest); foster care or aged out; school stop-out; child of a single parent; limited English fluency; teen parent.
- **Screener fields**: none — ⚠️ **data gap**
- **Notes**: MFB does not collect risk/demographic factor information. Given the breadth of the 11 qualifying factors and the program's focus on low-income MA youth, the vast majority of users meeting criteria 1–3 will meet this criterion. Inclusivity assumption applied: all users meeting age, income, and residency are assumed to qualify here. Surfaced in the description using "underserved communities or who face barriers to employment" with named examples (housing instability, limited English, disability, justice involvement) — broad enough to cover LGBTQ+ youth and youth of color without naming sensitive identity categories explicitly.
  - **Optional screener improvements:**
    - `disabled` (Special Circumstances tile, already collected) → general disability. Note: `long_term_disability` is a separate field specifically for programs that require a duration threshold (e.g. SSDI); do not use it as a proxy for general disability here — they serve distinct eligibility purposes.
    - **New field proposed:** A "Foster Care" Special Circumstances tile (`foster_care`, boolean, per-member) — "Are you currently in foster care or have you aged out of foster care?" This is more complete than using `relationship: "fosterChild"`, which only captures foster children listed as household members and misses youth who are HoH and in/aged out of foster care. Pattern seen across multiple programs (Head Start, etc.).
  - **Not suggested for remaining factors:** LGBTQ+ and Person of Color — sensitive identity categories; justice-involved — off-limits per MFB policy; housing insecurity — `housing_situation` exists in the DB but is not collected by the screener; school stop-out — `student: false` is too broad; single-income household / child of a single parent / teen parent — derivable but too noisy; limited English fluency — `request_language_code` reflects app language, not English proficiency.
- **Source**: YouthWorks RFP 2026–27, Table E2 (p.21–22); FAQs for Young People

## Benefit Value

**Estimated annual value: $2,400**

Methodology: 160 hours × $15/hr (MA minimum wage), representing a typical 8-week summer placement at 20 hours/week. This estimate covers Cycle 1 (summer) participation only; the RFP caps Cycle 1 combined wages, incentives, and stipends at $3,000 per participant and Cycle 2 (school year) at $5,000 per participant — a youth enrolled in both cycles could earn up to $8,000. RFP Section C (p.9) states wages range from a base of $15/hr up to $20/hr across all tiers; $15/hr is used here as the conservative floor. Corroborated by back-calculation: PY26–27 total funding of $14.4M × 60% minimum participant wage share ÷ 3,786 youth served ≈ $2,283 average. (Note: 3,786 is the PY26-27 planned enrollment announced in the April 13, 2026 grant announcement — higher than the RFP's pre-award estimate of ~3,000. $2,400 sits above the $2,283 per-youth average, which is expected since the average includes youth in shorter or lower-wage placements.) $2,400 applied as a fixed estimate across all eligible scenarios.

Sources: YouthWorks RFP 2026–27, Section C (Available Funding, p.8; Participant Wages, p.9–10); Section F (Focus on Participant Wage, p.27); Healey-Driscoll Administration grant announcement, April 13, 2026.

## Implementation Coverage

- ✅ Evaluable criteria: 3 (age, income, Massachusetts residency)
- ⚠️ Data gaps: 1 (risk/demographic factor — inclusivity assumption applied)

## Research Sources

- [YouthWorks Program Overview — Commonwealth Corporation (Line Item 7002-0012)](https://commcorp.org/program/youthworks/)
- [YouthWorks FAQs for Young People (Ages 14–25) — Eligibility, Pay, and Program Details](https://commcorp.org/hubfs/wp-migrated/FAQs-for-Young-People.pdf?hsLang=en)
- [YouthWorks Request for Proposals (RFP) — Program Years 2026–2027](https://commcorp.org/hubfs/Final_YouthWorksRFP26-27.pdf?hsLang=en)
- [YouthWorks Regions Table — Eligible Communities and Local Program Providers by Region](https://commcorp.org/resource/youthworks-regions-table)
- [Healey-Driscoll Administration Announces Nearly $14.4 Million for Youth Jobs — Grant Announcement, April 13, 2026](https://www.mass.gov/news/healey-driscoll-administration-announces-nearly-144-million-for-youth-jobs-launches-yes-initiative-to-expand-youth-employment-and-skills-training)

## Acceptance Criteria

- [ ] Scenario 1 (Clearly Eligible Youth — 16-Year-Old in Boston): **eligible**, **$2,400/yr**
- [ ] Scenario 2 (Mid-Range Age — 17-Year-Old in Springfield): **eligible**, **$2,400/yr**
- [ ] Scenario 3 (Income Just Below 200% FPL — 16-Year-Old in Springfield): **eligible**, **$2,400/yr**
- [ ] Scenario 4 (Income at 100% FPL — 16-Year-Old in Worcester): **eligible**, **$2,400/yr**
- [ ] Scenario 5 (Income Just Above 200% FPL — 16-Year-Old in Lowell): **ineligible**
- [ ] Scenario 6 (Age Exactly at Minimum — 14-Year-Old in Boston): **eligible**, **$2,400/yr**
- [ ] Scenario 7 (Age Just Below Minimum — 13-Year-Old in Boston): **ineligible**
- [ ] Scenario 8 (Age Exactly at Maximum — 25-Year-Old in Boston): **eligible**, **$2,400/yr**
- [ ] Scenario 9 (Eligible Location — 16-Year-Old in Lawrence): **eligible**, **$2,400/yr**
- [ ] Scenario 10 (Upper Age Boundary — 24-Year-Old in Boston): **eligible**, **$2,400/yr**
- [ ] Scenario 11 (Age Just Above Maximum — 26-Year-Old in Boston): **ineligible**
- [ ] Scenario 12 (Mixed Household — Eligible 16-Year-Old, Ineligible 12-Year-Old): **eligible**, **$2,400/yr**
- [ ] Scenario 13 (Multiple Eligible Youth — Two Teens in Same Household): **eligible**, **$4,800/yr**
- [ ] Scenario 14 (Edge Case — Youth Turning 14 This Month): **eligible**, **$2,400/yr**
- [ ] Scenario 15 (Out-of-State — 16-Year-Old in Providence, RI): **ineligible**
- [ ] Scenario 16 (Over-Income — 22-Year-Old HoH, 1-Person Household): **ineligible**

## Test Scenarios

### Scenario 1: Clearly Eligible Youth — 16-Year-Old in Boston

**What we're checking**: Happy path for a typical youth who clearly qualifies for YouthWorks.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 3 people
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: head of household, Employment income: `$2,500/month`
- **Person 2**: Birth month/year: `January 2010` (age 16), Relationship: child, No income
- **Person 3**: Birth month/year: `May 2014` (age 12), Relationship: child, No income

**Why this matters**: Validates that a straightforward case — a youth in a participating MA city with a low-income household — is correctly identified as eligible for YouthWorks.

---

### Scenario 2: Mid-Range Age — 17-Year-Old in Springfield

**What we're checking**: Youth of a typical age (17) with no income in Springfield is correctly identified as eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `01103`, city `Springfield`
- **Household**: 1 person
- **Person 1**: Birth month/year: `August 2008` (age 17), Relationship: head of household, No income

**Why this matters**: Validates that a youth well within the age range is correctly surfaced in a 1-person, zero-income household. Complements the age boundary scenarios (Scenarios 6–11) by confirming the screener doesn't falsely exclude non-boundary cases.

---

### Scenario 3: Income Just Below 200% FPL — 16-Year-Old in Springfield

**What we're checking**: Youth with household income just below the 200% FPL ceiling remains eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `01103`, city `Springfield`
- **Household**: 3 people
- **Person 1**: Birth month/year: `January 1980` (age 46), Relationship: head of household, Employment income: `$4,400/month` (~$52,800/year, just below the $53,300 200% FPL threshold for household of 3)
- **Person 2**: Birth month/year: `March 2010` (age 16), Relationship: child, No income
- **Person 3**: Birth month/year: `September 2014` (age 11), Relationship: child, No income

**Why this matters**: Boundary test on the income ceiling — mirrors Scenario 5's just-above case. Income $42/month below the threshold should remain eligible.

---

### Scenario 4: Income at 100% FPL — 16-Year-Old in Worcester

**What we're checking**: Youth whose household income is at approximately 100% FPL (well below the 200% FPL threshold) is eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `01604`, city `Worcester`
- **Household**: 3 people
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: head of household, Employment income: `$2,221/month` (~$26,650/year, approximately 100% FPL for household of 3)
- **Person 2**: Birth month/year: `September 2009` (age 16), Relationship: child, No income
- **Person 3**: Birth month/year: `January 2015` (age 11), Relationship: child, No income

**Why this matters**: Guards against an off-by-one error that could use 100% FPL as the threshold instead of 200%.

---

### Scenario 5: Income Just Above 200% FPL — 16-Year-Old in Lowell

**What we're checking**: Youth whose household income exceeds the 200% FPL threshold is correctly ineligible.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `01851`, city `Lowell`
- **Household**: 3 people
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: head of household, Employment income: `$4,500/month` (~$54,000/year, just above the $53,300 200% FPL threshold for household of 3)
- **Person 2**: Birth month/year: `September 2009` (age 16), Relationship: child, No income
- **Person 3**: Birth month/year: `January 2015` (age 11), Relationship: child, No income

**Why this matters**: Validates the income ceiling is enforced at 200% FPL. A household earning just above this threshold should be excluded.

---

### Scenario 6: Age Exactly at Minimum — 14-Year-Old in Boston

**What we're checking**: Youth who is exactly 14 (the minimum age) is eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 3 people
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: head of household, Employment income: `$2,000/month`
- **Person 2**: Birth month/year: `June 2012` (age 14, exactly at minimum), Relationship: child, No income
- **Person 3**: Birth month/year: `September 2016` (age 9), Relationship: child, No income

**Why this matters**: Tests the lower age boundary — ensures the screener uses ≥14 not >14. Note: Scenario 14 uses the same birth date (June 2012) in a 2-person household; both intentionally test the same `birth_year`/`birth_month` calculation from different household contexts.

---

### Scenario 7: Age Just Below Minimum — 13-Year-Old in Boston

**What we're checking**: Youth aged 13 (one year below the minimum) is correctly ineligible.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `02118`, city `Boston`
- **Household**: 3 people
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: head of household, Employment income: `$2,000/month`
- **Person 2**: Birth month/year: `September 2012` (age 13), Relationship: child, No income
- **Person 3**: Birth month/year: `January 2020` (age 6), Relationship: child, No income

**Why this matters**: Confirms the age floor is enforced. Complements Scenario 6 — one year below the minimum should be excluded.

---

### Scenario 8: Age Exactly at Maximum — 25-Year-Old in Boston

**What we're checking**: Young adult aged exactly 25 (the upper ceiling) is eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 1 person
- **Person 1**: Birth month/year: `June 2001` (age 25, exactly at upper cap), Relationship: head of household, Employment income: `$1,200/month`

**Why this matters**: Tests the upper age ceiling precisely — ensures the screener uses ≤25 not <25. Mirrors Scenario 11 (age 26 → ineligible) and Scenario 10 (age 24 → eligible).

---

### Scenario 9: Eligible Location — 16-Year-Old in Lawrence

**What we're checking**: Youth in Lawrence (Merrimack Valley MassHire region) is geographically eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `01841`, city `Lawrence`
- **Household**: 3 people
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: head of household, Employment income: `$1,800/month`
- **Person 2**: Birth month/year: `January 2010` (age 16), Relationship: child, No income
- **Person 3**: Birth month/year: `May 2015` (age 11), Relationship: child, No income

**Why this matters**: Verifies geographic eligibility for a Gateway City outside Boston/Springfield/Worcester. Lawrence is one of the highest-need YouthWorks communities.

---

### Scenario 10: Upper Age Boundary — 24-Year-Old in Boston

**What we're checking**: Young adult at age 24 (within the 14–25 range) is eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 1 person
- **Person 1**: Birth month/year: `May 2002` (age 24), Relationship: head of household, Employment income: `$1,200/month`

**Why this matters**: Tests the upper end of the 14–25 age range. Confirms that the age ceiling is ≤25, not ≤21 or ≤18, and that Tier 4 participants (ages 22–25) are correctly identified as eligible.

---

### Scenario 11: Age Just Above Maximum — 26-Year-Old in Boston

**What we're checking**: Young adult aged 26 (one year above the 25-year ceiling) is correctly ineligible.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 1 person
- **Person 1**: Birth month/year: `May 2000` (age 26), Relationship: head of household, Employment income: `$1,200/month`

**Why this matters**: Confirms the upper age cap is enforced at 25. Complements Scenario 10 — one year above the maximum should be excluded.

---

### Scenario 12: Mixed Household — Eligible 16-Year-Old, Ineligible 12-Year-Old

**What we're checking**: Household where one youth qualifies and one is too young — per-member eligibility logic.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 4 people
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: head of household, Employment income: `$2,000/month`
- **Person 2**: Birth month/year: `July 1982` (age 44), Relationship: spouse, Employment income: `$500/month`
- **Person 3**: Birth month/year: `January 2010` (age 16), Relationship: child, No income — eligible for YouthWorks
- **Person 4**: Birth month/year: `September 2013` (age 12), Relationship: child, No income — below minimum age

**Why this matters**: Validates per-member eligibility logic — YouthWorks should be surfaced for the 16-year-old without applying to the 12-year-old.

---

### Scenario 13: Multiple Eligible Youth — Two Teens in Same Household

**What we're checking**: Two youth (ages 15 and 17) in the same household both independently qualify.

**Expected**: Eligible — estimated annual value: $4,800

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 4 people
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: head of household, Employment income: `$1,800/month`
- **Person 2**: Birth month/year: `July 1982` (age 44), Relationship: spouse, Employment income: `$800/month`
- **Person 3**: Birth month/year: `January 2009` (age 17), Relationship: child, No income
- **Person 4**: Birth month/year: `September 2010` (age 15), Relationship: child, No income

**Why this matters**: Confirms the screener surfaces YouthWorks for multiple eligible youth and sums per-member values ($2,400 × 2 = $4,800). YouthWorks is a per-person placement program — each eligible youth receives their own job placement, so values sum per eligible member. Follows the same pattern as ECEAP (WA), where multiple eligible children each receive their own slot and values are summed.

---

### Scenario 14: Edge Case — Youth Turning 14 This Month

**What we're checking**: Youth born June 2012 who turns 14 in June 2026 (current month) is eligible.

**Expected**: Eligible — estimated annual value: $2,400

**Steps**:
- **Location**: ZIP code `02118`, city `Boston`
- **Household**: 2 people
- **Person 1**: Birth month/year: `March 1980` (age 46), Relationship: head of household, Employment income: `$1,200/month`
- **Person 2**: Birth month/year: `June 2012` (turned 14 in June 2026), Relationship: child, No income

**Why this matters**: Validates that the age calculation using `birth_year`/`birth_month` correctly includes youth who reached the minimum age in the current program year. Note: Scenario 6 uses the same birth date (June 2012) in a 3-person household; both intentionally test the same calculation from different household contexts.

---

### Scenario 15: Out-of-State — 16-Year-Old in Providence, RI

**What we're checking**: Youth living outside Massachusetts is correctly ineligible even if all other criteria are met.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `02903`, city `Providence, RI`
- **Household**: 3 people
- **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: head of household, Employment income: `$2,000/month`
- **Person 2**: Birth month/year: `January 2010` (age 16), Relationship: child, No income
- **Person 3**: Birth month/year: `May 2014` (age 12), Relationship: child, No income

**Why this matters**: Confirms the MA residency requirement is enforced — a youth who meets age and income criteria but lives outside Massachusetts is excluded.

---

### Scenario 16: Over-Income — 22-Year-Old HoH, 1-Person Household

**What we're checking**: Youth who is the sole earner in a 1-person household with income above the HH1 200% FPL threshold is correctly ineligible on income alone.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `02119`, city `Boston`
- **Household**: 1 person
- **Person 1**: Birth month/year: `May 2004` (age 22), Relationship: head of household, Employment income: `$2,800/month` (~$33,600/year, above the $31,300 200% FPL threshold for household of 1)

**Why this matters**: Validates the income ceiling for a 1-person household where the youth is their own HoH. All existing 1-person HH scenarios are either comfortably under the threshold (Scenarios 2, 8, 10) or ineligible by age alone (Scenario 11) — none test the HH1 income cutoff specifically. Also exercises the edge case noted in Criterion 2: even though the program's "family" definition technically requires 2+ people, RFP Appendix 1 includes a HH1 FPL row ($31,300 at 200%), and income must be enforced at that threshold.

---

## Source Documentation

- https://commcorp.org/program/youthworks/
- https://commcorp.org/hubfs/wp-migrated/FAQs-for-Young-People.pdf?hsLang=en
- https://commcorp.org/hubfs/Final_YouthWorksRFP26-27.pdf?hsLang=en
- https://commcorp.org/resource/youthworks-regions-table
- https://www.mass.gov/news/healey-driscoll-administration-announces-nearly-144-million-for-youth-jobs-launches-yes-initiative-to-expand-youth-employment-and-skills-training
