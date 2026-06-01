# Program Details

* **Program**: Apple Health (Medicaid)
* **State**: WA
* **White Label**: wa
* **Research Date**: 2026-04-14
* **Review Date**: 2026-05-13

## Eligibility Criteria

 1. **Must be a Washington State resident**
    * Screener fields:
      * `zipcode`
      * `county`
    * Source: WAC 182-503-0510 (definition of WA residency); WAC 182-503-0520 (continuity during temporary absence); HCA Eligibility Overview
 2. **Income eligibility — Adults 19–64: MAGI at or below 133% FPL (138% effective after standard 5% disregard)**
    * Eligibility:
      * Age 19–64
      * Household MAGI ≤ 133% FPL nominal / 138% effective (after standard 5% income disregard per 42 CFR § 435.603(d)(4)). HCA chart (2026, 138% effective amounts): $1,835/mo single, $2,490 2-person, $3,142 3-person, $3,795 4-person, $4,449 5-person, $5,102 6-person, $5,755 7-person.
      * WA resident (criterion 1); citizenship/qualifying immigration (criterion 10 data gap)
      * **Not entitled to or enrolled in Medicare** (42 CFR § 435.119(b)(3)) — Medicare-entitled adults qualify via SSI-related ABD (criterion 6) or Medicare Savings Programs (separate program family), not under expansion.
    * Routes to EXPANSION_ADULT bucket ($471/month). Applies regardless of parental status; parents below the §1931 standard route to NON_EXPANSION_ADULT instead (criterion 3).
    * Screener fields: `household_size`, `income (all types via calc_gross_income)`, `age`, `insurance.medicare` (dev to confirm boolean exists)
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(i)(VIII); 42 CFR § 435.119; WAC 182-505-0100; HCA Apple Health for Adults (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/individual-adults)
 3. **Income eligibility — Parents/Caretaker Relatives (§1931 pathway): Adult 19–64 with dependent child under 18; household MAGI ≤ WA §1931 income standard**
    * Eligibility:
      * Age 19–64
      * At least one dependent child under 18 in the household
      * Household MAGI ≤ WA §1931 income standard. HCA chart (2026): $511/mo single, $658 2-person, $820 3-person, $972 4-person, $1,127 5-person, $1,284 6-person, $1,471 7-person. Derived from WA's pre-ACA AFDC standard (~38–39% FPL for single); annually adjusted — reference HCA's published income-standards file rather than hardcoding.
      * WA resident (criterion 1); citizenship/qualifying immigration (criterion 10 data gap)
    * Routes to NON_EXPANSION_ADULT bucket ($445/month).
    * **Dual pathway:** Parents above the §1931 standard but ≤ 138% FPL qualify via ACA Adult Expansion (criterion 2), routing to EXPANSION_ADULT ($471/month). Combined binary screening ceiling for any parent: 138% FPL. (Distinct from **HCA Apple Health Expansion**, the state-funded coverage for non-qualifying immigrant adults — separate ticket.)
    * **Transitional Medical Assistance (Health Care Extension):** Parents enrolled in §1931 for at least 3 of last 6 months who lose eligibility due to increased income → up to 12 months extended coverage, automatic (no separate application). §1925 SSA / 42 U.S.C. § 1396r-6. ⚠️ Screener data gap: prior enrollment history not captured. Surface in program description.
    * 💡 **Screener improvement:** Add "Transitional Medical Assistance (Health Care Extension)" to the Current Household Benefits options in the screener. People already on TMA/HCE self-identify; people transitioning off §1931 Medicaid due to increased income can be surfaced the program as a benefit they may roll into automatically. Closes the prior-enrollment-history sub-gap without requiring a sensitive or complex new question.
    * Screener fields: `household_size`, `income (all types)`, `age` (parent 19–64; child <18), `relationship`
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(i)(I); 42 CFR § 435.110; WAC 182-505-0240; §1925 SSA (TMA); HCA Parents and Caretakers (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/parents-and-caretakers)
 4. **Income eligibility — Children (under 19): Free or premium-based coverage by MAGI tier; effective ceiling 317% FPL (312% nominal)**
    * Eligibility:
      * Under age 19
      * WA resident (criterion 1)
      * U.S. citizen or qualifying immigrant (criterion 10 data gap). Non-qualifying immigrant kids → Cover All Kids extension via MFB-789, separate ticket.
    * **Income tiers** (effective % FPL including standard 5% MAGI disregard; HCA 2026 single-person amounts shown for illustration):
      * **Free:** MAGI ≤ 215% effective (210% nominal). HCA: $2,860/mo single.
      * **Premium Tier 1** ($20/child, $40/family max): MAGI 215%–265% effective. HCA: up to $3,525/mo single. Uninsured children only (PEBB/SEBB exception).
      * **Premium Tier 2** ($30/child, $60/family max): MAGI 265%–317% effective (312% nominal ceiling per WAC 182-505-0215). HCA: up to $4,216/mo single. Uninsured children only (PEBB/SEBB exception).
    * Routes to CHILD bucket ($233/month).
    * **Continuous eligibility:** Children under 6 → continuous coverage through the month they turn 6, regardless of income changes. Children 6+ on free tier OR any age on premium tier → 12 months continuous eligibility. Federal authority: §1902(e)(12) SSA. ⚠️ Doesn't affect screening-time eligibility; surface as a benefit feature in the program description.
    * Screener fields: `household_size`, `income (all types)`, `age` (<19), `insurance.employer`/`insurance.private` (for premium-tier uninsured-only check — dev to confirm fields)
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(i)(III), (VII); 42 CFR § 435.118; 42 CFR § 457.310; WAC 182-505-0210; WAC 182-505-0215; RCW 74.09.470; HCA Apple Health for Kids (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/children)
 5. **Income eligibility — Pregnant Individuals: Household MAGI at or below 210% FPL (215% effective after standard 5% disregard)**
    * Eligibility:
      * Currently pregnant
      * Household MAGI ≤ 210% FPL nominal / 215% effective. HCA chart (2026, 215% amounts): $3,879/mo 2-person, $4,896 3-person, $5,913 4-person, $6,932 5-person, $7,949 6-person, $8,966 7-person. (Single column is n/a — a pregnant person is always at least a 2-person household.)
      * WA resident (criterion 1)
      * U.S. citizen, qualifying immigrant, or lawfully residing pregnant person under CHIPRA (WA elected). Non-qualifying immigrant pregnant women → state-funded extension, separate ticket.
    * Routes to NON_EXPANSION_ADULT bucket ($445/month).
    * **Household size includes unborn child(ren)** per WAC 182-506-0010. ⚠️ Screener data gap: `household_size` may understate for pregnant applicants.
    * **After-Pregnancy Coverage (APC):** 12 months postpartum coverage, automatic; income changes do not affect. Applicants who have recently given birth should apply even if not currently pregnant — coverage may extend back to delivery. Federal authority: Consolidated Appropriations Act, 2023 (Pub. L. 117-328) / 42 U.S.C. § 1902(e)(7)(A) (permanent federal requirement as of March 31, 2023; mandatory for all states).
    * 💡 **Screener improvement — unborn child:** Add `unbornChild` to the `relationship` enum on HouseholdMember so a pregnant person can add an "Unborn Child" the same way they'd add any other child. Closes the household-size undercount gap. Also benefits WIC.
    * 💡 **Screener improvement — retroactive APC:** Add a "Pregnant any time in the last 12 months" checkbox under Special Circumstances (alongside the existing `pregnant` checkbox). Closes the retroactive After-Pregnancy Coverage gap. Also benefits WIC postpartum, NFP, and other postpartum supports.
    * Screener fields: `household_size`, `income (all types)`, `pregnant`
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(i)(III)–(IV); 42 CFR § 435.116; §9812 ARPA; WAC 182-505-0115; WAC 182-506-0010; HCA Pregnant Individuals (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/pregnant-individuals)
 6. **Aged, Blind, or Disabled (ABD): SSI-related Medicaid for individuals aged 65+, blind, or disabled; countable income ≤ 74% FPL (SSI federal benefit rate)**
    * Eligibility (any one trigger):
      * Age 65+, OR
      * Disabled (per SSA definition), OR
      * Blind (per SSA definition)
    * Plus:
      * Income ≤ 74% FPL using **SSI methodology** (individual/couple amounts, not MAGI household size). HCA 2026: $994/mo individual, $1,491/mo couple.
      * Countable resources within asset limit (see criterion 7)
      * WA resident (criterion 1); citizenship/qualifying immigration (criterion 10)
    * Routes to AGED_DISABLED bucket. KFF 2023 WA per-capita: $1,921/month (Seniors, age 65+ trigger); $2,627/month (People with Disabilities, blind/disabled trigger).
    * **Income methodology:** SSI-based (with $20 general / $65 earned / half-earned disregards under WAC 182-512-0800 through -0880) — distinct from MAGI used in criteria 2–5. ⚠️ Screener doesn't apply precise SSI disregards; `income (all types)` is a screening approximation.
    * **Application portal:** washingtonconnection.org (not Healthplanfinder; serves SSI-related pathways). Worth surfacing in config `apply_button_link` for ABD-eligible users.
    * **HWD scope-out:** Working disabled with income above 74% FPL SSI standard → HWD (MFB-790, separate ticket).
    * Screener fields: `age` (≥65), `disabled`, `long_term_disability`, `visually_impaired`, `income (all types)`
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(ii); 42 U.S.C. § 1382 (SSI); WAC 182-512; HCA Aged, Blind, or Disabled (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/aged-blind-or-disabled)
 7. **Resource/Asset limit for SSI-related (non-MAGI) Medicaid: $2,000 for an individual, $3,000 for a couple**
    * The $3,000 couple limit applies when the applicant has a spouse in the household; otherwise the $2,000 individual limit applies. The calculator determines which limit to use via the `relationship` field — if any household member has `relationship: spouse`, the couple limit applies to the head of household. No asset test applies to MAGI-based pathways (criteria 2–5).
    * Screener fields:
      * `household_assets`
      * `relationship` (to distinguish individual vs. couple limit)
    * Source: WAC 182-512-0200 (controlling WA rule); 42 U.S.C. § 1382(a)(3) (background SSI statute)

 8. **Medically Needy (Spend-Down): Categorical eligibility for individuals above standard income or asset limits who incur qualifying medical expenses** ⚠️ *data gap*
    * Note: Individuals who meet a categorical Medicaid group (ABD, pregnant, children, parents/caretakers) but whose income or assets exceed the standard limits may still qualify through the medically needy pathway. They "spend down" excess income by incurring medical expenses until their remaining income falls to or below WA's medically needy income level, set annually by HCA. There is no separate asset limit for the medically needy pathway (asset rules follow the underlying categorical group). Common use case: ABD individuals with income above the SSI rate ($994/mo individual) who have large recurring medical bills.
    * ⚠️ Screener data gap: Cannot calculate spend-down amounts without detailed medical expense data not captured in the screener. Surface the medically needy pathway in the program description so high-income ABD and other near-eligible users know to apply.
    * 🔧 **Dev flag:** The screener's existing Healthcare expense field ("Medical Insurance Premium &/or Bills") already captures qualifying medical expenses (premiums + out-of-pocket bills) needed for spend-down calculation. Dev to confirm whether the calculator currently uses this field when evaluating the Medically Needy pathway — if not, wiring it in would close this gap without any screener change.
    * Screener fields: none
    * Source: 42 U.S.C. § 1396a(a)(10)(C); WAC 182-519; WAC 182-519-0100 (medically needy income levels)
    * Impact: Medium (meaningful population of near-poor ABD/senior individuals; fully unscreenable but important to surface)

 9. **Breast and Cervical Cancer Treatment Program (BCCTP): Categorical Medicaid for uninsured women screened through the CDC/WFBCC program** ⚠️ *data gap*
    * Note: Uninsured women who are screened for breast or cervical cancer through Washington's Free Breast and Cervical Cancer Screenings (WFBCC) program — the state's CDC National Breast and Cervical Cancer Early Detection Program (NBCCEDP) affiliate — and found to need diagnostic or treatment services qualify for full Apple Health coverage through the categorical BCCTP group. WA income limit: ≤200% FPL. No asset test. ⚠️ Immigration status: the federal BCCTP provision (42 U.S.C. § 1396a(a)(10)(A)(ii)(XVIII)) does not waive the standard Medicaid lawful-presence requirement — dev to confirm whether WA's BCCTP implementation covers any non-qualifying-immigrant women via state-funded supplement and, if so, provide the authority. Coverage is limited to treatment-related services.
    * ⚠️ Screener data gap: Cannot determine whether an applicant has been screened through the CDC/WFBCC program. Surface BCCTP in the program description so eligible women self-identify and contact HCA.
    * 💡 **Screener improvement:** Add "Breast and Cervical Cancer Treatment Program (BCCTP) / Washington Free Breast and Cervical Cancer Screenings (WFBCC)" to the Current Household Benefits options. Already-enrolled women self-identify, preventing the screener from surfacing Apple Health as a new benefit to someone already on BCCTP for the same coverage. The program description handles awareness for newly-screened women who haven't yet enrolled.
    * Screener fields: none
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(ii)(XVIII); WAC 182-505-0217; HCA Free Breast and Cervical Cancer Screenings (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/breast-and-cervical-cancer-treatment)
    * Impact: Low (narrow — requires prior CDC-program screening; fully unscreenable but important to surface for the population it serves)

