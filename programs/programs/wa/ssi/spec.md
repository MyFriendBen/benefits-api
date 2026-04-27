# WA: Supplemental Security Income (SSI)

- **Program**: Supplemental Security Income (SSI)
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-04-27

## Eligibility Criteria

| # | Criterion | Screener Fields | Can Evaluate? | Notes | Source |
|---|-----------|-----------------|---------------|-------|--------|
| 1 | Aged 65 or older | `household_member.age` | ✅ | | 42 U.S.C. § 1382c(a)(1)(A); 20 CFR § 416.202(a) |
| 2 | Blind — central visual acuity ≤ 20/200 in better eye, or visual field ≤ 20° | `household_member.visually_impaired` | ⚠️ | `visually_impaired` is broader than SSA statutory blindness; treat as a likely-eligible signal, not a definitive determination | 42 U.S.C. § 1382c(a)(2); 20 CFR §§ 416.981, 416.983 |
| 3 | Disabled — medically determinable impairment expected to last 12+ months or result in death; for adults, unable to engage in SGA | `household_member.long_term_disability` | ⚠️ | Screener captures duration via `long_term_disability` but cannot assess functional/vocational limits; SSA medical adjudication is required | 42 U.S.C. § 1382c(a)(3); 20 CFR §§ 416.905, 416.906 |
| 4 | U.S. citizen or qualified non-citizen meeting SSI alien restrictions | `legal_status_required` | ✅ | Captured via program's `legal_status_required` configuration. Note: most non-citizens face strict 7-year limits or 40-quarter requirements under PRWORA | 8 U.S.C. § 1612(a)(2); 42 U.S.C. § 1382c(a)(1)(B) |
| 5 | Resident of one of the 50 states, DC, or Northern Mariana Islands | `screen.white_label`, `screen.zipcode` | ✅ | WA white label + WA zipcode satisfies state residency for screener purposes | 42 U.S.C. § 1382c(a)(1)(B)(i); 20 CFR § 416.1603 |
| 6 | Countable income below the Federal Benefit Rate (FBR) | `household_member.has_income`, `income_streams (type, amount, frequency)` | ⚠️ | Income streams are collected, but countable-income computation (general/earned-income exclusions, in-kind support and maintenance, deeming) is non-trivial; left to PolicyEngine | 42 U.S.C. § 1382(a); 20 CFR §§ 416.1100–416.1182 |
| 7 | Countable resources ≤ $2,000 individual / $3,000 couple | `screen.household_assets` | ⚠️ | `household_assets` is a single number; the screener cannot separate countable from excluded resources (home, one vehicle, burial space, etc.), so this is an over-conservative signal | 42 U.S.C. § 1382(a)(3); 20 CFR §§ 416.1201, 416.1205, 416.1210 |
| 8 | Spousal income/resource deeming (eligible individual + ineligible spouse) | `household_member.relationship`, `income_streams`, `household_assets` | ⚠️ | Household composition is captured; deeming math is left to PolicyEngine | 20 CFR §§ 416.1160, 416.1163 |
| 9 | Parental deeming for child applicants (under 18 living with parents) | `household_member.relationship`, `household_member.age`, `income_streams`, `household_assets` | ⚠️ | Same as above — composition captured, deeming computed by PolicyEngine | 20 CFR §§ 416.1165, 416.1202 |
| 10 | Not already receiving SSI | `screen.has_ssi` | ✅ | Captured via the "Current household benefits" step | — |
| 11 | Filed for / receiving any other benefits the applicant is entitled to (SS, pensions, etc.) | `income_streams (sSRetirement, sSDisability, sSSurvivor, sSDependent, pension, veteran)` | ✅ | Inferred from income streams; counts as unearned income against the FBR rather than as a hard disqualifier | 20 CFR § 416.210; 42 U.S.C. § 1382(e)(2) |
| 12 | Not absent from the U.S. for 30+ consecutive days | — | ❌ | Not collected by the screener | 20 CFR § 416.1327; 42 U.S.C. § 1382(f) |
| 13 | Not a resident of a public institution (with limited exceptions) | — | ❌ | Not collected by the screener | 42 U.S.C. § 1382(e)(1); 20 CFR § 416.211 |
| 14 | Not a fugitive felon, parole/probation violator, or in confinement for a felony | — | ❌ | Not collected by the screener | 42 U.S.C. § 1382(e)(4)–(5); 20 CFR § 416.1339 |
| 15 | Applicant assigns rights to other federal benefits if applicable | — | ❌ | Procedural; happens at application time, not evaluable here | 20 CFR § 416.210 |

