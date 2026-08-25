# Implement Nurse-Family Partnership (MO) Program

## Program Details

- **Program**: Nurse-Family Partnership
- **State**: MO
- **White Label**: mo
- **Research Date**: 2026-08-10
- **Review Date**: 2026-08-18

## Eligibility Criteria

1. **Must be pregnant — the participant must be currently pregnant**
   - Screener fields:
     - `pregnant`
   - Source: NFP National Model Elements (Changent): "Enroll client early in pregnancy, no later than the 28th week of gestation"; "low-income, first-time mothers" — https://changent.org/what-we-do/nurse-family-partnership/

2. **Must reside in one of 14 Missouri jurisdictions served by one of three regional NFP providers (geographic eligibility) — not statewide**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: geography confirmed directly against each current provider's own page (not the 2024 NFP National Service Office map, whose Southeast footprint predates Missouri's 2025 home-visiting administrative restructuring — DESE's MCH-funded NFP contract, which the old 10-county Southeast map was tied to, ended September 30, 2025: https://dese.mo.gov/communications/missouri-home-visiting-programs-restructured):
     - **Kansas City region** (Kansas City Health Department) — Cass, Clay, Jackson, Johnson, Lafayette, Platte, Ray counties — https://www.kcmo.gov/city-hall/departments/health/community-and-family-health-education
     - **Southeast region** (Building Blocks of Missouri Southeast / Mercy) — Butler, Dunklin, Pemiscot, Ripley, Wayne counties — https://www.mercy.net/practice/mercy-birthplace-cape-girardeau/building-blocks-of-missouri-southeast/
     - **St. Louis region** (St. Louis County Department of Public Health) — St. Louis County, St. Louis City — https://dese.mo.gov/childhood/home-visiting/nurse-family-partnership; https://stlouiscountymo.gov/st-louis-county-departments/public-health/divisions/health-promotion-and-public-health-research/public-health-nursing/nurse-family-partnership/
   - Note: This 14-jurisdiction list replaces the earlier 18-county list, which included a 10-county Southeast footprint (Bollinger, Cape Girardeau, Dunklin, Mississippi, New Madrid, Pemiscot, Perry, Ste. Genevieve, Scott, Stoddard) sourced from the outdated 2024 map. Mercy's own current applicant-facing page lists only 5 Southeast counties. Greene and Boone counties remain outside all three provider footprints and should not be included.

3. **Low-income — under 185% of the Federal Poverty Level (statewide income gate)**
   - Screener fields:
     - `calc_gross_income("yearly", ["all"])`
     - `household_size`
   - Source: Children's Trust Fund of Missouri (CTF), MIECHV Home Visiting Programs page — https://ctf4kids.org/home-visiting-programs/miechv/ — states that all four CTF-administered home visiting models, including Nurse-Family Partnership, require families to be "low-income under 185% of poverty" per ASPE federal poverty guidelines. This is CTF's statewide rule, current as of the 2025 home-visiting administrative restructuring.
   - Resolution note (see Flag for Reviewer in the review changelog): the earlier draft used 201% FPL via the MO HealthNet for Pregnant Women threshold (MO DSS manual §1850.000.00) — a Medicaid-eligibility proxy that predates CTF's 2025 assumption of home-visiting oversight. Mercy's Southeast page separately describes eligibility informally as "women who qualify for Medicaid or Missouri WIC benefits," with no percentage cited. Because CTF is the current statewide administering body and publishes an explicit numeric threshold that applies to NFP by name, 185% FPL is adopted as the single statewide rule. Missouri NFP does not use a separate provider-specific income rule.

4. **Must be a first-time parent (first baby)** ⚠️ *data gap*
   - Note: The screener has no field for parity (number of previous births/children). The `pregnant` field confirms pregnancy but not whether this is a first pregnancy resulting in a live birth. Per the "default to inclusive" principle, do not exclude — surface this requirement in the program description so the user self-identifies. This is a core eligibility criterion for NFP.
   - Source: NFP National Model Elements (Changent) — "low-income, first-time mothers" — https://changent.org/what-we-do/nurse-family-partnership/; HomVEE model profile — https://homvee.acf.gov/models/nurse-family-partnership-nfpr
   - Impact: High