10. **U.S. citizenship or qualifying immigration status**
    * **Comprehensive Apple Health adult pathways (criteria 2, 3, 6):** `citizen`, `gc_5plus`, `refugee`, `otherWithWorkPermission`. `gc_5less` is subject to the federally-mandated 5-year bar (8 U.S.C. § 1613) for adult pathways.
    * **Pregnant (criterion 5) and kids (criterion 4):** Above PLUS `gc_5less` — WA elected the CHIPRA option to waive the 5-year bar for lawfully residing pregnant individuals and children (8 U.S.C. § 1612(b)).
    * **Alien Emergency Medical (AEM) — narrow federal exception:** Federal Medicaid emergency-only coverage (42 U.S.C. § 1396b(v)(3); WAC 182-507) for `non_citizen` and `gc_5less` adults with a qualifying medical emergency. Applicant must still meet an Apple Health pathway's income/categorical rules. ⚠️ Not directly screenable (the screener cannot determine current emergency status); surface AEM in the program description for `non_citizen` / `gc_5less` adult users.
    * **Granular detail not captured (minor data gap):** specific exempt subcategories beyond the 6 categorical values (trafficking victims, COFA migrants, sponsor deeming).
    * **Config:** `legal_status_required` lists all 6 values (`non_citizen` justified by AEM; `gc_5less` justified by CHIPRA + AEM). Calculator routes each person to the correct pathway.
    * Screener fields: per-member `legal_status`
    * Source: 8 U.S.C. § 1611, § 1612, § 1613; 42 U.S.C. § 1396b(v); 42 CFR § 435.406; WAC 182-503-0535; WAC 182-507 (AEM); HCA Noncitizens (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/noncitizens)