## Coverage

- **Fully evaluable**: 4 of 15 criteria (27%) — age, citizenship/qualified status, U.S. residency, duplicate enrollment
- **Partially evaluable**: 6 of 15 (40%) — blindness, disability duration, countable income, countable resources, spousal deeming, parental deeming
- **Not evaluable**: 5 of 15 (33%) — vocational/functional disability adjudication, U.S. absence, institutional residence, fugitive/incarceration status, procedural assignment of rights
- **Summary**: The screener can confidently identify applicants who are demographically and categorically in scope (aged 65+, long-term disabled, blind, with WA residence and qualifying citizenship) and not currently receiving SSI. Income and resource feasibility checks are best handled by PolicyEngine, which applies the federal countable-income exclusions and deeming rules. The screener cannot perform SSA's medical or vocational determination, nor verify residency duration, institutional status, or felony/fugitive flags.

## Benefit Value

SSI benefits equal the Federal Benefit Rate (FBR) minus countable income. As of 2026 (after the 2.8% COLA):

- **Individual FBR**: $994/month ($11,928/year)
- **Eligible couple FBR**: $1,491/month ($17,892/year)

Washington does **not** pay a state supplement to SSI for most aged, blind, or disabled adults living independently. (Some narrow categories — e.g., individuals in certain residential care facilities — receive a small state supplement administered by Washington DSHS, but this is out of scope for the screener at launch.) The estimated benefit value should be the federal SSI amount as computed by PolicyEngine for the household, reduced by countable income via the SSA exclusions (general $20 + earned $65 + ½ remaining earned).

## Sources

