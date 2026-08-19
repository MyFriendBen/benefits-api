# Missouri Property Tax Credit (Circuit Breaker)

## Program Details

- **Program**: Missouri Property Tax Credit (PTC), commonly called the Circuit Breaker
- **State**: MO
- **Program key**: `mo_pts` (the `mo_ptc` in the original draft collides confusingly with the already-registered `mo_aca_ptc`, the ACA premium tax credit)
- **Policy year**: 2026
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
   - **2026 filing-status gate**: RSMo §135.030 defines 2026 income limits only for a PTC filing status of **single** or **married filing combined** — a married-filing-separate claimant no longer qualifies for 2026 (per the enacted bill's fiscal note). MFB does not collect the claimant's actual PTC filing status (⚠️ *data gap*). Committed inclusive proxy: derive filing status from household structure — if a spouse is listed (`relationship = spouse`), treat the claim as married filing combined; otherwise treat it as single. MFB cannot identify a married-filing-separate claimant, so that filing-status exclusion is not directly screened.
   - **Assistance unit**: PTC income counts the claimant, spouse, and minor children; an adult child's income is excluded regardless of dependency status.
   - **PTC income** = Missouri AGI (RSMo §143.121), plus required add-backs (full Social Security benefit, railroad retirement, veterans' payments/benefits, other pensions/annuities, public assistance/unemployment received in cash, SSI, child support, interest on U.S./state/subdivision obligations), with no deduction for losses not incurred in a trade or business (RSMo §135.010(5)(d)), less the filing deduction: **$0** (single) / **$2,800** (married-combined, renter or not full-year owner) / **$5,800** (married-combined, full-year owner). There is no deduction pathway for married filing separate — that filing status is out of scope per the gate above. Detailed add-back itemization and any nonbusiness-loss claim are a data gap (⚠️ use reported gross income as proxy; the calculator does not subtract an unmodeled nonbusiness loss).
   - **Veteran-income exclusion**: a claimant/spouse who is 100% service-connected disabled (pathway B) is not required to list veterans' payments/benefits as income at all. DOR instructions extend this exclusion to a veteran rated **below** 100% whose qualifying impairment results entirely from military service and meets the same substantial-gainful-activity/duration-or-death standard as the general disability pathway (Form MO-PTC 2025 Instructions) — this is a rule about which income is excluded, not a broader eligibility pathway. MFB uses the same proxy as pathway B — a `veteran` **income stream** plus `disabled`/`long_term_disability`, not the unpopulated `veteran` field — since the exact rating/service-causation detail isn't collected (⚠️ *data gap*).
   - Veteran income must route to PolicyEngine's `veterans_benefits` variable, not the shared pension mapping (`PensionIncomeDependency` groups `veteran` with `pension` under `taxable_pension_income` today) — otherwise the veterans'-benefit exclusion above silently never triggers.
   - The exclusion is additionally gated on PolicyEngine's Person-level `is_fully_disabled_service_connected_veteran`, which has no formula and is therefore false unless MFB sends it. **The mapping and the flag are jointly required.** Measured at PE 1.786.5 on Scenarios 13 and 22 (both expect $1,100): `veterans_benefits` mapping without the flag → $0 / $272; flag set but income routed to `taxable_pension_income` → $0 / $272; both → $1,100 / $1,100. The $272 case returns `eligible=true` with a wrong value, so tests must assert value and not eligibility alone.
   - **Resulting PTC income must be ≤** the applicable 2026 tier: single renter/part-year owner **$38,200**; single full-year homeowner **$42,200**; married-combined renter/part-year owner **$41,000**; married-combined full-year homeowner **$48,000**. Full-year-ownership status is assumed when duration is unavailable (⚠️ *data gap* — treat any indicated homeowner as full-year owner).
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
2. PTC income = MO AGI less filing deduction plus add-backs (criterion 2). No deduction pathway exists for married filing separate — that filing status is out of scope for 2026 (criterion 2).
3. Four income-limit tiers gate eligibility (criterion 2); above the limit, not eligible.
4. Minimum base: **$14,300**. At or below it, credit = qualifying property tax/rent-equivalent paid, capped at the statutory maximum, no phaseout.
5. Statutory maximum: **$1,055** renters / **$1,550** homeowners.
6. Rent equivalent = 20% of qualifying gross rent paid.
7. Above the minimum base, apply the statutory table method below. **2026 calculation basis**: apply the 2026 statutory parameters using the bracket-boundary convention established by DOR's 2025 Property Tax Claim Chart.
   - PTC income is placed in $495-wide bands counting up from the minimum base; phaseout = 1/16 percentage point per band, capped at **2%**.
   - Qualifying payment is placed in $25-wide bands counted down from the statutory cap.
   - Each band's midpoint is a half-dollar value (band is open at the lower bound, closed at the upper): e.g., $1,031–$1,055 → midpoint $1,042.50.
   - Credit = (payment-band midpoint) − (phaseout % × income-band midpoint), rounded half-up to the nearest dollar.
   - **Terminal-band rule**: for each of the four tiers, truncate the final income band at that tier's statutory upper limit (not extended to a full $495 width) — MFB's committed implementation rule, based on the 2025 chart's own precedent of truncating its final row at the chart's overall ceiling.
8. Result floored at **$0** — a household can satisfy every eligibility gate and still receive $0 (not a statutory exclusion).
9. Credit is computed **before** any delinquent-tax debt offset (RSMo §135.815, extended by §135.830); the offset is a downstream payment-administration step, not part of the calculator's output.
10. Unmodeled allocation detail — special assessments/penalties/interest/service charges, partial ownership, part-year ownership, multiple homesteads, mixed/business use, non-arm's-length or excess rent, bundled services, shared-rent/facility adjustments (RSMo §135.010, §135.025): use the household's reported out-of-pocket property tax or rent as an inclusive proxy; DOR may adjust the qualifying amount when the claim is filed.

Source: RSMo §135.030 (2026 formula, limits, caps); 2025 Property Tax Credit Chart (`Property Tax Claim Chart_2025.pdf`) for chart-method validation only — no 2026 chart has been published.

## Acceptance Criteria

Unless stated otherwise, scenarios use a valid Missouri location, no unrelated income/expenses, and the committed data-gap treatments above. "Valid Missouri location" is a current-routing assumption only (via `zipcode`/`county`); it does not by itself establish tax-year homestead location, which follows the committed inclusive data-gap treatment in criterion 3.

**Binding implementation assertions** (independent of the scenario list below):
- [ ] Age is computed as of December 31, 2026 from `birth_year`/`birth_month`, not the screening date.
- [ ] Filing status is derived via the spouse-presence proxy, and the four 2026 income-limit tiers are applied correctly by filing status and owner/renter status.
- [ ] The survivor pathway (D) is routed claimant-only; it does not qualify a household through the spouse.
- [ ] General disability (pathway C) maps to PolicyEngine's `is_disabled`-compatible variable, not `is_ssi_disabled`.
- [ ] Veteran income is mapped to `veterans_benefits` on both the claimant and spouse sides — not the shared pension dependency — so the veterans'-benefit exclusion (criterion 2) actually triggers, **and** `is_fully_disabled_service_connected_veteran` is sent so the exclusion is un-gated. Both are required; either alone leaves the credit computed off unexcluded income.

**Implementation-discovered assertions** (added during build; each was found by a scenario failing live against PolicyEngine 1.786.5, and each is a shared-dependency routing defect rather than a rule error):
- [ ] **Age input is the end-of-claim-year age.** The shared `AgeDependency` sends `member.calc_age()`, which measures against the *screening date*. Scenario 6's September-1961 claimant therefore arrives as `age=64` and fails the age-65 pathway when screened before September — the calculator sends a claim-year age instead.
- [ ] **Survivor benefits are sent as `social_security_survivors`, not only the `social_security` total.** PolicyEngine defines `social_security` as an `adds` aggregate over its four components; setting the total leaves every component at zero, and `mo_ptc_taxunit_eligible`'s survivor test reads the component. Without the component input, Scenario 12 returns ineligible / $0.
- [ ] **Reported SSI is sent as `ssi`, not `ssi_reported`.** `mo_ptc_gross_income` adds the `ssi` variable. `ssi_reported` feeds only `applicable_ssi`, which PolicyEngine documents as deprecated and which no program reads, so reported SSI never reaches PTC income. With `ssi_reported`, Scenario 17 returns $1,178 instead of $1,069 (the child's $4,800 SSI is dropped from household income).
- [ ] Benefit calculation uses $495-wide income bands, $25-wide payment bands, the 1/16-point-per-band phaseout capped at 2%, half-dollar band midpoints, and half-up whole-dollar rounding, floored at $0.
- [ ] Output is annual and refundable (`value_format: estimated_annual`, `value_type: tax_credit`).
- [ ] All 22 executable scenarios below return the committed eligibility result and benefit value.

No new screener field or feature is required by any acceptance criterion above.

## Test Scenarios

### Scenario 1: Golden-Path Senior Renter
**What this tests**: Validates the baseline age-65 pathway with a renter homestead and positive rent paid.
**Expected**: Eligible, **$1,033**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1954` (age 72), Has income: `Yes`, Income type: `Social Security`, Income amount: `$14,400` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$6,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $14,400 (band midpoint $14,547.50, phaseout 0.0625%); qualifying rent-equiv 20%×$6,000=$1,200 → top renter band midpoint $1,042.50. Credit = $1,042.50 − $9.09 = $1,033.41, rounds to $1,033.

**Relevant evidence or source**: Criteria 1(A), 2, 4; Benefit Value items 4–7.

---

### Scenario 2: Single-Renter Income Exactly at the $38,200 Limit
**What this tests**: Single-renter income-limit exact boundary.
**Expected**: Eligible, **$280**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1958` (age 68), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$38,200` per year (single filer, $0 deduction), Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$9,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Final truncated band $38,061–$38,200, midpoint $38,130, phaseout capped at 2%; qualifying rent-equiv 20%×$9,000=$1,800 → top renter band midpoint $1,042.50. Credit = $1,042.50 − $762.60 = $279.90, rounds to $280.

**Relevant evidence or source**: Criteria 2, 4; Benefit Value items 3, 7.

---

### Scenario 3: Single-Homeowner Income Exactly at the $42,200 Limit
**What this tests**: Single-homeowner income-limit exact boundary.
**Expected**: Eligible, **$695**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1958` (age 68), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$42,200` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,800` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Final truncated band $42,021–$42,200, midpoint $42,110, phaseout capped at 2%; qualifying tax $1,800 → top owner band midpoint $1,537.50. Credit = $1,537.50 − $842.20 = $695.30, rounds to $695.

**Relevant evidence or source**: Criteria 2, 3, 4; Benefit Value items 3, 7.

---

### Scenario 4: Single Renter $1 Over the $38,200 Limit
**What this tests**: Income-limit exclusion with positive rent present, isolating income as the sole cause of ineligibility.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1954` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$38,201` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$6,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $38,201 exceeds the $38,200 single-renter limit by $1; the income-limit gate fails despite positive rent paid.

**Relevant evidence or source**: Criterion 2.

---

### Scenario 5: Age Exactly 65 and PTC Income Exactly at the $14,300 Minimum Base
**What this tests**: Age-65 boundary and minimum-base boundary.
**Expected**: Eligible, **$1,500**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1961` (age 65), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$14,300` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,500` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: At minimum base, 0% phaseout; qualifying tax $1,500 is under the $1,550 cap, so the full amount is paid.

**Relevant evidence or source**: Criteria 1(A), 3, 4; Benefit Value item 4.

---

### Scenario 6: Turns 65 Later in the Claim Year
**What this tests**: Age is measured as of Dec 31 of the claim year, not the screening date.
**Expected**: Eligible, **$1,200**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `September 1961` (turns 65 in September, before Dec 31), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$12,000` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: At/below minimum base, no phaseout; full qualifying tax paid.

**Relevant evidence or source**: Criterion 1(A).

---

### Scenario 7: No Homestead
**What this tests**: The Missouri-homestead eligibility gate (criterion 3).
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1954` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Neither` (neither owns nor rents)
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Fails the Missouri-homestead gate — the claimant neither owns nor rents a qualifying homestead.

**Relevant evidence or source**: Criterion 3.

---

### Scenario 8: Adult Child's Income Excluded
**What this tests**: Adult child's independent income is excluded from household income; married full-year-homeowner deduction; homeowner cap.
**Expected**: Eligible, **$1,550**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1956` (age 70), Has income: `Yes`, Income type: `Social Security`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1958` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$8,400` per year, Veteran: `No`, Disability: `No`
- **Person 3 (Adult Child)**: Relationship: `Child`, Birth month/year: `January 1987` (age 39), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$3,000` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$2,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+). Household income counts claimant + spouse only ($19,200); the adult child's $3,000 wage income is excluded. PTC income after $5,800 deduction = $13,400 (at/below minimum base); qualifying tax $2,200 capped at $1,550.

**Relevant evidence or source**: Criteria 1(A), 2 (assistance unit).

---

### Scenario 9: Married Full-Year Homeowners Over the $48,000 Limit
**What this tests**: Income-limit exclusion for married full-year homeowners.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1955` (age 71), Has income: `Yes`, Income type: `Social Security`, Income amount: `$22,800` per year; also Income type: `Pension/Retirement`, Income amount: `$18,000` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1957` (age 69), Has income: `Yes`, Income type: `Social Security`, Income amount: `$9,600` per year; also Income type: `Pension/Retirement`, Income amount: `$3,600` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$2,500` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+), so the income limit is the isolated cause of ineligibility. Combined gross income $54,000; PTC income after $5,800 deduction = $48,200, which exceeds the $48,000 limit.

**Relevant evidence or source**: Criteria 1(A), 2.

---

### Scenario 10: Claimant General-Disability Pathway
**What this tests**: Pathway C (general disability), satisfied by the claimant independent of age.
**Expected**: Eligible, **$960**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1970` (age 56), Has income: `Yes`, Income type: `SSDI`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `Yes`
- **Housing**: Housing situation: `Rent`, Rent paid: `$4,800` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $10,800 is at/below minimum base; qualifying rent-equiv 20%×$4,800=$960 is under the $1,055 cap.

**Relevant evidence or source**: Criterion 1(C).

---

### Scenario 11: No Qualifying Pathway
**What this tests**: A claimant genuinely under 65, not disabled, and not a survivor has no qualifying pathway.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1962` (turns 65 the following year), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$12,000` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,400` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: No qualifying pathway (A–D) is satisfied.

**Relevant evidence or source**: Criterion 1.

---

### Scenario 12: Claimant-Only Survivor Pathway
**What this tests**: Pathway D — claimant age 60+ receiving surviving-spouse Social Security benefits.
**Expected**: Eligible, **$1,055**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1966` (age 60), Has income: `Yes`, Income type: `Social Security Survivor Benefits`, Income amount: `$13,200` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$5,400` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income $13,200 is at/below minimum base; qualifying rent-equiv 20%×$5,400=$1,080 capped at $1,055.

**Relevant evidence or source**: Criterion 1(D).

---

### Scenario 13: Claimant Veteran-and-Disability Proxy, VA Benefits Excluded
**What this tests**: MFB's `veteran`-income-stream + `disabled` inclusive proxy (pathway B / veteran-income exclusion) and the `veterans_benefits` income exclusion. The household's only income is `VA Disability Compensation`, which is the `veteran` income stream, so the proxy resolves without relying on the unpopulated `veteran` field. Note: `disabled=true` alone also satisfies pathway C independently, so this scenario doesn't isolate pathway B in the calculator's control flow — its value is testing the proxy and the income exclusion, not proving the exact statutory 100%-service-connected pathway.
**Expected**: Eligible, **$1,100**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1975` (age 51), Has income: `Yes`, Income type: `VA Disability Compensation`, Income amount: `$46,800` per year (only income, excluded from PTC income → PTC income $0), Veteran: `Yes`, Disability: `Yes`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,100` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: At/below minimum base; qualifying tax $1,100 is under the $1,550 cap.

**Relevant evidence or source**: Criteria 1(B), 2 (veteran-income exclusion).

---

### Scenario 14: Married Renter Household at the $41,000 Limit
**What this tests**: Married-renter income-limit exact boundary; $2,800 (not $5,800) deduction.
**Expected**: Eligible, **$227**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1958` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$16,800` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1960` (age 66), Has income: `Yes`, Income type: `Social Security`, Income amount: `$14,400` per year; also Income type: `Pension/Retirement`, Income amount: `$12,600` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$7,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+). Gross income $43,800; PTC income after $2,800 deduction = $41,000 (final truncated band midpoint $40,767.50, phaseout capped at 2%); qualifying rent-equiv 20%×$7,200=$1,440 → top renter band midpoint $1,042.50. Credit = $1,042.50 − $815.35 = $227.15, rounds to $227.

**Relevant evidence or source**: Criteria 1(A), 2 ($2,800 deduction tier); Benefit Value items 3, 7.

---

### Scenario 15: Spouse-Only Age Pathway
**What this tests**: Pathway A (age) satisfied through the spouse alone, not the claimant.
**Expected**: Eligible, **$1,474**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1970` (age 56, not disabled/veteran/65+), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$9,600` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1958` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$13,200` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,700` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Gross income $22,800; PTC income after $5,800 deduction = $17,000 (band midpoint $17,022.50, phaseout 0.375%); qualifying tax $1,700 → top owner band midpoint $1,537.50. Credit = $1,537.50 − $63.83 = $1,473.67, rounds to $1,474.

**Relevant evidence or source**: Criterion 1(A) (spouse-only pathway).

---

### Scenario 16: Spouse Survivor Status Does Not Qualify Claimant
**What this tests**: Pathway D (survivor) is claimant-only; it does not route through the spouse.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1978` (age 48, not disabled/veteran/65+), Has income: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1966` (age 60), Has income: `Yes`, Income type: `Social Security Survivor Benefits`, Income amount: `$12,000` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,500` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: The spouse's survivor status cannot qualify the claimant — pathway D requires the claimant to be the age-60+ survivor.

**Relevant evidence or source**: Criterion 1(D); Acceptance Criteria assertion on claimant-only survivor routing.

---

### Scenario 17: Minor Child's Income Included
**What this tests**: A minor child's benefit income counts toward household income (contrast Scenario 8, where an adult child's income is excluded).
**Expected**: Eligible, **$1,069**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1958` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$14,400` per year
- **Person 2 (Minor Child)**: Relationship: `Child`, Birth month/year: `January 2015` (age 11), Has income: `Yes`, Income type: `SSI`, Income amount: `$4,800` per year
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,200` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Household income $19,200 ($0 single deduction); PTC income $19,200 (band midpoint $19,002.50, phaseout 0.625%); qualifying tax $1,200 → tax band midpoint $1,187.50. Credit = $1,187.50 − $118.77 = $1,068.73, rounds to $1,069.

**Relevant evidence or source**: Criterion 2 (assistance unit).

---

### Scenario 18: Zero Qualifying Payment
**What this tests**: The positive-qualifying-payment eligibility gate (criterion 4).
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1954` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$10,800` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$0` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Fails the positive-qualifying-payment gate — $0 property tax paid.