11. **Must not be an inmate of a public institution (except as an inpatient in a medical institution)** ⚠️ *data gap*
    * Note: Federal law prohibits Medicaid payment for services to inmates of public institutions (jails, prisons, state hospitals) except for inpatient hospital services. The screener has no field for incarceration status. Note: WA has received a Section 1115 waiver for pre-release Medicaid services for incarcerated individuals transitioning back to the community.
    * Screener fields: none
    * Source: 42 U.S.C. § 1396d(a)(31); WAC 182-503-0505
    * Impact: Low

12. **Tax filing status and relationships for MAGI household composition** ⚠️ *data gap*
    * Note: MAGI household composition depends on tax filing status (filer, dependent, non-filer) and specific relationship rules. While the screener has `household_size` and `last_tax_filing_year`, it doesn't capture the detailed tax filing relationships needed for precise MAGI household determination. The screener's `household_size` is used as a reasonable approximation.
    * 💡 **Screener improvement:** Add optional `tax_filing_status` per HouseholdMember (values: `filer`, `jointFiler`, `dependent`, `nonFiler`) to the Basic Information section. Optional — calculator falls back to the existing `household_size` approximation when blank, so users who don't know or prefer to skip aren't blocked. For users who do provide it, closes the MAGI household composition gap — currently the screener can miscount households with complex filing arrangements (e.g., a 22-year-old claimed as a dependent by over-income parents, but who files separately and qualifies independently). Also benefits all other MAGI-based programs: ACA Medicaid expansion, CHIP, APTC/CSR marketplace eligibility.
    * Screener fields: none
    * Source: 42 CFR § 435.603(f); WAC 182-506-0010
    * Impact: Medium