5. **Must enroll by 28 weeks of gestation** ⚠️ *data gap*
   - Note: No gestational-age field exists in the screener. Cannot determine how far along the pregnancy is. Per the "default to inclusive" principle, do not exclude — add a note in the program description that early enrollment is required (by 28 weeks).
   - Source: NFP National Model Elements (Changent) — "Enroll client early in pregnancy, no later than the 28th week of gestation" — https://changent.org/what-we-do/nurse-family-partnership/
   - Impact: Medium

## Priority Criteria (MIECHV service priorities — not eligibility gates)

CTF's MIECHV page (https://ctf4kids.org/home-visiting-programs/miechv/) identifies populations that receive **priority for services** within the pool of income-eligible families, not additional eligibility requirements:

- Pregnant people under age 21
- Families with a history of child-welfare-services involvement
- Families with a history of substance misuse, or tobacco/tobacco-product use
- Families with children who have developmental delays or disabilities
- Primary caregivers who have served or are serving in the armed forces

These are explicitly framed as outreach/service-priority factors that determine which eligible families a provider serves first when demand exceeds capacity, not eligibility gates. Do not use any of these as calculator logic or screener criteria, and do not add scenarios that test them as pass/fail conditions.

## Benefit Value

NFP provides registered nurse home visits from enrollment through the child's second birthday. There is no direct cash payment to participants — this is MFB's estimated annual in-kind value per eligible participant, not cash.

- Value type: in-kind benefit (calculated)
- Methodology: ~60 nurse home visits over the 2.5-year program period, valued at $100/visit (mid-range rate for private-duty/skilled home nursing) = $6,000 total value ÷ 2.5 years = **$2,400/year**
- Sources: https://www.cebc4cw.org/program/nurse-family-partnership/detailed (visit schedule); https://arhomecare.com/blog/how-much-does-private-home-care-really-cost-your-2025-price-guide (hourly rate range)
- Matches the existing IL (`il_nfp`) and CO (`co_nfp`) NFP calculators, which use `amount = 6_000 / 2.5` from the same two sources
- Value is per eligible individual (each pregnant person enrolls independently with their own nurse)
- For screener display: $2,400/year

## Data Gaps

- First-time parent / parity — see Criterion 4 above.
- Gestational age at enrollment (≤28 weeks) — see Criterion 5 above.

Willingness to receive home visits and provider capacity/waitlist status are not household eligibility criteria and are not treated as data gaps — they describe program operation, not who qualifies.

## Implementation Coverage

- Evaluable criteria: 3
- Data gaps: 2

Five eligibility criteria were identified for the Nurse-Family Partnership program in Missouri. Of these, 3 can be evaluated with current screener fields: pregnancy status via the `pregnant` field, geographic eligibility via `zipcode`/`county` gated to the 14-jurisdiction NFP service area (St. Louis, Kansas City, and Southeast regions), and income gated at 185% FPL (CTF/MIECHV statewide threshold). 2 criteria cannot be evaluated with current screener fields: first-time-parent status (no parity field — High impact gap) and gestational age / 28-week enrollment deadline (no field — Medium impact). Per the "default to inclusive" principle, both unevaluable criteria are surfaced in the program description rather than used to exclude potentially eligible participants.

## Research Sources

