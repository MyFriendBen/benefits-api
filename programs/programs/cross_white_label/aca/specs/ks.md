# Implement ACA Premium Tax Credit / Marketplace Subsidy (KS)

## Program Details

- **Program**: ACA Premium Tax Credit (Marketplace Subsidy)
- **State**: KS
- **White Label**: ks
- **Implementation**: PolicyEngine (`aca_ptc` variable, tax-unit level, annual). Eligibility and benefit value are both computed entirely by PolicyEngine's federal calculator — Kansas has no state-specific eligibility or value logic of its own. KS uses HealthCare.gov (not a state-based exchange), so there is no state marketplace layer either.
- **Engine + Tier**: PE, **Fed (value varies)** — config + light spec.
- **Research Date**: 2026-08-17
- **Review Date**: 2026-08-25

---

## Benefit Value

**Formula**: `aca_ptc = max(0, SLCSP − required contribution)`, computed annually per tax unit, where `SLCSP` (Second Lowest Cost Silver Plan) is the benchmark Silver-plan premium for the household's rating area and age, and the required contribution is a sliding-scale percentage of MAGI (Modified Adjusted Gross Income) relative to the federal poverty line (FPL).

**Calculation chain**: county/rating area → KS benchmark premium (`state_rating_area_cost`, Kansas has 7 rating areas; PolicyEngine keys this off `county_str`, not `zip_code`) → age-adjusted benchmark premium (federal age curve) → prior-year FPL (2026 coverage uses the **2025 HHS poverty guideline** — **$15,650** for a household of 1 — not the 2026 guideline; per the Federal Register, 90 FR 5917) → required contribution (sliding-scale % of MAGI/FPL, set annually under 26 U.S.C. § 36B(b)(3) — for household income under 133% FPL, the 2026 rate is a flat **2.10%** per IRS Rev. Proc. 2025-25 §3.01, which reproduces the $394.38 contribution PolicyEngine computes for Scenarios 1–2) → `aca_ptc` = benchmark premium − required contribution, floored at $0, then truncated to a whole dollar (matches `PolicyEngineTaxUnitCalulator.tax_unit_value()`, which does `int()` on PE's raw float).

**This is an estimated, benchmark-based *maximum* credit — not necessarily the amount ultimately applied to the plan someone chooses.** The statute caps the actual credit at the premium of the plan the household selects; a household that picks a plan priced below the benchmark receives less than this estimate. `estimated_value` and all user-facing copy must say "estimated" or "up to," never a guaranteed number.

**Cadence and display**: `estimated_value` returned by the API is the truncated **annual** figure; `value_format: null` ("Default (Monthly)") divides it by 12 for the results-page display. Test scenarios assert the annual value, since that's what the API exposes.

---

## Implementation Coverage

- ✅ Evaluable: full eligibility (federal, PolicyEngine-native), benefit value (federal SLCSP-based, KS-specific rating-area table), the non-expansion 100–138% FPL coverage-gap case, and the county/rating-area value isolation (Scenarios 1–2).
- ✅ Rating-area benchmark cross-checked against the Kansas Health Institute's Jan 2026 analysis of CMS's 2026 Marketplace data (KHI/26-02) — PolicyEngine's Rating Area 1 and Rating Area 6 benchmarks match KHI/CMS within 0.1%. No PE/policy discrepancy to flag.
- ⚠️ **No `KsAca` calculator exists yet.** Sibling implementations now live at `programs/programs/cross_white_label/aca/{base,tx,mo}.py`. `TxAca` (`tx.py`) only adds a state-code dependency on the federal `Aca` base, which under-counts SLCSP accuracy (zip code alone doesn't disambiguate rating areas) and never wires `has_esi` — a statutory PTC disqualifier PolicyEngine only applies if told. `MoAca` (`mo.py`) fixes both gaps for Missouri. **`KsAca` should follow `MoAca`'s pattern**, and the two inputs it needs already exist and are unused: `KsStateCodeDependency` and `KsCountyDependency` in `programs/framework/pe_dependencies/household.py`, and `HasEsiDependency` in `programs/framework/pe_dependencies/member.py`. Building `KsAca` is registering these three dependencies on the federal `Aca` base — no new dependency classes required.
- **MFB → PE mapping**: PolicyEngine stays authoritative for eligibility and value. MFB's job is only to map truthful screener data (state, county, current employer-sponsored-coverage status) into PE's native `state_code` / `county_str` / `has_esi` inputs — no custom ACA eligibility or value logic, overrides, fallback logic, or substituted PE inputs/results. If a required input can't be populated from the screener, that's an implementation limitation to document, not a reason to add custom logic.

---

## Research Sources

**Statute & regulations**
- [26 U.S.C. § 36B](https://www.law.cornell.edu/uscode/text/26/36B) — Premium Tax Credit statute
- [26 CFR § 1.36B-2](https://www.law.cornell.edu/cfr/text/26/1.36B-2) — Eligibility for premium tax credit
- Federal Register, 90 FR 5917 (2025-01-17) — 2025 HHS poverty guidelines (the vintage used for 2026 coverage)
- [IRS Rev. Proc. 2025-25](https://www.irs.gov/pub/irs-drop/rp-25-25.pdf) §3.01 — 2026 Applicable Percentage Table (required-contribution rate)

**Agency & policy data**
- [HealthCare.gov — Lower Costs](https://www.healthcare.gov/lower-costs/)
- Kansas Health Institute, [*2026 Affordable Care Act Health Insurance Marketplace*](https://www.khi.org/wp-content/uploads/2026/01/2026-Affordable-Care-Act-Health-Insurance-Marketplace-Web.pdf) (KHI/26-02, January 2026) — KHI's analysis of CMS's 2026 Health Insurance Marketplace data; source for the rating-area benchmark cross-check above
- [CMS Marketplace Public Use Files](https://www.cms.gov/marketplace/resources/data/public-use-files) — underlying CMS rate/service-area data KHI's analysis is built on

**PolicyEngine source** (`PolicyEngine/policyengine-us`)
- `policyengine_us/variables/gov/aca/ptc/*.py`, `policyengine_us/variables/gov/aca/slspc/slcsp.py` — PTC and SLCSP calculation
- `policyengine_us/parameters/gov/aca/state_rating_area_cost.yaml` — KS's 7-rating-area benchmark table

**`benefits-api` sibling implementations**
- `programs/programs/cross_white_label/aca/tx.py` (`TxAca`) — county/`has_esi` gap, not yet fixed
- `programs/programs/cross_white_label/aca/mo.py` (`MoAca`) — the pattern `KsAca` should follow
- `programs/framework/pe_dependencies/household.py` — `KsStateCodeDependency`, `KsCountyDependency` (already defined, unused)
- `programs/framework/pe_dependencies/member.py` — `HasEsiDependency`

---

## Acceptance Criteria

- [ ] Scenario 1 (Single adult, Wyandotte County/Rating Area 1, 120% FPL, non-expansion coverage gap): User should be **eligible** — $6,257/year (~$521.42/month)
- [ ] Scenario 2 (same household, Sedgwick County/Rating Area 6 — isolates rating-area/SLCSP variation): User should be **eligible** — $7,599/year (~$633.25/month)
- [ ] Scenario 3 (Single adult, Wyandotte County, 50% FPL, below-floor): User should be **ineligible** — $0
- [ ] Scenario 4 (Single adult, Wyandotte County, 402.6% FPL — above the restored 400% FPL cap): User should be **ineligible** — $0
- [ ] Scenario 5 (Scenario 1's household, but with employer-sponsored coverage): User should be **ineligible** — $0

---

## Test Scenarios

> All three scenarios use a single-person tax unit, no employer-sponsored insurance, no dependents, 2026. Ages are entered via birth month/year (the screener's actual fields).

### Scenario 1: Single Adult, Wyandotte County — 120% FPL, Non-Expansion Coverage Gap (Golden Path)

- **Household**: 1 adult, birth month/year `March 1991` (age 35), employment income $18,780/year, KS resident, Wyandotte County (zip 66101), no health coverage, no employer offer, U.S. citizen.
- **Expected**: Eligible. `aca_ptc` = **$6,257/year** (~$521.42/month). `medicaid` = $0.

### Scenario 2: Same person, same income, Sedgwick County — isolates rating-area/SLCSP variation

- **Household**: 1 adult, birth month/year `March 1991` (age 35), employment income $18,780/year, KS resident, Sedgwick County (zip 67202), no health coverage, no employer offer, U.S. citizen.
- **Expected**: Eligible. `aca_ptc` = **$7,599/year** (~$633.25/month).
- **Why this matters**: holding age, income, and household composition constant against Scenario 1 and changing only county isolates the rating-area/SLCSP effect — the value should move by exactly the benchmark-premium delta between Rating Area 1 and Rating Area 6, and nothing else should change (both remain eligible).

### Scenario 3: Single Adult, Wyandotte County — 50% FPL, Below-Floor

- **Household**: 1 adult, birth month/year `March 1991` (age 35), employment income $7,825/year, KS resident, Wyandotte County (zip 66101), no health coverage, no employer offer, U.S. citizen.
- **Expected**: Ineligible. `aca_ptc` = **$0**.

### Scenario 4: Single Adult, Wyandotte County — 402.6% FPL, Above the Restored 400% Cap

- **Household**: 1 adult, birth month/year `March 1991` (age 35), employment income $63,000/year, KS resident, Wyandotte County (zip 66101), no health coverage, no employer offer, U.S. citizen.
- **Expected**: Ineligible. `aca_ptc` = **$0**.
- **Why this matters**: the enhanced (ARPA/IRA) premium tax credits expired after 2025, so the 400% FPL eligibility cap is **back in force for 2026** — PolicyEngine models this (`gov/aca/ptc_income_eligibility.yaml` returns the >400% bracket to `false` from `2026-01-01`). This is the single largest behavioral change in the program for 2026 and the coverage gap's upper edge: the same household $1,000 lower, at $62,000 (396.2% FPL), is eligible for $476/year. Without this scenario a re-extension of the enhanced credits — or a PolicyEngine parameter change — would silently flip thousands of Kansas households between $0 and a subsidy with nothing failing.

### Scenario 5: Scenario 1's Household, With Employer-Sponsored Coverage

- **Household**: identical to Scenario 1 (1 adult, age 35, $18,780/year, Wyandotte County, zip 66101) **except** the adult reports health coverage through a job.
- **Expected**: Ineligible. `aca_ptc` = **$0**.
- **Why this matters**: enrollment in an eligible employer plan is a statutory disqualifier (26 U.S.C. § 36B(c)(2)(C)), and PolicyEngine applies it **only if we send `has_esi`**. Holding everything else constant against Scenario 1 isolates that one input: $6,257 → $0. If `HasEsiDependency` is ever dropped from `KsAca`, this is the only scenario that fails.

---

## Data Gaps and Known Discrepancies

- **PolicyEngine excludes households at *exactly* 400% FPL.** Both the statute and the regulation make the cap inclusive — 26 U.S.C. § 36B(c)(1)(A) covers a household whose income "equals or exceeds 100 percent but does not exceed 400 percent," and 26 CFR § 1.36B-2(b)(1) reads "at least 100 percent but not more than 400 percent." PolicyEngine's `ptc_income_eligibility` brackets apply each amount at its threshold *and above*, which makes the 100% floor correct and the 400% cap off by one. Verified for a single adult (2025 guideline, $15,650) at PE 1.821.2 and 1.821.10 alike:

  | Income | % FPL | `aca_ptc` | Statute |
  | -- | -- | -- | -- |
  | $15,649 | 99.99% | $0.00 | ineligible ✓ |
  | $15,650 | 100.00% | $6,322.92 | eligible ✓ |
  | $62,599 | 399.99% | $416.71 | eligible ✓ |
  | $62,600 | 400.00% | $0.00 | **eligible ✗** |

  The affected band is a single dollar of annual income, so this is documented rather than worked around, and **Scenario 4 deliberately sits at 402.6% FPL** — where the statute and PolicyEngine agree — instead of encoding the discrepancy as an assertion. Reported upstream to PolicyEngine.
- **`estimated_value` is deliberately left blank**, so the results page shows the household's own computed figure rather than a static "up to" string. The Benefit Value section above asks for "estimated" or "up to" framing, and this is how that is satisfied: the program page already labels the figure **"Estimated Annual Value"** (`YearlyValueLabel`, default `value_format`), and the `description` states that actual savings may be lower depending on the plan chosen. Setting `estimated_value` would have replaced the personalized number with the same text for every household *and* dropped the program from its category total — `calculateTotalValue()` in `FormattedValue.tsx` skips any program carrying an override. Preserving the household-specific number and the category total was judged the better trade. A frontend `up_to` `value_format` that prefixes the personalized figure ("Up to $521/month") would satisfy both and is worth doing for the whole ACA family, `mo_aca_ptc` included — it needs a `benefits-calculator` change, so it is not part of this ticket.
- **Ages are asserted as fixed integers in the codified tests**, not as the birth month/year the scenarios state. The recorded cassettes match on the exact request body, so an age derived from the current date would break the suite on a calendar boundary. `March 1991` is age 35 throughout the 2026 coverage year either way, so the values are unaffected — but the screener's birth-date path is exercised by API QA rather than by these tests.