13. **Foster Care, Adoption Support, and Foster Care Alumni: Federal Medicaid categorical pathways; no income test**
    * Federal categorical eligibility (any one trigger):
      * **Foster Care:** Children ≤20 in licensed foster care or relative placement (via DCYF or tribal authority); extended foster care 18–21 by self-enrollment.
      * **Adoption Support:** Children ≤21 receiving title IV-E adoption assistance payments.
      * **Foster Care Alumni:** Adults aged 18 through the end of the month they turn 26, who were in foster care AND on Medicaid on their 18th birthday (in any U.S. state). WA residency required; no income/household/marital test.
    * Auto-enrolled in Apple Health Core Connections (AHCC), a statewide managed care plan administered by Coordinated Care.
    * Routes to CHILD bucket ($233/month) for those ≤18. For alumni 19–26: dev to confirm PE handling under §1396a(a)(10)(A)(i)(IX) (continued categorical Medicaid eligibility for former foster care youth).
    * Screener fields: per-member `relationship` (foster/adopted child values — dev to confirm), `income_streams.type` (for adoption assistance — dev to confirm), `age` (≤20 for current placement; 18–26 for alumni).
    * ⚠️ **Sub-data-gap (Alumni only):** screener doesn't capture prior foster care + Medicaid history at age 18; surface the alumni pathway in the program description so eligible users self-identify.
    * 💡 **Screener improvement — alumni:** Add `was_in_foster_care` (Yes/No) under Special Circumstances. The existing `age` field already covers the 18–26 eligibility window as a proxy; this field captures the foster care history fact. Closes the Foster Care Alumni sub-gap. Also benefits Chafee Foster Care Independence Program, Education and Training Vouchers (ETV), and state tuition waivers (each with their own age windows, all resolvable via `age`).
    * 💡 **Screener improvement — adoption support:** Add `adoption_assistance` to the `income_streams.type` enum (currently captured under "other"). Closes the Adoption Support identification gap. Also benefits adoption tax credits.
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(i)(I), (IX); 42 CFR § 435.145, § 435.150; title IV-E SSA; WAC 182-505-0211 (foster care); WAC 182-505-0220 (adoption support); HCA Foster Care (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/foster-care)

