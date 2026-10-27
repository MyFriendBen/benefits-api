# Missouri Property Tax Credit (Circuit Breaker)

## Program Details

- **Program**: Missouri Property Tax Credit (PTC), commonly called the Circuit Breaker
- **State**: MO
- **Program key**: `mo_pts` (the `mo_ptc` in the original draft collides confusingly with the already-registered `mo_aca_ptc`, the ACA premium tax credit)
- **Policy year**: 2025 (claim year) — the program's configured `year`. For a tax credit that is the year a household screening now files: the calendar year just ended, rolling over on January 1. The 2025 claim is due April 15, 2026, and DOR accepts it up to three years late.
- **Law in force**: claim year 2025 runs under RSMo §135.030 as it stood before Missouri's 2026 expansion. The expansion (limits of $38,200–$48,000, caps of $1,055/$1,550, a 2% phaseout cap) starts with claim year 2026, which becomes the configured year on January 1, 2027; this spec's earlier revision in git history describes it.
- **Chart-verified**: DOR published the 2025 Property Tax Credit Chart, so every expected value below is read from it as well as computed by PolicyEngine 2.9.0, and the two agree.
- **Calculator type**: PE Custom
- **Value cadence/type**: `value_format: estimated_annual`, `value_type: tax_credit` (annual, refundable — any credit exceeding tax liability is refunded; RSMo §135.020)

The claimant's own legal/immigration status is not a PTC eligibility factor. Criterion 5 concerns employer conduct, not the claimant's immigration status.

## Eligibility Criteria