- [Children's Trust Fund of Missouri – MIECHV Home Visiting Programs](https://ctf4kids.org/home-visiting-programs/miechv/)
- [Missouri DESE – Missouri Home Visiting Programs Restructured](https://dese.mo.gov/communications/missouri-home-visiting-programs-restructured)
- [Missouri DESE – Nurse Family Partnership](https://dese.mo.gov/childhood/home-visiting/nurse-family-partnership)
- [St. Louis County Department of Public Health – Nurse-Family Partnership Program Page](https://stlouiscountymo.gov/st-louis-county-departments/public-health/divisions/health-promotion-and-public-health-research/public-health-nursing/nurse-family-partnership/)
- [Kansas City Health Department – Community and Family Health Education](https://www.kcmo.gov/city-hall/departments/health/community-and-family-health-education)
- [Mercy – Building Blocks of Missouri Southeast](https://www.mercy.net/practice/mercy-birthplace-cape-girardeau/building-blocks-of-missouri-southeast/)
- [Changent – Nurse-Family Partnership](https://changent.org/what-we-do/nurse-family-partnership/)
- [Changent – Locations](https://changent.org/locations/)
- [HomVEE Evidence Review – Nurse-Family Partnership (NFP®) Model Profile (ACF/OPRE)](https://homvee.acf.gov/models/nurse-family-partnership-nfpr)
- [HHS/ASPE 2026 Poverty Guidelines](https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines)

## Acceptance Criteria

[ ] Scenario 1 (Golden Path — First-Time Pregnant Woman in St. Louis County): User should be **eligible** with $2,400/year
[ ] Scenario 2 (Eligible in Kansas City Region — Jackson County): User should be **eligible** with $2,400/year
[ ] Scenario 3 (Eligible in Southeast Region — Butler County): User should be **eligible** with $2,400/year
[ ] Scenario 4 (Not Pregnant — Excluded): User should be **ineligible**
[ ] Scenario 5 (Outside Service Area — Greene County): User should be **ineligible**
[ ] Scenario 6 (Income Exactly at the 185% FPL Boundary): User should be **eligible** with $2,400/year
[ ] Scenario 7 (Income Just Above the 185% FPL Boundary): User should be **ineligible**
[ ] Scenario 8 (Mixed Household — One Eligible Member): User should be **eligible** with $2,400/year
[ ] Scenario 9 (Two Eligible Pregnant Members in Same Household): User should be **eligible** with $2,400/year per eligible member ($4,800/year total for the household)

## Test Scenarios

### Scenario 1: Golden Path — First-Time Pregnant Woman in St. Louis County
**What we're checking**: A first-time pregnant woman with low income, residing in the St. Louis service region, is correctly identified as eligible.
**Expected**: Eligible, value: $2,400/year

**Steps**:
- **Location**: ZIP code `63121`, county `St. Louis County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 2002`, Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$1,500/month` ($18,000/year), Current benefits: none, Health insurance: `None`

**Why this matters**: Core happy-path case for the most typical NFP applicant profile.

---

### Scenario 2: Eligible in Kansas City Region — Jackson County
**What we're checking**: A first-time pregnant woman residing in the Kansas City service region (Jackson County) is correctly identified as eligible, confirming geographic coverage outside St. Louis.
**Expected**: Eligible, value: $2,400/year

**Steps**:
- **Location**: ZIP code `64106`, county `Jackson County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `September 2002`, Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$1,200/month` ($14,400/year), Current benefits: none, Health insurance: `None`

**Why this matters**: Confirms the Kansas City region's 7 counties are correctly recognized as in-service-area.

---

### Scenario 3: Eligible in Southeast Region — Butler County
**What we're checking**: A first-time pregnant woman residing in the Southeast service region (Butler County) is correctly identified as eligible.
**Expected**: Eligible, value: $2,400/year

**Steps**:
- **Location**: ZIP code `63901`, county `Butler County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `December 2003`, Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$900/month` ($10,800/year), Current benefits: none, Health insurance: `None`

**Why this matters**: Confirms the corrected 5-county Southeast footprint (Butler, Dunklin, Pemiscot, Ripley, Wayne) is correctly recognized as in-service-area.

---

### Scenario 4: Not Pregnant — Excluded
**What we're checking**: A household with no pregnant member is excluded from NFP eligibility, even in a valid service area.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `63101`, county `St. Louis City`
- **Household**: Number of people: `2`
- **Person 1**: Birth month/year: `March 1996`, Sex: `Male`, Relationship: `Head of Household`, Pregnant: `No`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,500/month`
- **Person 2**: Birth month/year: `July 1998`, Sex: `Female`, Relationship: `Spouse`, Pregnant: `No`, Citizenship status: `US Citizen`, Has income: `No`

**Why this matters**: Confirms pregnancy is the gating criterion regardless of income or location.

---

### Scenario 5: Outside Service Area — Greene County
**What we're checking**: A first-time pregnant woman with low income who resides outside all three NFP provider footprints (Greene County, Springfield) is correctly excluded.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `65806`, county `Greene County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 2002`, Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$1,200/month`

**Why this matters**: Greene County is not served by any of the three current NFP providers; this confirms the geographic gate correctly excludes it despite the person otherwise qualifying.

---

### Scenario 6: Income Exactly at the 185% FPL Boundary
**What we're checking**: A first-time pregnant woman with household income exactly at 185% FPL for a household of 1 is correctly shown as eligible.
**Expected**: Eligible, value: $2,400/year

**Steps**:
- **Location**: ZIP code `63121`, county `St. Louis County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 2001`, Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,460.50/month` ($29,526/year — exactly 185% of the 2026 FPL for a household of 1, $15,960)

**Why this matters**: Confirms the income gate treats the exact boundary value as a pass (`<=`, not `<`).

---

### Scenario 7: Income Just Above the 185% FPL Boundary
**What we're checking**: A first-time pregnant woman with household income just above 185% FPL for a household of 1 is correctly excluded.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP code `63121`, county `St. Louis County`
- **Household**: Number of people: `1`
- **Person 1**: Birth month/year: `March 2001`, Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,500/month` ($30,000/year — above the $29,526/year 185% FPL threshold for a household of 1)

**Why this matters**: Confirms the income gate excludes households just over the line rather than rounding in the household's favor.

---

### Scenario 8: Mixed Household — One Eligible Member
**What we're checking**: A household where only one member (the pregnant partner) meets NFP's criteria is correctly shown as eligible based on that member, while non-pregnant members do not block eligibility.
**Expected**: Eligible, value: $2,400/year

**Steps**:
- **Location**: ZIP code `63121`, county `St. Louis County`
- **Household**: Number of people: `3`
- **Person 1**: Birth month/year: `March 1998`, Sex: `Male`, Relationship: `Head of Household`, Pregnant: `No`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,400/month`
- **Person 2**: Birth month/year: `June 2000`, Sex: `Female`, Relationship: `Spouse`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `No`
- **Person 3**: Birth month/year: `January 1966`, Sex: `Female`, Relationship: `Other related`, Pregnant: `No`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Social Security Retirement`, Income amount: `$1,200/month`

**Why this matters**: Combined household income ($43,200/year for a household of 3) stays under the $50,542/year 185% FPL threshold for a household of 3, confirming the household is not disqualified by aggregate income and that the eligible member drives the result.

---

### Scenario 9: Two Eligible Pregnant Members in Same Household
**What we're checking**: A household with two separate first-time pregnant members is correctly identified as having two eligible individuals rather than only one.
**Expected**: Eligible, value: $2,400/year per eligible member ($4,800/year total for the household)

**Steps**:
- **Location**: ZIP code `63101`, county `St. Louis City`
- **Household**: Number of people: `4`
- **Person 1**: Birth month/year: `March 2001`, Sex: `Female`, Relationship: `Head of Household`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$1,500/month`
- **Person 2**: Birth month/year: `November 2004`, Sex: `Female`, Relationship: `Other related`, Pregnant: `Yes`, First-time parent: `Yes`, Citizenship status: `US Citizen`, Has income: `No`
- **Person 3**: Birth month/year: `June 1999`, Sex: `Male`, Relationship: `Spouse`, Pregnant: `No`, Citizenship status: `US Citizen`, Has income: `Yes`, Income type: `Wages`, Income amount: `$2,800/month`
- **Person 4**: Birth month/year: `January 2024`, Sex: `Male`, Relationship: `Other related`, Pregnant: `No`, Citizenship status: `US Citizen`, Has income: `No`

**Why this matters**: NFP eligibility is individual — each pregnant person enrolls independently with their own nurse — so the calculated $2,400/year in-kind value applies per eligible member.