14. **Long-Term Services and Supports (LTSS) and Hospice** ⚠️ *partial data gap*
    * **LTSS:** Federal Medicaid for individuals needing institutional care (nursing facility, alternate living facility) or home/community-based services (HCS, DDA, Community First Choice, HCBS waivers). Different, higher financial eligibility standards apply: institutional LTSS uses the federal **Special Income Level** up to 300% SSI federal benefit rate (~$2,982/mo at 2026 SSI individual rate); HCBS waivers use pathway-specific financial rules under 42 CFR § 435.217. Standard ABD asset limits and SSI-rate income limits do not apply to LTSS pathways.
    * **Hospice:** Benefit category for terminally ill individuals (6-month prognosis with physician certification) — covered under most Apple Health programs. A separate Hospice Program (higher income/resource standards) exists for those not on Apple Health.
    * ⚠️ Screener data gap: Functional assessment for LTC level of care, and physician hospice certification, are not screenable. Surface LTSS and hospice options in the program description so elderly / disabled / terminally ill users self-identify.
    * 💡 **Screener improvement:** Add `needs_long_term_care` (Yes/No) checkbox under Special Circumstances. A Yes answer can trigger a description callout directing LTSS-eligible users to washingtonconnection.org and DSHS Home and Community Services. Also benefits Medicaid HCBS waivers and ADRC referrals.
    * **Application portal:** washingtonconnection.org / DSHS Home and Community Services office (not Healthplanfinder).
    * Routes to AGED_DISABLED bucket for most LTSS recipients.
    * Screener fields: none
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(ii); §1915 SSA (HCBS waivers); §1924 SSA (institutional spousal impoverishment); WAC 182-513 (LTC institutional); WAC 182-515 (HCBS waivers); HCA Long-term care and hospice (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/long-term-care-and-hospice)
    * Impact: Medium (federally-mandated pathway; largely unscreenable but surfaceable in description)

## Priority Criteria

N/A — Apple Health (Medicaid) is a federal entitlement program. There is no waitlist, lottery, or priority queue: all applicants who meet the eligibility criteria at the time of application must be enrolled. No priority ordering of criteria is needed.

## Benefit Value

Apple Health is health insurance coverage. Per MFB convention, insurance benefits are valued by total program spending divided by the number of beneficiaries, producing an average per-beneficiary cost.

**Methodology:** For each eligible household member, the calculator looks up the per-enrollee spending figure for the eligibility pathway under which the member qualifies, divides by 12 to get a monthly value, and sums across all eligible members in the household. Ineligible members contribute $0.

**Per-pathway monthly values** (from KFF State Health Facts, 2023 — Medicaid Spending Per Full-Benefit Enrollee, Washington):

| Eligibility pathway | KFF category | Annual | Monthly |
|---|---|---|---|
| Adults 19-64 (ACA Expansion at 138% FPL) | ACA Expansion Adults | $5,652 | $471 |
| Parents/Caretaker (§1931 standard, lower-income parents) | Adults (NON_EXPANSION_ADULT) | $5,340 | $445 |
| Pregnant (215% FPL effective) | Adults | $5,340 | $445 |
| Children 0-18 (up to 317% FPL effective; includes free and premium tiers) | Children | $2,796 | $233 |
| Aged 65+ (ABD pathway) | Seniors | $23,052 | $1,921 |
| Blind/Disabled (ABD pathway) | People with Disabilities | $31,524 | $2,627 |

**Sources:**
* KFF State Health Facts (2023) — Medicaid Spending Per Full-Benefit Enrollee, Washington: https://www.kff.org/statedata/
* Underlying data: CMS Medicaid Financial Management Reports (CMS-64)
* WA HCA Finance and Rates: https://www.hca.wa.gov/about-hca/finance-and-rates

⚠️ **Reviewer note:** KFF 2023 figures are point-in-time. Refresh these values when KFF publishes more recent data or when WA HCA publishes updated per-enrollee spending. If MFB later adopts a different methodology for valuing insurance benefits (e.g., premium savings vs. marketplace plan), update this section and the validation JSON to match.

