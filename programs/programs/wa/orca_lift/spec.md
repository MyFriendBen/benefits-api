# Implement ORCA LIFT (WA) Program

## Program Details

- **Program**: ORCA LIFT Reduced Fare Program
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-05-12

## Scope Note

This ticket implements **ORCA LIFT only**. There are four other ORCA reduced-fare programs (Youth Ride Free, Senior RRFP, Disability RRFP, Subsidized Annual Pass) that are out of scope for this ticket and will be tracked in future tickets. The long-term plan is to consolidate all five into a single combined "ORCA Reduced Fare" program record once each has been individually researched and implemented.

## Eligibility Criteria

### Logical structure

A household qualifies for ORCA LIFT when **all** of the following are true:

- **Criterion 1 is met** (at least one household member aged 19–64), **AND**
- **At least one of Criteria 2, 3, or 4 is met** — the three are independent OR-pathways, **AND**
- **Criterion 5 is met** (Washington residency — enforced at the program level via `white_label = wa`)

The benefit value scales with the number of household members aged 19–64.

---

### Criterion 1 — At least one household member must be aged 19–64

- **Screener fields** (per HouseholdMember):
  - `birth_year`
  - `birth_month`
- **Note**: Cards are issued to individuals aged 19–64. Members aged 18 and under should use Youth Ride Free instead (separate future program); members aged 65+ should use the Regional Reduced Fare Permit (separate future program). The calculator counts members in the 19–64 range to scale the benefit value (one card per eligible adult). Use `birth_year` + `birth_month` to compute age — the deprecated `age` field should not be relied on.
- **Source**: [myORCA — ORCA LIFT](https://info.myorca.com/lift/) ("Your age is between 19-64."); [King County Metro — ORCA LIFT FAQ](https://kingcounty.gov/en/dept/metro/fares-and-payment/reduced-fares/orca-lift)

---

### Criterion 2 — Pathway A: enrolled in a qualifying Washington benefit program

- **Screener fields** (Screen level — current benefits, checked via `has_benefit(...)`):
  - `medicaid` — general Medicaid current-benefit enrollment
  - `wa_apple_health_medicaid` — WA Apple Health (Medicaid) program (name_abbreviated)
  - `wa_apple_health_for_kids` — WA Apple Health for Kids program (name_abbreviated)
  - `snap` — Washington Basic Food / EBT
  - `wic`
- **Note**: If any household member is enrolled in Apple Health/Medicaid, Washington Basic Food, or WIC, the entire household qualifies for ORCA LIFT regardless of income. The calculator checks the household's Medicaid current benefit and the dedicated WA Apple Health programs (`wa_apple_health_medicaid`, `wa_apple_health_for_kids`) via `has_benefit()` — both pathways trigger the same categorical bypass. The per-member `medicaid` insurance flag is separate and should not be substituted.
- **Source**: [King County Metro — ORCA LIFT](https://kingcounty.gov/en/dept/metro/fares-and-payment/reduced-fares/orca-lift) ("Those receiving Apple Health Medicaid, WIC and Basic Food are eligible for the program."); [Reduced Fare Portal](https://reducedfare.kingcounty.gov/en-US/orca-lift-main/)

---

### Criterion 3 — Pathway B: Washington State Opportunity Grant recipient ⚠️ *data gap*

- **Screener fields**: `none`. No `opportunity_grant` (or equivalent) current benefit exists in the screener inventory. The closest available fields (the `pell_grant` current benefit, `student`, `student_full_time`, `student_job_training_program`) all capture related but different concepts — none of them isolates Washington State Opportunity Grant enrollment specifically.
- **Note**: The screener cannot directly detect Opportunity Grant recipients. For the calculator we apply an **inclusivity assumption** and skip this pathway entirely — Opportunity Grant recipients must be at or below 200% FPL as a condition of the grant itself ([SBCTC — Opportunity Grant](https://www.sbctc.edu/paying-for-college/opportunity-grant-student.aspx)), so they will be captured by Criterion 4 (income) in the vast majority of cases. The only edge case this assumption may miss is a grant recipient whose income rose just over 200% FPL after award but who remains eligible for ORCA LIFT for the duration of the grant. Surfaced in the program description so users know to apply via this pathway directly if needed.
- **Suggested screener improvement**: Add a new state-specific `opportunity_grant` (or `wa_opportunity_grant`) entry to the WA white-label's current-benefits follow-up list on the screener's **Section 10 — Current Public Assistance Benefits** page (per `mfb_screener_fields_source.md`), under the question *"Does anyone in your household currently have public assistance benefits?"*. Best placed alongside existing education/student-aid benefits — analogous to where the `pell_grant` current benefit lives — likely under a "Child Care, Youth, & Education" or equivalent WA-specific category. Once the entry exists, the calculator can check it via `has_benefit(...)` and this inclusivity assumption becomes unnecessary, closing the only data gap in the ORCA LIFT eligibility logic.
- **Source**: [Reduced Fare Portal](https://reducedfare.kingcounty.gov/en-US/orca-lift-main/) ("If you're a college student who receives the Washington State Opportunity Grant, you qualify for ORCA LIFT."); [SBCTC — Opportunity Grant Information for Students](https://www.sbctc.edu/paying-for-college/opportunity-grant-student.aspx)

---

### Criterion 4 — Pathway C: household gross income (most recent 30 days) at or below 200% of the Federal Poverty Level

- **Screener fields**:
  - `household_size` (Screen level) — sets the FPL row
  - `income_streams[].type`, `income_streams[].amount`, `income_streams[].frequency` (per HouseholdMember) — gross income inputs
- **Note**: The program evaluates **gross income (before any taxes or deductions are taken out) for the most recent 30 days**, not annual income or net/take-home pay. Use `calc_gross_income('monthly', ['all'])` summed across all household members (which already converts the screener's per-member income streams to a monthly total), compared to 200% of the HHS FPL monthly amount for `household_size`. The comparison is `<=` (inclusive — see Scenario 7). Pair with the active FPL year in the program config (2026 — see the FPL table below). At application time the program requires 30 days of income documentation (e.g., paystubs), which is consistent with the monthly framing.
- **Methodology approximation (not a data gap)**: The screener captures current/ongoing monthly income, while the program technically evaluates *the most recent 30 days*. For households with stable income these are equivalent. For households mid-transition (just started or just lost a job), the screener-based estimate may diverge slightly from what an actual program reviewer would calculate from 30 days of paystubs. This is a standard limitation of monthly-income screeners across MFB programs and not specific to ORCA LIFT.
- **Source**: [myORCA — ORCA LIFT](https://info.myorca.com/lift/) ("Your gross income for the most recent 30 days is at or below: [size 1: $2,660; size 2: $3,607; ...]"); [King County Metro — ORCA LIFT](https://kingcounty.gov/en/dept/metro/fares-and-payment/reduced-fares/orca-lift) ("To qualify, your gross household income (before taxes are taken out) must be no more than 200 percent of the Federal Poverty Level, as established by the U.S. Health and Human Services Department." — and on the documentation side, "Proof of gross income for last 30 days (paystubs...)"); [Pierce Transit — ORCA LIFT](https://piercetransit.org/orca/#ORCA-LIFT) (regional corroboration); [Community Transit — ORCA](https://www.communitytransit.org/orca) (Snohomish County corroboration)

---

### Criterion 5 — Washington state residency

- **Screener fields** (Screen level):
  - `zipcode`
  - `county`
- **Note**: White-label filtering (`wa`) handles state residency at the program level, so the calculator typically does not need to re-check ZIP/county. The ORCA LIFT card is only useful on participating Puget Sound transit (primarily King, Pierce, Snohomish, and Kitsap counties); we are intentionally not filtering by county per design decision, but the program description surfaces this service-area limitation so users outside Puget Sound understand the card's practical use. **Note: no source in our research explicitly states a residency requirement** — residency is implicit from program administration via King County.
- **Source**: [King County Metro — ORCA LIFT](https://kingcounty.gov/en/dept/metro/fares-and-payment/reduced-fares/orca-lift) (program administered by King County, agency price list shows only Puget Sound region participants)

---

### What is NOT an eligibility criterion

These are commonly assumed to be checks but are explicitly NOT part of ORCA LIFT's eligibility logic. The calculator should not gate on any of them.

- **No citizenship/immigration restriction.** The program explicitly has no citizenship or immigration status requirements. The config's `legal_status_required` lists all 6 base values (`citizen`, `non_citizen`, `refugee`, `gc_5plus`, `gc_5less`, `otherWithWorkPermission`) so the program is offered regardless of household legal status. The screener has no citizenship/immigration field (a global screener gap per `mfb_screener_fields_source.md`), but it is not a gap that affects this program since no check is needed.
  - Source: [myORCA — ORCA LIFT FAQ](https://info.myorca.com/lift/) ("Do I need U.S. citizenship? No. ORCA LIFT has no citizenship or immigration status requirements."); [Help Me Grow Washington](https://helpmegrowwa.org/orca-lift).
- **No asset / resource test.** ORCA LIFT publishes no asset limit. The `household_assets` field is not used for eligibility.
- **No work history requirement.** Unlike SSDI or SSI, ORCA LIFT does not require Social Security work credits, lifetime work history, or any employment history.
- **No disability, pregnancy, or medical-condition requirement.** Member-level health flags (`disabled`, `pregnant`, `long_term_disability`, `visually_impaired`) do not affect ORCA LIFT eligibility. They would be relevant for the separate Disability RRFP program — out of scope for this ticket.

### Administrative requirements (handled via documents/application, NOT calculator)

- Proof of identity and proof of income are required at application time. Captured in the `documents` array of the config.
- Application can be online (Reduced Fare Portal), by phone (CHAP at 1-800-756-5437), or in person at authorized enrollment offices. Captured in the program description and navigators.
- Card is valid for 2 years; renewal requires re-qualification. Surfaced in the description.

### Data gaps summary

Complete inventory of the data the calculator needs, mapped to available screener fields:

| Data needed | Screener field | Status | Handling |
|---|---|---|---|
| Age 19–64 | `birth_year`, `birth_month` (HouseholdMember) | ✓ Available | Calculator computes age per member; counts those in range to scale benefit |
| Apple Health / Medicaid enrollment | `medicaid` current benefit; `wa_apple_health_medicaid` / `wa_apple_health_for_kids` (CurrentBenefit join table) | ✓ Available | All three checked via `has_benefit()` for Criterion 2 |
| SNAP / Basic Food enrollment | `snap` current benefit (`current_benefits`) | ✓ Available | Checked via `has_benefit()` for Criterion 2 |
| WIC enrollment | `wic` current benefit (`current_benefits`) | ✓ Available | Checked via `has_benefit()` for Criterion 2 |
| WA State Opportunity Grant enrollment | *(no field — suggested: add an `opportunity_grant` entry to the Section 10 "Current Public Assistance Benefits" follow-up list, alongside the `pell_grant` current benefit)* | ⚠️ **Data gap** | **Inclusive assumption** — calculator skips Pathway B (Criterion 3) entirely. Opportunity Grant recipients are caught via Criterion 4 (the grant itself requires ≤200% FPL). Surfaced in description so users can apply via this pathway directly. **Closing this gap**: adding the suggested entry would let the calculator check it directly. |
| Household gross income | `income_streams[].type` / `.amount` / `.frequency` (HouseholdMember), `household_size` (Screen) | ✓ Available | `calc_gross_income('monthly', ['all'])` compared to 200% FPL for `household_size` |
| WA residency / Puget Sound location | `zipcode`, `county` (Screen) | ✓ Available | Handled by `white_label = wa` at program level; service-area limitation surfaced in description |
| Citizenship / immigration status | *(no field — global screener gap)* | ✓ Not needed | Program has no restriction; all 6 `legal_status_required` values used |
| Asset / resource limit | `household_assets` (Screen) | ✓ Not needed | Program has no asset test |

## Priority Criteria

None published. ORCA LIFT does not currently advertise priority eligibility within the income-qualified population.

Note: Users who meet the higher bar of *≤80% FPL plus enrollment in TANF/SFA, RCA, ABD, PWA, SSI, or HEN* should apply for the **Subsidized Annual Pass** instead (free fares rather than $1.00 fares). That is a separate program — flag in the description but do not gate ORCA LIFT on it.

## Benefit Value

**Methodology — informed estimate based on the monthly PugetPass differential.**

The ORCA LIFT benefit is the difference between the regular adult fare and the discounted LIFT fare. The cleanest dollar anchor is the monthly PugetPass price ladder:

- Regular Adult PugetPass (covering $3.00 trip value): **$108.00/month**
- ORCA LIFT PugetPass (covering $1.00 trip value): **$36.00/month**
- **Monthly savings = $108 − $36 = $72.00 per eligible cardholder per month**
- **Annual savings = $72 × 12 = $864.00 per eligible cardholder per year**

**Calculator value (stored annually):** `$864 × (count of household members aged 19–64)` per year. The value is stored as an annual amount; when `value_format = null` (monthly display), the frontend divides by 12 to show $72/month.

**Ridership caveat:** $72/month ($864/year) is a representative estimate anchored to monthly-pass usage. Actual savings vary with ridership:

- Casual rider (~10 trips/month): saves ~$20/month / **$240/year** ($2 per-trip × 10 trips)
- Regular commuter (~36 trips/month, the break-even point for buying a monthly pass): saves ~$72/month / **$864/year**
- Heavy commuter (60+ trips/month): saves $120+/month / **$1,440+/year**

We anchor the calculator value to the monthly-pass differential because it is the cleanest citable figure (both endpoints are published in the King County Metro PugetPass cost table) and it reflects typical usage for someone whose transit needs justify acquiring an ORCA LIFT card. Estimates for users with very different transit patterns will be less accurate.

- Source — Adult fare: [King County Metro — Prices](https://kingcounty.gov/en/dept/metro/fares-and-payment/prices) (effective September 1, 2025; "Adult fares (19 to 64 years) Single ride $3.00" and PugetPass cost table "$3.00 trip value → $108.00/month")
- Source — LIFT fare: [King County Metro — ORCA LIFT](https://kingcounty.gov/en/dept/metro/fares-and-payment/reduced-fares/orca-lift) ("Your ORCA LIFT card gives you a reduced fare of $1.00") and PugetPass table ("$1.00 trip value → $36.00/month")

## 2026 FPL Reference (200% monthly, 48 contiguous states)

Per the [HHS 2026 Detailed Poverty Guidelines](https://aspe.hhs.gov/sites/default/files/documents/b1bfa16b20ae9b89d525bc35de7c1643/detailed-guidelines-2026.pdf):

| Household size | 200% FPL monthly |
|---|---|
| 1 | $2,660.00 |
| 2 | $3,606.67 |
| 3 | $4,553.33 |
| 4 | $5,500.00 |
| 5 | $6,446.67 |
| 6 | $7,393.33 |
| 7 | $8,340.00 |
| 8 | $9,286.67 |

## Test Scenarios

This spec defines 8 scenarios covering every major branch of the eligibility logic. Three of these are extracted into `wa_orca_lift_test_cases.json` for the automated validation suite (see the "Extracted for JSON validation" note below). All ages are valid as of the research date (May 12, 2026).

### Scenario 1: Single Working Adult Below 200% FPL in King County

**What we're checking**: Income pathway (Criterion 4) — a single working adult under 200% FPL qualifies for ORCA LIFT through income alone, with no categorical benefits and no special circumstances.
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98101`, county `King County`
- **Household size**: 1
- **Person 1** (head): birth `Mar 1991` (age 35), `relationship: headOfHousehold`
  - Income: Employment / Wages, `$2,000`/month
  - Insurance: I do not have health insurance
- **Current benefits**: none

**Why this matters**: The most common ORCA LIFT applicant profile — a working adult whose wages fall below 200% FPL in the program's core service area (King County). This is the program's primary regression test: if this scenario breaks, the income pathway is broken end-to-end. Expected calculator output: 1 × $864 = $864/year (stored annual; displayed as $72/month).

---

### Scenario 2: Single Adult Over 200% FPL With No Categorical Benefit

**What we're checking**: Income ceiling enforcement (Criterion 4) — an adult earning above the 200% FPL threshold with no Apple Health/SNAP/WIC enrollment is correctly denied.
**Expected**: Ineligible

**Steps**:
- **Location**: ZIP `98101`, county `King County`
- **Household size**: 1
- **Person 1** (head): birth `Mar 1991` (age 35), `relationship: headOfHousehold`
  - Income: Employment / Wages, `$4,500`/month
  - Insurance: Employer-provided health insurance
- **Current benefits**: none

**Why this matters**: The most common ineligible case — a moderate-income adult above the ceiling with no qualifying benefits. Confirms that the income test rejects households over the threshold and that the calculator doesn't silently let everyone through. Without this scenario, an open income test bug could go undetected.

---

### Scenario 3: Family on SNAP With Income Over Threshold, Pierce County

**What we're checking**: Categorical override (Criterion 2) — Washington Basic Food (SNAP) enrollment qualifies the household even when total income exceeds 200% FPL; benefit value scales by count of members aged 19–64.
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98402`, county `Pierce County`
- **Household size**: 4
- **Person 1** (head): birth `Jan 1996` (age 30), `relationship: headOfHousehold`
  - Income: Employment / Wages, `$6,000`/month
  - Insurance: Employer-provided health insurance
- **Person 2**: birth `Jan 1961` (age 65), `relationship: spouse`
  - Insurance: Medicare
- **Person 3**: birth `Apr 2009` (age 17), `relationship: child`
  - Insurance: I do not have health insurance
- **Person 4**: birth `Feb 2018` (age 8), `relationship: child`
  - Insurance: I do not have health insurance
- **Current benefits**: `snap` (Washington Basic Food)

**Why this matters**: Many working families with children are above 200% FPL on paper but receive Basic Food — and those families still qualify for ORCA LIFT through the categorical pathway. This is the most distinctive branch of ORCA LIFT eligibility, and it's easy for a calculator to silently skip if the dev only implements the income test. Also validates that benefit value reflects only the 19–64 member (the 30-year-old): the 65-year-old would use Senior RRFP and the children would use Youth Ride Free — both out of scope. Expected calculator output: 1 × $864 = $864/year (stored annual; displayed as $72/month).

---

### Scenario 4: Two-Adult Household on Apple Health/Medicaid, King County

**What we're checking**: Categorical via Apple Health (Criterion 2) — Apple Health/Medicaid enrollment qualifies a household with two adults aged 19–64; per-member benefit value scales linearly.
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98103`, county `King County`
- **Household size**: 2
- **Person 1** (head): birth `Jan 1996` (age 30), `relationship: headOfHousehold`
  - Income: Employment / Wages, `$2,500`/month
  - Insurance: Apple Health (Medicaid)
- **Person 2**: birth `Jan 1998` (age 28), `relationship: spouse`
  - Income: Employment / Wages, `$2,000`/month
  - Insurance: Apple Health (Medicaid)
- **Current benefits**: `medicaid`

**Why this matters**: Apple Health (Washington's Medicaid brand) is one of the three categorical pathways explicitly listed by King County Metro. This scenario also exercises per-member benefit value scaling: with two eligible adults, the household value should double. Catches calculator bugs where value defaults to one cardholder regardless of household composition. Expected calculator output: 2 × $864 = $1,728/year (stored annual; displayed as $144/month).

---

### Scenario 5: Young Family on WIC With Pregnant Spouse, Snohomish County

**What we're checking**: Categorical via WIC (Criterion 2) — WIC enrollment qualifies a household with a pregnant member; the `pregnant` flag on a household member does not disrupt eligibility logic.
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98201`, county `Snohomish County`
- **Household size**: 3
- **Person 1** (head): birth `Jan 2001` (age 25), `relationship: headOfHousehold`
  - Income: Employment / Wages, `$3,500`/month
  - Insurance: Employer-provided health insurance
- **Person 2**: birth `Jan 2002` (age 24), `relationship: spouse`
  - `pregnant = true`
  - Income: Employment / Wages, `$1,500`/month
  - Insurance: Employer-provided health insurance
- **Person 3**: birth `Apr 2025` (age 1), `relationship: child`
  - Insurance: Apple Health (Medicaid)
- **Current benefits**: `wic`

**Why this matters**: WIC is the third categorical pathway and is most commonly held by households with pregnant members and young children. This scenario validates that a typical young-family WIC composition with `pregnant = true` on a spouse triggers ORCA LIFT eligibility correctly, and confirms the calculator treats `pregnant` as a member-level flag without surprising the eligibility logic. Expected calculator output: 2 × $864 = $1,728/year (stored annual; displayed as $144/month).

---

### Scenario 6: Grandparent Raising Grandchildren — No 19-64 Member

**What we're checking**: Age gate (Criterion 1) — a household that qualifies on both income AND categorical pathways but has no member aged 19–64 is correctly ineligible because no one can receive a card.
**Expected**: Ineligible

**Steps**:
- **Location**: ZIP `98101`, county `King County`
- **Household size**: 3
- **Person 1** (head): birth `Jan 1956` (age 70), `relationship: headOfHousehold`
  - Income: Pension, `$2,000`/month
  - Income: Investment, `$1,000`/month
  - Insurance: Medicare, Apple Health (Medicaid)
- **Person 2**: birth `Mar 2014` (age 12), `relationship: grandChild`
  - Insurance: Apple Health (Medicaid)
- **Person 3**: birth `Mar 2016` (age 10), `relationship: grandChild`
  - Insurance: Apple Health (Medicaid)
- **Current benefits**: `medicaid`

**Why this matters**: Grandparent-headed households raising grandchildren are common in lower-income Puget Sound demographics. This scenario validates that the age gate (Criterion 1) is enforced as a hard requirement — the household qualifies on both income ($3,000/month is below the $4,553.33 size-3 threshold) AND categorical (Medicaid), but no member is 19–64, so no one can actually receive a card. Catches a common AI/calculator bug where income/categorical alone are treated as sufficient and the age requirement is silently dropped.

---

### Scenario 7: Income Exactly at 2026 200% FPL Threshold

**What we're checking**: Boundary inclusivity (Criterion 4) — income at exactly the 200% FPL threshold for the household size is eligible; the rule is "at or below," not "below."
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98101`, county `King County`
- **Household size**: 1
- **Person 1** (head): birth `Jan 1996` (age 30), `relationship: headOfHousehold`
  - Income: Employment / Wages, `$2,660`/month (exactly the 2026 200% FPL for size 1)
  - Insurance: I do not have health insurance
- **Current benefits**: none

**Why this matters**: The King County Metro source uses the phrase "no more than 200 percent" (inclusive language). This boundary test ensures the calculator uses `<=` rather than `<`. An off-by-one rejection at the threshold would silently exclude every household landing exactly on the line — a real and common occurrence for households on standardized benefit amounts. Expected calculator output: 1 × $864 = $864/year (stored annual; displayed as $72/month).

---

### Scenario 8: Income $1 Over 2026 200% FPL Threshold

**What we're checking**: Boundary precision (Criterion 4) — income $1 above the 200% FPL threshold with no categorical pathway is correctly ineligible.
**Expected**: Ineligible

**Steps**:
- **Location**: ZIP `98101`, county `King County`
- **Household size**: 1
- **Person 1** (head): birth `Jan 1996` (age 30), `relationship: headOfHousehold`
  - Income: Employment / Wages, `$2,661`/month (one dollar above the 2026 200% FPL for size 1)
  - Insurance: I do not have health insurance
- **Current benefits**: none

**Why this matters**: The ceiling-side companion to Scenario 7. Together they bracket the threshold exactly — Scenario 7 confirms the calculator includes the boundary, this scenario confirms it excludes one dollar above. Without both, a comparison-operator bug could pass undetected.

---

### Coverage matrix

| Branch | Eligible scenario(s) | Ineligible scenario(s) |
|---|---|---|
| Income test (≤ 200% FPL) | 1, 7 | 2, 8 |
| Categorical: Apple Health/Medicaid | 4, 6 | — |
| Categorical: SNAP | 3 | — |
| Categorical: WIC | 5 | — |
| Age 19–64 requirement | 1, 2, 3, 4, 5, 7, 8 | 6 |
| Benefit value scales by 19–64 count | 4 ($1,728/year), 5 ($1,728/year) | n/a |
| Boundary precision | 7 (at threshold) | 8 (just over) |

### Extracted for JSON validation (`wa_orca_lift_test_cases.json`)

Per the 2.3 guidance, three scenarios are extracted into the automated validation file. These three give the broadest coverage of the eligibility logic:

- **Scenario 1** → JSON case 1 (golden path / primary regression)
- **Scenario 2** → JSON case 2 (primary exclusion)
- **Scenario 3** → JSON case 3 (categorical override + age-filtered value scaling)

The remaining 5 scenarios (4–8) live in this spec as documentation for the dev and QA to walk through manually during implementation.

## Notes for the Dev

- Eligibility is a household-level OR across three pathways (categorical / Opportunity Grant data gap / income). The data gap is intentionally skipped in the calculator (inclusivity assumption).
- Benefit value scales linearly with `count(household_members where 19 <= age <= 64)`. Use `birth_year`/`birth_month` for age — `age` is deprecated.
- The categorical Apple Health check covers three cases: the `medicaid` current benefit, the `wa_apple_health_medicaid` program, and the `wa_apple_health_for_kids` program. All three are checked via `has_benefit()` — if any returns true, the household qualifies categorically.
- Use the 2026 HHS Poverty Guidelines for the 200% threshold (table above).
- The service-area limitation is surfaced in the description, not enforced by the calculator.
- No `base_program` value currently fits ORCA LIFT — flag for the dev team to consider adding `"orca_lift"` or a generic `"transit_reduced_fare"` once the related ORCA programs (Youth, Senior RRFP, Disability RRFP, Subsidized Annual Pass) are added.
- Optional screener enhancement: there is no `orca_lift` current benefit, so households already enrolled will still see ORCA LIFT recommended in their results. Consider adding an `orca_lift` entry to the WA white-label's Section 10 current-benefits follow-up list (alongside `lifeline` / `section_8`-style state-specific transit/regional benefits) so `has_benefit("orca_lift")` can suppress duplicate recommendations.
- Navigator emails: all three verified by the program researcher (`chap@kingcounty.gov`, `info@withinreachwa.org`, `info@ccsww.org`).

## Research Sources

1. [King County Metro — ORCA LIFT](https://kingcounty.gov/en/dept/metro/fares-and-payment/reduced-fares/orca-lift)
2. [King County Metro — Prices (effective September 1, 2025)](https://kingcounty.gov/en/dept/metro/fares-and-payment/prices)
3. [King County Reduced Fare Portal](https://reducedfare.kingcounty.gov/en-US/orca-lift-main/)
4. [myORCA — ORCA LIFT](https://info.myorca.com/lift/)
5. [HHS — 2026 Detailed Poverty Guidelines (PDF)](https://aspe.hhs.gov/sites/default/files/documents/b1bfa16b20ae9b89d525bc35de7c1643/detailed-guidelines-2026.pdf)
6. [Help Me Grow Washington — ORCA LIFT](https://helpmegrowwa.org/orca-lift)
7. [Pierce Transit — ORCA / ORCA LIFT](https://piercetransit.org/orca/#ORCA-LIFT)
8. [Community Transit — ORCA](https://www.communitytransit.org/orca)
9. [Catholic Community Services of Western Washington — ORCA LIFT](https://ccsww.org/services/orca-lift/)
10. [SBCTC — Opportunity Grant Information for Students](https://www.sbctc.edu/paying-for-college/opportunity-grant-student.aspx)

## JSON Test Cases
File: `wa_orca_lift_test_cases.json`

## Program Configuration
File: `wa_orca_lift_initial_config.json`