**Relevant evidence or source**: Criterion 4.

---

### Scenario 19: Eligible, $0 Floor
**What this tests**: The $0-floor result — a household can be eligible but receive $0, rather than being excluded outright.
**Expected**: Eligible, **$0**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1954` (age 72), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$37,900` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Rent`, Rent paid: `$600` per year (qualifying rent-equiv $120)
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PTC income is near the $38,200 limit; the 2% phaseout at this band's midpoint exceeds the $120 rent-equivalent, so the result floors at $0.

**Relevant evidence or source**: Benefit Value item 8.

---

### Scenario 20: Spouse General-Disability Pathway
**What this tests**: Pathway C satisfied through the spouse alone — the sole available pathway for either household member.
**Expected**: Eligible, **$1,474**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1970` (age 56, not disabled/veteran/65+), Has income: `Yes`, Income type: `Pension/Retirement`, Income amount: `$9,600` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1970` (age 56), Has income: `Yes`, Income type: `SSDI`, Income amount: `$13,200` per year, Disability: `Yes`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,700` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Same as Scenario 15 ($17,000 PTC income, band midpoint $17,022.50, phaseout 0.375%, tax band midpoint $1,537.50), qualified through the spouse's disability instead of age.

**Relevant evidence or source**: Criterion 1(C) (spouse-only pathway).

