# Missouri Working Family Tax Credit (MO WFTC) — Implementation Spec

## Program Details

- **Program:** Missouri Working Family Tax Credit (MO WFTC)
- **Program key:** `mo_wftc`
- **State:** Missouri
- **White label:** `mo`
- **Engine / Tier:** PolicyEngine, State (custom)
- **Policy years:** TY2023, TY2024, TY2025

---

## Eligibility Criteria

1. **Allowed a federal Earned Income Credit (EIC) for the same tax year.**
   - **Screener fields:** `has_income`, `income_streams`, `HouseholdMember.birth_year`, `HouseholdMember.birth_month`, `HouseholdMember.relationship`
   - Federal EITC eligibility is delegated to the existing federal EITC calculator ([MFB-1264](https://linear.app/myfriendben/issue/MFB-1264)). This gate is satisfied whenever PE's `eitc` variable is `> $0`.
   - **Committed basis:** PE's current-year `eitc` calculation is MFB's proxy for the federal EIC amount Form MO-WFTC Line 5 asks the filer to enter (Line 27 for TY2023–TY2024; Line 27a for TY2025). This is a calculated proxy, since MFB has no access to a taxpayer's filed federal return.
   - **Operative quote (Form MO-WFTC 2025, Line 1):** "Did you qualify for the Federal Earned Income Credit (EIC) on Federal Form 1040 or 1040-SR? ... No - STOP. You do not qualify for the Missouri Working Family Tax Credit."
   - **Source:** RSMo 143.177; Form MO-WFTC, Line 1

2. **Missouri resident.**
   - **Screener fields:** `zipcode`
   - MFB's Missouri screener/ZIP routing is the residency proxy — a household is only evaluated against `mo_wftc` once routed to Missouri via ZIP.
   - **⚠️ Data gap:** MFB does not separately determine tax-year domicile or part-year residency. Missouri ZIP routing is the inclusive residency proxy — routed households are treated as satisfying this criterion.
   - **Operative quote (Form MO-WFTC, top instructions, all years):** "To claim this credit, you must be a resident individual with a filing status of single, head of household, qualifying widow(er), or married filing combined, and who is allowed a federal Earned Income Credit (EIC) on their federal return."
   - **Source:** RSMo 143.177; Form MO-WFTC, top instructions

3. **Filing status: Single, Head of Household, Surviving Spouse, or Joint only — MFS excluded.**
   - **Screener fields:** `HouseholdMember.relationship` (derives `is_tax_unit_head`/`is_tax_unit_spouse`) — MFB has no direct `filing_status` field.
   - **⚠️ Data gap:** actual filing status isn't observed; relationship fields only support inference, which can't distinguish MFS or Surviving Spouse from Single/HOH/Joint. **Committed handling:** spouse present → Joint; no spouse → Single/HOH; MFS is never detected or excluded; Surviving Spouse is folded into the inferred Single/HOH treatment.
   - **Operative quote (Form MO-WFTC 2025, Line 2):** "Do you have a filing status of married filing separately or claimed as a dependent? Yes - STOP. You do not qualify for the Missouri Working Family Tax Credit."
   - **Operative quote (Form MO-WFTC 2023, Line 2 — MFS only, no dependent clause):** "Are you a married taxpayer whose filing status is married filing separately? Yes - STOP. You do not qualify for the Missouri Working Family Tax Credit."
   - **Source:** RSMo 143.177; MO DOR FAQ; Form MO-WFTC (2023–2025), Line 2

4. **Not claimed as a dependent on another return — TY2024 and forward only.**
   - **Screener fields:** none
   - **⚠️ Data gap:** MFB doesn't capture dependent-elsewhere status. **Committed handling:** do not exclude.
   - New starting TY2024: the 2023 form's Line 2 asks only about MFS (quoted under Criterion 3); the 2024/2025 forms fold "claimed as a dependent" into that same question.
   - **Source:** Form MO-WFTC (2023), Line 2 vs. Form MO-WFTC (2024/2025), Line 2

5. **Investment income below the Missouri threshold — comparator and threshold change by tax year.**
   - **Screener fields:** `income_streams` (`investment` category)
   - Standard test: tax-exempt interest + taxable interest + ordinary dividends + capital gain net income (if positive).
   - **Not universal:** Form MO-WFTC routes any filer with Schedule E, Form 4797, Form 8814, rental of personal property, or passive-activity income/loss to IRS Publication 596 Worksheet 1 instead (all years 2023–2025). Worksheet 1 expressly folds rental/royalty and passive-activity amounts into investment income. Missouri's definition therefore **does** reach rental/passive income for these filers.

     | Tax year | Rule | Operative quote (Form MO-WFTC, Line 3) |
     |---|---|---|
     | TY2023 | Disqualified if `>` $4,050 | "Do you have investment income equal to or greater than $4,050 (see instructions)?" (MFB's committed comparator differs from this literal wording — see below) |
     | TY2024 | Disqualified if `>` $4,300 | "Do you have investment income greater than $4,300 (see instructions)?" |
     | TY2025 | Disqualified if `>` $4,400 | "Do you have investment income greater than $4,400 (see instructions)?" |

   - **MFB data gap, not a Missouri exclusion:** MFB's `investment` field maps to PE's `long_term_capital_gains`; `rental` maps to PE's `rental_income` — a coarse total with no Schedule E/Form 4797/8814/passive-activity detail. MFB can't reconstruct Worksheet 1 Line 14 from this.
   - **Committed handling:** delegate the gate to PolicyEngine's `mo_wftc_eligible`, which approximates Missouri's test with `eitc_relevant_investment_income` — a measure that counts rental income dollar-for-dollar against the threshold. Neither MFB nor PolicyEngine implements Missouri's real branching test: MFB cannot reconstruct Worksheet 1 from a coarse `rental` total, and PolicyEngine's own code notes it substitutes the federal EITC investment measure. Accepting PE's approximation keeps one source of truth for the whole credit rather than overriding the gate.
   - **Direction of the error, disclosed:** PE's measure disqualifies at the threshold on rental income alone, so a filer whose true Worksheet 1 result would have cleared the limit can be shown ineligible. Verified at PE 1.786.5: holding a household fixed at $40,000 wages with one child and varying only rental income, `mo_wftc_eligible` flips `False` between $4,400 and $4,401 — the same TY2025 boundary that governs interest and dividends. The Department of Revenue makes the actual determination, and the screener does not claim to reproduce Worksheet 1. An earlier draft of this criterion committed to the opposite handling (rental excluded from the gate, which would have required overriding PolicyEngine); that was reversed in favor of PE's single implementation. No new screener fields are required.
   - The DOR FAQ's generalized "equal to or greater than" wording is not controlling for TY2024/TY2025; the year-specific form lines above are implemented instead.
   - **TY2023 comparator — disclosed source conflict:** official 2023 sources conflict — Line 3's checkbox/instructions and the current DOR FAQ use `>=` $4,050, while the form's front-page summary ("cannot exceed") and Worksheet 1 fallback ("exceeds") both use `>` $4,050, matching TY2024/2025's comparator.
   - **Committed rule:** disqualify only when investment income is `> $4,050` for TY2023. Exactly $4,050 remains eligible. Single committed implementation, not an open fork.
   - **Source:** Form MO-WFTC (2023/2024/2025), Line 3, front-page eligibility summary, and Worksheet 1 instructions; MO DOR FAQ; IRS Publication 596, Worksheet 1

6. **Positive remaining Missouri tax liability after Miscellaneous Tax Credits (Line 42) and Property Tax Credit (Line 43).**
   - **Screener fields:** household composition/income fields from Criteria 1–5; `rent`, `real_estate_taxes` (Property Tax Credit)
   - **⚠️ Data gap — Miscellaneous Tax Credits:** no Line 42/Form MO-TC input. **Committed handling:** assume Miscellaneous Tax Credits = $0. Property Tax Credit is netted via `rent`/`real_estate_taxes`. A household whose remaining liability nets to $0 after Lines 42–43 is **not eligible**.
   - **Operative quote (MO DOR WFTC FAQ):** "You have a tax liability after the application of a miscellaneous tax credit or a Property Tax Credit."
   - **Source:** MO DOR FAQ ("Eligibility Requirements"); MO-1040 Instructions, Line 44; Form MO-WFTC worksheet, Lines 7–9

---

## Priority Criteria

None. MO WFTC is a non-competitive tax credit.

---

## Benefit Value

`MO WFTC = min(MO rate × federal EITC, max(0, MO tax − Line 42 − Property Tax Credit))`

1. **Federal EITC base** — PE's current-year `eitc` calculation, per Criterion 1's committed basis (Line 27 for TY2023–TY2024; Line 27a for TY2025).
   - **Disclosed conflict:** RSMo 143.177 and the MO-1040 instructions define the credit by reference to federal EITC law "as of January 1, 2021," while Form MO-WFTC Line 5 tells filers to enter the current-year federal EIC actually claimed.
   - **Committed treatment:** implement Line 5's current-year approach, since that's what every year's form (2023–2025) actually administers.
   - **Operative quote (Line 5, 2025 form):** "Federal Earned Income Credit (EIC) from Federal Form 1040 or 1040-SR, Line 27a."
   - **Operative quote (Line 5, 2023/2024 forms):** "Federal Earned Income Credit (EIC) from Federal Form 1040 or 1040-SR, Line 27." (The Line 27 → 27a change tracks the IRS's own 1040 line-lettering change, not a Missouri methodology change.)
2. **Multiply by the Missouri rate:**

   | Tax year | Rate | Operative quote (Line 6) |
   |---|---|---|
   | TY2023 | 10% | "Multiply Line 5 by 10% and enter the result." |
   | TY2024 and forward | 20% | "Multiply Line 5 by 20% and enter the result." |

3. **Remaining Missouri liability** = MO-1040 Line 36 (Total Tax) − Line 42 (assumed $0) − Line 43 (Property Tax Credit), floored at $0.
   - **Operative quotes (Lines 7–9):** "Total Tax from Form MO-1040, Line 36." / "Add Line 42 and Line 43 from Form MO-1040 and enter the result." / "Subtract Line 8 from Line 7, if less than 0, enter 0."
4. **Final credit** = the smaller of (rate × federal EIC) or (remaining Missouri liability).
   - **Operative quote (Line 10):** "Enter the smaller amount of Line 6 or Line 9 here and on Form MO-1040, Line 44."
5. Nonrefundable; does not carry forward.
6. Round to the nearest whole dollar (MO-1040 rounding rule: cents 1–49 down, 50–99 up).
7. Cadence: annual (`value_format: estimated_annual`).

**Source:** RSMo 143.177; MO DOR FAQ; Form MO-WFTC (2023, 2024, Rev. 12-2025); MO-1040 Instructions, Line 44

---

## Implementation

Binding directives not already fully stated above:

- **Read PE's `mo_wftc` as the binding result.** PolicyEngine models the whole chain — `mo_wftc_eligible` for the gate, `mo_wftc_potential` for `eligible × eitc × rate`, `mo_wftc_liability_cap` for the Form MO-WFTC Lines 7-9 netting (including the Property Tax Credit), and `mo_wftc` for the final smaller-of result. The calculator is a thin `PolicyEngineTaxUnitCalulator` wrapper: `pe_name = "mo_wftc"`, the federal `Eitc.pe_inputs` set, plus `MoStateCodeDependency`.
  - Verified at PE 1.786.5 (PolicyEngine's `current`): 15 of the 16 scenarios below match to the dollar, including all four investment-income boundary pairs, both Property-Tax-Credit netting cases, the TY2023 10% rate, and the Joint path. Scenario 15 is the one intentional divergence and its expectation reflects PE's behavior.
  - An earlier draft of this section directed building the credit from parts — PE's `eitc`, the rate, remaining liability, and the Property Tax Credit — with an MFB-computed investment gate. That was reversed: it would have duplicated arithmetic PE already performs correctly, and it required overriding PE's eligibility gate to preserve a rental exemption we cannot actually substantiate (criterion 5).
  - Note `mo_income_tax_before_credits` is a **person**-level variable, not tax-unit; requesting it on `tax_units` returns HTTP 500. The thin wrapper never reads it, but anyone reconstructing the liability cap by hand needs to sum it across people.
- **Renters: rent is deliberately not sent to PolicyEngine.** PolicyEngine's property tax credit counts 20% of gross rent alongside real estate taxes, so `RentDependency` would make `mo_property_tax_credit` correct for a renter. It is omitted anyway, because it cannot change a WFTC result. Missouri's renter income limit is $27,500 for TY2025 against $30,000 for an owner-occupied homestead, and Missouri liability for the households in these scenarios does not turn positive until roughly $28,400 of wages — so wherever a renter's property tax credit is non-zero the liability cap is already $0, and wherever the cap is positive the renter's credit has phased out. Measured at PE 1.786.5 across an 11-point wage sweep from $24,000 to $32,000 with $12,000 annual rent: sending rent moved `mo_property_tax_credit` from $0 to as much as $107 while `mo_wftc` stayed identical at every point, a $0 difference throughout.
  - This is why no renter Test Scenario appears below. A renter case can be constructed that returns not eligible (for example $27,100 wages with $12,000 rent), but it returns not eligible with or without the rent input, so it would pass either way and could not detect the omission. Scenario 16's positive-credit-after-PTC case is only reachable for an owner, who gets the higher homestead income limit.
  - Revisit if Missouri's renter limit rises relative to the liability threshold, or if a scenario emerges where the two windows overlap. Adding the input also invalidates every recorded cassette, since the request body gains a `rent` field.
- **Rounding is PE's.** `mo_wftc` already applies Form MO-WFTC's line-by-line rounding and the Line 6 vs. Line 9 smaller-of comparison; the screener truncates to whole dollars on output as it does for every program. Do not re-implement the rounding sequence on top of PE's result.

---

## Acceptance Criteria

- Federal EITC base uses PE's current-year `eitc` as the Line 27/27a proxy (Criterion 1).
- Only Missouri-screened households are evaluated.
- Relationship structure produces the intended Single/HOH or Joint treatment (Criterion 3).
- Unmodeled MFS, Surviving Spouse, dependent-filer, and detailed-residency facts receive the committed inclusive handling (Criteria 2–4).
- The investment-income gate is PolicyEngine's `mo_wftc_eligible`, whose measure counts rental income; the accepted error direction is documented in Criterion 5 and pinned by Scenario 15.
- Year-specific thresholds/comparators applied correctly: `>` $4,050 TY2023; `>` $4,300 TY2024; `>` $4,400 TY2025.
- TY2023 uses 10%; TY2024 and forward use 20% (per current MO DOR guidance).
- Property Tax Credit reduces remaining liability before the WFTC cap; Line 42 assumed $0.
- A household with $0 remaining liability returns not eligible.
- Final value is the smaller of the rate-based amount and remaining liability, via the line-by-line rounding sequence; annual, rounded to a whole dollar.
- All 16 executable scenarios match both policy-correct eligibility and rounded value.

---

## Test Scenarios

> **Whole-dollar expectations are truncated, not rounded.** The API truncates
> `estimated_value` before serving it (`screener/views.py`, `clean_program`), so a
> PolicyEngine result of `104.83` is shown to the user as **$104**. Expected values
> below state the truncated figure. An earlier draft rounded instead, which overstated
> six scenarios by $1.


### Scenario 1: HOH Golden Path, Uncapped Credit
**What this tests**: Validates the baseline WFTC calculation at the 20% rate for a household not capped by remaining Missouri liability.
**Expected**: Eligible, $333

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Baseline uncapped-credit pathway — federal EITC and remaining Missouri liability are both well above 20% × EITC, so the full rate-based amount is paid. Confirms the core calculation chain before any boundary or cap is introduced.

**Relevant evidence or source**: Benefit Value items 1–4.

---

### Scenario 2: TY2023, 10% Rate
**What this tests**: Validates that TY2023's 10% rate applies instead of TY2024+'s 20% rate.
**Expected**: Eligible, $104

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 33 in TY2023), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 8 in TY2023), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Same household shape as Scenario 1, evaluated in TY2023, confirming the 10% rate applies instead of TY2024+'s 20%.

**Relevant evidence or source**: Benefit Value item 2.

---

### Scenario 3: Investment Income Over the TY2025 Limit
**What this tests**: Verifies Missouri's stricter investment-income limit denies the credit even when the federal test passes.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$6,000` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms Missouri's investment-income limit is enforced independently of federal EITC eligibility. At $6,000 of investment income in TY2025, the household exceeds Missouri's $4,400 limit and is not eligible, even though the federal EITC test alone would pass this household.

**Relevant evidence or source**: Criterion 5.

---

### Scenario 4: $0 Remaining Liability
**What this tests**: Verifies that MO's standard deduction floors tax before credits at $0, and that the eligibility gate denies the claim rather than paying $0.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$25,000` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: A $0 remaining-liability result is denied, not paid at $0.

**Relevant evidence or source**: Criterion 6.

---

### Scenario 5: Capped Credit
**What this tests**: Validates that when remaining liability is positive but below 20% of federal EITC, the smaller, capped amount is paid.
**Expected**: Eligible, $292

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$35,000` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms the liability cap binds correctly mid-range.

**Relevant evidence or source**: Benefit Value items 3–4.

---

### Scenario 6: Federal EITC Phases to $0
**What this tests**: Verifies that a household above the federal EITC cutoff is denied MO WFTC entirely.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$55,000` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms the federal gate alone blocks the credit, with no Missouri-specific rule needed.

**Relevant evidence or source**: Criterion 1.

---

### Scenario 7: Investment Income at the TY2025 Exact Threshold ($4,400)
**What this tests**: Validates that exactly $4,400 of investment income passes under the TY2025 `>` comparator.
**Expected**: Eligible, $192

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$4,400` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms the TY2025 boundary passes exactly at the threshold — $4,400 of investment income is eligible, since the disqualifying condition is `>` $4,400, not `>=`.

**Relevant evidence or source**: Criterion 5.

---

### Scenario 8: Investment Income $1 Over the TY2025 Threshold ($4,401)
**What this tests**: Verifies that the immediate next dollar above the TY2025 threshold fails.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$4,401` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms the TY2025 boundary fails one dollar past the threshold — $4,401 of investment income exceeds the $4,400 limit and is not eligible.

**Relevant evidence or source**: Criterion 5.

---

### Scenario 9: Investment Income at the TY2023 Exact Threshold ($4,050)
**What this tests**: Verifies that TY2023's `>` comparator passes at exactly $4,050 — the threshold itself remains eligible; only amounts above it disqualify.
**Expected**: Eligible, $40

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 33 in TY2023), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$4,050` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 8 in TY2023), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms TY2023's committed `>` comparator — exactly $4,050 of investment income does not disqualify, consistent with TY2024/2025's `>` rule and the federal-law basis for the threshold. Investment income of $4,050 reduces federal EITC to $401.098... (versus $1,048.29 with $0 investment income, per Scenario 2's identical household). Following the rounding sequence (Line 5 rounds first): Line 5 rounds to $401; Line 6 = 10% × $401 = $40.10, rounded to $40. Remaining Missouri liability comfortably exceeds this amount, so the credit is uncapped.

**Relevant evidence or source**: Criterion 5; Implementation rounding sequence.

---

### Scenario 10: Investment Income at the TY2024 Exact Threshold ($4,300)
**What this tests**: Validates that TY2024 applies its own distinct threshold and `>` comparator.
**Expected**: Eligible, $152

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 34 in TY2024), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$4,300` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 9 in TY2024), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms TY2024 uses its own threshold, not TY2023's or TY2025's — $4,300 of investment income is eligible under TY2024's `>` $4,300 rule.

**Relevant evidence or source**: Criterion 5.

---

### Scenario 11: Investment Income $1 Over the TY2024 Threshold ($4,301)
**What this tests**: Verifies that the immediate next dollar above the TY2024 threshold fails.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 34 in TY2024), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year; also Income type: `Investment Income (Dividends/Interest)`, Income amount: `$4,301` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 9 in TY2024), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms the TY2024 boundary fails one dollar past the threshold — $4,301 of investment income exceeds the $4,300 limit and is not eligible.