## Implementation Coverage

* ✅ Evaluable criteria: 9
* ⚠️  Data gaps: 5

The 9 evaluable criteria cover residency, income thresholds across all major Medicaid coverage groups (adults 138% FPL, children 317% effective, pregnant 215% effective, ABD 74% SSI rate), age, disability, pregnancy, asset limits, categorical immigration status, and Foster Care / Adoption Support pathways. The 5 data gaps (criteria 8, 9, 11, 12, 14) are documented per-criterion above, with impact ratings. HWD (MFB-790) and Apple Health Expansion are tracked under separate tickets.

## Screener Improvement Opportunities

The following changes to the MFB screener would close data gaps identified in this spec. Each is flagged inline under its relevant criterion above. None are required for the initial implementation; all would improve accuracy and/or benefit multiple programs beyond Apple Health.

| # | Suggested change | Closes | Also benefits |
|---|---|---|---|
| 1 | Add "Transitional Medical Assistance (Health Care Extension)" to Current Household Benefits options | Criterion 3 sub-gap — TMA/HCE prior enrollment history not screenable | — |
| 2 | Add `unbornChild` to `relationship` enum | Criterion 5 — unborn child household size undercount | WIC |
| 3 | Add "Pregnant any time in last 12 months" checkbox (Special Circumstances) | Criterion 5 — retroactive APC gap | WIC postpartum, NFP, postpartum supports |
| 4 | Add "BCCTP / WFBCC program" to Current Household Benefits options | Criterion 9 — already-enrolled BCCTP women can self-identify; program description handles newly-screened women | — |
| 5 | Add optional `tax_filing_status` per HouseholdMember (`filer`, `jointFiler`, `dependent`, `nonFiler`) — Basic Information section; falls back to `household_size` when blank | Criterion 12 — MAGI household composition miscounts | ACA Medicaid expansion, CHIP, APTC/CSR marketplace |
| 6 | Add `was_in_foster_care` (Yes/No) checkbox (Special Circumstances) — age field covers the 18–26 window as proxy | Criterion 13 sub-gap — Foster Care Alumni identification | Chafee, ETV, state tuition waivers |
| 7 | Add `adoption_assistance` to `income_streams.type` enum | Criterion 13 — Adoption Support identification | Adoption tax credits |
| 8 | Add `needs_long_term_care` (Yes/No) checkbox (Special Circumstances) | Criterion 14 — LTSS/hospice routing | Medicaid HCBS waivers, ADRC referrals |


## Test Scenarios