---

### Scenario 21: Married Full-Year Homeowners Exactly at the $48,000 Limit
**What this tests**: Married-homeowner income-limit exact boundary — the highest of the four tiers.
**Expected**: Eligible, **$578**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1958` (age 68), Has income: `Yes`, Income type: `Social Security`, Income amount: `$31,200` per year, Veteran: `No`, Disability: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1960` (age 66), Has income: `Yes`, Income type: `Social Security`, Income amount: `$22,600` per year, Veteran: `No`, Disability: `No`
- **Housing**: Housing situation: `Own`, Property tax paid: `$1,700` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Claimant and spouse both satisfy pathway A (age 65+). Gross income $53,800; PTC income after $5,800 deduction = $48,000 (final truncated band midpoint $47,980, phaseout capped at 2%); qualifying tax $1,700 → top owner band midpoint $1,537.50. Credit = $1,537.50 − $959.60 = $577.90, rounds to $578.

**Relevant evidence or source**: Criteria 1(A), 2 (highest income tier); Benefit Value item 7 (terminal-band rule).

---

### Scenario 22: Spouse Veteran-and-Disability Proxy, VA Benefits Excluded
**What this tests**: Same proxy and income exclusion as Scenario 13, confirmed for the spouse role. Same caveat applies: `disabled=true` alone also satisfies pathway C, so this doesn't isolate pathway B specifically.
**Expected**: Eligible, **$1,100**

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `January 1970` (age 56, no income, no pathway), Has income: `No`
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `January 1975` (age 51), Has income: `Yes`, Income type: `VA Disability Compensation`, Income amount: `$46,800` per year (only income, excluded → PTC income $0), Veteran: `Yes`, Disability: `Yes`
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
| 2026 filing-status restriction | RSMo §135.030.1(1); enacted-bill fiscal note (House fiscal note, `1683S.04T.ORG.pdf`) | §135.030.1(1) ties each 2026 maximum-upper-limit tier to "a filing status of single" or "a filing status of married filing combined" only — no married-filing-separate tier exists; the fiscal note states married-filing-separate claimants "will no longer be eligible" beginning 2026 |
| Spouse exemption and income add-backs | RSMo §135.010(5) | "for all calendar years beginning on or after January 1, 2026, less two thousand eight hundred dollars, or in the case of a homestead owned and occupied, for the entire year, by the claimant, less five thousand eight hundred dollars, as an exemption for the claimant's spouse residing at the same address" (no statutory exemption applies to the $0 single case); requires add-back of Social Security, railroad retirement, veterans' payments, pensions, public assistance received in cash, SSI, and child support (Form MO-PTC 2025 Instructions, Line 5); §135.010(5)(d) additionally provides "no deduction being allowed for losses not incurred in a trade or business" |
| Four 2026 income limits ($38,200/$42,200/$41,000/$48,000) | RSMo §135.030.1(1)(a)–(d) | "(a) Thirty-eight thousand two hundred dollars for claimants with a filing status of single; (b) Forty-two thousand two hundred dollars for claimants with a filing status of single and who owned and occupied a homestead for the entire year; (c) Forty-one thousand dollars for claimants with a filing status of married filing combined; and (d) Forty-eight thousand dollars for claimants with a filing status of married filing combined and who owned and occupied a homestead for the entire year" |
| Homestead definition | RSMo §135.010(4) | "Homestead" means the dwelling owned or rented and occupied as the claimant's principal residence, plus up to 5 surrounding acres |
| Positive qualifying payment / tax-exempt-facility exclusion | RSMo §135.010(3),(6),(7); Form MO-PTC Instructions | Requires property tax or rent constituting property tax actually paid; rent equivalent is "'Rent constituting property taxes accrued', twenty percent of the gross rent paid by a claimant and spouse in the calendar year" (§135.010(7)); excludes renters of facilities not subject to property tax |
| Minimum base | RSMo §135.030.1(2) | "For all calendar years beginning on or after January 1, 2008, the minimum base shall be the sum of fourteen thousand three hundred dollars" |
| 2026 caps, phaseout increment/cap, bands, midpoint, rounding | RSMo §135.030.3(1),(2) | Not-over-minimum-base: "0 percent with credit not to exceed $1,550 in actual property tax or rent equivalent paid up to $1,055"; over-minimum-base: "1/16 percent accumulative per $495 ... from 0 percent to 2 percent"; "property tax shall be in increments of twenty-five dollars and the income in increments of four hundred ninety-five dollars"; "credit shall be the amount rounded to the nearest whole dollar computed on the basis of the property tax and income at the midpoints of each increment" |
| Household income definition (claimant/spouse/minor children only) | Form MO-PTC 2025 Instructions (DOR) | "Household income is all income received by a claimant, spouse, and minor children" — an adult child's income is excluded |
| Accrued taxes/rent, caps, and allocation | RSMo §135.025; §135.010(1),(6) | §135.025 governs totaling property tax/rent, the statutory caps, and allocation rules for part-year/mixed-use homesteads; §135.010(6) governs partial ownership and §135.010(1) governs combined claims — not the homestead-occupancy gate (criterion 3) |
| Missouri AGI definition | RSMo §143.121 | Missouri adjusted gross income is federal adjusted gross income subject to the modifications in §143.121, the base figure criterion 2's PTC income starts from |
| Refundability | RSMo §135.020 | Credit above income-tax liability is treated as an overpayment and refunded |
| Delinquent-tax offset | RSMo §135.815; extended to all tax-credit programs by RSMo §135.830 | Downstream payment-administration offset, applied after the credit is computed |
| Unauthorized-worker employer-conduct gate | RSMo §285.025; Form MO-PTC signature declaration | "No employer who employs illegal aliens shall be eligible for any state-administered or subsidized tax credit, tax abatement or loan from this state," including credits under chapter 135; the Form MO-PTC signature declaration has the signer affirm they employ no illegal or unauthorized aliens |