1. **Qualifying pathway** — claimant or spouse (except D, claimant-only) satisfies one of:
   - **(A)** Attained age 65 on or before Dec 31 of the claim year, and was a Missouri resident all year (⚠️ *data gap* — full-year MO residency isn't collected; assume satisfied). Age is computed as of Dec 31 of the claim year, not the screening date. The statutory death-related residency exceptions (RSMo §135.010(1)) are subsumed by this inclusive full-year-residency assumption; no separate scenario is required.
   - **(B)** A veteran who became **100% disabled as a result of such service** (RSMo §135.010(1)). The inclusive proxy is a **`veteran` income stream** plus `disabled`/`long_term_disability` (⚠️ *data gap* — exact VA rating/service-causation isn't collected). **Correction to the original draft:** the draft named the `veteran` *field* as the proxy's first term. `HouseholdMember.veteran` exists in the model and serializer but is never populated by the frontend (local DB: `None` 19,352 / `False` 654 / `True` 7), so a `veteran`-field proxy is dead code — every household would fail it. The `veteran` income type *is* collected, and using it is the established workaround (`ks/k40h`, `co/denver_property_tax_relief`, `nc/nc_head_start`). Implemented as `member.calc_gross_income("yearly", ["veteran"]) > 0 and (member.disabled or member.long_term_disability)`. Note: DOR's veteran-**income** treatment (criterion 2) separately covers a below-100%-rated veteran; that is a rule about which income counts, not an alternate eligibility pathway.
   - **(C)** Disabled: "inability to engage in any substantial gainful activity by reason of any medically determinable physical or mental impairment which can be expected to result in death or which has lasted or can be expected to last for a continuous period of not less than twelve months" (no percentage rating required).
   - **(D)** Claimant only (not spouse) reached age 60 on or before Dec 31 of the claim year and received surviving-spouse Social Security benefits during the year.
   - Screener fields: `birth_year`, `birth_month`, `disabled`, `long_term_disability`, `veteran`, `relationship = spouse`, `income_streams[].type = sSSurvivor` (claimant only).
   - Source: RSMo §135.010(1),(2).

2. **Household PTC income** — determine the filing status and assistance unit, count income, apply the deduction, and compare to the applicable limit:
   - **Filing status**: Form MO-PTC 2025 offers **single**, **married filing combined**, and **married – living separate for entire year** (a separate claim with no deduction). MFB does not collect the claimant's actual PTC filing status (⚠️ *data gap*). Committed inclusive proxy: derive filing status from household structure — if a spouse is listed (`relationship = spouse`), treat the claim as married filing combined; otherwise treat it as single. MFB cannot identify a spouse living separately for the whole year. (From claim year 2026 married-filing-separate claimants are no longer eligible; that does not apply to 2025.)
   - **Assistance unit**: PTC income counts the claimant, spouse, and minor children; an adult child's income is excluded regardless of dependency status.
   - **PTC income** = Missouri AGI (RSMo §143.121), plus required add-backs (full Social Security benefit, railroad retirement, veterans' payments/benefits, other pensions/annuities, public assistance/unemployment received in cash, SSI, child support, interest on U.S./state/subdivision obligations), with no deduction for losses not incurred in a trade or business (RSMo §135.010(5)(d)), less the filing deduction: **$0** (single, or married living separate) / **$2,000** (married-combined, renter or not full-year owner) / **$4,000** (married-combined, full-year owner) — Form MO-PTC 2025, Line 7. Detailed add-back itemization and any nonbusiness-loss claim are a data gap (⚠️ use reported gross income as proxy; the calculator does not subtract an unmodeled nonbusiness loss).
   - **Veteran-income exclusion**: a claimant/spouse who is 100% service-connected disabled (pathway B) is not required to list veterans' payments/benefits as income at all. DOR instructions extend this exclusion to a veteran rated **below** 100% whose qualifying impairment results entirely from military service and meets the same substantial-gainful-activity/duration-or-death standard as the general disability pathway (Form MO-PTC 2025 Instructions) — this is a rule about which income is excluded, not a broader eligibility pathway. MFB uses the same proxy as pathway B — a `veteran` **income stream** plus `disabled`/`long_term_disability`, not the unpopulated `veteran` field — since the exact rating/service-causation detail isn't collected (⚠️ *data gap*).
   - Veteran income must route to PolicyEngine's `veterans_benefits` variable, not the shared pension mapping (`PensionIncomeDependency` groups `veteran` with `pension` under `taxable_pension_income` today) — otherwise the veterans'-benefit exclusion above silently never triggers.
   - The exclusion is additionally gated on PolicyEngine's Person-level `is_fully_disabled_service_connected_veteran`, which has no formula and is therefore false unless MFB sends it. **The mapping and the flag are jointly required.** Measured at PE 1.786.5 at claim year 2026 on Scenarios 13 and 22 (both expect $1,100): `veterans_benefits` mapping without the flag → $0 / $272; flag set but income routed to `taxable_pension_income` → $0 / $272; both → $1,100 / $1,100. The $272 case returns `eligible=true` with a wrong value, so tests must assert value and not eligibility alone. At claim year 2025 the unexcluded $46,800 is over the $30,000 limit, so the failure shows as not eligible instead.
   - **Resulting PTC income (Line 8, net household income) must be ≤** the applicable 2025 limit, which does not vary by filing status: renter or part-year owner **$27,500** in statute, but the phaseout leaves no renter credit above **$27,200**, which is the limit DOR's form states; full-year homeowner **$30,000**. Before the deduction a married couple's limits are $29,200 and $34,000 (the form's eligibility diagram). Full-year-ownership status is assumed when duration is unavailable (⚠️ *data gap* — treat any indicated homeowner as full-year owner).
   - Screener fields: `income_streams`, `relationship` (including spouse/child, determines filing status and assistance unit), `birth_year`, `birth_month` (minor-child determination), and `housing_situation` (owner/renter deduction tier).
   - Source: RSMo §135.010(1),(5); RSMo §135.030(1)(1); RSMo §143.121; Form MO-PTC (Line 7).

3. **Missouri homestead** — claimant must have owned and occupied, or rented and occupied, a Missouri homestead (dwelling + up to 5 surrounding acres) during the tax year.
   - ⚠️ **Data gap — tax-year Missouri homestead location:** MFB does not collect historical homestead location. Treat an otherwise qualifying reported owned/rented residence as a Missouri homestead for the claim year; DOR verifies the tax-year property/rental documentation at filing. Current `zipcode`/`county` support routing only and do not independently establish this historical fact.
   - Screener field: `housing_situation`.
   - Source: RSMo §135.010(4); DOR Property Tax Credit qualification instructions. (§135.025 governs accrued taxes/rent, maximum amounts, and allocation, not this gate.)

4. **Positive qualifying payment** — claimant must have paid more than $0 in qualifying property tax or gross rent on the homestead during the tax year. For benefit calculation, rent equivalent equals 20% of qualifying gross rent. A renter whose facility doesn't pay property tax doesn't qualify (⚠️ *data gap* — assume facility pays).
   - Screener fields: `housing_situation`, `expenses[].type = rent` or `propertyTax`.
   - Source: RSMo §135.010(3),(6),(7); Form MO-PTC Instructions (tax-exempt-facility renter exclusion).

5. **Unauthorized-worker employer-conduct gate** — Missouri law makes any employer (including an individual) who employs unauthorized workers ineligible for any Chapter 135 tax credit, including the PTC. ⚠️ *Data gap*: MFB does not collect whether the claimant is an employer or whether this affirmation can truthfully be made. Committed inclusive treatment: assume the claimant can truthfully make the required affirmation; do not exclude the household in the screener. DOR verifies the affirmation when the claim is filed.
   - Screener fields: none.
   - Source: RSMo §285.025; Form MO-PTC signature declaration.

## Priority Criteria

None. The PTC has no priority, preference, or served-first criteria — all applicants meeting the eligibility rules receive the credit.

## Benefit Value

1. Annual, refundable tax credit (`value_format: estimated_annual`, `value_type: tax_credit`).
2. PTC income = MO AGI less filing deduction plus add-backs (criterion 2).
3. Two income limits gate eligibility (criterion 2); above the limit, not eligible.
4. Minimum base: **$14,300**. At or below it, credit = qualifying property tax/rent-equivalent paid, capped at the statutory maximum, no phaseout.
5. Statutory maximum: **$750** renters / **$1,100** homeowners.
6. Rent equivalent = 20% of qualifying gross rent paid.
7. Above the minimum base, apply the statutory table method below — or read DOR's 2025 Property Tax Credit Chart, which tabulates it.
   - PTC income is placed in $300-wide bands counting up from the minimum base; phaseout = 1/16 percentage point per band, capped at **4%** (never reached below the $30,000 limit, where it is 3.3125%).
   - Qualifying payment is placed in $25-wide bands counted down from the statutory cap.
   - Bands are open at the lower bound and closed at the upper, so a $25 payment band's midpoint is a half-dollar value ($726–$750 → $737.50) and a $300 income band's is a whole dollar ($14,301–$14,600 → $14,450).
   - Credit = (payment-band midpoint) − (phaseout % × income-band midpoint), rounded half-up to the nearest dollar.
   - **Terminal-band rule**: the final income band is truncated at the $30,000 limit — the chart's last row is $29,901–$30,000, not a full $300 band.
8. Result floored at **$0** — a household can satisfy every eligibility gate and still receive $0 (not a statutory exclusion). MFB reports a $0 result as ineligible and does not surface it; see Scenario 19.
9. Credit is computed **before** any delinquent-tax debt offset (RSMo §135.815, extended by §135.830); the offset is a downstream payment-administration step, not part of the calculator's output.
10. Unmodeled allocation detail — special assessments/penalties/interest/service charges, partial ownership, part-year ownership, multiple homesteads, mixed/business use, non-arm's-length or excess rent, bundled services, shared-rent/facility adjustments (RSMo §135.010, §135.025): use the household's reported out-of-pocket property tax or rent as an inclusive proxy; DOR may adjust the qualifying amount when the claim is filed.

Source: RSMo §135.030 (formula, limits and caps for claim years through 2025); 2025 Property Tax Credit Chart (Form MO-PTC 2025 Instructions, pages 14–16), which every scenario value below is checked against.

## Acceptance Criteria

Unless stated otherwise, scenarios use a valid Missouri location, no unrelated income/expenses, and the committed data-gap treatments above. "Valid Missouri location" is a current-routing assumption only (via `zipcode`/`county`); it does not by itself establish tax-year homestead location, which follows the committed inclusive data-gap treatment in criterion 3.

**Binding implementation assertions** (independent of the scenario list below):
- [ ] Age is computed as of December 31, 2025 from `birth_year`/`birth_month`, not the screening date.
- [ ] Filing status is derived via the spouse-presence proxy, the $0/$2,000/$4,000 deduction is applied by filing status and ownership, and the $27,200 (renter, effective) and $30,000 (full-year owner) limits are applied to the result.
- [ ] The survivor pathway (D) is routed claimant-only; it does not qualify a household through the spouse.
- [ ] General disability (pathway C) maps to PolicyEngine's `is_disabled`-compatible variable, not `is_ssi_disabled`.
- [ ] Veteran income is mapped to `veterans_benefits` on both the claimant and spouse sides — not the shared pension dependency — so the veterans'-benefit exclusion (criterion 2) actually triggers, **and** `is_fully_disabled_service_connected_veteran` is sent so the exclusion is un-gated. Both are required; either alone leaves the credit computed off unexcluded income.

**Implementation-discovered assertions** (added during build; each was found by a scenario failing live against PolicyEngine 1.786.5, and each is a shared-dependency routing defect rather than a rule error):
- [ ] **Age input is the end-of-claim-year age.** The shared `AgeDependency` sends `member.calc_age()`, which measures against the *screening date*. Scenario 6's September-1960 claimant therefore arrives as `age=64` and fails the age-65 pathway when screened before September — the calculator sends a claim-year age instead.
- [ ] **Survivor benefits are sent as `social_security_survivors`, not only the `social_security` total.** PolicyEngine defines `social_security` as an `adds` aggregate over its four components; setting the total leaves every component at zero, and `mo_ptc_taxunit_eligible`'s survivor test reads the component. Without the component input, Scenario 12 returns ineligible / $0.
- [ ] **Reported SSI is sent as `ssi`, not `ssi_reported`.** `mo_ptc_gross_income` adds the `ssi` variable. `ssi_reported` feeds only `applicable_ssi`, which PolicyEngine documents as deprecated and which no program reads, so reported SSI never reaches PTC income. With `ssi_reported`, Scenario 17 returns $1,078 instead of $883 (the child's $4,800 SSI is dropped from household income).
- [ ] Benefit calculation uses $300-wide income bands, $25-wide payment bands, the 1/16-point-per-band phaseout capped at 4%, half-dollar band midpoints, and half-up whole-dollar rounding, floored at $0 — matching the 2025 chart.
- [ ] Output is annual and refundable (`value_format: estimated_annual`, `value_type: tax_credit`).
- [ ] All 22 executable scenarios below return the committed eligibility result and benefit value.

No new screener field or feature is required by any acceptance criterion above.

## Test Scenarios

### Scenario 1: Golden-Path Senior Renter
**What this tests**: Validates the baseline age-65 pathway with a renter homestead and positive rent paid.
**Expected**: Eligible, **$728**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1953` (age 72), Has income: `Yes`, Income type: `Social Security`, Income amount: `$14,400` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$6,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $14,400 (band $14,301–$14,600, midpoint $14,450, phaseout 0.0625%); qualifying rent-equiv 20%×$6,000=$1,200, capped at $750 → band midpoint $737.50. Credit = $737.50 − $9.03 = $728.47, rounds to $728. 2025 chart: row $14,301–$14,600, column $726–$750 = $728.

**Relevant evidence or source**: Criteria 1(A), 2, 4; Benefit Value items 4–7.

---

### Scenario 2: Single Renter at $27,200, the Last Band with a Renter Credit
**What this tests**: The effective single-renter limit: the last income band in which any renter credit remains.
**Expected**: Eligible, **$11**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1957` (age 68), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$27,200` per year (single filer, $0 deduction), Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$9,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $27,200 (band $26,901–$27,200, midpoint $27,050, phaseout 2.6875%); qualifying rent-equiv 20%×$9,000=$1,800, capped at $750 → midpoint $737.50. Credit = $737.50 − $726.97 = $10.53, rounds to $11. 2025 chart: row $26,901–$27,200, column $726–$750 = $11. The next row is blank for every renter column, which is why DOR states $27,200 as the renter limit.

**Relevant evidence or source**: Criteria 2, 4; Benefit Value items 3, 7.

---

### Scenario 3: Single Homeowner Income Exactly at the $30,000 Limit
**What this tests**: Single-homeowner income-limit exact boundary.
**Expected**: Eligible, **$95**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1957` (age 68), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$30,000` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,800` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Final truncated band $29,901–$30,000 (midpoint $29,950, phaseout 3.3125%); qualifying tax $1,800 capped at $1,100 → top owner band midpoint $1,087.50. Credit = $1,087.50 − $992.09 = $95.41, rounds to $95. 2025 chart: row $29,901–$30,000, column $1,076–$1,100 = $95.

**Relevant evidence or source**: Criteria 2, 3, 4; Benefit Value items 3, 7.

---

### Scenario 4: Single Renter $1 Over $27,200
**What this tests**: A renter just past the effective limit, with positive rent present, isolating income as the sole cause of ineligibility.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1953` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$27,201` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$6,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $27,201 falls in the $27,201–$27,500 band, where the phaseout exceeds the largest renter credit: 2025 chart: row $27,201–$27,500 is blank for every renter column. Under the statute's $27,500 limit but with nothing to pay, so not eligible.

**Relevant evidence or source**: Criterion 2.

---

### Scenario 5: Age Exactly 65 and PTC Income Exactly at the $14,300 Minimum Base
**What this tests**: Age-65 boundary and minimum-base boundary.
**Expected**: Eligible, **$1,000**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1960` (age 65), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$14,300` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: At the minimum base, 0% phaseout; qualifying tax $1,000 is under the $1,100 cap, so the full amount is paid. 2025 chart: row $1–$14,300 — the refund is the actual tax paid.

**Relevant evidence or source**: Criteria 1(A), 3, 4; Benefit Value item 4.

---

### Scenario 6: Turns 65 Later in the Claim Year
**What this tests**: Age is measured as of Dec 31 of the claim year, not the screening date.
**Expected**: Eligible, **$1,100**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `September 1960` (turns 65 in September 2025, before Dec 31), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$12,000` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: At/below minimum base, no phaseout; qualifying tax $1,200 is capped at $1,100.

**Relevant evidence or source**: Criterion 1(A).

---

### Scenario 7: No Homestead
**What this tests**: The Missouri-homestead eligibility gate (criterion 3).
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1953` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Neither` (neither owns nor rents)
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Fails the Missouri-homestead gate — the claimant neither owns nor rents a qualifying homestead.

**Relevant evidence or source**: Criterion 3.

---

### Scenario 8: Adult Child's Income Excluded
**What this tests**: Adult child's independent income is excluded from household income; married full-year-homeowner deduction; homeowner cap.
**Expected**: Eligible, **$1,059**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1955` (age 70), Has income: `Yes`, Income type: `Social Security`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1957` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$8,400` per year, Veteran: `No`, Disability: `No`
- **Person 3 (Adult Child)**: Relationship: `Child`, Birth month/year: `January 1986` (age 39), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,000` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$2,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+). Household income counts claimant + spouse only ($19,200); the adult child's $3,000 wage income is excluded. PTC income after the $4,000 deduction = $15,200; qualifying tax $2,200 capped at $1,100. 2025 chart: row $14,901–$15,200, column $1,076–$1,100 = $1,059. Counting the child would move income to $18,200 and pay $941 (row $17,901–$18,200).

**Relevant evidence or source**: Criteria 1(A), 2 (assistance unit).

---

### Scenario 9: Married Full-Year Homeowners $1 Over the $30,000 Limit
**What this tests**: Income-limit exclusion for married full-year homeowners.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1954` (age 71), Has income: `Yes`, Income type: `Social Security`, Income amount: `$18,000` per year; also Income type: `Pension/Retirement`, Income amount: `$2,801` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1956` (age 69), Has income: `Yes`, Income type: `Social Security`, Income amount: `$9,600` per year; also Income type: `Pension/Retirement`, Income amount: `$3,600` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$2,500` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+), so the income limit is the isolated cause of ineligibility. Combined gross income $34,001; PTC income after the $4,000 deduction = $30,001, which exceeds the $30,000 limit.

**Relevant evidence or source**: Criteria 1(A), 2.

---

### Scenario 10: Claimant General-Disability Pathway
**What this tests**: Pathway C (general disability), satisfied by the claimant independent of age.
**Expected**: Eligible, **$720**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1969` (age 56), Has income: `Yes`, Income type: `SSDI`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `Yes`
- **Housing**: Housing situation: `Rent`, Rent paid: `$3,600` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $10,800 is at/below minimum base; qualifying rent-equiv 20%×$3,600=$720 is under the $750 cap.

**Relevant evidence or source**: Criterion 1(C).

---

### Scenario 11: No Qualifying Pathway
**What this tests**: A claimant genuinely under 65, not disabled, and not a survivor has no qualifying pathway.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1961` (turns 65 in 2026), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$12,000` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,400` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: No qualifying pathway (A–D) is satisfied.

**Relevant evidence or source**: Criterion 1.

---

### Scenario 12: Claimant-Only Survivor Pathway
**What this tests**: Pathway D — claimant age 60+ receiving surviving-spouse Social Security benefits.
**Expected**: Eligible, **$750**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1965` (age 60), Has income: `Yes`, Income type: `Social Security Survivor Benefits`, Income amount: `$13,200` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$5,400` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $13,200 is at/below minimum base; qualifying rent-equiv 20%×$5,400=$1,080 capped at $750.

**Relevant evidence or source**: Criterion 1(D).

---

### Scenario 13: Claimant Veteran-and-Disability Proxy, VA Benefits Excluded
**What this tests**: MFB's `veteran`-income-stream + `disabled` inclusive proxy (pathway B / veteran-income exclusion) and the `veterans_benefits` income exclusion. The household's only income is `VA Disability Compensation`, which is the `veteran` income stream, so the proxy resolves without relying on the unpopulated `veteran` field. Note: `disabled=true` alone also satisfies pathway C independently, so this scenario doesn't isolate pathway B in the calculator's control flow — its value is testing the proxy and the income exclusion, not proving the exact statutory 100%-service-connected pathway.
**Expected**: Eligible, **$1,100**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1974` (age 51), Has income: `Yes`, Income type: `VA Disability Compensation`, Income amount: `$46,800` per year (only income, excluded from PTC income → PTC income $0), Veteran: `Yes`, Disability: `Yes`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,100` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: At/below minimum base; qualifying tax $1,100 is exactly the $1,100 cap.

**Relevant evidence or source**: Criteria 1(B), 2 (veteran-income exclusion).

---

### Scenario 14: Married Renter Household at $27,200 After the $2,000 Deduction
**What this tests**: Married-renter boundary; the $2,000 (not $4,000) deduction.
**Expected**: Eligible, **$11**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1957` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$12,000` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1959` (age 66), Has income: `Yes`, Income type: `Social Security`, Income amount: `$10,000` per year; also Income type: `Pension/Retirement`, Income amount: `$7,200` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$7,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+). Gross income $29,200; PTC income after the $2,000 deduction = $27,200; qualifying rent-equiv 20%×$7,200=$1,440 capped at $750. 2025 chart: row $26,901–$27,200, column $726–$750 = $11 — the same cell as Scenario 2, reached through the married deduction.

**Relevant evidence or source**: Criteria 1(A), 2 ($2,000 deduction tier); Benefit Value items 3, 7.

---

### Scenario 15: Spouse-Only Age Pathway
**What this tests**: Pathway A (age) satisfied through the spouse alone, not the claimant.
**Expected**: Eligible, **$913**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1969` (age 56, not disabled/veteran/65+), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$9,600` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1957` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$13,200` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,700` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Gross income $22,800; PTC income after the $4,000 deduction = $18,800; qualifying tax $1,700 capped at $1,100. 2025 chart: row $18,501–$18,800, column $1,076–$1,100 = $913.

**Relevant evidence or source**: Criterion 1(A) (spouse-only pathway).

---

### Scenario 16: Spouse Survivor Status Does Not Qualify Claimant
**What this tests**: Pathway D (survivor) is claimant-only; it does not route through the spouse.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1977` (age 48, not disabled/veteran/65+), Has income: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1965` (age 60), Has income: `Yes`, Income type: `Social Security Survivor Benefits`, Income amount: `$12,000` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,500` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: The spouse's survivor status cannot qualify the claimant — pathway D requires the claimant to be the age-60+ survivor.

**Relevant evidence or source**: Criterion 1(D); Acceptance Criteria assertion on claimant-only survivor routing.

---

### Scenario 17: Minor Child's Income Included
**What this tests**: A minor child's benefit income counts toward household income (contrast Scenario 8, where an adult child's income is excluded).
**Expected**: Eligible, **$883**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1957` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$14,400` per year
- **Person 2 (Minor Child)**: Relationship: `Child`, Birth month/year: `January 2014` (age 11), Has income: `Yes`, Income type: `SSI`, Income amount: `$4,800` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Household income $19,200 ($0 single deduction); qualifying tax $1,200 capped at $1,100. 2025 chart: row $19,101–$19,400, column $1,076–$1,100 = $883.

**Relevant evidence or source**: Criterion 2 (assistance unit).

---

### Scenario 18: Zero Qualifying Payment
**What this tests**: The positive-qualifying-payment eligibility gate (criterion 4).
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1953` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$0` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Fails the positive-qualifying-payment gate — $0 property tax paid.

**Relevant evidence or source**: Criterion 4.

---

### Scenario 19: $0 Floor Is Not Surfaced
**What this tests**: The $0-floor result — a household satisfies every eligibility gate and the phaseout still floors the credit at $0.
**Expected**: Not shown (**$0**)

**Note on the expected result.** Discovery recorded this as "Eligible, $0", which is correct as a statement about the statute — the $0 is a phaseout outcome, not an exclusion (Benefit Value item 8). It is not a correct expected *screener* result. The results page requires `program.eligible && programValue(program) > 0` to display a program (`filterPrograms.ts`), so a $0 credit is never shown whichever way eligibility is reported. The calculator therefore uses the inherited `value > 0` rule and reports this household ineligible: telling someone they qualify for $0 would invite a filing that pays nothing. PolicyEngine's separate `mo_ptc_taxunit_eligible` flag is deliberately not read.

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1953` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$25,000` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$600` per year (qualifying rent-equiv $120)
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $25,000 (band $24,801–$25,100) carries a 2.25% phaseout, about $561, which exceeds the $120 rent-equivalent, so the result floors at $0. 2025 chart: row $24,801–$25,100 is blank in the $101–$125 column.

**Relevant evidence or source**: Benefit Value item 8.

---

### Scenario 20: Spouse General-Disability Pathway
**What this tests**: Pathway C satisfied through the spouse alone — the sole available pathway for either household member.
**Expected**: Eligible, **$913**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1969` (age 56, not disabled/veteran/65+), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$9,600` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1969` (age 56), Has income: `Yes`, Income type: `SSDI`, Income amount: `$13,200` per year, Disability: `Yes`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,700` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Same as Scenario 15 ($18,800 PTC income, $1,100 qualifying tax, $913), qualified through the spouse's disability instead of age.

**Relevant evidence or source**: Criterion 1(C) (spouse-only pathway).

---

### Scenario 21: Married Full-Year Homeowners Exactly at the $30,000 Limit
**What this tests**: Married-homeowner income-limit exact boundary, reached through the $4,000 deduction.
**Expected**: Eligible, **$95**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1957` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$20,000` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1959` (age 66), Has income: `Yes`, Income type: `Social Security`, Income amount: `$14,000` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,700` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+). Gross income $34,000; PTC income after the $4,000 deduction = $30,000; qualifying tax $1,700 capped at $1,100. 2025 chart: row $29,901–$30,000, column $1,076–$1,100 = $95 — the same cell as Scenario 3, reached through the married deduction.

**Relevant evidence or source**: Criteria 1(A), 2; Benefit Value item 7 (terminal-band rule).

---

### Scenario 22: Spouse Veteran-and-Disability Proxy, VA Benefits Excluded
**What this tests**: Same proxy and income exclusion as Scenario 13, confirmed for the spouse role. Same caveat applies: `disabled=true` alone also satisfies pathway C, so this doesn't isolate pathway B specifically.
**Expected**: Eligible, **$1,100**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole County`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1969` (age 56, no income, no pathway), Has income: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1974` (age 51), Has income: `Yes`, Income type: `VA Disability Compensation`, Income amount: `$46,800` per year (only income, excluded → PTC income $0), Veteran: `Yes`, Disability: `Yes`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,100` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Same as Scenario 13.

**Relevant evidence or source**: Criteria 1(B), 2 (veteran-income exclusion, spouse side).

## Source Documentation

Short operative excerpts backing the key rules above, plus the underlying source list. Quotation marks are used only where the language is verbatim source text; otherwise the cell is a rule summary.

| Rule | Source | Operative rule summary |
| --- | --- | --- |
| Claimant pathways (age/veteran/disabled/survivor) | RSMo §135.010(1),(2) | Defines "claimant" as a person 65+, a veteran "one hundred percent disabled as a result of such service," disabled per SSA-equivalent standard, or 60+ surviving spouse receiving Social Security survivor benefits |
| Veteran-income exclusion for below-100%-rated veterans | Form MO-PTC 2025 Instructions (DOR) | Extends the veterans'-payments income exclusion to a veteran rated below 100% whose qualifying impairment results entirely from military service, meeting the same substantial-gainful-activity/duration-or-death standard — an income-counting rule, not a distinct eligibility pathway |
| Combined-claim rule (assistance unit) | RSMo §135.010(1) | "eligible to file a joint federal income tax return and reside at the same address at any time during the taxable year" — such persons must file a combined claim reporting combined income and property taxes |
| 2025 filing statuses and Line 7 deduction | Form MO-PTC 2025 Instructions (DOR), Line 7 | "Single or Married Living Separate - Enter $0"; "Married and Filing Combined - rented or did not own your home for the entire year - Enter $2,000"; "Married and Filing Combined - owned and occupied your home for the entire year - Enter $4,000". (Married-filing-separate claimants lose eligibility from claim year 2026 — House fiscal note `1683S.04T.ORG.pdf` — which does not apply here.) |
| Spouse exemption and income add-backs | RSMo §135.010(5) | "less two thousand dollars for all calendar years ending on or before December 31, 2025, or in the case of a homestead owned and occupied, for the entire year, by the claimant, less four thousand dollars as an exemption for the claimant's spouse residing at the same address" (no statutory exemption applies to the $0 single case); requires add-back of Social Security, railroad retirement, veterans' payments, pensions, public assistance received in cash, SSI, and child support (Form MO-PTC 2025 Instructions, Line 5); §135.010(5)(d) additionally provides "no deduction being allowed for losses not incurred in a trade or business" |
| 2025 income limits ($27,500 / $30,000; $27,200 effective for renters) | RSMo §135.030.1(1); Form MO-PTC 2025 Instructions, Line 8 | Statute: twenty-seven thousand five hundred dollars, or thirty thousand dollars for a homestead owned and occupied for the entire year, for calendar years 2008 through 2025. Form: "If you rented or did not own and occupy your home for the entire year and Line 8 is greater than $27,200, you are not eligible to file this claim"; "If you owned and occupied your home for the entire year and Line 8 is greater than $30,000, you are not eligible to file this claim" |
| Homestead definition | RSMo §135.010(4) | "Homestead" means the dwelling owned or rented and occupied as the claimant's principal residence, plus up to 5 surrounding acres |
| Positive qualifying payment / tax-exempt-facility exclusion | RSMo §135.010(3),(6),(7); Form MO-PTC Instructions | Requires property tax or rent constituting property tax actually paid; rent equivalent is "'Rent constituting property taxes accrued', twenty percent of the gross rent paid by a claimant and spouse in the calendar year" (§135.010(7)); excludes renters of facilities not subject to property tax |
| Minimum base | RSMo §135.030.1(2) | "For all calendar years beginning on or after January 1, 2008, the minimum base shall be the sum of fourteen thousand three hundred dollars" |
| 2025 caps, phaseout increment/cap, bands, midpoint, rounding | RSMo §135.030.3; 2025 Property Tax Credit Chart | Through claim year 2025: credit not to exceed $1,100 in actual property tax or rent equivalent paid up to $750; 1/16 percent accumulative per $300 of income above the minimum base, from 0 to 4 percent; property tax in increments of twenty-five dollars and income in increments of three hundred dollars; computed at the midpoints of each increment and rounded to the nearest whole dollar. The chart tabulates the result |
| Filing deadline | Form MO-PTC 2025 Instructions, "When to file a claim" | "The 2025 Form MO-PTC is due April 15, 2026, but you may file up to three years from the due date and still receive your credit." |
| Household income definition (claimant/spouse/minor children only) | Form MO-PTC 2025 Instructions (DOR) | "Household income is all income received by a claimant, spouse, and minor children" — an adult child's income is excluded |
| Accrued taxes/rent, caps, and allocation | RSMo §135.025; §135.010(1),(6) | §135.025 governs totaling property tax/rent, the statutory caps, and allocation rules for part-year/mixed-use homesteads; §135.010(6) governs partial ownership and §135.010(1) governs combined claims — not the homestead-occupancy gate (criterion 3) |
| Missouri AGI definition | RSMo §143.121 | Missouri adjusted gross income is federal adjusted gross income subject to the modifications in §143.121, the base figure criterion 2's PTC income starts from |
| Refundability | RSMo §135.020 | Credit above income-tax liability is treated as an overpayment and refunded |
| Delinquent-tax offset | RSMo §135.815; extended to all tax-credit programs by RSMo §135.830 | Downstream payment-administration offset, applied after the credit is computed |
| Unauthorized-worker employer-conduct gate | RSMo §285.025; Form MO-PTC signature declaration | "No employer who employs illegal aliens shall be eligible for any state-administered or subsidized tax credit, tax abatement or loan from this state," including credits under chapter 135; the Form MO-PTC signature declaration has the signer affirm they employ no illegal or unauthorized aliens |

- [Missouri PTC – Program Overview (DOR)](https://dor.mo.gov/taxation/individual/tax-types/property-tax-credit/) — shows the 2025 $750/$1,100 maximums; general qualification/application guidance.
- [Property Tax Credit Claim FAQ (DOR)](https://dor.mo.gov/faq/taxation/individual/property-tax-credit-claim.html) — late-filing window (three years).
- [RSMo §135.010 – Definitions](https://revisor.mo.gov/main/OneSection.aspx?section=135.010)
- [RSMo §135.020 – Refundability](https://revisor.mo.gov/main/OneSection.aspx?section=135.020)
- [RSMo §135.025 – Accrued taxes/rent, caps, and allocation](https://revisor.mo.gov/main/OneSection.aspx?bid=57541&section=135.025)
- [RSMo §135.030 – Amount and computation](https://revisor.mo.gov/main/OneSection.aspx?section=135.030)
- [RSMo §143.121 – Missouri adjusted gross income](https://revisor.mo.gov/main/OneSection.aspx?section=143.121)
- [Form MO-PTC – 2025 Instructions/Chart](https://dor.mo.gov/forms/MO-PTC%20Instructions_2025.pdf) — form rules, Line 7 deduction, Line 8 limits, household-income definition, veteran-income wording, and the 2025 Property Tax Credit Chart every scenario value is checked against.
- [Missouri House Fiscal Note (HB/SB enacting the 2026 amounts), `1683S.04T.ORG.pdf`](https://documents.house.mo.gov/billtracking/bills251/fiscal/fispdf/1683S.04T.ORG.pdf) — the claim-year-2026 changes this spec moves to on January 1, 2027
- [RSMo §135.815 – Delinquent-tax offset](https://revisor.mo.gov/main/OneSection.aspx?section=135.815)
- [RSMo §135.830 – Extends §135.815 to all tax credit programs](https://revisor.mo.gov/main/OneSection.aspx?section=135.830)
- [RSMo §285.025 – Unauthorized-worker employer-conduct gate](https://revisor.mo.gov/main/OneSection.aspx?section=285.025)