*All scenarios use 2026 FPL values (matching the config's `year` field). Scenarios 1, 3, and 7 below are reflected in the validation JSON (`wa_apple_health.json`) as the validation suite's core 3 (golden path, primary exclusion, edge case). All other scenarios are documented here for broader QA coverage and traceability.*

### Scenario 1: Low-Income Single Adult Eligible (Golden Path) ✓ in validation JSON

**What we're checking**: A single adult aged 30 with very low income qualifies under ACA Adult Expansion (criterion 2: 19–64 at ≤138% FPL).
**Expected**: Eligible, value $5,652 annual (1 EXPANSION_ADULT × $5,652/yr; displays as $471/month with `value_format: null`).
**Steps**:
* Location: ZIP `98101`, county `King County`
* Household size: 1
* Person 1: Birth month/year `June 1995` (age 30), `headOfHousehold`, not pregnant, not disabled, US citizen, wages: $1,200/month, insurance: none
**Why this matters**: The most common Apple Health eligibility pathway. The "happy path" regression test for the calculator's core use case.

---

### Scenario 2: Single Adult at 138% FPL Boundary

**What we're checking**: Adult right at the 138% FPL threshold ($1,835/month for HH1 at 2026 FPL) is still eligible (criterion 2 boundary condition).
**Expected**: Eligible, value $5,652 annual (1 EXPANSION_ADULT × $5,652/yr; displays as $471/month with `value_format: null`).
**Steps**:
* Location: ZIP `98801`, county `Chelan County`
* Household size: 1
* Person 1: Birth month/year `June 1987` (age 38), `headOfHousehold`, not pregnant, not disabled, US citizen, wages: $1,830/month (just under $1,835), insurance: none
**Why this matters**: Tests the calculator's "≤" comparison at the maximum allowable income for adult expansion. A common edge case at portal-displayed thresholds.

---

### Scenario 3: Single Adult Above 138% FPL Ineligible ✓ in validation JSON

**What we're checking**: Adult with income above the 138% FPL threshold ($1,835 for HH1) is correctly determined ineligible (criterion 2 upper bound).
**Expected**: Not eligible (no value).
**Steps**:
* Location: ZIP `98103`, county `King County`
* Household size: 1
* Person 1: Birth month/year `June 1986` (age 39), `headOfHousehold`, not pregnant, not disabled, US citizen, wages: $1,900/month (above $1,835), insurance: none
**Why this matters**: Validates the upper income boundary for adult expansion. Applicants over this threshold should be routed to marketplace coverage instead.

---

### Scenario 4: Adult Entitled to Medicare — Ineligible for Expansion

**What we're checking**: Adult under 65 with Medicare entitlement is excluded from ACA Adult Expansion per 42 CFR § 435.119(b)(3), even with qualifying income (criterion 2 Medicare exclusion sub-rule). With no disability flag and not 65+, they also don't qualify under ABD.
**Expected**: Not eligible (no value).
**Steps**:
* Location: ZIP `98103`, county `King County`
* Household size: 1
* Person 1: Birth month/year `April 1971` (age 55), `headOfHousehold`, not pregnant, no disability flag, US citizen, wages: $1,200/month, **insurance: medicare** (entitled via SSDI / ESRD)
**Why this matters**: Validates the federally-uniform Medicare exclusion for ACA expansion. Medicare-entitled adults must qualify via ABD (if 65+ or disabled) or Medicare Savings Programs separately. Tests the routing logic that prevents double coverage.

---

### Scenario 5: Parent at §1931 Income — NON_EXPANSION_ADULT Routing

**What we're checking**: Parent with a dependent child at income below WA's §1931 standard ($658/mo HH2 at 2026) qualifies under the §1931 Parent/Caretaker pathway, routing to NON_EXPANSION_ADULT (criterion 3).
**Expected**: Eligible — parent at $5,340 annual (NON_EXPANSION_ADULT × $5,340/yr; displays as $445/month with `value_format: null`); child at $2,796 annual (CHILD × $2,796/yr; displays as $233/month); household total displays as **$678/month**.
**Steps**:
* Location: ZIP `98101`, county `King County`
* Household size: 2
* Person 1: Birth month/year `May 1995` (age 30), `headOfHousehold`, not pregnant, not disabled, US citizen, wages: $500/month (under $658 §1931 HH2), insurance: none
* Person 2: Birth month/year `January 2017` (age 9), relationship: `child`, no income, insurance: none
**Why this matters**: Tests the §1931 dual-pathway routing — parents at lower incomes route to NON_EXPANSION_ADULT ($445/mo per-capita) vs ACA expansion's EXPANSION_ADULT ($471/mo). Critical for correct dollar-value routing in mixed households.

---

### Scenario 6: Pregnant Individual at 215% Effective FPL

**What we're checking**: Pregnant person with income under the 215% FPL effective threshold ($3,879/mo HH2 at 2026 FPL) qualifies for Apple Health (criterion 5). Spouse at same income remains ineligible at 138% threshold ($2,490 HH2).
**Expected**: Eligible (pregnant person only); value $5,340 annual (1 NON_EXPANSION_ADULT × $5,340/yr; displays as $445/month with `value_format: null`); spouse ineligible and contributes $0.
**Steps**:
* Location: ZIP `98103`, county `King County`
* Household size: 2 (per WAC 182-506-0010 the unborn child should also count — using `household_size` approximation per criterion 5 data-gap note)
* Person 1: Birth month/year `June 1996` (age 29), `headOfHousehold`, **pregnant: yes**, US citizen, wages: $3,800/month, insurance: none
* Person 2: Birth month/year `September 1994` (age 31), relationship: `spouse`, not pregnant, US citizen, no income, insurance: none
**Why this matters**: Tests the pregnant pathway's higher income threshold (210% nominal / 215% effective) and the per-member eligibility independence (pregnant qualifies, spouse doesn't). Documents the unborn-child household-size approximation.

---

### Scenario 7: Mixed Household — Eligible Child, Ineligible Parents ✓ in validation JSON

**What we're checking**: In a multi-member household, eligibility is independent per member. Parents over 138% FPL ($3,142 HH3) but child under 215% effective free tier ($4,896 HH3) for kids (criterion 4 free tier).
**Expected**: Eligible (child only); value $2,796 annual (1 CHILD × $2,796/yr; displays as $233/month with `value_format: null`); parents ineligible and contribute $0.
**Steps**:
* Location: ZIP `98103`, county `King County`
* Household size: 3
* Person 1: Birth month/year `June 1990` (age 35), `headOfHousehold`, not pregnant, not disabled, US citizen, wages: $4,800/month (above 138% HH3; under 215% HH3 kids free tier), insurance: none
* Person 2: Birth month/year `September 1992` (age 33), relationship: `spouse`, not pregnant, US citizen, no income, insurance: none
* Person 3: Birth month/year `January 2019` (age 7), relationship: `child`, no income, insurance: none
**Why this matters**: Tests per-member eligibility independence in the most common multi-member household shape. Calculator must route only the child to the CHILD bucket while marking parents ineligible.