- [Missouri PTC – Program Overview (DOR)](https://dor.mo.gov/taxation/individual/tax-types/property-tax-credit/) — stale for 2026 dollar amounts (still shows pre-2026 $750/$1,100 maximums; effective 2026 maximums are $1,055/$1,550 per RSMo §135.030). Use for general qualification/application guidance only, not for dollar figures.
- [RSMo §135.010 – Definitions](https://revisor.mo.gov/main/OneSection.aspx?section=135.010)
- [RSMo §135.020 – Refundability](https://revisor.mo.gov/main/OneSection.aspx?section=135.020)
- [RSMo §135.025 – Accrued taxes/rent, caps, and allocation](https://revisor.mo.gov/main/OneSection.aspx?bid=57541&section=135.025)
- [RSMo §135.030 – Amount and computation](https://revisor.mo.gov/main/OneSection.aspx?section=135.030)
- [RSMo §143.121 – Missouri adjusted gross income](https://revisor.mo.gov/main/OneSection.aspx?section=143.121)
- [Form MO-PTC – 2025 Instructions/Chart](https://dor.mo.gov/forms/MO-PTC%20Instructions_2025.pdf) — form rules, household-income definition, veteran-income wording, and chart-method precedent; no 2026 form/chart exists yet.
- [Missouri House Fiscal Note (HB/SB enacting the 2026 amounts), `1683S.04T.ORG.pdf`](https://documents.house.mo.gov/billtracking/bills251/fiscal/fispdf/1683S.04T.ORG.pdf) — confirms the 2026 married-filing-separate exclusion
- [RSMo §135.815 – Delinquent-tax offset](https://revisor.mo.gov/main/OneSection.aspx?section=135.815)
- [RSMo §135.830 – Extends §135.815 to all tax credit programs](https://revisor.mo.gov/main/OneSection.aspx?section=135.830)
- [RSMo §285.025 – Unauthorized-worker employer-conduct gate](https://revisor.mo.gov/main/OneSection.aspx?section=285.025)
