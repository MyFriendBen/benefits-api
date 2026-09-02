# Implement CHIP (KS) Program

## Program Details

- **Program**: CHIP
- **State**: KS
- **White Label**: ks
- **Research Date**: 2026-06-23

## Eligibility Criteria

**Scope: children only.** Kansas CHIP covers children under 19. KS has **no separate CHIP for pregnant women** (CMS lists KS "Pregnant Women CHIP" = N/A) and no FCEP/unborn-child pathway — do not import pregnant-women CHIP language from other states (e.g., TX). (A *deemed newborn* auto-eligibility pathway exists per State Plan CS12 but is an automatic enrollment edge case, not a screening criterion.)

1. **Child must be under age 19 (ages 0-18)**
   - Screener fields:
     - `birth_year` + `birth_month` (age is computed from these; the `age` field is deprecated)
     - `relationship`
   - Source: KanCare CHIP State Plan CS7 (Targeted Low-Income Children, "under age 19"); 42 CFR 457.320(a)(2) ("Age (up to, but not including, age 19)"); 42 U.S.C. § 1397jj(c)(1); KLRD Briefing Book 2026

2. **Household income must be at or below 255% of the Federal Poverty Level (MAGI-based)**
   - The KanCare CHIP State Plan (CS7) states the standard as "up to & including **250%** FPL"; eligibility then applies the standard **5% MAGI disregard**, so the **effective cap is 255% FPL**. PolicyEngine encodes this as `gov.hhs.chip.child.income_limit[KS]` = **2.55**, and eligibility is `medicaid_income_level <= 2.55`. **Validations must use 255% as the eligible/ineligible boundary, not 250%** (confirmed by a live PE run).
   - Lower bound is the Medicaid/M-CHIP threshold for the child's age (CMS Dec 2023: **166%** age 0–1, **149%** age 1–5, **133%** age 6–18); below that the child is Medicaid-eligible (criterion 3), not CHIP.
     - **Operative source (verified live this session):** KanCare CHIP State Plan **CS7** income-standards table states CHIP applies "Above (% FPL)" / "Up to & including (% FPL)" of **`0–1: above 166, up to 250`**, **`1–6: above 149, up to 250`**, **`6–19: above 133, up to 250`**, with the note that "the lower bound for CHIP eligibility should be the highest standard used for Medicaid poverty-level children for the same age group." This confirms the 166/149/133 age-banded floors directly from the State Plan (PE agrees). *Note:* the KLRD Briefing Book 2026 premium grid shows infant Medicaid only to ~150% — that grid is a simplified/inconsistent presentation; CS7 (operative) and PE govern.
   - **No asset/resource test.** KanCare applies no resource limit to families and children — do **not** apply any `household_assets` check in the calculator (the field is collected but unused here).
   - Screener fields:
     - `household_size`
     - `income (all types via calc_gross_income)`
   - Source: KanCare CHIP State Plan CS7 (Targeted Low-Income Children); CMS National Medicaid/CHIP Eligibility Levels; KLRD Briefing Book 2026; KFMAM §05000 (Income Guidelines); PE `income_limit.yaml` (KS = 2.55)

3. **Child must not already be eligible for or enrolled in Medicaid**
   - PE enforces this directly (`is_chip_eligible_child` requires `~is_medicaid_eligible`); coordinates with the KanCare Medicaid ticket (MFB-1054). Reported Medicaid coverage is also captured.
   - Screener fields:
     - `current_benefits` / `member.insurance.has_insurance_types(["medicaid"])` (reported Medicaid)
     - `household_size`, `birth_year` + `birth_month`, `income (all types via calc_gross_income)` (PE computes Medicaid eligibility)
   - Source: 42 CFR 457.310(b)(2)(i) (no-other-coverage standard — not eligible/potentially eligible for Medicaid); 42 U.S.C. § 1397jj(b)(1)(C); CMS Eligibility Levels (KS Medicaid 166/149/133% by age). *(State Plan CS14 is the narrow §2101(f)/457.310(d) disregard-elimination carve-out — not the general no-Medicaid rule — so it is not cited here.)*

4. **Child must be a Kansas resident**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: KanCare CHIP State Plan CS17 (Non-Financial Eligibility — Residency); 42 CFR 457.320(e) (Residency; (e)(1) applies §435.403(i) for non-institutionalized children) — *note: the May 8, 2024 amendment (89 FR 39436) moved Residency from (d) to (e); (d) is now "Citizenship and immigration status"*; KanCare Eligibility Overview

5. **Household must include at least one child (program is child-specific)**
   - Largely implied by criterion 1; kept to document that CHIP applies per-child (a household with no member under 19 yields no CHIP-eligible person).
   - Screener fields:
     - `birth_year` + `birth_month`
     - `relationship`
   - Source: KanCare CHIP State Plan CS7; 42 U.S.C. § 1397aa et seq.