---

### Scenario 8: Child at Premium Tier

**What we're checking**: Child in household with income between 215% and 317% effective FPL qualifies for the premium tier of Apple Health for Kids (criterion 4). Premium tier requires the child to be uninsured.
**Expected**: Eligible (child only); value $2,796 annual (1 CHILD × $2,796/yr; displays as $233/month). Family pays $20/child/month premium (Tier 1).
**Steps**:
* Location: ZIP `98101`, county `King County`
* Household size: 3
* Person 1: Birth month/year `June 1990` (age 35), `headOfHousehold`, US citizen, wages: $6,000/month (above $4,896 free tier; under $7,218 premium tier ceiling HH3), insurance: employer
* Person 2: Birth month/year `September 1992` (age 33), `spouse`, US citizen, no income, insurance: employer
* Person 3: Birth month/year `January 2019` (age 7), `child`, no income, **insurance: none** (uninsured — required for premium tier)
**Why this matters**: Tests the premium tier of Apple Health for Kids. The uninsured-only requirement (HCA exception for PEBB/SEBB-employee kids aside) ensures parents with employer coverage for their kids don't double-dip. Distinguishes premium tier routing from free tier.

---

### Scenario 9: ABD Pathway — Eligible at 65+ with Assets Under Limit

**What we're checking**: Aged 65+ individual at ≤74% FPL with assets under $2,000 individual limit qualifies via SSI-related Medicaid (criterion 6).
**Expected**: Eligible, value $23,052 annual (1 Seniors × $23,052/yr; displays as $1,921/month with `value_format: null`).
**Steps**:
* Location: ZIP `98101`, county `King County`
* Household size: 1
* Person 1: Birth month/year `April 1961` (age 65), `headOfHousehold`, not pregnant, no disability flag (qualifies via 65+ trigger alone), US citizen, Social Security retirement income: $900/month (under $994 SSI individual rate), assets: $1,800
**Why this matters**: Tests the aged 65+ trigger of ABD (criterion 6) and the asset limit (criterion 7) together. SSI methodology (individual amount, not MAGI household size) is distinct from criteria 2–5. The $1,921 Seniors per-capita differs from the $2,627 People with Disabilities value — confirms the calculator routes correctly by trigger type.

---

### Scenario 10: ABD Pathway — Ineligible Due to Assets Over Limit

**What we're checking**: Aged 65+ individual with low income but assets above the $2,000 individual limit is ineligible for ABD (criterion 7).
**Expected**: Not eligible (no value).
**Steps**:
* Location: ZIP `98101`, county `King County`
* Household size: 1
* Person 1: Birth month/year `April 1961` (age 65), `headOfHousehold`, US citizen, Social Security retirement income: $900/month, assets: $5,000 (above $2,000 limit)
**Why this matters**: Validates that the asset limit blocks ABD eligibility even with qualifying age and income. Applicants over the asset limit may instead be eligible via Medicaid spend-down (medically needy) — surfaced in description.

---

### Scenario 11: Foster Care Child via `relationship: fosterChild`

**What we're checking**: Child placed in foster care via `relationship: fosterChild` is eligible under the federal Foster Care categorical pathway regardless of household income (criterion 13).
**Expected**: Eligible (foster child only); value $2,796 annual (1 CHILD × $2,796/yr; displays as $233/month with `value_format: null`); foster parent ineligible at this income.
**Steps**:
* Location: ZIP `98103`, county `King County`
* Household size: 2
* Person 1: Birth month/year `June 1980` (age 45), `headOfHousehold`, US citizen, wages: $5,000/month (above 138% HH2 of $2,490; ineligible under adult expansion), insurance: employer
* Person 2: Birth month/year `March 2017` (age 9), **relationship: `fosterChild`**, no income, insurance: none
**Why this matters**: Tests the federal Foster Care categorical pathway, which has no income test (children in foster care qualify regardless of foster-family income). Validates that `relationship: fosterChild` triggers the categorical override of standard income rules. **Note:** Foster Care Alumni (18–26 with prior foster + Medicaid history at age 18) is not separately testable here because the screener doesn't capture historical foster placement; surfaced in the program description instead.

---

## Source Documentation

* https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/eligibility-overview
* https://www.hca.wa.gov/assets/free-or-low-cost/22-315.pdf
* https://www.kff.org/statedata/
