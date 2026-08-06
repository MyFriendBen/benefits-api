# Implement ACA Premium Tax Credit (MO) Program

## Program Details

- **Program**: ACA Premium Tax Credit (PTC)
- **State**: MO
- **White Label**: mo
- **Engine + Tier**: PE Federal (value varies) — eligibility and the benefit formula are federal (26 U.S.C. § 36B); nothing that governs *whether* a Missouri household qualifies differs from any other state. What varies for Missouri is the **dollar value** of the credit, driven by the household's county (which sets the benchmark Silver-plan premium) and income relative to the federal poverty line (FPL).
- **Research Date**: 2026-07-26

Missouri uses the federal Health Insurance Marketplace (HealthCare.gov), not a state-based exchange, so there is no state agency rule to research. A Missouri-specific wiring layer is still needed on the MFB side to get county and current-coverage data to PolicyEngine (PE), but the underlying eligibility/value formula itself is not Missouri-specific.

---

## Federal Eligibility Scope

PolicyEngine implements federal ACA PTC eligibility nationwide (26 U.S.C. § 36B). Missouri households are subject to the same filing-status, MAGI-to-FPL, Medicaid-coordination, immigration-status, and coverage tests as any other state. This light spec does not reimplement or exhaustively test federal eligibility; its scenarios isolate Missouri's state-specific benefit value (see Benefit Value and Implementation Coverage below), except for Scenario 4, which is an MFB wiring regression check (see Implementation Coverage).

- **Immigration status**: MFB's `legal_status_required` schema bundles DACA recipients into the same `otherWithWorkPermission` bucket as TPS/asylee/parolee holders, even though the ACA excludes DACA recipients specifically. Committed handling: accept this over-inclusion (DACA recipients will be shown as potentially eligible when they are not) — consistent with how other MFB programs handle this same schema limitation. No screener change is being made for this.
- **Filing status** is never set directly by MFB — it is derived from household relationship data (who is the head of household, spouse, dependents). No MFB calculator sets it explicitly, and this program's test scenarios don't either.
- **Framing**: this estimates *potential* eligibility, not a completed coverage month. The statute requires actual enrollment, no disqualifying coverage, and premium payment for at least one month — facts a pre-application screener cannot know. Any household that clears the income/status/coverage checks is shown as potential/estimated eligibility, never a guaranteed determination. The program description must use "estimated maximum" framing, not a guaranteed dollar amount.

---

## Benefit Value

**Formula**: `PTC = max(0, SLCSP − required contribution)`, computed annually per tax unit, where `SLCSP` (Second Lowest Cost Silver Plan) is the benchmark Silver-plan premium for the coverage family's rating area and the required contribution is an income-to-FPL sliding-scale percentage of MAGI (Modified Adjusted Gross Income).

**Calculation chain**:
1. Determine tax-unit size and the applicable FPL amount (see FPL source below).
2. Compute MAGI ÷ FPL as a percentage.
3. Look up the applicable-percentage bracket for that FPL percentage (IRS Revenue Procedure 2025-25 §3.01, table below) and interpolate within the bracket.
4. Required annual contribution = MAGI × applicable percentage.
5. Determine SLCSP for the coverage family's rating area (single-person tier when dependents don't pay a marketplace premium — see Mixed-coverage households below).
6. PTC = max(0, SLCSP − required annual contribution).
7. Truncate to a whole dollar (this is the binding annual value).
8. Display monthly = truncated annual ÷ 12, rounded.

**This is a benchmark-based maximum, not the household's final legal credit.** The statute determines the actual credit month-by-month and caps it at the premium of the plan someone actually picks — information the screener never has pre-application. A household may end up receiving less than the estimate if their selected plan's premium is below the benchmark. `estimated_value` and all user-facing copy must say "estimated" or "up to," never a guaranteed number.

**Worked example**, showing the calculation for the three test-scenario households below (values are calculated, not citable program amounts):