6. **Child must not be covered by a group health plan or other health insurance coverage (must be uninsured)**
   - Handled by MFB's hybrid: PE returns the CHIP value, and the calculator zeroes it unless the child's insurance is `none` (see `TxChip.member_value` precedent). **PE now fully models this** (as of 1.752.1, resolved 2026-07-01): `is_chip_eligible_child` gates on `~has_health_coverage_other_than_chip`, covering employer-sponsored coverage, private direct-purchase, Medicaid, Medicare, TRICARE, CHAMPVA, VA, and any other non-CHIP source. Pass `has_health_coverage_other_than_chip: true` for a child known to have non-CHIP coverage. IHS-only coverage remains allowed. *(Prior versions only checked `~has_esi`; non-ESI coverage was not excluded by PE — gap #8577, now closed.)* MFB's hybrid zero-out (`member_value → 0` unless insurance is `none`) remains a valid implementation path — it covers all non-`none` coverage types without requiring MFB to pass a PE flag. **IHS implementation note (LOW):** IHS is not currently in MFB's insurance type enum, so a child with IHS-only coverage will select `none` and be correctly eligible via the hybrid. If MFB adds an IHS insurance type in future, confirm the hybrid allows it rather than zeroing it out.
   - Screener fields:
     - `member.insurance` — the child is eligible **only when their insurance is exactly `none`**. Any other captured insurance type disqualifies (treat the full enum as the disqualifying set): `employer`, `private`, `medicaid`, `medicare`, `chp`, `emergency_medicaid`, `family_planning`, `va`, `mass_health`, `dont_know`. Implement as "eligible if `has_insurance_types(["none"])` is the member's only coverage; otherwise zero out" — do not hard-code a partial list.
   - Source: 42 CFR 457.310(b)(2)(ii) (no-other-coverage standard — not covered under a group health plan/health insurance); KanCare CHIP State Plan CS20 (Substitution of Coverage); 42 U.S.C. § 1397jj(b)(1)(C)

7. **U.S. citizenship or qualified non-citizen immigration status required** — *handled by the citizenship filter (not an open data gap)*
   - How it's handled: MFB does **not** send `immigration_status` to PolicyEngine; instead the program's `legal_status_required` list in the config drives MFB's citizenship/immigration **results filter**, which controls who is shown CHIP. Kansas covers U.S. citizens and qualified non-citizens under 8 U.S.C. § 1641 (PRWORA § 431) who are not barred by the 5-year rule (8 U.S.C. § 1613). **Kansas does not elect CHIPRA §214** (State Plan CS18, SPA# KS-14-0013, eff. Jan 1, 2014 — election box = No), so the 5-year bar applies to LPRs under 5 years. Covered statuses: `citizen`, `gc_5plus` (LPR 5+ years, bar met), and `refugee` (eligible under the § 402(b) time-limited exception, 8 U.S.C. § 1612(b) — not subject to the standard 5-year LPR bar). This criterion is enforced at the results-filter layer, not as an unassessable screener field. (Confirmed: federal `Chip`/`TxChip` calculators send no `immigration_status`; MFB's citizenship filter governs display.)
   - ⚠️ **Upcoming law change (effective Oct 1, 2026 — H.R.1):** federal CHIP eligibility ends for refugees and asylees (the `refugee` status in this plan's `legal_status_required`) unless they hold LPR, Cuban/Haitian entrant, or COFA status. For CHIP there is **no grandfather** — states must terminate coverage for affected enrollees on that date (the continuous-eligibility carve-out applies to Medicaid, not CHIP), so early enrollment does not preserve coverage. After the Oct 1 flip, `legal_status_required` becomes `["citizen", "gc_5plus"]`.
     - **Decision (2026-06-24 review; warning banner removed 2026-06-28):**
       - The program **description carries no law-change content** (it describes the program, priority criteria, and next steps only).
       - **Required:** on/around Oct 1, 2026, flip `legal_status_required` — remove `refugee` so CHIP stops showing for that group. This is the actual eligibility change.
       - **No warning banner.** A warning banner was considered and removed (2026-06-28): the `legal_status_required` flip is the sufficient and correct mechanism; the banner's useful life before Oct 1 is too short to justify the operational overhead of a timed removal, and it could discourage eligible enrollment in the transitional period.
       - Tracked on MFB-1055 + the weekday PE/law monitor.
   - Source: KanCare CHIP State Plan CS18 (Citizenship — CHIPRA §214 not elected, SPA# KS-14-0013, eff. Jan 1, 2014); KFMAM §02000 (General Eligibility); 8 U.S.C. § 1641; 8 U.S.C. § 1612(b) (§ 402(b) time-limited exception — refugees not subject to the standard 5-year LPR bar)
   - Impact: Handled (was mislabeled HIGH data gap by the researcher)

8. **Child must not be an inmate of a public institution** ⚠️ *data gap*
   - Screener fields: none. Handling assumption (inclusive): incarceration/institutional status isn't captured, so we don't exclude on it — a tiny share of self-serve screener users, confirmed at application.
   - Source: 42 CFR 457.310(c)(2)(i) (CHIP exclusion — inmate of a public institution, per § 435.1010)
   - Impact: LOW

9. **Child must not be a patient in an institution for mental diseases (IMD)** ⚠️ *data gap*
   - Screener fields: none. Handling assumption (inclusive): not captured; not excluded. Rare edge case.
   - Source: 42 CFR 457.310(c)(2)(ii) (CHIP exclusion — patient in an institution for mental diseases, per § 435.1010)
   - Impact: LOW

## Priority Criteria

None. Kansas CHIP has no enrollment cap, waitlist, or priority/ranking — all eligible children are enrolled (≈61,100 enrolled as of April 2025, per KLRD Briefing Book 2026). There is no "who gets served first" ordering to model.

## Benefit Value

CHIP is health-insurance coverage; the screened value is the per-enrollee value PolicyEngine assigns (`per_capita_chip`, average state CHIP spend per child), surfaced via the `chip` output. The KS-specific layer is the **monthly premium** the family pays:

- **Expected coverage value (pinned): `$1,896/yr` per eligible child** (PE 1.752.1, verified 2026-07-01). PE's `chip` output = `per_capita_chip` = KS **separate-CHIP** spending ÷ separate-CHIP enrollment (MACPAC FY2024: $136.6M ÷ 72,018 = **$1,896/yr net**; gross adds $4.7M in premium/cost-sharing offsets for ~$1,962/yr — PE uses the net figure). Prior versions used all-CHIP spending ÷ all-CHIP enrollment ($189.6M ÷ 89,803 = $2,112); the denominator was revised to separate-CHIP only because PE models Medicaid-expansion CHIP children through Medicaid (PE issues #8673/#8679, now resolved). The value is flat: every eligible child receives the full $1,896 regardless of income or premium tier (take-up not applied). Re-confirm with a live PE run if the param updates.

- **Premium tiers** (per family, not per child — KanCare April 2025 / KLRD Briefing Book 2026, confirmed against PE `ks_chip_premium` in a live run): **≤166% FPL → $0** · **167–191% → $20/mo** · **192–218% → $30/mo** · **219–255% → $50/mo**. Computed by PE `ks_chip_premium` (TaxUnit), one flat premium covering all CHIP-eligible children. Premiums are cost-sharing, **not** an eligibility gate (non-payment can cause later disenrollment, but never blocks *initial* eligibility — which is all the screener determines). *Note on re-enrollment lockout:* the current State Plan **CS21** (transmittal KS-25-0013, verified live this session) answers "premium lock-out period? **No**," whereas the KLRD Briefing Book 2026 describes a 90-day re-enrollment bar after delinquency. The two disagree; since CS21 is the operative State Plan and this detail does not affect screening eligibility or value, no lockout is asserted here.
  - **Operative source (verified live, 2026-06-26):** PE `parameters/gov/states/ks/hhs/chip/premium.yaml` defines the premium as *"this KanCare monthly CHIP premium per household, based on the tax unit's modified adjusted gross income as a fraction of the federal poverty line"* with brackets (threshold as a fraction of FPL → monthly amount): **`-inf → $0`**, **`1.67 → $20`**, **`1.92 → $30`**, **`2.19 → $50`**. These thresholds map exactly to the FPL bands above (e.g. the $50 tier begins at 219% FPL and runs to the 255% eligibility cap). KS `gov.hhs.chip.child.income_limit` = **2.55** (effective 2022-07-01), verified in the same file set.
- **KS build note:** the TX precedent (`TxChip`) outputs only the benefit value and surfaces no premium. The KS calculator must additionally output `ks_chip_premium`. **Display treatment (committed):** surface the **$1,896/yr coverage value** as the benefit value; output the **monthly premium** (`ks_chip_premium ÷ 12`) as a separate line alongside it — not netted against the value. This shows what coverage is worth and what the family pays, independently. Each scenario below lists both. **PE implementation note:** `ks_chip_premium` is a TaxUnit-level variable that returns an **annual** figure (the `premium.yaml` monthly amount × 12); the display layer must divide by 12 to surface the monthly amount (e.g., PE returns 240 for the $20/mo tier, 360 for $30/mo, 600 for $50/mo). This is the only KS-specific surface — the coverage value (`chip` / `per_capita_chip`) flows through the standard annual benefits path unchanged.
- Source: PE `parameters/gov/states/ks/hhs/chip/premium.yaml`; KLRD Briefing Book 2026; KanCare CHIP State Plan CS21 (Non-Payment of Premiums)

> **Folded into the config, not eligibility criteria** (removed from this section as administrative): **SSN** must be provided/applied for → covered by the `ks_ssn` document in the config; **application submission** through KanCare → covered by the apply button + description. Neither is a screening criterion.

## Implementation Coverage

- ✅ Evaluable by the screener/PE: 6 (age, income ≤255% FPL, KS residency, child present, current Medicaid status, current insurance status)
- ✅ Handled outside the eligibility calc: 1 (citizenship/immigration → `legal_status_required` results filter)
- ⚠️ True data gaps (all LOW for screening): institutionalization (inmate/IMD), SSN, application submission — rare or procedural; none blocks a screening result

The core screening factors are fully covered: age (under 19), income (at or below the **255% FPL** effective cap), Kansas residency (ZIP/county), presence of a child, current Medicaid enrollment, and current insurance status (the "uninsured only" rule, enforced via MFB's hybrid zero-out). Citizenship/immigration is handled through the `legal_status_required` filter — not a screener data gap. The remaining gaps are low-population edge cases or procedural application steps and do not affect screening eligibility.

> **Federal rules researched and confirmed non-operative in KS (not eligibility criteria):** The 90-day ESI drop waiting period is not imposed in KS — State Plan CS20 (SPA# KS-19-0021) election = No. The SEHP exclusion (42 CFR 457.310(c)(1)) does not apply in KS — State Plan CS10 (SPA# KS-16-0001) elects the maintenance-of-agency-contribution option, covering these children anyway. Neither rule is enforced and neither requires a screener field or inclusivity assumption.

## Research Sources

### Kansas program sources (the 5 researcher inputs)

- [KanCare CHIP State Plan (full PDF, 01/26/2026)](https://www.kancare.ks.gov/home/showpublisheddocument/6596/639069975141800000) — includes the per-criterion State Plan sub-sections cited above:
  - [CS7 Targeted Low-Income Children](https://www.kancare.ks.gov/home/showpublisheddocument/6592/639069950294930000) · [CS10 Access to Public Employee Coverage](https://www.kancare.ks.gov/home/showpublisheddocument/6566/639069950237730000) · [CS12 Deemed Newborns](https://www.kancare.ks.gov/home/showpublisheddocument/6568/639069950243270000) · [CS14 Children Ineligible for Medicaid](https://www.kancare.ks.gov/home/showpublisheddocument/6570/639069950246830000) · [CS17 Residency](https://www.kancare.ks.gov/home/showpublisheddocument/6574/639069950254030000) · [CS18 Citizenship](https://www.kancare.ks.gov/home/showpublisheddocument/6576/639069950257570000) · [CS20 Substitution of Coverage](https://www.kancare.ks.gov/home/showpublisheddocument/6580/639069950265170000) · [CS21 Non-Payment of Premiums](https://www.kancare.ks.gov/home/showpublisheddocument/6582/639069950269900000)
- [KLRD Briefing Book 2026 — Children's Eligibility for CHIP, M-CHIP, Medicaid, and HCBS (incl. CHIP premiums)](https://klrd.gov/2026/03/02/briefing-book-2026-childrens-eligibility-for-chip-mchip-medicaid-and-hcbs-including-information-on-premium-requirements-for-chip/)
- [KanCare Eligibility Overview](https://www.kancare.ks.gov/apply-now/eligibility)
- [Kansas Family Medical Assistance Manual (KFMAM) — full manual](https://khap.kdhe.ks.gov/kfmam/main.asp) (§02000 General Eligibility; §05000 Income Guidelines)
- [CMS National Medicaid, CHIP, and BHP Eligibility Levels by State](https://www.medicaid.gov/medicaid/national-medicaid-chip-program-information/medicaid-childrens-health-insurance-program-basic-health-program-eligibility-levels)

### Federal regulation & statute (added during review for citation precision)

- [42 CFR 457.310 — Targeted low-income child (standards & exclusions: Medicaid, group coverage, SEHP, institutions)](https://www.law.cornell.edu/cfr/text/42/457.310)
- [42 CFR 457.320 — Other eligibility standards (age <19, residency, citizenship)](https://www.law.cornell.edu/cfr/text/42/457.320)
- [42 U.S.C. § 1397jj — CHIP definitions (child, targeted low-income child)](https://www.law.cornell.edu/uscode/text/42/1397jj); § 1397aa et seq.
- [8 U.S.C. § 1641 — definition of "qualified alien"](https://www.law.cornell.edu/uscode/text/8/1641)

### PolicyEngine verification

- policyengine-us 1.752.1 (`master`): `is_chip_eligible_child.py`, `ks_chip_premium.py`, `premium.yaml`, `income_limit.yaml`, `max_age.yaml` — plus **live simulation runs** used to derive/verify every test-scenario expected value (eligibility + premium). Updated 2026-07-01: `has_health_coverage_other_than_chip` replaces `has_esi` as the CHIP coverage gate (gap #8577 resolved); `per_capita_chip` revised to separate-CHIP spending/enrollment ($1,896/yr, was $2,112; issues #8673/#8679 resolved).

### Upcoming law change — H.R.1 (eff. Oct 1, 2026); basis for criterion 7

- [SHVS — H.R.1's changes to non-citizen coverage (FAQ)](https://shvs.org/h-r-1s-changes-to-non-citizen-coverage-frequently-asked-questions-2/)
- [SHVS — CMS guidance on H.R.1 non-citizen restrictions in Medicaid & CHIP](https://shvs.org/cms-guidance-on-h-r-1s-restrictions-for-non-citizen-coverage-in-medicaid-and-chip/)
- [Georgetown CCF — new immigrant eligibility restrictions](https://ccf.georgetown.edu/2025/10/01/new-immigrant-eligibility-restrictions-coming-to-federally-funded-health-coverage/)

## Acceptance Criteria

**All 16 scenarios are run through PolicyEngine** (policyengine-us 1.752.1, 2026 FPL, verified 2026-07-01). **All 16 match** the MFB-expected result — no known mismatches (PE gap #8577 resolved). "Premium" is the KS-specific `ks_chip_premium` (per family/month). The displayed health-coverage value is PE `per_capita_chip` = **$1,896/yr** per eligible child ($136,581,734 ÷ 72,018 = $1,896.49/yr → $1,896).
- [ ] Scenario 1 (Golden path — uninsured child, ~176% FPL): **eligible**, $1,896/yr value, $20/mo premium
- [ ] Scenario 2 ($0-premium band — ~146% FPL): **eligible**, $1,896/yr value, $0/mo premium
- [ ] Scenario 3 ($30 premium tier — ~201% FPL): **eligible**, $1,896/yr value, $30/mo premium
- [ ] Scenario 4 ($50 tier, just under the 255% cap — ~253% FPL): **eligible**, $1,896/yr value, $50/mo premium
- [ ] Scenario 5 (Income just over the 255% cap — ~264% FPL): **ineligible**
- [ ] Scenario 6 (Medicaid boundary — ~110% FPL, child is Medicaid-eligible): **ineligible for CHIP**
- [ ] Scenario 7 (Newborn, age 0): **eligible**, $1,896/yr value, $20/mo premium
- [ ] Scenario 8 (Child already turned 19): **ineligible**
- [ ] Scenario 9 (No child under 19 in household): **ineligible**
- [ ] Scenario 10 (Child covered by a group health plan / other non-CHIP coverage): **ineligible**
- [ ] Scenario 11 (Mixed household — one insured child (age 12), one uninsured (age 5), ~164% FPL): **eligible** for the uninsured child, $1,896/yr value, $0/mo premium (insured child excluded, $0)
- [ ] Scenario 12 (Age-banded Medicaid floor — infant, age 0, ~158% FPL): **ineligible for CHIP** (infant is Medicaid-eligible)
- [ ] Scenario 13 (Age-banded Medicaid floor — child age 3, ~145% FPL): **ineligible for CHIP** (age 1–5 child is Medicaid-eligible)
- [ ] Scenario 14 (Oldest eligible age — child age 18, ~177% FPL): **eligible**, $1,896/yr value, $20/mo premium
- [ ] Scenario 15 (Child with non-ESI / private coverage — `has_health_coverage_other_than_chip=True`): **ineligible/$0** — PE correctly returns ineligible (gap #8577 resolved in PE 1.752.1)
- [ ] Scenario 16 (Two CHIP-eligible uninsured children — ~178% FPL): **eligible**, $3,792/yr value (PE raw per child $1,896.4944 → 2 × = $3,792.99, which the platform **truncates** to the integer **$3,792** — not rounded to $3,793), $20/mo premium (per-family charge, not doubled)

## Test Scenarios

Each scenario lists PE-verified expected eligibility and premium. Birth years assume the current year is 2026. Income is the household total (placed on the head unless noted); premium is per family.

> **County naming note:** Scenarios use bare KS county names (`Sedgwick`, `Riley`, `Shawnee`, `Douglas`, `Finney`) with no "County" suffix — consistent with the TX/IL convention in `test_case_schema.json` and confirmed against the KS SNAP config. All ZIP↔county pairings are verified correct (67202 Sedgwick/Wichita, 66502 Riley/Manhattan, 66604 Shawnee/Topeka, 66044 Douglas/Lawrence, 67846 Finney/Garden City).

### Scenario 1: Golden path — uninsured child, working family
**What we're checking**: Typical eligible household — child under 19, income above the Medicaid threshold but under the 255% CHIP cap, KS resident, no other coverage.
**Expected**: Eligible · coverage value **$1,896/yr** (PE `chip` / `per_capita_chip`) · **$20/mo** premium (child FPL ≈176%)

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$2,800`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, employment income `$1,200`/mo, insurance: none
- **Person 3**: Child, born `January 2019` (age 7), no income, insurance: none, not on Medicaid

**Why this matters**: Primary regression test for the common case, and it confirms the $20 premium tier (167–191% FPL) — note the golden path is NOT $0.

---

### Scenario 2: $0-premium band (above Medicaid, below 167% FPL)
**What we're checking**: Eligible child whose family income sits in the no-premium CHIP band.
**Expected**: Eligible · coverage value **$1,896/yr** (PE `chip` / `per_capita_chip`) · **$0/mo** premium (child FPL ≈146%)

**Steps**:
- **Location**: ZIP `66502`, county `Riley`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$3,333`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, no income, insurance: none
- **Person 3**: Child, born `January 2016` (age 10), no income, insurance: none, not on Medicaid

**Why this matters**: Tests the bottom of the premium schedule ($0 below 167% FPL) and that a child just above the Medicaid line (133% for age 6–18) lands in CHIP, not Medicaid.

---

### Scenario 3: $30 premium tier
**What we're checking**: Eligible child in the 192–218% FPL band.
**Expected**: Eligible · coverage value **$1,896/yr** (PE `chip` / `per_capita_chip`) · **$30/mo** premium (child FPL ≈201%)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$4,583`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, no income, insurance: none
- **Person 3**: Child, born `January 2018` (age 8), no income, insurance: none, not on Medicaid

**Why this matters**: Verifies the middle premium tier ($30 at 192–218% FPL).

---

### Scenario 4: $50 premium tier — just under the 255% cap
**What we're checking**: Eligible child near the top of the income range.
**Expected**: Eligible · coverage value **$1,896/yr** (PE `chip` / `per_capita_chip`) · **$50/mo** premium (child FPL ≈253%)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$5,750`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, no income, insurance: none
- **Person 3**: Child, born `January 2019` (age 7), no income, insurance: none, not on Medicaid

**Why this matters**: Confirms the top premium tier ($50 at 219–255%) AND that eligibility holds right below the 255% cap — the eligible half of the boundary pair with Scenario 5.

---

### Scenario 5: Income just over the 255% cap — ineligible
**What we're checking**: Household just above the 255% effective cap.
**Expected**: Not eligible (child FPL ≈264%)

**Steps**:
- **Location**: ZIP `66502`, county `Riley`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$6,000`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, no income, insurance: none
- **Person 3**: Child, born `January 2019` (age 7), no income, insurance: none, not on Medicaid

**Why this matters**: The ineligible half of the boundary pair. ≈264% FPL is just over the 255% cap, so PE returns ineligible. (Replaces the original scenario that used ≈232% FPL and wrongly expected ineligible.)

---

### Scenario 6: Medicaid boundary — low income, Medicaid-eligible
**What we're checking**: A low-income child who qualifies for Medicaid is NOT CHIP-eligible (CHIP is only for those above the Medicaid threshold).
**Expected**: Not eligible for CHIP (child is Medicaid-eligible; child FPL ≈110%)

**Steps**:
- **Location**: ZIP `67846`, county `Finney`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$2,500`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, no income, insurance: none
- **Person 3**: Child, born `January 2016` (age 10), no income, insurance: none, not on Medicaid

**Why this matters**: Tests the lower bound — CHIP requires `~is_medicaid_eligible`. The child should screen into Medicaid (MFB-1054), not CHIP. This is the dependency on the Medicaid ticket made concrete.

---

### Scenario 7: Newborn (age 0)
**What we're checking**: Youngest eligible age.
**Expected**: Eligible · coverage value **$1,896/yr** (PE `chip` / `per_capita_chip`) · **$20/mo** premium (FPL ≈176%)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$2,800`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, employment income `$1,200`/mo, insurance: none
- **Person 3**: Child, born `March 2026` (age 0), no income, insurance: none, not on Medicaid

**Why this matters**: Confirms infants are recognized at the bottom age boundary.

---

### Scenario 8: Child already turned 19 — ineligible (age)
**What we're checking**: Upper age boundary.
**Expected**: Not eligible (age ≥ 19)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas`
- **Household**: 2 people
- **Person 1**: Head of Household, born `September 1981`, employment income `$2,500`/mo, insurance: none
- **Person 2**: Child, born `March 2007` (turned 19 in March 2026), no income, insurance: none, not on Medicaid

**Why this matters**: PE limit is `age < 19`. Confirms a 19-year-old is excluded even with otherwise-eligible income/coverage.

---

### Scenario 9: No child under 19 — ineligible
**What we're checking**: Program scope (children only).
**Expected**: Not eligible (no CHIP-eligible person in household)

**Steps**:
- **Location**: ZIP `66502`, county `Riley`
- **Household**: 2 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$2,500`/mo, insurance: none
- **Person 2**: Spouse, born `January 1990`, no income, insurance: none

**Why this matters**: An all-adult household yields no CHIP-eligible child.

---

### Scenario 10: Child covered by a group health plan — ineligible
**What we're checking**: The "uninsured only" rule (MFB hybrid zero-out).
**Expected**: Not eligible (child has other coverage)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$3,200`/mo, insurance: employer / group health plan
- **Person 2**: Spouse, born `September 1989`, employment income `$1,500`/mo, insurance: employer / group health plan
- **Person 3**: Child, born `January 2019` (age 7), no income, insurance: employer / group health plan (covered under parent's plan)

**Why this matters**: Income (~$56k/yr, size 3) is under the cap, but the child has group coverage. PE excludes all non-CHIP coverage via `has_health_coverage_other_than_chip` (PE 1.752.1; prior versions only checked `~has_esi`). MFB's hybrid (`member_value` → 0 unless insurance is `none`) also enforces the exclusion for all coverage types without passing a PE flag.

---

### Scenario 11: Mixed household — one insured child, one uninsured
**What we're checking**: Per-child insurance differentiation with household-level income.
**Expected**: Eligible for the uninsured child · coverage value **$1,896/yr** (PE `chip` / `per_capita_chip`) · **$0/mo** premium (FPL ≈164%); the insured child is excluded ($0).

**Steps**:
- **Location**: ZIP `66044`, county `Douglas`
- **Household**: 4 people
- **Person 1**: Head of Household, born `March 1988`, employment income `$3,000`/mo, insurance: employer / group health plan
- **Person 2**: Spouse, born `September 1991`, employment income `$1,500`/mo, insurance: employer / group health plan
- **Person 3**: Child, born `January 2014` (age 12), no income, insurance: employer / group health plan (covered under parent's plan)
- **Person 4**: Child, born `November 2020` (age 5), no income, insurance: none, not on Medicaid

**Why this matters**: Insurance is evaluated per child (hybrid zero-out) while income (≈164% FPL, size 4) is household-level. The uninsured 5-year-old is eligible at $0/mo (age 1–5 Medicaid floor is 149%, effective ≈154%; 164% is above it → CHIP); the insured 12-year-old is excluded. Also covers the 1–5 eligible band — the only scenario where this child is in CHIP rather than Medicaid.

---

### Scenario 12: Age-banded Medicaid floor — infant (age 0)
**What we're checking**: The CHIP/Medicaid lower boundary is **age-banded**, not a single FPL. Kansas Medicaid covers infants (age 0–1) up to a higher FPL than older children (CMS Dec 2023: **166%** age 0–1 vs **133%** age 6–18; effective ≈170% age 0–1 after the 5% MAGI disregard). An income that lands an *older* child in CHIP can keep an **infant in Medicaid** — so this band must be tested on its own (prior scenarios only exercised the age-6+ floor in Scenario 6).
**Expected**: Not eligible for CHIP — infant is **Medicaid-eligible** (child FPL ≈158%, below the ≈170% infant Medicaid line)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$3,600`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, no income, insurance: none
- **Person 3**: Child, born `March 2026` (age 0), no income, insurance: none, not on Medicaid

**Why this matters**: At ≈158% FPL an age 6–18 child is CHIP-eligible (cf. Scenario 2 at 146%), but an **infant at the same FPL is Medicaid-eligible, not CHIP**. Confirms PE applies the age 0–1 Medicaid threshold (`is_chip_eligible_child` requires `~is_medicaid_eligible`). Verified against a live PE run (chip_elig=False, medicaid_elig=True).

---

### Scenario 13: Age-banded Medicaid floor — child age 1–5
**What we're checking**: The middle age band (age 1–5), whose Medicaid line (≈149%, effective ≈154% after disregard) sits between the infant and age-6+ bands. No prior scenario tested it.
**Expected**: Not eligible for CHIP — child is **Medicaid-eligible** (child FPL ≈145%, below the ≈154% age 1–5 Medicaid line)

**Steps**:
- **Location**: ZIP `66502`, county `Riley`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$3,300`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, no income, insurance: none
- **Person 3**: Child, born `January 2023` (age 3), no income, insurance: none, not on Medicaid

**Why this matters**: A 145% FPL age 6–18 child would be CHIP-eligible, but an **age 1–5 child at the same FPL is Medicaid-eligible**. Completes coverage of all three age-banded Medicaid floors (0–1, 1–5, 6–18). Verified against a live PE run (chip_elig=False, medicaid_elig=True).

### Scenario 14: Oldest eligible age (18) — eligible
**What we're checking**: Upper age boundary, eligible side — pairs with Scenario 8 (age 19, ineligible) to bracket the `age < 19` cutoff.
**Expected**: Eligible · coverage value **$1,896/yr** (PE `chip` / `per_capita_chip`) · **$20/mo** premium (child FPL ≈177%)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 2 people
- **Person 1**: Head of Household, born `March 1982` (age 44), employment income `$3,200`/mo, insurance: none
- **Person 2**: Child, born `March 2008` (age 18), no income, insurance: none, not on Medicaid

**Why this matters**: Confirms an 18-year-old is still eligible (PE `age < 19`), completing the upper-age boundary pair with Scenario 8 (age 19 → ineligible). Verified live (FPL ≈177%, eligible, $20/mo).

---

### Scenario 15: Child with non-ESI / private coverage
**What we're checking**: Criterion 6 ("no other coverage") for non-employer coverage — now fully modeled by PE via `has_health_coverage_other_than_chip` (gap #8577 resolved in PE 1.752.1, 2026-07-01).
**Expected**: **Ineligible / $0** — child has private direct-purchase coverage; both PE and MFB agree.

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$2,800`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, employment income `$1,200`/mo, insurance: none
- **Person 3**: Child, born `January 2019` (age 7), no income, insurance: **private / direct-purchase (non-employer)** → `has_health_coverage_other_than_chip: true`

**Why this matters**: This is Scenario 1 (~176% FPL) with only the child's coverage changed, isolating the insurance dimension. PE now natively excludes children with non-CHIP coverage when `has_health_coverage_other_than_chip: true` is passed. MFB's hybrid zero-out remains a valid implementation path (no PE flag required). The scenario guards against a dev using only `has_esi` and silently missing non-ESI coverage types.

---

### Scenario 16: Two CHIP-eligible uninsured children — value scales, premium stays flat
**What we're checking**: When two siblings are both CHIP-eligible and uninsured, the coverage value is per-child ($1,896.4944/yr × 2 = $3,792.99, truncated to **$3,792/yr** total) while the household premium remains a single flat charge ($20/mo, not doubled).
**Expected**: Eligible · coverage value **$3,792/yr** (PE raw per child $1,896.4944; 2 × = $3,792.99, which the platform **truncates** to the integer **$3,792** — the per-child display value is still $1,896) · **$20/mo** premium (per-family, FPL ≈178%)

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick`
- **Household**: 4 people
- **Person 1**: Head of Household, born `March 1986`, employment income `$4,000`/mo, insurance: none
- **Person 2**: Spouse, born `September 1988`, employment income `$800`/mo, insurance: none
- **Person 3**: Child, born `January 2019` (age 7), no income, insurance: none, not on Medicaid
- **Person 4**: Child, born `March 2016` (age 10), no income, insurance: none, not on Medicaid

**Why this matters**: Verifies two implementation requirements that could independently fail: (1) the coverage value aggregates per child — PE's `chip` output returns `per_capita_chip` (~$1,896.49) for each eligible member, so both must be summed (2 × $1,896.4944 = $3,792.99, which the platform truncates to the integer **$3,792**; the $1,896 display value is the per-child figure, not the aggregate); (2) `ks_chip_premium` is a TaxUnit/household-level output — it returns one flat premium regardless of how many children are enrolled. A developer could plausibly double the premium for two children, or fail to sum per-child coverage values correctly. Both children are ages 6–18 at ~178% FPL (above the 133% Medicaid floor) and uninsured — each is independently CHIP-eligible.

---

> **Coverage note — criteria not exercised by a PE scenario:** Citizenship/immigration (criterion 7) is enforced at the `legal_status_required` results-filter layer, not in PE, so it has no PE simulation scenario (the Oct 1 2026 change is handled via the `legal_status_required` flip). KS residency (criterion 4) is a ZIP/county screener filter, not a PE input, so there is no negative-residency PE scenario. The two LOW data gaps (inmate, IMD) are intentionally not tested — inclusive handling, no screener field captured. The 90-day ESI drop waiting period and SEHP exclusion are not tested because neither applies in KS (CS20 election = No; CS10 waives the SEHP exclusion). There is no $0-premium scenario for an age 0–1 child: CHIP-eligible infants must have income above the age 0–1 Medicaid floor (166%, effective ≈171% after the 5% MAGI disregard), which exceeds the 167% threshold below which the $0 premium tier applies — so infants in CHIP are structurally always in the $20/mo tier or above (confirmed: Scenario 7, age 0, 175.7% FPL → $20/mo).

## Program Configuration
File: `ks_chip_initial_config.json` (reviewed separately)
