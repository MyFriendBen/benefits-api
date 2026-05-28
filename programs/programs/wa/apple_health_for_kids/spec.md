# Program Details

* **Program**: Apple Health for Kids
* **State**: WA
* **White Label**: wa
* **Research Date**: 2026-04-14
* **Review Date**: 2026-05-24

## Eligibility Criteria

 1. **Household includes at least one child under age 19**
    * Screener fields:
      * `birth_year + birth_month (HouseholdMember)`
      * `relationship (HouseholdMember)`
      * `household_size`
    * Note: Apple Health for Kids is a per-child eligibility program — each child in the household is evaluated independently. The screener evaluates per-member age and routes eligible children to this program.
    * **Deemed newborn pathway (WAC 182-505-0210(2)(a))** ⚠️ *data gap* — A separate subsection of WAC 182-505-0210 provides that a newborn under age 1 is automatically eligible for categorically needy (CN) coverage if the birth parent was enrolled in Apple Health (or CHIP) on the date of delivery, including via a retroactive eligibility determination. This automatic coverage runs through the end of the month the infant turns 1 and requires no separate application or income determination. **Calculator handling (inclusivity assumption):** skip this check — the screener cannot capture "was birth parent enrolled in Apple Health at time of delivery." In practice, families using this pathway are likely already enrolled automatically and would not need the screener to surface the benefit. The income-based pathway in criterion 2 is the relevant screening path for all other infants.
    * **Out-of-scope parallel pathways (WAC 182-505-0210(2)(b)–(c))** — Two additional deemed eligibility groups exist in the same WAC section but are handled by separate program entries, not this MAGI-based spec: (1) SSI-eligible children → automatically eligible for CN coverage under WAC 182-510-0001, no application required; (2) children in foster care or receiving subsidized adoption services (age ≤20) → eligible for CN coverage under WAC 182-505-0211. Neither pathway uses MAGI income testing. The wa_apple_health_for_kids calculator should not implement these; they require their own dedicated calculator entries. Noting here so the dev does not inadvertently exclude children arriving via these pathways from broader Apple Health coverage.
    * Source: WAC 182-505-0210; WAC 182-505-0210(2)(a) (deemed newborn / categorically needy); WAC 182-510-0001 (SSI-eligible children); WAC 182-505-0211 (foster care / adoption support); 42 CFR § 435.118; RCW 74.09.470; HCA Apple Health for Kids (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/children)
 2. **Income eligibility — Children by MAGI tier; effective ceiling 317% FPL (312% nominal)**
    * Eligibility:
      * Under age 19 (criterion 1)
      * WA resident (criterion 3)
      * Citizenship or qualifying immigration — CHIPRA waives the 5-year bar for kids and the Cover All Kids state extension covers non-qualifying immigrant kids (criterion 5)
    * **Income tiers** (effective % FPL including standard 5% MAGI disregard; HCA 2026 single-person amounts shown for illustration — refresh annually from HCA Income Standards):
      * **Free, all children under 19:** MAGI ≤ 215% effective (210% nominal). HCA: up to $2,860/mo single.
      * **Premium Tier 1** ($20/child/mo; premiums charged for a maximum of 2 children per household): all children under 19, MAGI 215%–265% effective (210%–260% nominal per WAC 182-505-0215). HCA: up to $3,525/mo single. Children without other creditable group health coverage only (see criterion 6). **PEBB/SEBB exception:** children eligible for PEBB or SEBB coverage through a family member's employment with a WA state agency or school district ARE eligible for this tier despite having PEBB/SEBB available (WAC 182-505-0215 explicit carve-out). **AI/AN premium exemption:** American Indian or Alaska Native children are exempt from the monthly premium requirement (WAC 182-505-0215). ⚠️ Both the PEBB/SEBB distinction and AI/AN status are screener data gaps — see criterion 6 for PEBB/SEBB; AI/AN exemption is documented in Screener Improvement Suggestion #9.
      * **Premium Tier 2** ($30/child/mo; max 2 children charged): all children under 19, MAGI 265%–317% effective (260%–312% nominal per WAC 182-505-0215). HCA: up to $4,216/mo single. Same PEBB/SEBB exception and AI/AN exemption apply.
    * Routes to CHILD bucket ($233/month per eligible child — see Benefit Value).
    * **Continuous eligibility:** Children under 6 → coverage continues through the month they turn 6 regardless of income changes (free or premium tier; WAC 182-504-0015(6), as amended eff. January 8, 2025 to extend this to the premium tier). Children 6+ → 12 months continuous eligibility (any tier). Federal authority: §1902(e)(12) SSA. ⚠️ Doesn't affect screening-time eligibility; surface as a benefit feature in the program description.
    * **MAGI methodology approximation:** The screener uses `household_size` + gross income from `income_streams` to approximate MAGI but does not precisely replicate tax-filing-based household composition or specific MAGI adjustments (student loan interest, IRA contributions, alimony, etc.). For screening purposes, gross income is a reasonable proxy; actual eligibility determinations at application may differ slightly at the margins. Authority: 42 CFR § 435.603(f); WAC 182-506-0010; WAC 182-509-0300.
    * **Unborn child household size** ⚠️ *data gap* — WAC 182-506-0010 requires that household size include unborn children for MAGI-based eligibility calculations. The screener has no `unbornChild` relationship type, so a pregnant adult cannot add an unborn child as a household member. This understates household size, which overstates the effective FPL percentage — most impactful at tier boundaries where the correct MAGI household size would keep a family in a lower premium tier or under the income ceiling. **Calculator handling (inclusivity assumption):** skip this check — the screener cannot capture pregnancy in a way that maps to MAGI household composition. **Suggested improvement:** Add `unbornChild` to the `relationship` enum on HouseholdMember so pregnant adults can add an unborn child the same way as any other household member (Screener Improvement Suggestion #4). Screener fields: `none`.
    * Screener fields: `household_size`, `income (all IncomeStream records)`, `birth_year + birth_month` (<19). Note: `insurance.employer` / `insurance.private` on the child are NOT used for premium-tier gating — criterion 6 is now a data gap (see below); inclusivity assumption applies to all employer-insured children at screening time.
    * Source: 42 U.S.C. § 1396a(a)(10)(A)(i)(III), (VII); 42 CFR § 435.118; 42 CFR § 457.310; WAC 182-505-0210; WAC 182-505-0215; WAC 182-505-0225 (premium dollar amounts); RCW 74.09.470; HCA Apple Health for Kids — eligibility & coverage overview (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/children); HCA Apple Health for Kids with and without premiums (https://www.hca.wa.gov/free-or-low-cost-health-care/i-help-others-apply-and-access-apple-health/apple-health-kids-and-without-premiums); Healthplanfinder Apple Health for Kids with premiums (https://www.wahealthplanfinder.org/us/en/insurance-payment-options/washington-apple-health-for-kids-with-premiums.html); HCA Income Standards (https://www.hca.wa.gov/assets/free-or-low-cost/income-standards.pdf)
 3. **Must reside in Washington state**
    * Screener fields:
      * `zipcode`
      * `county`
    * Source: WAC 182-503-0520 (residency); WAC 182-503 chapter root (https://app.leg.wa.gov/wac/default.aspx?cite=182-503); HCA Apple Health Eligibility Manual (https://www.hca.wa.gov/free-or-low-cost-health-care/i-help-others-apply-and-access-apple-health/apple-health-eligibility-manual-overview)
 4. **No asset/resource test (MAGI rules apply)**
    * Screener fields: `none` — `household_assets` is collected but deliberately ignored for Kids eligibility
    * Note: Apple Health for Kids follows MAGI-based eligibility methodology, which has no resource/asset test (distinct from SSI-related Apple Health pathways like ABD). The calculator must NOT gate Kids eligibility on `household_assets`.
    * Source: 42 CFR § 435.603(g); WAC 182-505-0100; WAC 182-509-0300
 5. **Citizenship or qualifying immigration status (effectively waived for children in WA via Cover All Kids)** ⚠️ *data gap*
    * Screener fields: `none` — per the canonical MyFriendBen screener field reference, citizenship / immigration status is not captured by the screener (no `legal_status` field exists)
    * Note: Federally-funded Apple Health for Kids requires U.S. citizenship or qualifying immigration status. WA elected the CHIPRA option to waive the federal 5-year bar for lawfully residing children (8 U.S.C. § 1612(b)(3)). Washington additionally passed the Cover All Kids Act (RCW 74.09.875), which extends Apple Health coverage to all children under 19 regardless of immigration status using state funds (effective 2024). **Calculator handling (inclusivity assumption):** skip this check at screening time. Under Cover All Kids, every child in WA qualifies regardless of immigration status, so the screener's lack of a citizenship field has no practical impact on eligibility outcomes for Kids. The funding source (federal vs. state-funded via Cover All Kids) may differ but the binary eligibility outcome is the same. **SSN handling:** Federally-funded coverage requires an SSN (or applying for one — WAC 182-503-0515; 42 CFR § 435.910). Children without SSNs may still qualify under the Cover All Kids state-funded extension. The SSN requirement is a documentation step (handled via `documents` and the program `description`), not a screener-time eligibility check.
    * **Suggested improvement:** None recommended. Per `find-screener-fields.md` Step 4 guidance, immigration/citizenship status should NOT be added as a screener field — it's sensitive PII, the inclusivity assumption combined with Cover All Kids handles WA Kids correctly, and funding-source attribution (federal vs. state-funded) can be determined at the application stage rather than at screening.
    * Source: 8 U.S.C. § 1612(b); WAC 182-503-0535; RCW 74.09.875 (Cover All Kids Act, effective 2024); HCA Apple Health for Kids (https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/children)
    * Impact: Low
 6. **Child must not be eligible for or enrolled in other creditable group health coverage (premium tier only)** ⚠️ *data gap*
    * Screener fields: `none` — the screener captures `insurance.employer` and `insurance.private` per-member, but cannot distinguish PEBB/SEBB employer coverage (which is exempt) from non-PEBB/SEBB employer coverage (which disqualifies). See note.
    * Note: WAC 182-505-0215 establishes a two-part rule for the CHIP-funded premium tier:
      * **General rule:** A child is NOT eligible for the premium tier if they have creditable health insurance coverage as defined in WAC 182-500-0020 (i.e., qualifying group health coverage through an employer or private plan).
      * **PEBB/SEBB exception (WAC 182-505-0215 explicit carve-out):** A child WITH creditable coverage MAY still be eligible for the premium tier if they are eligible for PEBB coverage through a family member's employment with a WA state agency, university, community college, or technical college — OR eligible for SEBB coverage through a family member's employment with a WA school district, charter school, or educational service district. These families can access Apple Health for Kids with premiums even when PEBB/SEBB is available, because WA recognizes that state and school employee coverage may be unaffordable for families in the premium-tier income range.
      * **Coverage start date:** Coverage under the premium tier begins no sooner than the month after any prior creditable coverage ends (WAC 182-505-0215 enrollment timing rule). This is an administrative timing rule, not an eligibility criterion.
      * **This restriction applies to the premium tier only.** Children on the free tier (≤210% nominal FPL) remain eligible regardless of other coverage.
    * **Calculator handling (inclusivity assumption):** The screener captures `child.insurance.employer` and `child.insurance.private` per-member but cannot determine whether the employer coverage is PEBB/SEBB (exempt) or non-PEBB/SEBB (disqualifying). Since the PEBB/SEBB population is a significant subset of employer-insured families in WA (state and school employees), applying a blanket `employer = true → ineligible` rule would incorrectly exclude an entire exempt class. **Treat all children as potentially eligible for the premium tier at screening time regardless of insurance.employer status.** HCA verifies at application whether the specific coverage is creditable and non-PEBB/SEBB. The program description should note that children with employer coverage may still qualify and to apply to find out.
    * **Suggested improvement:** A new screener question — "Does your employer work for a Washington state agency, university, community college, school district, charter school, or educational service district?" — would allow the screener to distinguish PEBB/SEBB families (eligible) from other employer-insured families (ineligible for premium tier). This is a targeted, non-sensitive question that could close this gap and sharpen premium-tier eligibility signals for a large WA employer population. However, per `find-screener-fields.md` Step 4 guidance, this should be surfaced to screener PMs as a potential improvement, not implemented unilaterally.
    * Source: WAC 182-505-0215; WAC 182-500-0020 (creditable coverage definition); 42 CFR § 457.310(b)(2)
    * Impact: Medium — PEBB/SEBB families are a non-trivial share of premium-tier income households in WA; the old logic would have incorrectly excluded them from the screener recommendation.
 7. **Children in public institutions have restricted (not full) Apple Health eligibility** ⚠️ *data gap*
    * Screener fields: `none`
    * Note: WAC 182-505-0210(7) (amended effective July 1, 2025) establishes two institution-specific restrictions:
      * **Incarceration (WAC 182-505-0210(7)(b)):** A child incarcerated in a public institution is eligible only for (i) inpatient hospital services and (ii) pre- and post-release reentry services. This is a restriction, not a full exclusion — incarcerated children retain limited Apple Health coverage. The reentry services provision was added in the July 2025 amendment as part of HCA's reentry services project. Federal authority: 42 CFR § 435.1010; 42 U.S.C. § 1396d(a)(31).
      * **Institution for mental disease (IMD) (WAC 182-505-0210(7)(a)):** A child residing in an IMD (as defined in WAC 182-500-0050) is NOT eligible for inpatient hospital services, unless unconditionally discharged from the IMD before receiving the services. This is the federal IMD exclusion applied at the state level.
    * **Calculator handling (inclusivity assumption):** skip both checks at screening time — institutional residence is sensitive PII, very rare for children, and verified at application. The inclusivity assumption is safe.
    * **Suggested improvement:** None recommended. Per `find-screener-fields.md` Step 4 guidance, incarceration status should NOT be added as a screener field.
    * Source: 42 CFR § 435.1010; 42 U.S.C. § 1396d(a)(31); WAC 182-505-0210(7) (as amended WSR 25-09-020, eff. July 1, 2025); WAC 182-503-0505
    * Impact: Low

## Priority Criteria

None — Apple Health for Kids is an entitlement program. Any child meeting the eligibility criteria above is entitled to coverage; there is no waitlist or means-tested priority ranking.

## Benefit Value

Apple Health for Kids is health insurance coverage. Per MFB convention, insurance benefits are valued by total program spending divided by the number of beneficiaries, producing an average per-beneficiary cost.

**Methodology:** For each eligible child in the household, the calculator looks up the per-enrollee spending figure for the federal Medicaid CHILD bucket, divides by 12 to get a monthly value, and sums across all eligible children. Ineligible household members (adults, age-19+ youth) contribute $0.

**Per-eligible-child monthly value** (from KFF State Health Facts, 2023 — Medicaid Spending Per Full-Benefit Enrollee, Washington):

| Eligibility pathway | KFF category | Annual | Monthly |
|---|---|---|---|
| Children 0–18 (CHILD bucket) | Children | $2,801 | $233 |

**Per-household value:** `$233 × (count of eligible children in household)` per month. Examples:

* 1 eligible kid → $233/month
* 2 eligible kids → $466/month
* 3 eligible kids → $699/month

The same per-enrollee value applies across both MAGI tiers (free all-under-19 ≤210% nominal; premium all-under-19 at 210%–312% nominal) — KFF's "Children" category does not break out by age or by free-vs-premium status, and WA HCA's published per-capita spending uses the same federal CHILD bucket regardless of tier. **Validation JSON convention:** scenarios store the annual figure (`"value": 2801`); the frontend divides by 12 for monthly display (~$233/month).

**Premium tier handling (210%–312% FPL nominal):** Per the Federal review, the Healthplanfinder family premium ($20/child or $30/child sliding by tier; family caps of $40 / $60) is NOT netted out of the calculator value. MFB convention treats the benefit value as gross program spending per enrollee, not net-of-cost-to-household. The premium amount is surfaced separately in the program `description` so premium-tier-income families know to expect it.

**Sources:**

* [KFF State Health Facts (2023) — Medicaid Spending Per Full-Benefit Enrollee, Washington](https://www.kff.org/statedata/)
* Underlying data: CMS Medicaid Financial Management Reports (CMS-64)
* [WA HCA — Finance and Rates](https://www.hca.wa.gov/about-hca/finance-and-rates)

⚠️ **Reviewer note (refresh):** KFF 2023 figures are point-in-time. Refresh when KFF publishes more recent data or when WA HCA publishes updated per-enrollee spending. If MFB later adopts a different methodology for valuing insurance benefits (e.g., premium savings vs. marketplace plan), update this section and the validation JSON to match.

## Implementation Coverage

* ✅ Evaluable criteria: 4
* ⚠️  Data gaps: 4

4 of 7 total eligibility criteria can be evaluated with current screener fields. The core criteria — at least one child under 19 (per-member age check), household income relative to the two MAGI tiers (free all-under-19 ≤210% nominal / 215% effective; premium all-under-19 at 210%–312% nominal / 215%–317% effective), Washington state residency, and the no-asset-test rule for MAGI eligibility — are all evaluable. The 4 remaining data gaps are: citizenship/immigration status (canonical screener reference confirms no such field; mooted in WA by Cover All Kids — inclusivity assumption is automatically correct); the premium-tier other-coverage check (criterion 6 — the screener cannot distinguish PEBB/SEBB employer coverage, which is explicitly exempt from disqualification, from non-PEBB/SEBB employer coverage, which disqualifies; inclusivity assumption applies to all employer-insured children at screening time); incarceration status (rare for children; inclusivity assumption applies); and unborn child household size (criterion 2 — WAC 182-506-0010 requires unborn children to be counted in MAGI household size, but the screener has no `unbornChild` relationship type; understating household size overstates FPL% at tier boundaries; inclusivity assumption applies). Administrative requirements that were previously listed as criteria — application submission (procedural) and SSN provision (documentation) — have been moved to the program `description` and `documents` per program-reviewer guidance.

## Screener Improvement Suggestions

Roll-up of the suggested improvements documented per data-gap criterion above. None are blockers — the current screener is sufficient for high-confidence eligibility screening with the inclusivity assumptions documented in criteria 5 and 7. This section is the place where screener PMs can pick what to advance for future iterations.

### What the screener captures well today (no gap)

| Eligibility need | Screener field(s) |
|---|---|
| Under-19 age check (criterion 1) | `birth_year` + `birth_month` (per-member); `relationship` for child-vs-adult routing |
| Household composition | `household_size`, `relationship` |
| Income — earned + unearned by type | `income_streams[].type`, `.amount`, `.frequency`; `calc_gross_income()` |
| WA residency (criterion 3) | `zipcode`, `county` |
| MAGI no-asset rule (criterion 4) | `household_assets` collected but deliberately ignored |
| Already-enrolled exclusion | `insurance.medicaid` per-member; `has_medicaid` household-level |

### Gaps closed by inclusivity assumption (no field change recommended)

* **Citizenship / immigration status** (criterion 5). Sensitive PII; per `find-screener-fields.md` Step 4 guidance, do NOT add. Cover All Kids makes this binary-eligibility-moot in WA Kids. The screener cannot collect this and shouldn't.
* **Premium-tier other-coverage check** (criterion 6). The screener captures `insurance.employer` and `insurance.private` per-member, but cannot distinguish PEBB/SEBB employer coverage (explicitly exempt from the premium-tier disqualification under WAC 182-505-0215) from non-PEBB/SEBB employer coverage (disqualifying). Applying a blanket `employer = true → ineligible` rule would incorrectly exclude WA state and school district employee families. All employer-insured children are treated as potentially eligible at screening time; HCA verifies at application. See Kids-specific improvement suggestion below.
* **Incarceration status** (criterion 7). Sensitive PII; per `find-screener-fields.md` Step 4 guidance, do NOT add. Very rare for children at screening time; inclusivity assumption is safe.

### Kids-specific screener improvement: employer type for PEBB/SEBB distinction (criterion 6)

When a household member selects employer-provided health insurance (`insurance.employer: true`), trigger a conditional follow-up in the Insurance section: "Does that employer work for a Washington state agency, university, community college, school district, charter school, or educational service district?"

- **Yes** → PEBB/SEBB family → eligible for the Apple Health for Kids premium tier despite having employer coverage (WAC 182-505-0215 explicit carve-out)
- **No** → standard rule applies → employer coverage disqualifies the child from the premium tier

This is a targeted, non-sensitive conditional off an existing insurance selection. It closes the criterion 6 data gap without adding a new top-level field, and sharpens premium-tier eligibility signals for a significant WA employer population (state agencies, universities, community colleges, school districts). Per `find-screener-fields.md` Step 4 guidance, surface to screener PMs as a potential improvement rather than implementing unilaterally. Tracked in CLAUDE.md as Screener Improvement Suggestion #11.

### Cross-program suggestions (not Kids-specific)

Tracked in `CLAUDE.md` "Screener improvement suggestions" section, originally flagged during MFB-788 (Federal) review. These benefit Federal Apple Health (Medicaid) and HWD more than Kids but are listed here for awareness:

1. `was_in_foster_care_at_18` (Yes/No) under Special Circumstances — closes Foster Care Alumni gap (federal Medicaid). Also useful for Chafee, ETV, tuition waivers.
2. `needs_long_term_care` (Yes/No) under Special Circumstances — closes LTSS gap. Useful for LTSS, Medicaid HCBS, ADRC referrals.
3. Add `adoption_assistance` to `income_streams.type` enum — closes Adoption Support gap. Useful for adoption support Medicaid and adoption tax credits.
4. Add `unbornChild` to the `relationship` enum on HouseholdMember — pregnant person adds an "Unborn Child" the same way as any other child. Useful for Apple Health pregnant pathway and WIC.
5. Add "Pregnant in the last 12 months" checkbox under Special Circumstances — closes retroactive After-Pregnancy Coverage gap. Useful for APC, WIC postpartum, NFP, postpartum supports.
6. Add `is_tribal_member` / `is_ai_an` (Yes/No) under Special Circumstances — closes AI/AN premium exemption gap (criterion 2; WAC 182-505-0215). American Indian/Alaska Native children are exempt from the monthly premium; this field would let the calculator apply the exemption and avoid overstating cost-to-household for these families. Also useful for IHS coordination and tribal benefit programs.
7. Add `in_foster_care` and `receives_adoption_assistance` (Yes/No) under Special Circumstances AND add foster care / adoption assistance options under Current Household Benefits — closes AHCC routing gap. Children in foster care or receiving adoption assistance are auto-enrolled in Apple Health Core Connections (AHCC) via WAC 182-505-0211 (deemed eligible, no income test). Special Circumstances flag enables correct routing; Current Household Benefits option allows already-enrolled children to indicate existing coverage and enables automatic-eligibility passthrough for other programs. Complements suggestions #1 and #3.

## Acceptance Criteria

\[ \] Scenario 1 (Clearly Eligible Family with One Child Under 210% FPL): User should be **eligible** with $2,801/year (1 eligible child)
\[ \] Scenario 2 (Minimally Eligible - Income at Exactly 210% FPL for Child Age 18): User should be **eligible** with $None/year
\[ \] Scenario 3 (Income $1 Below 210% FPL for Household of 3 - Child Age 5): User should be **eligible** with $None/year
\[ \] Scenario 4 (Infant Under Age 1, Income at Premium Tier Ceiling — 317% Effective / 312% Nominal FPL): User should be **eligible** with $2,801/year (1 eligible child; premium tier — $30/child/month premium applies at application)
\[ \] Scenario 5 (Income $1 Above 312% FPL for Household of 4 - Child Age 10 - Not Eligible): User should be **ineligible**
\[ \] Scenario 6 (Newborn (Age 0) at Minimum Age - Eligible for Apple Health for Kids): User should be **eligible** with $None/year
\[ \] Scenario 7 (All Household Members Age 19+ - No Eligible Children Present): User should be **ineligible**
\[ \] Scenario 8 (Child Age 17 (Well Above Minimum Age) - Eligible for Apple Health for Kids): User should be **eligible** with $None/year
\[ \] Scenario 9 (Eligible Washington State Resident - Valid WA ZIP Code (Spokane, 99201)): User should be **eligible** with $None/year
\[ \] Scenario 10 (Family Already Receiving Apple Health for Kids - Exclusion Check): User should be **ineligible**
\[ \] Scenario 11 (Household Participating in SNAP - No Exclusion for Apple Health for Kids): User should be **eligible** with $None/year
\[ \] Scenario 12 (Mixed Household - Two Adults (19+), One Eligible Child (Age 8), One Adult Child (Age 20) - Under 210% FPL): User should be **eligible** with $None/year
\[ \] Scenario 13 (Multiple Eligible Children - Three Kids Ages 0, 7, and 16 with Income Under 210% FPL): User should be **eligible** with $None/year
\[ \] Scenario 14 (Child Currently 18, Turning 19 Next Month - Age Boundary Edge Case): User should be **eligible** with $None/year
\[ \] Scenario 15 (Premium Tier 1 - Child Age 8, Income in 215%-265% Effective FPL Range - $20/child premium): User should be **eligible** with $None/year
\[ \] Scenario 16 (Premium Tier 2 - Child Age 10, Income in 265%-317% Effective FPL Range - $30/child premium): User should be **eligible** with $None/year
\[ \] Scenario 17 (Premium Tier 1 Income, Child Has Employer Insurance — Inclusivity Assumption): User should be **eligible** (criterion 6 is a data gap; PEBB/SEBB exception means screener cannot enforce employer-insurance disqualifier; all employer-insured children treated as potentially eligible at screening time)

## Test Scenarios

### Scenario 1: Clearly Eligible Family with One Child Under 210% FPL

**What we're checking**: Typical household with a child age 5 and income well below 210% FPL qualifies for free Apple Health for Kids
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `6 1990` (age 35), Relationship: `headOfHousehold`, Has income: Yes, Employment income: `$2,500` per month, Insurance: `employer`, Citizenship: US Citizen
* **Person 2**: Birth month/year: `9 1992` (age 33), Relationship: `spouse`, Has income: No, Insurance: `employer`, Citizenship: US Citizen
* **Person 3**: Birth month/year: `1 2021` (age 5), Relationship: `child`, Has income: No, Insurance: `none`, Citizenship: US Citizen
* **Assets**: Enter household assets: `$0`
* **Current Benefits**: No current benefits selected

**Why this matters**: This is the most common happy-path scenario: a working family in Washington with a young uninsured child and income clearly below the 210% FPL threshold. It validates that the screener correctly identifies free Apple Health for Kids eligibility when all criteria are straightforwardly met.

---

### Scenario 2: Eligible at 215% Effective FPL Boundary — Child Age 18 (HH of 2)

**What we're checking**: Verifies free-tier eligibility when household income sits at the upper effective limit (215% effective FPL = 210% nominal FPL + 5pp MAGI disregard) and the child is at the oldest eligible age (18, just under 19)
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98001`, Select county `King`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: `headOfHousehold`, Has income: Yes, Enter monthly gross income of `$3,879` (employment/wages), Insurance: None
* **Person 2**: Birth month/year: `May 2008` (age 18), Relationship: `child`, Has income: No, Insurance: None
* **Assets**: Enter `$0` for household assets
* **Current Benefits**: Select no current benefits
* **Citizenship**: Select US citizen

**Why this matters**: Tests the boundary conditions simultaneously: the child is at the maximum eligible age (18, just under 19) and household income is right at the 215% effective FPL limit for the free tier (210% nominal + 5pp MAGI disregard). 2026 FPL for a household of 2 is $21,652, so 215% effective = $46,553/year ≈ $3,879/month. Using $3,879/month tests the calculator's eligibility decision exactly at the effective boundary, catching off-by-one and rounding errors.

---

### Scenario 3: Income $1 Below 215% Effective FPL — HH of 3, Child Age 5

**What we're checking**: Validates that a household with income just $1 below the effective free-tier limit (215% effective FPL = 210% nominal + 5pp MAGI disregard) qualifies for free Apple Health for Kids (criterion 2)
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: `Head of Household`, Has income: Yes, Employment income: `$4,894` per month, No other income sources, Insurance: None, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `Spouse`, Has income: No, Insurance: None, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2021` (age 5), Relationship: `Child`, Has income: No, Insurance: None, Citizenship: US Citizen
* **Assets**: Enter `$0` for household assets
* **Current Benefits**: Select no current benefits

**Why this matters**: Testing the boundary $1 below the 215% effective FPL income threshold ensures the screener correctly identifies families as eligible for free Apple Health when income is marginally under the effective limit. Using 2026 FPL for a household of 3 ($27,322): 215% effective = $58,742/year ≈ $4,895/month. Setting income to $4,894/month puts the household exactly $1/month (~$12/year) below the effective limit — the just-eligible side of the boundary. Catches off-by-one and rounding errors in income comparison logic.

---

### Scenario 4: Infant Under Age 1, Income at Premium Tier Ceiling — 317% Effective FPL (HH of 3)

**What we're checking**: Validates that a household with an infant at exactly the premium tier ceiling (317% effective FPL = 312% nominal + 5pp MAGI disregard) is eligible for Apple Health for Kids under the premium tier — which applies to all children under 19, including infants
**Expected**: Eligible (Premium Tier 2 — $30/child premium applies at application)

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: `headOfHousehold`, Has income: Yes, Monthly gross income: `$7,218`, Income type: Employment/wages, Insurance: None
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Has income: No, Insurance: None
* **Person 3**: Birth month/year: `January 2026` (age 0, infant), Relationship: `child`, Has income: No, Insurance: None

**Why this matters**: All children under 19 — including infants — share the same income tiers: free at ≤210% nominal (215% effective), and premium-based at 210%–312% nominal (215%–317% effective). This test validates that the calculator correctly determines eligibility at the absolute upper boundary of the premium tier for a child who happens to be an infant. At $7,218/month for HH3, the household is at exactly 317% effective FPL (312% nominal + 5pp MAGI disregard), placing the infant in Premium Tier 2 ($30/child/month premium at application). Catches off-by-one errors in the ceiling comparison and confirms that the premium tier ceiling applies correctly to infants as well as older children. Note: the infant in this scenario has no other health insurance (`insurance.none: true`), satisfying criterion 6 for premium-tier eligibility.

---

### Scenario 5: Income $1 Above 317% Effective FPL — HH of 4, Child Age 10, Not Eligible

**What we're checking**: Validates that a household with income $1 above the upper effective limit (317% effective FPL = 312% nominal + 5pp MAGI disregard) is correctly determined NOT eligible for any tier of Apple Health for Kids
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `4`
* **Person 1**: Birth month/year: `June 1988` (age 37), Relationship: `headOfHousehold`, Has income: Yes, Enter monthly gross income of `$8,719` (employment/wages), Insurance: `employer`
* **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: `spouse`, Has income: No, Insurance: `employer`
* **Person 3**: Birth month/year: `March 2016` (age 10), Relationship: `child`, Has income: No, Insurance: `employer`
* **Person 4**: Birth month/year: `November 2019` (age 6), Relationship: `child`, Has income: No, Insurance: `employer`

**Why this matters**: Tests the absolute upper boundary for Apple Health for Kids. Even the premium tier (WAC 182-505-0215) caps eligibility at 312% nominal / 317% effective FPL, so income above this level should produce ineligibility across all tiers. Using 2026 FPL for a household of 4 ($33,000): 317% effective = $104,610/year ≈ $8,718/month. Setting income to $8,719/month puts the household exactly $1/month over the effective ceiling — just-ineligible. Catches off-by-one errors in the income comparison logic. Children also have employer insurance, which would have further restricted them out of the premium tier even if income were below 317% — belt-and-suspenders confirmation that ineligibility is driven by income alone in this case (kids would still be eligible for free tier with employer insurance if income were lower).

---

### Scenario 6: Newborn (Age 0) at Minimum Age - Eligible for Apple Health for Kids

**What we're checking**: Validates that a newborn (age 0, born in current year) meets the minimum age requirement and qualifies for Apple Health for Kids under the free tier (≤210% nominal FPL), which applies equally to infants and all other children under 19
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: `headOfHousehold`, Has income: Yes, Monthly employment income: `$4,000`, Insurance: `none`, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Has income: No, Insurance: `none`, Citizenship: US Citizen
* **Person 3**: Birth month/year: `February 2026` (age 0 - newborn, approximately 2 months old), Relationship: `child`, Has income: No, Insurance: `none`, Citizenship: US Citizen

**Why this matters**: This test validates the minimum age boundary — a newborn at age 0 is the youngest possible applicant. At $4,000/month for a household of 3, income is approximately 175% effective FPL, well within the free tier (≤215% effective / ≤210% nominal), which applies equally to infants and all other children under 19. The test confirms the age routing correctly identifies the infant as under 19 and eligible for the free tier — not that infants have a different income threshold than older children (they don't).

---

### Scenario 7: All Household Members Age 19+ - No Eligible Children Present

**What we're checking**: Validates that Apple Health for Kids requires at least one child under age 19. A household where the youngest member is exactly 19 should NOT be eligible.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `June 1980` (age 45), Relationship: `Head of Household`, Has income: Yes, Gross monthly income: `$2,500`, Income frequency: `Monthly`, Insurance: None, Citizenship: US Citizen
* **Person 2**: Birth month/year: `March 2007` (age 19), Relationship: `Child`, Has income: No, Insurance: None, Citizenship: US Citizen

**Why this matters**: Apple Health for Kids explicitly requires children to be under age 19 (WAC 182-505-0210). A person who has already turned 19 is above the age threshold and should not trigger eligibility. This tests the lower boundary exclusion — ensuring that age 19 is treated as ineligible, distinguishing it from age 18 which is the last eligible age.

---

### Scenario 8: Child Age 17 (Well Above Minimum Age) - Eligible for Apple Health for Kids

**What we're checking**: Validates that a 17-year-old child, well above the minimum age of 0 but still under the 19-year cutoff, qualifies for Apple Health for Kids with household income under 210% FPL
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: Head of Household, Has income: Yes, Employment income: `$2,800` monthly, Insurance: None
* **Person 2**: Birth month/year: `January 1988` (age 38), Relationship: Spouse, Has income: Yes, Employment income: `$1,000` monthly, Insurance: None
* **Person 3**: Birth month/year: `September 2008` (age 17), Relationship: Child, Has income: No, Insurance: None

**Why this matters**: This test confirms that older children well above the minimum age threshold (age 0) but still under 19 are correctly identified as eligible. A 17-year-old is near the upper boundary but should clearly qualify, ensuring the program does not incorrectly restrict eligibility to younger children only.

---

### Scenario 9: Eligible Washington State Resident - Valid WA ZIP Code (Spokane, 99201)

**What we're checking**: Validates that a household residing within Washington state (using a valid WA ZIP code in Spokane) meets the geographic residency requirement for Apple Health for Kids
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `99201`, Select county `Spokane`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: `headOfHousehold`, Has income: Yes, Monthly employment income: `$2,500`, Insurance: `none`, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Has income: No, Insurance: `none`, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2020` (age 6), Relationship: `child`, Has income: No, Insurance: `none`, Citizenship: US Citizen

**Why this matters**: This test confirms that a valid Washington state ZIP code in eastern Washington (Spokane area) is correctly recognized as within the Apple Health for Kids service area. It ensures the program is not limited to specific regions within WA and that the geographic eligibility check works for ZIP codes across the state.

---

### Scenario 10: Family Already Receiving Apple Health for Kids - Exclusion Check

**What we're checking**: Whether a household that already receives Apple Health for Kids is flagged appropriately (e.g., shown as ineligible or given a different message indicating they already have the benefit)
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Has income: Yes, Monthly employment income: `$2,500`, Insurance: None, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: Spouse, Has income: No, Insurance: None, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2020` (age 6), Relationship: Child, Has income: No, Insurance: None, Citizenship: US Citizen
* **Current Benefits**: Select that the household currently receives **Apple Health for Kids** (or Medicaid/CHIP for children if listed)

**Why this matters**: Households that already receive Apple Health for Kids should not be directed to re-apply for the same benefit. The screener should detect current enrollment and either suppress the recommendation or provide appropriate guidance, preventing confusion and unnecessary duplicate applications.

---

### Scenario 11: Household Participating in SNAP - No Exclusion for Apple Health for Kids

**What we're checking**: Verifies that participation in other programs (e.g., SNAP) does not exclude a household from Apple Health for Kids eligibility, unlike programs such as CSFP where other program participation can be exclusionary. Apple Health for Kids has no such cross-program exclusion.
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: Head of Household, Has income: Yes, Monthly employment income: `2,500`, Insurance: None, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: Spouse, Has income: No, Insurance: None, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2020` (age 6), Relationship: Child, Has income: No, Insurance: None, Citizenship: US Citizen
* **Current Benefits**: Select that the household currently receives SNAP (Basic Food)

**Why this matters**: Some benefit programs (like CSFP) exclude participants who receive benefits from other specific programs. Apple Health for Kids, being a Medicaid/CHIP program under MAGI rules, has no such cross-program exclusion. This test confirms that receiving SNAP or other assistance does not trigger a false exclusion from Apple Health for Kids eligibility. It validates that the screener correctly handles the absence of program-participation-based exclusions.

---

### Scenario 12: Mixed Household - Two Adults (19+), One Eligible Child (Age 8), One Adult Child (Age 20) - Under 210% FPL

**What we're checking**: Validates that in a multi-member household, only children under 19 are flagged as eligible for Apple Health for Kids, while adult members (19+) are not eligible under this program, even when household income qualifies
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `4`
* **Person 1**: Birth month/year: `June 1986` (age 39), Relationship: Head of Household, Has income: Yes, Employment income: `$3,200` per month, Insurance: None, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: Spouse, Has income: Yes, Employment income: `$1,500` per month, Insurance: None, Citizenship: US Citizen
* **Person 3**: Birth month/year: `November 2005` (age 20), Relationship: Child, Has income: No, Insurance: None, Citizenship: US Citizen
* **Person 4**: Birth month/year: `March 2018` (age 8), Relationship: Child, Has income: No, Insurance: None, Citizenship: US Citizen

**Why this matters**: This tests a realistic mixed household where some members are children under 19 (eligible) and others are adults or adult children over 19 (not eligible for this specific program). It ensures the screener correctly identifies which household members qualify for Apple Health for Kids rather than applying eligibility uniformly to all members.

---

### Scenario 13: Multiple Eligible Children - Three Kids Ages 0, 7, and 16 with Income Under 210% FPL

**What we're checking**: Validates that all children under 19 in a household — including an infant — are identified as eligible when household income is below 210% FPL, and that per-child values are summed correctly across all eligible members
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `5`
* **Person 1**: Birth month/year: `June 1990` (age 35), Relationship: `headOfHousehold`, Has income: Yes, Gross monthly income (employment): `$3,800`, Insurance: `none`
* **Person 2**: Birth month/year: `September 1992` (age 33), Relationship: `spouse`, Has income: No, Insurance: `none`
* **Person 3**: Birth month/year: `January 2026` (age 0 - infant), Relationship: `child`, Has income: No, Insurance: `none`
* **Person 4**: Birth month/year: `March 2019` (age 7), Relationship: `child`, Has income: No, Insurance: `none`
* **Person 5**: Birth month/year: `August 2010` (age 15, turning 16 in August), Relationship: `child`, Has income: No, Insurance: `none`

**Why this matters**: This scenario tests that the screener correctly identifies multiple eligible children of varying ages within the same household. At $3,800/month for a household of 5, income is approximately 118% effective FPL — well within the free tier (≤215% effective) for all children under 19, including the infant. All three children (infant, age 7, age 15) qualify for the free tier under the same income threshold; there is no infant-specific threshold. Ensures the calculator sums per-eligible-child values correctly ($233 × 3 = $699/month) and excludes the adult household members.

---

### Scenario 14: Child Currently 18, Turning 19 Next Month — Age Boundary Edge Case

**What we're checking**: Whether a child currently age 18 — who will turn 19 next month — is correctly evaluated as eligible (under age 19) at screening time
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: `Head of Household`, Has income: Yes, Employment income: `$2,500` per month, Insurance: `None`
* **Person 2**: Birth month/year: `June 2007` (age 18, turning 19 next month), Relationship: `Child`, Has income: No, Insurance: `None`

**Why this matters**: Tests the latest-eligible boundary at the screener level. The screener captures only birth month + birth year (not day-of-month), so MFB's age derivation is month-granular: a child born in any month X is age 19 from the start of month X in their 19th year. The latest-eligible birth date is therefore the month immediately following the current month — here, June 2007 → today (May 2026) → age 18, will turn 19 in June 2026. Counterpart to scenario 7 which tests age 19 → ineligible; together these bracket the under-19 boundary at month granularity.

---

### Scenario 15: Premium Tier 1 — Child Age 8, Income in 215%–265% Effective FPL Range, Uninsured

**What we're checking**: Validates eligibility under the CHIP-funded Premium Tier 1 ($20/child/month, $40/family max) for an uninsured child ages 1–18 with household income between 215% and 265% effective FPL
**Expected**: Eligible (with $20/month premium expected at application)

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1987` (age 38), Relationship: `headOfHousehold`, Has income: Yes, Monthly employment income: `$5,500`, Insurance: `private`, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1989` (age 36), Relationship: `spouse`, Has income: No, Insurance: `private`, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: `child`, Has income: No, Insurance: `none`, Citizenship: US Citizen
* **Assets**: Enter `$0` for household assets
* **Current Benefits**: No current benefits selected

**Why this matters**: Tests the middle income tier of Apple Health for Kids — Premium Tier 1 (WAC 182-505-0215). For 2026 FPL household of 3 ($27,322): 215% effective = $4,895/month; 265% effective = $6,034/month. Setting income to $5,500/month puts the household in the middle of Tier 1 (≈245% effective). The child is uninsured (required for premium tiers; parents' private insurance does not disqualify the child). Validates that (a) the calculator routes the child to the premium tier rather than ineligibility and (b) the premium amount ($20/child = $20/month for this household, well under the $40 family cap) is correctly surfaced to the family. See Scenario 17 for the employer-insurance variant, which tests the criterion 6 inclusivity assumption.

---

### Scenario 16: Premium Tier 2 — Child Age 10, Income in 265%–317% Effective FPL Range, Uninsured

**What we're checking**: Validates eligibility under the CHIP-funded Premium Tier 2 ($30/child/month, $60/family max) for an uninsured child ages 1–18 with household income between 265% and 317% effective FPL
**Expected**: Eligible (with $30/month premium expected at application)

**Steps**:

* **Location**: Enter ZIP code `98103`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1985` (age 40), Relationship: `headOfHousehold`, Has income: Yes, Monthly employment income: `$6,500`, Insurance: `private`, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1987` (age 38), Relationship: `spouse`, Has income: No, Insurance: `private`, Citizenship: US Citizen
* **Person 3**: Birth month/year: `March 2016` (age 10), Relationship: `child`, Has income: No, Insurance: `none`, Citizenship: US Citizen
* **Assets**: Enter `$0` for household assets
* **Current Benefits**: No current benefits selected

**Why this matters**: Tests the upper income tier of Apple Health for Kids — Premium Tier 2 (WAC 182-505-0215). For 2026 FPL household of 3 ($27,322): 265% effective = $6,034/month; 317% effective = $7,218/month. Setting income to $6,500/month puts the household in Tier 2 (≈286% effective). Validates that the calculator routes the child to Tier 2 (not Tier 1, not ineligibility), and that the higher per-child premium ($30/child = $30/month here, under the $60 family cap) is reflected. Together with scenario 15 (Tier 1), scenario 4 (free infant boundary), and scenario 5 (above-ceiling ineligibility), these four scenarios bracket all four MAGI-tier branches of criterion 2.

---

### Scenario 17: Premium Tier 1 Income, Child Has Employer Insurance — Inclusivity Assumption (Eligible)

**What we're checking**: Validates that the screener correctly applies the inclusivity assumption for criterion 6 — a child whose family income falls in the premium tier range and who is enrolled in employer group coverage IS flagged as eligible at screening time, because the screener cannot determine whether the employer coverage is PEBB/SEBB (exempt) or non-PEBB/SEBB (disqualifying)
**Expected**: Eligible

**Steps**:

* **Location**: Enter ZIP code `98101`, Select county `King`
* **Household**: Number of people: `3`
* **Person 1**: Birth month/year: `June 1987` (age 38), Relationship: `headOfHousehold`, Has income: Yes, Monthly employment income: `$5,500`, Insurance: `employer`, Citizenship: US Citizen
* **Person 2**: Birth month/year: `September 1989` (age 36), Relationship: `spouse`, Has income: No, Insurance: `employer`, Citizenship: US Citizen
* **Person 3**: Birth month/year: `January 2018` (age 8), Relationship: `child`, Has income: No, Insurance: `employer`, Citizenship: US Citizen
* **Assets**: Enter `$0` for household assets
* **Current Benefits**: No current benefits selected

**Why this matters**: Criterion 6 (premium-tier other-coverage disqualifier) is a screener data gap — the screener captures `insurance.employer` per-member but cannot distinguish PEBB/SEBB employer coverage (explicitly exempt from the premium-tier disqualification per WAC 182-505-0215) from non-PEBB/SEBB employer coverage (disqualifying). This scenario is the deliberate complement to scenario 15: same household composition, same Premium Tier 1 income range (~245% effective FPL, $5,500/month for HH of 3 in 2026 FPL), but the child has employer insurance. The calculator must NOT enforce `child.insurance.employer = true → ineligible` at screening time, because this family could be a WA state agency or school district employee family (PEBB/SEBB) who is explicitly eligible under WAC 182-505-0215. Instead, the screener treats the child as potentially eligible and the program description directs families with employer coverage to apply and have HCA verify.

---

## Research Sources

* [WA HCA – Apple Health for Kids](https://www.hca.wa.gov/free-or-low-cost-health-care/i-need-medical-dental-or-vision-care/children)
* [WA HCA – Apple Health for Kids with and without premiums](https://www.hca.wa.gov/free-or-low-cost-health-care/i-help-others-apply-and-access-apple-health/apple-health-kids-and-without-premiums)
* [Healthplanfinder – Apple Health for Kids with premiums](https://www.wahealthplanfinder.org/us/en/insurance-payment-options/washington-apple-health-for-kids-with-premiums.html)
* [HCA Income Standards (PDF)](https://www.hca.wa.gov/assets/free-or-low-cost/income-standards.pdf)
* [WAC 182-505-0210 – Categorically Needy medical, children](https://app.leg.wa.gov/wac/default.aspx?cite=182-505-0210)
* [WAC 182-505-0215 – CHIP (Apple Health for Kids with premiums)](https://app.leg.wa.gov/wac/default.aspx?cite=182-505-0215)
* [WAC 182-505-0211 – Apple Health Core Connections (foster/adoption)](https://app.leg.wa.gov/wac/default.aspx?cite=182-505-0211)
* [WAC 182-503-0520 – Residency](https://app.leg.wa.gov/wac/default.aspx?cite=182-503-0520)
* [WAC 182-506-0010 – Household composition / MAGI](https://app.leg.wa.gov/wac/default.aspx?cite=182-506-0010)
* [WAC 182-509-0300 – MAGI methodology](https://app.leg.wa.gov/wac/default.aspx?cite=182-509-0300)
* [WAC 182-504-0015 – Continuous eligibility](https://app.leg.wa.gov/wac/default.aspx?cite=182-504-0015)
* [RCW 74.09.875 – Cover All Kids Act](https://app.leg.wa.gov/rcw/default.aspx?cite=74.09.875)
* [KFF State Health Facts (2023) – Medicaid Spending Per Full-Benefit Enrollee, Washington](https://www.kff.org/statedata/)