**Relevant evidence or source**: Criterion 5.

---

### Scenario 12: Single, Childless Worker
**What this tests**: Validates the plain Single filing status and the federal childless-worker EITC path.
**Expected**: Eligible, $16

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1995` (age 30), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$18,000` per year
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Confirms the Single/childless-worker path computes correctly with no spouse present and no children.

**Relevant evidence or source**: Criterion 3.

---

### Scenario 13: Joint (Married Filing Combined)
**What this tests**: Validates Missouri's "married filing combined" branch, inferred from household relationship flags alone.
**Expected**: Eligible, $401

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `3`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$45,000` per year
- **Person 2 (Spouse)**: Relationship: `Spouse`, Birth month/year: `June 1990` (age 35), Has income: `No`
- **Person 3 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: MFB collects no direct filing-status input — confirms the Joint path computes correctly from the head/spouse relationship flags alone.

**Relevant evidence or source**: Criterion 3.

---

### Scenario 14: Property Tax Credit Netting (Age-Based Path)
**What this tests**: Verifies that the Property Tax Credit must reduce remaining liability before WFTC's cap applies.
**Expected**: Not eligible

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1959` (age 66), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$28,400` per year, Annual real estate taxes paid: `$1,200`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: The Property Tax Credit reduces remaining Missouri tax liability before the WFTC cap. Because the Property Tax Credit fully absorbs the remaining liability in this household, the household is not eligible for MO WFTC.

**Relevant evidence or source**: Criterion 6; Benefit Value item 3.

---

### Scenario 15: Rental Income Counts Toward the Missouri Investment-Income Gate (PolicyEngine Approximation)
**What this tests**: Pins the accepted approximation in the investment-income gate. The $5,000 rental figure is deliberately above every year's threshold, so this scenario detects whether the gate counts rental income. Per criterion 5 the calculator delegates to PolicyEngine's `mo_wftc_eligible`, whose `eitc_relevant_investment_income` measure counts rental dollar-for-dollar — so the household is excluded. A calculator that instead applied a rental-exempt four-component gate would return Eligible / $174; that behavior is deliberately *not* what we ship.
**Expected**: Not eligible, $0

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1990` (age 35), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$40,000` per year; also Income type: `Rental Income`, Income amount: `$5,000` per year
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: PolicyEngine's `eitc_relevant_investment_income` includes `rental_income`, so this household's measured investment income is $5,000 — above the TY2025 threshold of $4,400 — and `mo_wftc_eligible` returns `False`, making `mo_wftc` $0. Measured at PE 1.786.5.

Two other effects are worth separating out, because both are correct and neither is what fails here. First, the rental income independently reduces the federal EITC through ordinary AGI phaseout: $868.33 against $1,667.33 for the same wages without rental in Scenario 1. Second, remaining Missouri liability is $762.88, comfortably above 20% of that EITC, so the liability cap is not binding — had the gate passed, the credit would have been `0.20 × $868.33 = $173.67`, rounded to $174. The exclusion comes solely from the gate.

Missouri's real test would route this filer to Publication 596 Worksheet 1, whose result may or may not exceed the threshold. Neither MFB nor PolicyEngine computes that; see criterion 5 for the accepted error direction.

**Relevant evidence or source**: Criterion 5 — Missouri's own investment-income definition is not limited to interest/dividends/capital gains; filers with rental or passive-activity income are routed to IRS Pub. 596 Worksheet 1, which expressly includes rental/royalty and passive-activity amounts.

---

### Scenario 16: Property Tax Credit Partially Reduces Liability (Positive WFTC Remains)
**What this tests**: Verifies the distinct partial-offset interaction — the Property Tax Credit reduces remaining Missouri liability without exhausting it, leaving a smaller but still-positive WFTC — as opposed to Scenario 14's full-exhaustion case.
**Expected**: Eligible, $14

**Household inputs**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Relationship: `Head of Household`, Birth month/year: `June 1959` (age 66), Has income: `Yes`, Income type: `Wages/Salaries`, Income amount: `$30,000` per year, Annual real estate taxes paid: `$1,010`
- **Person 2 (Child)**: Relationship: `Child`, Birth month/year: `June 2015` (age 10), Has income: `No`
- **Current Benefits**: Select `None`

**Calculation or eligibility explanation**: Scenario 14 proves PTC can fully exhaust remaining liability; Scenario 5 proves the ordinary liability cap with no PTC involved. Neither proves the distinct case where PTC applies and reduces liability only partially, leaving a positive WFTC below the uncapped rate-based amount. This household sits at Missouri's $30,000 net-household-income Property Tax Credit ceiling — right at, not over, the limit. The Property Tax Credit amount is taken directly from the official 2025 Property Tax Credit Claim Chart: for the $29,901–$30,000 income row and $1,001–$1,025 real-estate-tax-paid column, the chart gives a credit of $20 — at $1,010 in real estate taxes paid, this household falls in that column. `mo_income_tax_before_credits = $34.99` (Line 7; from Missouri's ordinary income tax computation, not the PTC chart — real estate taxes paid do not affect it). Line 42 assumed $0; Line 8 = $0 + $20 = $20. Remaining liability = max(0, $35 − $20) = $15. Federal EITC here is $3,265.33, so 20% × $3,265 = $653 comfortably exceeds remaining liability — the credit is capped by the reduced liability, not by the rate. PolicyEngine computes the cap without the intermediate whole-dollar rounding the form's worksheet describes, so it works from $34.985 rather than $35 and returns `mo_wftc = 14.985001` — measured at PE 1.786.5, and the value recorded in this scenario's cassette. Truncated for display that is the expected **$14**. The `$35 − $20 = $15` line-rounded figure above is what Form MO-WFTC's own worksheet yields; the difference is a fraction of a dollar of pre-rounding liability, and PolicyEngine's unrounded value is what ships.

**Relevant evidence or source**: RSMo §135.030; Form MO-PTS (2025); 2025 Property Tax Credit Claim Chart; Benefit Value item 3 (whole-dollar rounding sequence).

---

## Source Documentation

**Missouri statute**
- RSMo §143.177 — MO Working Family Tax Credit Act. https://www.revisor.mo.gov/main/OneSection.aspx?section=143.177 — eligible taxpayer definition, filing-status list, 20% statutory ceiling, nonrefundable/no-carryforward.
- RSMo §135.030 — Property Tax Credit eligibility and income ceilings. https://www.revisor.mo.gov/main/OneSection.aspx?section=135.030 — owner-occupied 2025 net-household-income upper limit of $30,000, basis for Scenario 16's income ceiling.

**Missouri forms and instructions**
- Form MO-WFTC (2023). https://dor.mo.gov/forms/MO-WFTC_2023.pdf — Line 2 (MFS only), Line 3 (investment income; form wording reads `>=` $4,050, MFB commits to `>` — see Criterion 5), Line 5 (federal EIC, Line 27), Line 6 (10%).
- Form MO-WFTC (2024). https://dor.mo.gov/forms/MO-WFTC_2024.pdf — Line 2 (MFS or dependent), Line 3 (`>` $4,300), Line 5 (Line 27), Line 6 (20%).
- Form MO-WFTC (2025, Rev. 12-2025). https://dor.mo.gov/forms/MO-WFTC_2025.pdf — Line 2 (MFS or dependent), Line 3 (`>` $4,400), Line 5 (Line 27a), Line 6 (20%), Lines 7–9 (liability cap), Line 10 (smaller-of final credit).
- MO-1040 Instructions. https://dor.mo.gov/forms/MO-1040%20Instructions_2025.pdf — Line 42 (Misc. Tax Credits), Line 43 (Property Tax Credit), Line 44 (WFTC), rounding rule.
- Form MO-PTS (2025). https://dor.mo.gov/forms/MO-PTS_2025.pdf — Property Tax Credit Schedule; HOH uses the Single PTC filing status; owner-occupied net-household-income ceiling.
- 2025 Property Tax Credit Claim Chart. https://dor.mo.gov/forms/Property%20Tax%20Claim%20Chart_2025.pdf — income-band × property-tax-paid lookup used for Scenario 16's $20 PTC.

**Missouri DOR guidance**
- MO Working Family Tax Credit FAQ. https://dor.mo.gov/faq/taxation/individual/missouri-working-family-tax-credit.html — "Eligibility Requirements" (positive remaining liability).

**Federal EITC source**
- IRC §32; IRS Publication 596. https://www.irs.gov/publications/p596 — investment-income limit, Worksheet 1 (rental/royalty and passive-activity income included for filers with Schedule E, Form 4797/8814, rental of personal property, or passive-activity income/loss — basis for Criterion 5's rental data-gap disclosure).

**PolicyEngine source**
- `PolicyEngine/policyengine-us`, `.../mo/tax/income/credits/mo_wftc.py`, `mo_wftc_potential.py`, `mo_wftc_liability_cap.py` — WFTC formula; PTC netted against remaining liability before the WFTC cap.
- `.../credits/mo_wftc_eligible.py` — federal-EITC/MFS/dependent/investment-income eligibility gate.
- `.../gov/irs/credits/earned_income/eitc_relevant_investment_income.py`, `.../gov/irs/tax/federal_income/net_investment_income.py`, parameter `gov.irs.investment.income.sources` — confirms `eitc_relevant_investment_income` includes `rental_income`, the reason Implementation requires an independent Missouri investment-income gate.
- `.../mo_ptc_taxunit_eligible.py` — Property Tax Credit age/disability eligibility paths.

**MFB backend source**
- `MyFriendBen/benefits-api`, `programs/framework/pe_dependencies/member.py` — `InvestmentIncomeDependency` (→ PE `long_term_capital_gains`), `RentalIncomeDependency` (→ PE `rental_income`), `TaxUnitHeadDependency`, `TaxUnitSpouseDependency`, `RentDependency`, `PropertyTaxExpenseDependency`.