- [SSA — SSI Home](https://www.ssa.gov/ssi/)
- [SSA — Apply for SSI](https://www.ssa.gov/apply/ssi)
- [SSA — Understanding SSI](https://www.ssa.gov/ssi/text-understanding-ssi.htm)
- [SSA — SSI Federal Payment Amounts (2026)](https://www.ssa.gov/oact/cola/SSI.html)
- [SSA — 2026 COLA Fact Sheet](https://www.ssa.gov/news/en/cola/factsheets/2026.html)
- [Washington DSHS — Cash Assistance Programs](https://www.dshs.wa.gov/esa/community-services-offices/cash-assistance)
- [42 U.S.C. Chapter 7, Subchapter XVI — SSI](https://www.law.cornell.edu/uscode/text/42/chapter-7/subchapter-XVI)
- [20 CFR Part 416 — Supplemental Security Income for the Aged, Blind, and Disabled](https://www.ecfr.gov/current/title-20/chapter-III/part-416)

## Test Scenarios

### Scenario 1: Aged 65+, no income, no resources

**Checks**: Core happy path — age-eligible, no countable income, resources at $0
**Expected**: Eligible (full federal FBR for individual)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70`, Head of Household, U.S. Citizen, no disability, income: `$0`, no insurance
- **Household assets**: `$0`

**Why this matters**: Cleanest aged-only path. Confirms the screener treats age 65+ as a sufficient categorical entry into SSI when income and resources are clearly under thresholds.

---

### Scenario 2: Long-term disabled adult under 65, no income

**Checks**: Disability path via `long_term_disability` flag for an adult under retirement age
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `45`, Head of Household, U.S. Citizen, **long-term disability**, income: `$0`, no insurance
- **Household assets**: `$0`

**Why this matters**: Validates the disability route is honored independently of age, and that `long_term_disability` (not `disabled`) is the field the implementation should use for the 12-month duration requirement.

---

### Scenario 3: Visually impaired adult, no income

**Checks**: Blindness path via `visually_impaired` flag
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98052`, County `King`
- **Household**: 1 person
- **Person 1**: Age `40`, Head of Household, U.S. Citizen, **visually impaired**, no other disability, income: `$0`, no insurance
- **Household assets**: `$0`

**Why this matters**: Confirms the blind path is enabled. The screener's `visually_impaired` field is broader than SSA statutory blindness but should still surface SSI as a likely match for SSA review.

---

### Scenario 4: Aged 65+ with unearned income above FBR

**Checks**: Income disqualification — Social Security retirement income exceeds the FBR for an individual
**Expected**: Not eligible (countable unearned income > FBR after $20 general exclusion)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `68`, Head of Household, U.S. Citizen, no disability, income: `$1,200/month Social Security retirement`, no insurance
- **Household assets**: `$0`

**Why this matters**: Confirms the income test enforces the FBR ceiling. $1,200 SS retirement minus the $20 general exclusion = $1,180 countable, which is above the 2026 individual FBR of $994.

---

### Scenario 5: Aged 65+ with countable resources above $2,000

**Checks**: Resource disqualification — household assets above the individual SSI resource limit
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70`, Head of Household, U.S. Citizen, no disability, income: `$0`, no insurance
- **Household assets**: `$5,000`

**Why this matters**: Confirms the resource ceiling is enforced. Note that the screener's `household_assets` is a single conservative number; downstream calculation must apply SSA's resource exclusions (home, one vehicle, burial space) when integrated with PolicyEngine.

---

### Scenario 6: Eligible aged couple, no income

**Checks**: Couple FBR path — both spouses age-eligible, no income or assets
**Expected**: Eligible (couple benefit at $1,491/month FBR shared between members)

**Steps**:
- **Location**: ZIP `98109`, County `King`
- **Household**: 2 people
- **Person 1 (Head)**: Age `70`, U.S. Citizen, no disability, income: `$0`, no insurance
- **Person 2 (Spouse)**: Age `68`, U.S. Citizen, no disability, income: `$0`, no insurance
- **Household assets**: `$0`

**Why this matters**: Validates couple FBR application ($1,491/month for 2026) and that household composition is correctly evaluated for two-person eligibility.

---

### Scenario 7: Adult under 65 without disability or blindness

**Checks**: Categorical disqualification — fails age, blindness, and disability prongs
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `35`, Head of Household, U.S. Citizen, no disability, no visual impairment, income: `$0`, no insurance
- **Household assets**: `$0`

**Why this matters**: Confirms an adult who fails all three categorical entry routes is filtered out, even with zero income and assets.

---

### Scenario 8: Already receiving SSI

**Checks**: Duplicate enrollment — current SSI recipient should not be shown as a new recommendation
**Expected**: Not eligible (already has)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70`, Head of Household, U.S. Citizen, no disability, income: `$994/month SSI`, no insurance
- **Household assets**: `$0`
- **Current benefits**: SSI (`has_ssi = true`)

**Why this matters**: Validates the "already has" path so existing recipients aren't redundantly listed under "Programs Found".

---

### Scenario 9: Long-term disabled child with parental deeming below limits

**Checks**: Child applicant — parental deeming math left to PolicyEngine; the screener should still surface SSI as evaluable
**Expected**: Eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 3 people
- **Person 1 (Head)**: Age `40`, U.S. Citizen, no disability, wages: `$1,500/month`, employer insurance
- **Person 2 (Spouse)**: Age `38`, U.S. Citizen, no disability, income: `$0`, employer insurance
- **Person 3 (Child)**: Age `8`, U.S. Citizen, **long-term disability**, income: `$0`, employer insurance
- **Household assets**: `$0`

**Why this matters**: Confirms child SSI eligibility is surfaced when the disabled minor lives with low-income parents. Exact benefit value depends on PolicyEngine's deeming computation; the screener's job is to identify the household as a candidate.

---

### Scenario 10: General disability flag only, no long-term disability

**Checks**: SSI requires a disability of 12+ months; a short-term `disabled` flag without `long_term_disability` should not qualify
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `45`, Head of Household, U.S. Citizen, **disabled: true**, **long_term_disability: false**, income: `$0`, no insurance
- **Household assets**: `$0`

**Why this matters**: Mirrors the TX SSDI guidance that the long-term flag is the correct field for the 12-month duration test. A general "disabled" flag without the long-term qualifier is not sufficient on its own.

---

### Scenario 11: Aged 65+ with partial Social Security retirement income (under FBR)

**Checks**: Partial offset — eligible with reduced SSI when unearned income is below FBR
**Expected**: Eligible (reduced benefit)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `72`, Head of Household, U.S. Citizen, no disability, income: `$500/month Social Security retirement`, no insurance
- **Household assets**: `$0`

**Why this matters**: Validates that some unearned income reduces, but does not eliminate, the SSI benefit. Expected approximate value: $994 (2026 FBR) − ($500 − $20 general exclusion) = `$514/month`. The screener should flag eligibility; PolicyEngine performs the precise math.

---

### Out-of-band: Non-citizen without qualified status

The SSI alien restriction (8 U.S.C. § 1612(a)(2)) is enforced through the program's `legal_status_required` configuration (`["citizen", "gc_5plus"]`) and the post-results citizenship filter chip on the Results UI, not via a household-member field on the screen. As a result, this case is not represented in the JSON validation suite — it is verified manually by toggling the citizenship filter and confirming that `wa_ssi` disappears for users who do not select an SSI-qualifying status.
