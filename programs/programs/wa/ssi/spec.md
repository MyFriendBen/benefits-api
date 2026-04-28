# Implement Supplemental Security Income (SSI) (WA) Program

## Program Details

- **Program**: Supplemental Security Income (SSI)
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-04-27

## Eligibility Criteria

1. **Aged 65 or older**
   - Screener fields: `household_member.age`, `household_member.birth_year_month`
   - Source: 42 U.S.C. § 1382c(a)(1)(A); 20 CFR § 416.202(a). Aged status is one of three categorical entry routes to SSI.

2. **Disability — medically determinable physical or mental impairment expected to last 12+ continuous months or result in death; for adults, the impairment must prevent substantial gainful activity (SGA)**
   - Screener fields: `household_member.disabled` **OR** `household_member.long_term_disability`; `income_streams (wages, selfEmployment)`
   - Note: Either disability flag should satisfy this criterion. The screener question backing `disabled` is *"Currently have any disabilities that make you unable to work now or in the future"*, which already captures the SSA-relevant signal of an inability to work that is expected to continue, so it should not be filtered out. `long_term_disability` is a narrower self-attestation of a clearly long-term/permanent condition. This matches the model's existing `HouseholdMember.has_disability()` helper, which ORs `disabled || visually_impaired || long_term_disability`. The screener cannot perform SSA's medical adjudication or vocational analysis (Listings of Impairments, Medical-Vocational Guidelines), so eligibility is treated as a *likely-eligible* signal pending SSA review.
   - **SGA test is broken out as Criterion #2a below** (per Caton's PR review — promoted from a sub-bullet here so it is clearly an evaluable, screener-disqualifying criterion).
   - **Divergence from TX SSDI precedent**: `tx_ssdi`'s implementation requires `long_term_disability=true` and treats `disabled=true` alone as insufficient. Per product/review feedback, that interpretation is too strict for WA SSI. We accept either flag; recommend revisiting the TX SSDI rule in a follow-up.
   - Source: 42 U.S.C. § 1382c(a)(3); 20 CFR §§ 416.905, 416.906; SSA Blue Book.