| Step | Scenario 1 (Jackson, single) | Scenario 2 (Boone, single) | Scenario 3 (Jackson, parent + 2 kids) |
|---|---|---|---|
| FPL guideline used | 2025 HHS guideline (2026 coverage uses the prior year's published guideline) | same | same |
| Tax-unit size / FPL amount | 1 → $15,650 (contiguous US) | 1 → $15,650 | 3 → $15,650 + 2×$5,500 = $26,650 |
| MAGI | $30,000 | $30,000 | $39,000 |
| MAGI ÷ FPL | 191% | 191% | 146% |
| Applicable-percentage bracket | 150–200% | 150–200% | 133–150% |
| Applicable figure (interpolated within bracket) | 6.1662% | 6.1662% | 3.9429% |
| Required annual contribution | $1,849.86 | $1,849.86 | $1,537.75 |
| SLCSP (single-person tier — Scenario 3's children don't pay a premium) | $6,856.14 | $8,580.20 | $6,555.73 |
| PTC = SLCSP − contribution | $5,006.28 | $6,730.34 | $5,017.98 |
| **Binding annual value (whole-dollar truncated)** | **$5,006** | **$6,730** | **$5,017** |
| **Displayed monthly (÷12, rounded)** | **$417/month** | **$561/month** | **$418/month** |

**Sources for the two external inputs**, quoted so the numbers can't drift to the wrong year/row:

- **FPL guideline — use the 2025 HHS poverty guideline** (2026 coverage relies on the prior year's published guideline), per the Federal Register notice (90 FR 5917, 2025-01-17): for "the 48 contiguous states and the District of Columbia," the guideline table lists **"$15,650"** for a household size of 1, with instructions to **"add $5,500 for each additional person."** (The 2026 guideline, $15,960/$5,680, is a different row and does not apply to a 2026 coverage year.)
- **Applicable-percentage table — use the 2026 table**, IRS Revenue Procedure 2025-25 §3.01:

  | Household income as % of FPL | Initial percentage | Final percentage |
  |---|---|---|
  | At least 133% but less than 150% | 3.14% | 4.19% |
  | At least 150% but less than 200% | 4.19% | 6.60% |

  (The same Revenue Procedure separately sets a 9.96% "Required Contribution Percentage" — that is the employer-coverage affordability threshold covered under Federal Eligibility Scope, not part of this value calculation.)

**Geographic variation**: the SLCSP — not the formula — is the one input that genuinely varies by Missouri geography. Holding income/age/household size constant and changing only county: Jackson County (rating area 3) → $6,856.14 SLCSP; Boone County (rating area 5) → $8,580.20 SLCSP — a $1,724/year swing in the benchmark premium alone. **Scenarios 1 and 2 below isolate exactly this**, holding every other input constant and varying only county.

**Known limitation — PolicyEngine's SLCSP runs slightly below the CMS-filed benchmark.** For Jackson County, PolicyEngine's modeled SLCSP is about 1.6% below the true CMS second-lowest Silver premium ($571.35/mo modeled vs. $580.77/mo actual), understating the annual PTC estimate by roughly $108–113/year. Boone County's gap is much smaller (about $0.36/month, ~$5/year) because its lowest and second-lowest plans happen to be priced close together this year. Committed treatment: the calculator displays PolicyEngine's own computed value as-is; this is a known nationwide PolicyEngine model limitation, not something to correct per state.

**Mixed-coverage households are evaluated per person, not per household.** Eligibility and Medicaid status are computed per person. A parent can be PTC-eligible (on a single-person SLCSP, since dependents don't pay a marketplace premium) while children are simultaneously Medicaid-eligible (Scenario 3 below isolates this). The calculator must not describe the whole household as uniformly "on Medicaid" or "PTC-ineligible."

**Cadence and display**: annual value, displayed monthly (truncated annual ÷ 12). Refundable federal tax credit — eligible households can receive it regardless of tax liability.

**12-month assumption**: every value in this spec assumes 12 months of unchanged eligibility, income, and household composition. The real legal credit can differ month to month if any of those change — an inherent limitation of a point-in-time screener, shared by every other MFB annual-value calculator, not specific to this program.

---

## Implementation Coverage

- ✅ Evaluable and isolated by this spec's scenarios: county-driven SLCSP variation (Scenarios 1–2), per-person mixed-coverage handling (Scenario 3), current employer-sponsored insurance wiring (Scenario 4).
- ⚠️ Not yet built: county/FIPS derivation from ZIP, and `has_esi` (current employer-sponsored insurance) wiring to PolicyEngine — see the engineering implementation note under Acceptance Criteria below.
- This is a **light spec**: eligibility is federal and trusted to PolicyEngine, so the scenario suite isolates Missouri's state-specific *value* and the MFB wiring layer rather than re-testing every federal eligibility branch.

---

## Research Sources

**Statute & regulations**
- [26 U.S.C. § 36B](https://www.law.cornell.edu/uscode/text/26/36B) — Premium Tax Credit statute
- [26 CFR § 1.36B-1 et seq.](https://www.law.cornell.edu/cfr/text/26/1.36B-1) — PTC regulations
- [IRS Instructions for Form 8962 (2025)](https://www.irs.gov/instructions/i8962) — "not more than 400%" income eligibility language
- [IRS Revenue Procedure 2025-25](https://www.irs.gov/pub/irs-drop/rp-25-25.pdf) — 2026 applicable-percentage (required-contribution) table

**Agency data**
- CMS 2026 Exchange Public Use Files (rate, plan-attributes, service-area) — basis for the CMS cross-check on SLCSP accuracy noted under Benefit Value

---

## Acceptance Criteria

- [ ] Scenario 1 (single adult, $30,000/year, Jackson County): **eligible**, $5,006/year ($417/month)
- [ ] Scenario 2 (same household, Boone County — isolates county/SLCSP variation): **eligible**, $6,730/year ($561/month)
- [ ] Scenario 3 (single parent + 2 children, $39,000/year, Jackson County — isolates per-person mixed coverage): parent **PTC-eligible**, $5,017/year ($418/month); both children **Medicaid-eligible**, not PTC-eligible
- [ ] Scenario 4 (single adult with employer-sponsored insurance, Jackson County — MFB wiring regression check): **not eligible**

**Engineering implementation note.** Build required, not promotion — none of this exists yet:
- Register a Missouri-specific calculator (`MoAca`) under Missouri's `name_abbreviated` key.
- Derive county/FIPS from the screener's ZIP code and pass it to PolicyEngine as the rating-area input.
- Wire the screener's health-insurance field (`Employer-sponsored`) to PolicyEngine's `has_esi` input — today nothing wires this, so an otherwise-eligible household with employer coverage would incorrectly show as PTC-eligible until this is built (Scenario 4 is the regression check for it).
- Do not set filing status from MFB — pass household relationship data (head of household, spouse, dependents) and let PolicyEngine derive filing status from it.
- Handle mixed-eligibility households at the per-person level (see Benefit Value): a parent can be PTC-eligible while dependents are Medicaid-eligible in the same household, and the UI must reflect both statuses rather than one blanket status.
- `value_format`: monthly (annual truncated value ÷ 12).
- **Owner**: MFB engineering, during implementation. **Clears when**: `MoAca` is registered and all four scenarios pass through the real integrated `benefits-api` → PolicyEngine path.

---

## Test Scenarios

> Each eligible scenario asserts the expected **dollar value**, so a scenario breaks if Missouri's SLCSP or the calculation chain drifts. Ages are entered via birth month/year (the screener's actual fields, not a raw age field).

### Scenario 1: Single adult, mid-income, Jackson County (Kansas City) — baseline
**What we're checking**: Baseline PTC eligibility and value for a single adult with income in the Medicaid-expansion-to-400%-FPL band and no other coverage.
**Expected**: Eligible — **$5,006/year ($417/month)**

**Steps**:
- **Location**: ZIP `64108`, county `Jackson`
- **Household**: 1 person
- **Person 1**: Head of Household, birth month/year `March 1986` (age 40), employment income $2,500/month ($30,000/year), no health insurance, US citizen

**Why this matters**: the baseline happy-path case confirming a clearly eligible applicant is correctly identified with the right value.

---

### Scenario 2: Same person, same income, Boone County (Columbia) — isolates county/SLCSP variation
**What we're checking**: Whether the credit's dollar value shifts correctly with rating area alone, holding income, age, and household composition constant.
**Expected**: Eligible — **$6,730/year ($561/month)**

**Steps**:
- **Location**: ZIP `65201`, county `Boone`
- **Household**: 1 person
- **Person 1**: Head of Household, birth month/year `March 1986` (age 40), employment income $2,500/month ($30,000/year), no health insurance, US citizen

**Why this matters**: isolates the rating-area/SLCSP effect — the scenario that most directly demonstrates that only the value, not eligibility, varies by county.

---

### Scenario 3: Single parent, mixed coverage — parent PTC-eligible, children Medicaid-eligible
**What we're checking**: Whether the calculator correctly handles a mixed-coverage household, where the parent is PTC-eligible while both children are simultaneously Medicaid-eligible.
**Expected**: Parent's PTC = **$5,017/year ($418/month)**; both children Medicaid-eligible, not PTC-eligible

**Steps**:
- **Location**: ZIP `64108`, county `Jackson`
- **Household**: 3 people
- **Person 1**: Head of Household, birth month/year `March 1991` (age 35), employment income $3,250/month ($39,000/year), no health insurance, US citizen
- **Person 2**: Child, birth month/year `January 2016`, no income, no health insurance
- **Person 3**: Child, birth month/year `January 2019`, no income, no health insurance

**Why this matters**: this isolates the common real-world shape for a working single parent in Missouri (adult income above the Medicaid-expansion ceiling, children's Medicaid/CHIP ceiling much higher at the same income). Verifies the calculator picks the correct single-person SLCSP for the parent and doesn't describe the household as uniformly one eligibility status.

---

### Scenario 4: Current employer-sponsored insurance — MFB wiring regression check
**What we're checking**: Whether current employer-sponsored insurance correctly disqualifies an otherwise-eligible household once `has_esi` is wired to PolicyEngine.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `64108`, county `Jackson`
- **Household**: 1 person
- **Person 1**: Head of Household, birth month/year `March 1986` (age 40), employment income $2,500/month ($30,000/year), health insurance: Employer-sponsored, US citizen

**Why this matters**: confirms current employer coverage is correctly passed through and disqualifies the household — without the `has_esi` wiring (see the engineering implementation note under Acceptance Criteria), this household would incorrectly show as PTC-eligible.