2a. **Not engaged in Substantial Gainful Activity (SGA) — for non-blind disability claims**
   - Screener fields: `household_member.disabled` / `household_member.long_term_disability`; `household_member.visually_impaired`; `income_streams (wages, selfEmployment)`
   - Rule: A non-blind applicant claiming SSI on the disability path whose monthly earned income exceeds the SGA threshold is presumed to be **engaging in SGA** and is therefore **not disabled** for SSI purposes — disqualified at the screener stage. The blind path (Criterion #3) is statutorily exempt from the SGA test.
   - SGA thresholds (2026): **non-blind = $1,690/month**, **blind = $2,830/month** (PolicyEngine `gov.ssa.sga.non_blind` / `gov.ssa.sga.blind`).
   - PolicyEngine implementation: `ssi_engaged_in_sga` (in `variables/gov/ssa/ssi/eligibility/income/ssi_engaged_in_sga.py`) computes `monthly_income = ssi_earned_income / MONTHS_IN_YEAR` and returns `(monthly_income > p.non_blind) & ~is_blind`. The check uses earned income only — unearned income (e.g., SS retirement) does not affect SGA. The screener passes wages from `income_streams` to PE for evaluation.
   - Note: This criterion overlaps logically with Criterion #2 (Disability) but is broken out per reviewer guidance because (a) it is a distinct, evaluable, monthly-earnings-based test, (b) the PE variable is a separate boolean check, and (c) it has its own ineligible test scenario (Scenario 14). Visually impaired applicants on the blindness path are exempt and should still surface SSI as a candidate even when earning above the non-blind SGA limit.
   - Source: 42 U.S.C. § 1382c(a)(3)(D); 20 CFR §§ 416.971, 416.974; [SSA — SGA amounts](https://www.ssa.gov/oact/cola/sga.html).

3. **Statutory blindness — central visual acuity ≤ 20/200 in the better eye with corrective lens, or visual field ≤ 20°**
   - Screener fields: `household_member.visually_impaired`
   - Note: The screener's `visually_impaired` flag is broader than SSA's statutory definition of blindness; it should be treated as a *likely-eligible* signal pending SSA verification of acuity/field measurements.
   - Source: 42 U.S.C. § 1382c(a)(2); 20 CFR §§ 416.981, 416.983.

4. **U.S. citizen, U.S. national, or qualified alien meeting SSI's narrow PRWORA categories**
   - Screener fields: program-level `legal_status_required` (set to `["citizen", "gc_5plus", "refugee"]` in the program config); post-results citizenship filter chip
   - Note: Most non-citizens face strict SSI alien restrictions: 7-year limits for refugees/asylees/Cuban-Haitian entrants, 40-quarter requirements for LPRs, and U.S.-military-service exemptions. The screener filters at the program-config level and via the citizenship chip on the Results UI; immigration sub-status is not collected as a household-member field.
   - **Divergence from TX SSI precedent**: `tx_ssi_initial_config.json` uses `["citizen", "gc_5plus"]` only. We add `refugee` because (a) it is statutorily eligible (8 U.S.C. § 1612(a)(2)(A)), (b) PolicyEngine treats `REFUGEE` as a qualified noncitizen with no time cutoff in the model (see `parameters/gov/ssa/ssi/eligibility/status/qualified_noncitizen_status.yaml`), and (c) inclusion is more user-protective than omission for a likely-eligible filter. Recommend back-porting this fix to TX SSI in a follow-up.
   - **Coverage gap vs. PolicyEngine**: PE's qualified-noncitizen list also includes `ASYLEE`, `DEPORTATION_WITHHELD`, `CUBAN_HAITIAN_ENTRANT`, `CONDITIONAL_ENTRANT`, and `PAROLED_ONE_YEAR`. The MFB chip enum currently only exposes `refugee` from this set, so applicants in the other 4 PE-eligible noncitizen categories cannot self-select into SSI via the screener. Treat this as a known under-counting limitation pending a richer immigration-status capture.
   - **Known PolicyEngine model limitation**: `is_ssi_qualified_noncitizen.py` enforces the LPR 40-quarter rule but does **not** enforce the 7-year cutoff for refugees/asylees/Cuban-Haitian entrants. Long-tenured refugees who have exhausted the 7-year window will be over-counted by PolicyEngine. The screener's chip-level filter does not correct for this either; it is a policy-modeling gap to revisit when SSI calculator implementation begins.
   - Source: 8 U.S.C. § 1612(a)(2); 42 U.S.C. § 1382c(a)(1)(B); SSA POMS [SI 00502.100](https://secure.ssa.gov/poms.nsf/lnx/0500502100), [SI 00502.135](https://secure.ssa.gov/poms.nsf/lnx/0500502135).

5. **Resident of one of the 50 states, DC, or the Northern Mariana Islands**
   - Screener fields: `screen.white_label`, `screen.zipcode`
   - Source: 42 U.S.C. § 1382c(a)(1)(B)(i); 20 CFR § 416.1603. WA white label + WA ZIP code satisfies state residency for screener purposes.

6. **Not already receiving SSI**
   - Screener fields: `screen.has_ssi`
   - Note: Captured via the "Current household benefits" step. Households already receiving SSI are filtered out to prevent duplicate-enrollment recommendations.
   - Source: General SSI policy — households cannot be screened into a benefit they already receive.

7. **Countable income below the Federal Benefit Rate (FBR)**
   - Screener fields: `household_member.has_income`, `income_streams (type, amount, frequency)`
   - Note: Income streams are collected, but countable-income computation (general $20 exclusion, earned-income $65 + ½ remaining exclusion, in-kind support and maintenance reductions, deeming) is non-trivial. Detailed math is delegated to PolicyEngine; the screener applies a conservative pre-filter against the 2026 FBR ($994 individual / $1,491 couple).
   - PolicyEngine implementation (verified against `policyengine-us` parameters and variables):
     - General income exclusion: **$20/month** (`gov.ssa.ssi.income.exclusions.general`) — applied to unearned income first, remainder to earned.
     - Earned income flat exclusion: **$65/month** (`gov.ssa.ssi.income.exclusions.earned`).
     - Earned-income share excluded above flat: **0.5** (`gov.ssa.ssi.income.exclusions.earned_share`) — i.e., the standard "$65 + ½ remaining" rule.
     - In-kind support and maintenance (ISM): PolicyEngine implements both VTR (one-third reduction; `gov.ssa.ssi.amount.one_third_reduction_rate = 0.3333`) and PMV (presumed maximum value capped at 1/3 FBR + $20; `gov.ssa.ssi.income.ism.pmv_fbr_fraction = 0.3333`). The screener does not collect housing/food-from-others fields (`ssi_lives_in_another_persons_household`, `ssi_receives_shelter_from_others_in_household`, `ssi_receives_food_from_others`), so PE will default these to `false` and ISM reductions will not fire — applicants in another's household may be slightly over-credited at the screener stage.
     - Final variable: `ssi_countable_income`; eligibility check via `ssi_amount_if_eligible` and `ssi`.
   - Source: 42 U.S.C. § 1382(a); 20 CFR §§ 416.1100–416.1182, 416.1131, 416.1140.

8. **Countable resources at or below $2,000 (individual) or $3,000 (couple)**
   - Screener fields: `screen.household_assets`
   - Note: `household_assets` is a single conservative number; the screener cannot separate countable from excluded resources (home, one vehicle, household goods, burial space, etc.). Pre-filter on the raw asset value, then defer to PolicyEngine for the precise countable-resource calculation.
   - PolicyEngine implementation: Resource limits ($2,000 individual / $3,000 couple) have been unchanged since 1989 (`gov.ssa.ssi.eligibility.resources.limit.individual` / `couple`). The countable-resource list (`gov.ssa.ssi.eligibility.resources.countable`) includes only `bank_account_assets`, `stock_assets`, `bond_assets` — explicitly excluding home, one vehicle, household goods, burial plots, and retirement accounts. The screener's `household_assets` field is therefore a conservative over-estimate; some applicants flagged "ineligible" at the screener stage may pass once SSA's exclusions are applied.
   - Source: 42 U.S.C. § 1382(a)(3); 20 CFR §§ 416.1201, 416.1205, 416.1210; SSA POMS [SI 01140.200](https://secure.ssa.gov/poms.nsf/lnx/0501140200).

9. **Spousal income/resource deeming — for an eligible individual living with an ineligible spouse**
   - Screener fields: `household_member.relationship`, `income_streams`, `household_assets`
   - Note: Household composition (head + spouse) is captured. The screener does not perform deeming math; it is left to PolicyEngine.
   - Source: 20 CFR §§ 416.1160, 416.1163.

10. **Parental deeming — for child applicants under 18 living with parents**
    - Screener fields: `household_member.relationship`, `household_member.age`, `income_streams`, `household_assets`
    - Note: Household composition (parent/child) is captured. The screener does not perform parent-to-child deeming; it is left to PolicyEngine.
    - Source: 20 CFR §§ 416.1165, 416.1202.

11. **Filed for / receiving any other applicable benefits the applicant is entitled to (Social Security retirement, SSDI, pensions, etc.)**
    - Screener fields: `income_streams (sSRetirement, sSDisability, sSSurvivor, sSDependent, pension, veteran)`
    - Note: This is enforced as an income offset (counts as unearned income against the FBR), not a hard disqualifier. SSA requires SSI applicants to apply for any other benefits they may be entitled to before/while receiving SSI.
    - Source: 20 CFR § 416.210; 42 U.S.C. § 1382(e)(2).

12. **Not absent from the United States for 30+ consecutive days** ⚠️ *data gap*
    - Note: The screener does not collect U.S.-presence/absence data. This is a procedural verification at the application stage; affects a small subset of applicants.
    - Source: 42 U.S.C. § 1382(f); 20 CFR § 416.1327.
    - Impact: Low

13. **Not a resident of a public institution (jail, prison, hospital, nursing facility, etc.) — with limited exceptions** ⚠️ *data gap*
    - Note: The screener does not collect institutional-residence status. SSI is generally suspended during institutional residence longer than a calendar month.
    - Source: 42 U.S.C. § 1382(e)(1); 20 CFR § 416.211.
    - Impact: Low

14. **Not a fugitive felon, parole or probation violator, or in confinement for a felony** ⚠️ *data gap*
    - Note: The screener does not collect criminal-justice status. Disqualification under this rule affects a small population.
    - Source: 42 U.S.C. § 1382(e)(4)–(5); 20 CFR § 416.1339.
    - Impact: Low

15. **Procedural: applicant assigns rights to other federal benefits when applicable** ⚠️ *not evaluable*
    - Note: Procedural; happens at the application stage, not pre-screening. Out of scope for the screener.
    - Source: 20 CFR § 416.210.
    - Impact: Low

## Priority Criteria

SSI is a federal entitlement program — there is no waitlist or priority queue. Anyone who meets the eligibility criteria is entitled to receive benefits, subject to verification by the Social Security Administration. There are no priority criteria to surface in the program description.

The following are **administrative requirements** (intentionally excluded from "Eligibility Criteria" per the canonical reviewer guide) that should be mentioned in the user-facing description or `documents` list rather than as eligibility checks:

- Must apply through the Social Security Administration (online, by phone at 1-800-772-1213, or in person at a local SSA office).
- Must provide proof of identity, age, citizenship/immigration status, residence, income, and resources at the time of application.
- Must consent to SSA contacting medical providers and reviewing financial records.
- Must complete a disability interview (in-person or by phone) if applying on the disability or blindness pathway.

## Benefit Value

SSI benefits equal the **Federal Benefit Rate (FBR) minus countable income**. As of January 2026 (after the 2.8% COLA):

| Recipient Type | Monthly FBR | Annual Value |
|---|---|---|
| Eligible individual | $994 | $11,928 |
| Eligible couple | $1,491 | $17,892 |

Washington does **not** pay a state supplement to SSI for most aged, blind, or disabled adults living independently. Some narrow categories — e.g., individuals in certain residential care facilities — receive a small state supplement administered by Washington DSHS, but those programs are out of scope for the screener at launch. The estimated benefit value should be the federal SSI amount as computed by PolicyEngine for the household, reduced by countable income via the SSA exclusions (general $20 + earned $65 + ½ remaining earned).

- Source: [SSA — 2026 SSI Federal Payment Amounts](https://www.ssa.gov/oact/cola/SSI.html); [SSA — 2026 COLA Fact Sheet](https://www.ssa.gov/news/en/cola/factsheets/2026.html).

## Implementation Coverage

- ✅ Evaluable criteria: 12
- ⚠️  Data gaps: 4

12 of 16 total eligibility criteria can be evaluated with current screener fields (criteria 1, 2, 2a, 3, 4, 5, 6, 7, 8, 9, 10, 11). The screener confidently identifies applicants who are demographically and categorically in scope (aged 65+, long-term disabled, visually impaired) with WA residence and a qualifying citizenship status, who are not already receiving SSI, and whose income/asset profile pre-filters within the 2026 FBR and resource ceilings. The SGA test (Criterion #2a) is enforced via PolicyEngine's `ssi_engaged_in_sga` against monthly earned income from `income_streams`. Spousal and parental deeming household composition is captured for PolicyEngine to evaluate. Income and resource feasibility are conservative pre-filters; the precise countable-income calculation, asset exclusions, and deeming math are delegated to PolicyEngine. Primary gaps are SSA's medical/vocational disability adjudication (handled at application), U.S. absence (Low impact), institutional-residence status (Low impact), and fugitive/incarceration status (Low impact) — all handled procedurally at the SSA application stage.

## PolicyEngine Variable Mapping

This program will be implemented as a PolicyEngine calculator in a follow-up PR. The mapping below was reviewed against `policyengine-us` to ensure each criterion has a corresponding PE variable or parameter and the values agree with our spec.

| Criterion | PolicyEngine variable / parameter | File |
|---|---|---|
| Aged, blind, or disabled | `is_ssi_aged_blind_disabled` | `variables/gov/ssa/ssi/eligibility/status/is_ssi_aged_blind_disabled.py` |
| Aged threshold (65) | `gov.ssa.ssi.eligibility.aged_threshold` | `parameters/gov/ssa/ssi/eligibility/aged_threshold.yaml` |
| SGA disqualifier | `ssi_engaged_in_sga`, `gov.ssa.sga.non_blind`, `gov.ssa.sga.blind` | `variables/gov/ssa/ssi/eligibility/income/ssi_engaged_in_sga.py` |
| Resource test ($2K / $3K) | `meets_ssi_resource_test`, `gov.ssa.ssi.eligibility.resources.limit.individual` / `couple` | `parameters/gov/ssa/ssi/eligibility/resources/limit/{individual,couple}.yaml` |
| Countable resource sources | `ssi_countable_resources`, `gov.ssa.ssi.eligibility.resources.countable` | `parameters/gov/ssa/ssi/eligibility/resources/countable.yaml` |
| Citizen / qualified noncitizen | `is_ssi_qualified_noncitizen`, `gov.ssa.ssi.eligibility.status.qualified_noncitizen_status` | `variables/gov/ssa/ssi/eligibility/status/is_ssi_qualified_noncitizen.py` |
| LPR 40-quarter rule | `gov.ssa.ssi.income.sources.qualifying_quarters_threshold` | `parameters/gov/ssa/ssi/income/sources/qualifying_quarters_threshold.yaml` |
| Top-level eligibility (no income test) | `is_ssi_eligible` | `variables/gov/ssa/ssi/is_ssi_eligible.py` |
| 2026 FBR — individual ($994/mo) | `gov.ssa.ssi.amount.individual` | `parameters/gov/ssa/ssi/amount/individual.yaml` |
| 2026 FBR — couple ($1,491/mo) | `gov.ssa.ssi.amount.couple` | `parameters/gov/ssa/ssi/amount/couple.yaml` |
| Income exclusions ($20 / $65 / ½) | `gov.ssa.ssi.income.exclusions.{general,earned,earned_share}` | `parameters/gov/ssa/ssi/income/exclusions/*.yaml` |
| Countable income | `ssi_countable_income` | `variables/gov/ssa/ssi/eligibility/income/ssi_countable_income.py` |
| Spousal deeming | `is_ssi_spousal_deeming_applies`, `ssi_income_deemed_from_ineligible_spouse` | `variables/gov/ssa/ssi/eligibility/income/deemed/from_ineligible_spouse/` |
| Parental deeming | `ssi_unearned_income_deemed_from_ineligible_parent`, `ssi_ineligible_parent_allocation` | `variables/gov/ssa/ssi/eligibility/income/deemed/` |
| In-kind support — VTR | `gov.ssa.ssi.amount.one_third_reduction_rate` | `parameters/gov/ssa/ssi/amount/one_third_reduction_rate.yaml` |
| In-kind support — PMV | `gov.ssa.ssi.income.ism.pmv_fbr_fraction`, `ssi_pmv_amount` | `parameters/gov/ssa/ssi/income/ism/pmv_fbr_fraction.yaml` |
| Medical facility flat $30/mo | `gov.ssa.ssi.amount.medical_facility` | `parameters/gov/ssa/ssi/amount/medical_facility.yaml` |
| Final benefit (capped, takeup) | `ssi`, `ssi_amount_if_eligible`, `uncapped_ssi`, `takes_up_ssi_if_eligible` | `variables/gov/ssa/ssi/{ssi,ssi_amount_if_eligible}.py` |

**Living-arrangement reductions (additional data gap)**: PolicyEngine models VTR (one-third reduction for living in another's household), PMV (one-third FBR + $20 cap on in-kind support), and the $30/mo medical-facility rate. Our screener does not capture `ssi_lives_in_another_persons_household`, `ssi_receives_shelter_from_others_in_household`, or `ssi_lives_in_medical_treatment_facility`, so those PE variables will default to `false` and the standard FBR will be returned. Treat this as a known over-credit in fringe living arrangements; impact is low for typical WA SSI applicants.

## Acceptance Criteria

- [ ] Scenario 1 (Aged 65+ — No Income, No Resources): User should be **eligible** with $994/month ($11,928/year)
- [ ] Scenario 2 (Long-Term Disabled Adult Under 65 — No Income): User should be **eligible** with $994/month ($11,928/year)
- [ ] Scenario 3 (Visually Impaired Adult — No Income): User should be **eligible** with $994/month ($11,928/year)
- [ ] Scenario 4 (Aged 65+ with Unearned Income Above FBR): User should be **ineligible**
- [ ] Scenario 5 (Aged 65+ with Countable Resources Above $2,000): User should be **ineligible**
- [ ] Scenario 6 (Eligible Aged Couple — Both 65+, No Income): User should be **eligible** with $1,491/month ($17,892/year, household total)
- [ ] Scenario 7 (Adult Under 65 Without Disability or Visual Impairment): User should be **ineligible**
- [ ] Scenario 8 (Already Receiving SSI — Duplicate Enrollment): User should be **ineligible**
- [ ] Scenario 9 (Long-Term Disabled Child — Parental Deeming Under Limits): User should be **eligible** with $994/month ($11,928/year) — parent allocation absorbs deemed income; net deemed = $0
- [ ] Scenario 10 (General Disability Flag Only — `disabled=true`, `long_term_disability=false`): User should be **eligible** with $994/month ($11,928/year)
- [ ] Scenario 11 (Aged 65+ with Partial SS Retirement Income — Reduced Benefit): User should be **eligible** with $514/month ($6,168/year)
- [ ] Scenario 12 (Long-Term Disabled Adult with Partial Earned Wages — Reduced Benefit): User should be **eligible** with $836.50/month ($10,038/year)
- [ ] Scenario 13 (Disabled Adult with High-Income Ineligible Spouse — Spousal Deeming Disqualifies): User should be **ineligible**
- [ ] Scenario 14 (Long-Term Disabled Adult Above SGA Threshold — SGA Disqualification): User should be **ineligible** (non-blind earned income > $1,690/mo trips `ssi_engaged_in_sga`, even though countable income would otherwise leave them eligible)
- [ ] Scenario 15 (Eligible Aged Spouse + Ineligible Working Spouse — Partial Spousal Deeming): User should be **eligible** with $933.50/month ($11,202/year) — couple FBR less spousal deemed countable income

## Test Scenarios

> **Note on `value` units**: All `value` numbers below and in `wa_ssi.json` are **annual** dollars (per the screener's `estimated_value` convention — see `screener/management/commands/export_screener_data.py` and the `* 12` pattern in calculator implementations). Monthly amounts are also shown for human readability.

### Scenario 1: Aged 65+, No Income, No Resources

**What we're checking**: Cleanest aged-only path — confirms the screener treats age 65+ as a sufficient categorical entry into SSI when income and resources are clearly under thresholds.

**Expected**: Eligible (full federal individual FBR — $994/month)
**Expected `value`**: `11928` ($994/month × 12)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70` (born 1956), Head of Household, U.S. Citizen, no disability, no visual impairment, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: This is the canonical aged-only happy path. Validates that age alone (with zero income and resources) is treated as sufficient categorical entry into SSI, independent of disability or blindness flags.

---

### Scenario 2: Long-Term Disabled Adult Under 65, No Income

**What we're checking**: Disability path via the `long_term_disability` flag for an adult well below retirement age, with no income or resources.

**Expected**: Eligible (full federal individual FBR — $994/month)
**Expected `value`**: `11928` ($994/month × 12)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `45` (born 1981), Head of Household, U.S. Citizen, **long-term disability: true**, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates that the disability route is honored independently of age. The `long_term_disability` flag is one of two valid disability signals (the other is the general `disabled` flag — see Scenario 10).

---

### Scenario 3: Visually Impaired Adult, No Income

**What we're checking**: Blindness path via the `visually_impaired` flag for a working-age adult with no income or resources.

**Expected**: Eligible (full federal individual FBR — $994/month)
**Expected `value`**: `11928` ($994/month × 12)

**Steps**:
- **Location**: ZIP `98052`, County `King`
- **Household**: 1 person
- **Person 1**: Age `40` (born 1986), Head of Household, U.S. Citizen, **visually impaired: true**, no other disability, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms the blind path is enabled. The screener's `visually_impaired` field is broader than SSA's statutory blindness, but should still surface SSI as a likely-eligible match for SSA review.

---

### Scenario 4: Aged 65+ with Unearned Income Above FBR

**What we're checking**: Income disqualification — Social Security retirement income that exceeds the FBR for an individual after the $20 general exclusion.

**Expected**: Not eligible (countable unearned income > FBR)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `68` (born 1958), Head of Household, U.S. Citizen, no disability, Social Security retirement income: `$1,200/month`
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms the income test enforces the FBR ceiling. $1,200 SS retirement minus the $20 general exclusion = $1,180 countable, which is above the 2026 individual FBR of $994.

---

### Scenario 5: Aged 65+ with Countable Resources Above $2,000

**What we're checking**: Resource disqualification — household assets above the individual SSI resource limit.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70` (born 1956), Head of Household, U.S. Citizen, no disability, no income
- **Insurance**: None
- **Household assets**: `$5,000`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms the resource ceiling is enforced. Note: the screener's `household_assets` is a single conservative number; downstream calculation must apply SSA's resource exclusions (home, one vehicle, burial space) when integrated with PolicyEngine. This pre-filter accepts that some applicants with excludable wealth may be incorrectly denied at the screener stage.

---

### Scenario 6: Eligible Aged Couple — Both 65+, No Income

**What we're checking**: Couple FBR path — both spouses age-eligible, no income or assets.

**Expected**: Eligible (couple benefit at $1,491/month FBR for 2026, shared between members)
**Expected `value`**: `17892` ($1,491/month × 12 — MFB sums per-person PolicyEngine outputs so the household total equals the full couple rate)

**Steps**:
- **Location**: ZIP `98109`, County `King`
- **Household**: 2 people
- **Person 1 (Head)**: Age `70` (born 1956), U.S. Citizen, no disability, no income
- **Person 2 (Spouse)**: Age `68` (born 1958), U.S. Citizen, no disability, no income
- **Insurance**: None for both
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates couple FBR application and that household composition is correctly evaluated for two-person eligibility under SSI's eligible-couple rules.

---

### Scenario 7: Adult Under 65 Without Disability or Visual Impairment

**What we're checking**: Categorical disqualification — fails all three categorical entry prongs (age, blindness, disability).

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `35` (born 1991), Head of Household, U.S. Citizen, no disability, no visual impairment, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms an adult who fails all three categorical entry routes is correctly filtered out, even with zero income and assets. Without satisfying age, blindness, or disability, SSI is unavailable regardless of financial need.

---

### Scenario 8: Already Receiving SSI — Duplicate Enrollment

**What we're checking**: Duplicate enrollment — current SSI recipient should not be shown as a new recommendation.

**Expected**: Not eligible (already has)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `70` (born 1956), Head of Household, U.S. Citizen, no disability, SSI income: `$994/month`
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: **Currently receiving SSI** (`has_ssi = true`)

**Why this matters**: Validates the "already has" path so existing recipients aren't redundantly listed under "Programs Found".

---

### Scenario 9: Long-Term Disabled Child — Parental Deeming Under Limits

**What we're checking**: Child applicant — parental deeming math handled by PolicyEngine. With one earner at $1,500/mo and a non-earning spouse, the parent allocation exceeds the parents' countable income, so $0 is deemed to the child and the child receives the full individual FBR.

**Expected**: Eligible (child receives full individual FBR — $994/month)
**Expected `value`**: `11928` (parental-deeming math, annualized below)

**Deeming math (annualized; from PolicyEngine `ssi_ineligible_parent_allocation`)**:
- Parents' gross income: $1,500/mo × 12 = `$18,000/yr`
- After SSI exclusions ($20 general + $65 earned + ½ remainder): `($18,000 − $240 − $780) / 2 = $8,490/yr` countable parent income
- Parent allocation (2 ineligible parents, per `ssi.couple / 2 * MONTHS_IN_YEAR`): `$1,491 / 2 × 12 × 2 parents = $17,892/yr`
- Net deemed to child: `$8,490 − $17,892 = −$9,402 → capped at $0`
- Child SSI: full individual FBR = `$994 × 12 = $11,928/yr`

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 3 people
- **Person 1 (Head)**: Age `40` (born 1986), U.S. Citizen, no disability, wages: `$1,500/month`
- **Person 2 (Spouse)**: Age `38` (born 1988), U.S. Citizen, no disability, no income
- **Person 3 (Child)**: Age `8` (born 2018), U.S. Citizen, **long-term disability: true**, no income
- **Insurance**: Employer for all three
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Confirms child-SSI eligibility is surfaced when the disabled minor lives with low-income parents and validates that PolicyEngine's parent-to-child deeming math returns the full FBR when the parent allocation absorbs the parents' countable income.

---

### Scenario 10: General Disability Flag Only — `disabled=true`, `long_term_disability=false`

**What we're checking**: An adult who answers *"yes"* to the screener's general disability question (*"Currently have any disabilities that make you unable to work now or in the future"*) but has not separately set the long-term-disability flag should still surface SSI as a candidate. The screener question text already implies an ongoing inability to work, which is the SSA-relevant signal for SSI's disability path.

**Expected**: Eligible (full federal individual FBR — $994/month)
**Expected `value`**: `11928` ($994/month × 12)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `45` (born 1981), Head of Household, U.S. Citizen, **disabled: true**, **long_term_disability: false**, no income
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates that the calculator accepts either `disabled` or `long_term_disability` as a valid disability signal (matching the model's `HouseholdMember.has_disability()` OR-semantics). This corrects an earlier draft of this spec that treated `disabled=true, long_term_disability=false` as ineligible — that earlier interpretation mirrored TX SSDI's stricter rule but is too narrow for SSI per product/review feedback. Final disability adjudication remains with SSA at the application stage.

---

### Scenario 11: Aged 65+ with Partial SS Retirement Income — Reduced Benefit

**What we're checking**: Partial offset — eligible with reduced SSI when unearned income is below FBR. Confirms that some unearned income reduces, but does not eliminate, the SSI benefit.

**Expected**: Eligible (reduced benefit; $514/month)
**Expected `value`**: `6168` (`$994 − ($500 − $20 general exclusion) = $514/month × 12`)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `72` (born 1954), Head of Household, U.S. Citizen, no disability, Social Security retirement income: `$500/month`
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates that some unearned income reduces, but does not eliminate, the SSI benefit. Expected value math: $994 (2026 FBR) − ($500 − $20 general exclusion) = **$514/month**. The screener should flag eligibility; PolicyEngine performs the precise math via `ssi_countable_income` and `ssi_amount_if_eligible`.

---

### Scenario 12: Long-Term Disabled Adult with Partial Earned Wages — Reduced Benefit

**What we're checking**: Earned-income exclusion path — confirms the screener applies the $65 + ½ remaining exclusion (distinct from the unearned-only Scenario 11), and that earned income reduces but does not eliminate the SSI benefit.

**Expected**: Eligible (reduced benefit; $836.50/month)
**Expected `value`**: `10038` (`$994 − ($400 − $20 − $65) × ½ = $836.50/month × 12`; truncated to int per `validate.py`)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `45` (born 1981), Head of Household, U.S. Citizen, **long-term disability: true**, wages: `$400/month` (well below the 2026 SGA threshold of $1,690/mo)
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates the earned-income exclusion stack. Math: $400 earned − $20 (general) − $65 (earned flat) = $315; ½ of $315 = **$157.50 countable**. SSI = $994 − $157.50 = **$836.50/month**. Distinct from Scenario 11 (unearned-only path) and Scenario 4 (over-FBR disqualification). Earnings stay below SGA so the disability path is preserved.

---

### Scenario 13: Disabled Adult with High-Income Ineligible Spouse — Spousal Deeming Disqualifies

**What we're checking**: Spousal income deeming — when an ineligible spouse has income well above the deeming threshold, the deemed amount can exceed the couple FBR and zero out the SSI applicant's benefit.

**Expected**: Not eligible (spousal deemed income exceeds couple FBR after exclusions)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 2 people
- **Person 1 (Head)**: Age `60` (born 1966), U.S. Citizen, **long-term disability: true**, no income
- **Person 2 (Spouse)**: Age `58` (born 1968), U.S. Citizen, no disability, wages: `$4,000/month`
- **Insurance**: None for both
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates spousal deeming above the cutoff. Math: spouse gross $4,000 > $497/mo deeming threshold (FBR differential) → deeming applies; ($4,000 − $20 − $65) ÷ 2 = **$1,957.50 deemed countable**. With deeming applied, couple FBR ($1,491) − countable ($1,957.50) = −$466.50, capped at $0. The eligible spouse's SSI is zeroed out by spousal income. PolicyEngine variables: `is_ssi_spousal_deeming_applies`, `ssi_income_deemed_from_ineligible_spouse`.

---

### Scenario 14: Long-Term Disabled Adult Above SGA Threshold — SGA Disqualification

**What we're checking**: SGA disqualification (Criterion #2a) — a non-blind disability claimant whose monthly earned income exceeds the 2026 SGA threshold ($1,690/mo) is disqualified by `ssi_engaged_in_sga` even though their countable income, after the standard $20 + $65 + ½ exclusions, would otherwise leave them eligible. This isolates the SGA logic from the FBR income test (Criterion #7).

**Expected**: Not eligible (engaged in SGA — non-blind earned income > $1,690/month)
**Expected `value`**: omitted (ineligible)

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age `50` (born 1976), Head of Household, U.S. Citizen, **long-term disability: true**, **not visually impaired**, wages: `$1,700/month` (just above the 2026 non-blind SGA threshold of $1,690/mo)
- **Insurance**: None
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Validates the SGA cutoff at the screener level. Without the SGA test, this person would otherwise be eligible: countable income = ($1,700 − $20 − $65) × ½ = **$807.50/month**, which is below the individual FBR ($994), giving an apparent SSI payment of $994 − $807.50 = $186.50/mo. But because they earn above SGA on the non-blind disability path, PolicyEngine's `ssi_engaged_in_sga` flips to `True` and the disability claim is denied. Distinct from Scenario 4 (over-FBR unearned-income disqualification — purely income-test based) and Scenario 12 (earned wages well below SGA — disability path preserved). Also note: a *blind* applicant with the same wages would still be eligible because the blind path is exempt from the SGA test (`ssi_engaged_in_sga` returns `False & ~is_blind`).

---

### Scenario 15: Eligible Aged Spouse + Ineligible Working Spouse — Partial Spousal Deeming

**What we're checking**: Partial spousal deeming (Criterion #9) — the missing companion case to Scenarios 6 and 13. The eligible spouse is aged 65+ with no income; the ineligible spouse has earned income that crosses the deeming-applies threshold (FBR differential = $497/month) but is not large enough to fully zero out the SSI payment. PolicyEngine should switch to the **couple FBR** as the base and subtract the deemed countable income.

**Expected**: Eligible (reduced benefit; $933.50/month)
**Expected `value`**: `11202` (couple FBR less spousal deemed income — math derivation below)

**Deeming math (annualized; from PolicyEngine `is_ssi_spousal_deeming_applies` and `ssi_amount_if_eligible`)**:
- Spouse's earned income: $1,200/mo × 12 = `$14,400/yr`
- Spouse's deemed countable (after $20 general + $65 earned + ½ remainder, annualized): `($14,400 − $240 − $780) / 2 = $6,690/yr`
- FBR differential (annualized): `($1,491 − $994) × 12 = $5,964/yr`
- `$6,690 > $5,964` → **deeming applies** → benefit base switches to couple FBR
- SSI = couple FBR (`$1,491 × 12 = $17,892/yr`) − deemed countable (`$6,690/yr`) = `$11,202/yr` = **$933.50/month**

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 2 people
- **Person 1 (Head)**: Age `70` (born 1956), U.S. Citizen, no disability, no income (eligible — aged path)
- **Person 2 (Spouse)**: Age `60` (born 1966), U.S. Citizen, **no disability, no visual impairment** (ineligible spouse — not aged/blind/disabled), wages: `$1,200/month`
- **Insurance**: None for both
- **Household assets**: `$0`
- **Current Benefits**: Not currently receiving SSI

**Why this matters**: Closes the spousal-deeming coverage gap Caton flagged in PR review. Scenario 6 is the both-eligible joint claim (couple FBR, no deeming). Scenario 13 is the over-the-cutoff disqualification (deeming zeros out the benefit). This scenario is the in-between case — deeming applies and reduces the benefit but doesn't eliminate it. Validates that PolicyEngine's `is_ssi_spousal_deeming_applies` correctly switches the base from individual FBR to couple FBR (per the `where(deeming_applies, p.couple, p.individual)` branch in `ssi_amount_if_eligible`), and that `ssi_countable_income` correctly adds `ssi_income_deemed_from_ineligible_spouse` to the eligible person's countable income (via the `personal_countable + spousal_deemed` branch).

---

### Out-of-band: Non-citizen without qualified status

The SSI alien restriction (8 U.S.C. § 1612(a)(2)) is enforced through the program's `legal_status_required` configuration (`["citizen", "gc_5plus"]`) and the post-results citizenship filter chip on the Results UI, not via a household-member field on the screen. As a result, this case is not represented in the JSON validation suite — it is verified manually by toggling the citizenship filter and confirming that `wa_ssi` disappears for users who do not select an SSI-qualifying status.

## Research Sources

- [SSA — Supplemental Security Income (SSI) Home](https://www.ssa.gov/ssi/)
- [SSA — Apply for SSI](https://www.ssa.gov/apply/ssi)
- [SSA — Understanding SSI](https://www.ssa.gov/ssi/text-understanding-ssi.htm)
- [SSA — 2026 SSI Federal Payment Amounts](https://www.ssa.gov/oact/cola/SSI.html)
- [SSA — 2026 Cost-of-Living Adjustment Fact Sheet](https://www.ssa.gov/news/en/cola/factsheets/2026.html)
- [Washington DSHS — Cash Assistance Programs](https://www.dshs.wa.gov/esa/community-services-offices/cash-assistance)
- [Legal Information Institute — 42 U.S.C. Chapter 7, Subchapter XVI (SSI)](https://www.law.cornell.edu/uscode/text/42/chapter-7/subchapter-XVI)
- [eCFR — 20 CFR Part 416 (SSI for the Aged, Blind, and Disabled)](https://www.ecfr.gov/current/title-20/chapter-III/part-416)

## JSON Test Cases

File: `validations/management/commands/import_validations/data/wa_ssi.json`

The validations file currently contains the 3 representative scenarios called for by the canonical "Checking Program Researcher Output" reviewer guide (eligible standard, ineligible primary exclusion, earned-income edge case). The full 15 scenarios listed above remain in this spec.md as the dev's reference for implementation and future expansion.

**Important — `value` is annual**: the screener stores `program_eligibility.estimated_value` as an **annual** dollar figure (see `screener/management/commands/export_screener_data.py` and the `* 12` pattern in calculator implementations). All `value` numbers in `wa_ssi.json` are monthly × 12. `validate.py` casts to `int(validation.value)`, so non-integer monthly amounts truncate after annualization.

Expected `value` per scenario (annual):

| Scenario | Eligible? | `value` | Math |
|---|---|---|---|
| 1 — Aged 65+, no income | true | `11928` | $994/mo × 12 (full individual FBR) |
| 2 — Long-term disabled, no income | true | `11928` | $994/mo × 12 |
| 3 — Visually impaired, no income | true | `11928` | $994/mo × 12 |
| 4 — Aged 65+, unearned income above FBR | false | omitted | — |
| 5 — Aged 65+, resources > $2,000 | false | omitted | — |
| 6 — Eligible aged couple | true | `17892` | $1,491/mo × 12 (MFB sums per-person PE outputs to the household couple rate) |
| 7 — Adult under 65, no disability | false | omitted | — |
| 8 — Already receiving SSI | false | omitted | — |
| 9 — Disabled child, parental deeming | true | `11928` | parent allocation $17,892/yr exceeds parents' countable $8,490/yr → $0 deemed → full individual FBR |
| 10 — `disabled=true`, `long_term_disability=false` | true | `11928` | $994/mo × 12 |
| 11 — Aged 65+ with $500/mo SS retirement | true | `6168` | $994 − ($500 − $20) = $514/mo × 12 |
| 12 — Long-term disabled with $400/mo wages | true | `10038` | $994 − ($400 − $20 − $65) × ½ = $836.50/mo × 12; truncated to int |
| 13 — Spousal deeming disqualifies | false | omitted | — |
| 14 — Long-term disabled, $1,700/mo wages (above SGA) | false | omitted | non-blind earned income > $1,690/mo SGA threshold → `ssi_engaged_in_sga` = true → disability claim denied |
| 15 — Aged HoH + ineligible spouse with $1,200/mo wages (partial deeming) | true | `11202` | spouse's deemed countable ($6,690/yr) > FBR differential ($5,964/yr) → deeming applies → couple FBR ($17,892/yr) − deemed countable ($6,690/yr) = $11,202/yr |

Per the canonical guide, `value` is omitted (not set to `0`) for ineligible scenarios.

## Generated Program Configuration

File: `programs/management/commands/import_program_config_data/data/wa_ssi_initial_config.json`

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-04-27 | cdadams | Initial discovery spec — 11 evaluable criteria, 4 data gaps, 11 test scenarios, 2026 FBR amounts ($994 individual / $1,491 couple). |
| 2026-04-28 | cdadams | Added `refugee` to `legal_status_required` (matches federal statute and PolicyEngine; diverges from `tx_ssi` precedent — recommend back-port). Added 2026 SGA thresholds ($1,690 non-blind / $2,830 blind) to disability criterion. Added PolicyEngine implementation references for income exclusions, ISM (VTR/PMV), countable resources, and noncitizen rules. Added "PolicyEngine Variable Mapping" section. Documented coverage gap (PE has 4 additional qualified-noncitizen categories — asylee, deportation-withheld, Cuban-Haitian, conditional-entrant, paroled — not exposed in MFB chip enum) and PE model limitation (no 7-year refugee cutoff enforced). Added Scenarios 12 (earned-income partial offset, $836.50/mo) and 13 (spousal deeming disqualification) with `value` fields validated against PolicyEngine `policyengine-us` parameters. |
| 2026-04-28 | cdadams | Added two `navigators` entries to config: Northwest Justice Project CLEAR Hotline (statewide WA legal aid for SSI applications and appeals, 1-888-201-1014) and Solid Ground Benefits Legal Assistance (King County free SSI/SSDI denial representation, 206-694-6743). Addresses Caton's PR review note. |
| 2026-04-28 | cdadams | Added 6 missing program-level fields to config (per Caton's PR review): `base_program: "ssi"` (cross-white-label grouping for analytics + has-benefits filtering), `value_type: "monthly"` (Translation FK), `estimated_delivery_time: "6 to 8 months"` (Translation FK), `show_on_current_benefits: true`, `show_in_has_benefits_step: true`, and `has_calculator: true`. Updated `import_program_config.py` to handle three previously-silently-ignored config keys (`show_in_has_benefits_step`, `has_calculator`, `base_program`) — `base_program` is validated against `BaseProgram.choices`. Verified end-to-end with `--override` import and direct ORM inspection. |
| 2026-04-28 | cdadams | Disability criterion broadened per Caton's PR review: accept `disabled` **OR** `long_term_disability` as a valid disability signal for SSI (previously this spec required `long_term_disability` exclusively, mirroring TX SSDI). Caton confirmed the screener question backing `disabled` is *"Currently have any disabilities that make you unable to work now or in the future"*, which already captures the SSA-relevant ongoing-inability-to-work signal. This also aligns with the model's existing `HouseholdMember.has_disability()` helper which ORs `disabled || visually_impaired || long_term_disability`. Flipped Scenario 10 from **ineligible** → **eligible** (now validates that `disabled=true, long_term_disability=false` IS sufficient for the disability path) and updated its acceptance-criteria checkbox to match. Added a divergence note in the eligibility criterion calling out that the TX SSDI precedent should be revisited in a follow-up. |
| 2026-04-28 | cdadams | Aligned all three artifacts to the canonical "Checking Program Researcher Output" reviewer guide: (a) corrected `value_type: "monthly"` → `"benefit"` (the model accepts any string but the canonical valid values are `"tax_credit"` or `"benefit"`); (b) added explicit `"value_format": null` for the monthly cadence default; (c) reformatted navigator phone numbers to E.164 (`+18882011014`, `+12066946743`); (d) filled in navigator emails (`webmaster@nwjustice.org`, `benefitslegalhelp@solid-ground.org`); (e) tightened the user-facing `description` to remove duplication of screener-checked eligibility criteria and added the application paths (online / 1-800-772-1213 / in person) per the description guidance; (f) pruned `wa_ssi.json` from 13 scenarios to the 3 representative scenarios called for by the guide (eligible standard, ineligible primary exclusion, edge case for the $20+$65+½ earned-income methodology); (g) removed `value: 0` from ineligible scenarios (guide says omit entirely); (h) added "Priority Criteria" section to this spec.md (N/A for SSI as a federal entitlement). The full 13-scenario coverage remains in the "Test Scenarios" section below for the implementation dev's reference. **Open question for reviewer**: per the guide, `year` should be omitted for non-FPL programs (SSI uses its own FBR, not FPL income tests), but `tx_ssdi_initial_config.json` keeps `"year": "2026"` and the calculator may need it at runtime — kept it for now to match TX SSDI precedent. |
| 2026-04-28 | cdadams | Added explicit `value` numbers per Caton's PR review (annualized — the screener stores `program_eligibility.estimated_value` as an annual figure; see `screener/management/commands/export_screener_data.py` and the `* 12` pattern in calculator implementations like `medicare_savings`). Updated `wa_ssi.json` to use annual values (`994 → 11928`, `836.50 → 10038`). Added an explicit `Expected value` line to each scenario in spec.md with annualization math. Verified Caton's Scenario 9 deeming math against PolicyEngine `ssi_ineligible_parent_allocation` (returns `couple_fbr / 2 * MONTHS_IN_YEAR` per ineligible parent → 2 × $745.50/mo × 12 = $17,892/yr parent allocation, exceeds parents' $8,490/yr countable income → $0 deemed → child receives full individual FBR `$11,928/yr`). Added a "JSON Test Cases" summary table with all 13 scenarios' expected `value` numbers and math derivations for the implementation dev. |
| 2026-04-28 | cdadams | Closed the two test-coverage gaps Caton flagged on PR #1467: (a) **SGA** — promoted the SGA test from a sub-bullet of Criterion #2 to its own evaluable Criterion #2a ("Not engaged in SGA — for non-blind disability claims") and added Scenario 14 (long-term disabled adult earning $1,700/mo, just above the 2026 non-blind SGA threshold of $1,690/mo, expected ineligible — wage chosen so that countable income alone would otherwise leave them eligible at $186.50/mo, isolating the SGA logic from the FBR income test); (b) **Spousal deeming partial case** — added Scenario 15 (aged HoH with no income + ineligible spouse age 60 with $1,200/mo wages → spouse's deemed countable $6,690/yr exceeds FBR differential $5,964/yr → deeming applies → couple FBR $17,892/yr − $6,690/yr = $11,202/yr, expected eligible at $933.50/mo). Verified PolicyEngine's `is_ssi_spousal_deeming_applies`, `ssi_amount_if_eligible` (which switches the base from individual to couple FBR when deeming applies), and `ssi_countable_income`. Updated Implementation Coverage from 11/15 → 12/16 evaluable, Acceptance Criteria checkboxes, and the JSON Test Cases summary table accordingly. **Note on Caton's "~$1,550/month in 2026" SGA threshold**: PolicyEngine's `gov.ssa.sga.non_blind` lists $1,550 for **2024**; the 2026 value is $1,690/mo (matches our spec). |
