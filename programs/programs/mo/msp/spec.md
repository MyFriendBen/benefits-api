# Implement Medicare Savings Program (MO)

## Program Details

- **Program**: Medicare Savings Program (MSP) — QMB / SLMB / QI
- **State**: MO
- **White Label**: mo
- **Implementation**: PolicyEngine (`msp` variable, category sub-variable `msp_category`: QMB > SLMB > QI priority). Eligibility (age/Medicare enrollment, income, asset test) and benefit value are computed by PolicyEngine; the only state-keyed **PE input** is `state_code: MO`, which resolves PE's asset-test-applies parameter. Missouri does have several additional state-specific policy nuances beyond that PE input — see the confirmed MO-specific limitations in Implementation below — none of which are configurable via PE and are documented as accepted gaps instead.
- **Engine + Tier**: PE, Fed (elig varies) — config + **full spec**, per the ticket's own Decision block.
- **Research Date**: 2026-08-02
- **Implementation Verification**: 2026-08-12 — all 10 scenarios (plus the Scenario 9 companion point) re-run through the actual `MoMsp` calculator against live PolicyEngine at the **pinned model version `1.786.5`**, the version MFB serves. Results in the Implementation Verification Log at the end of this document. The 120% boundary was re-confirmed as **SLMB** at 1.786.5; see the note on criterion 2, which now also records why PolicyEngine's checked-out source appears to disagree.
- **Review Date**: 2026-08-06 (revised after Discovery-review flags — see corrections marked "Correction from initial draft") — **re-verified 2026-08-06** against `MoMsp`'s actual source code, `benefits-api`'s config-import validation, and 10 live calls to PolicyEngine's production API (not assumed from documentation or from PolicyEngine's unreleased source); see the Verification Log at the end of this document.

---

## Eligibility Criteria

1. **Enrolled in (or applying concurrently for) Medicare Part A**
   - Screener field: `insurance.medicare` (per-person)
   - Source: 42 U.S.C. § 1396d(p)(1); PolicyEngine `is_medicare_eligible`
   - Known limitation (not MO-specific): Medicare eligibility below age 65 can also come from disability or ESRD, which the screener doesn't track. PolicyEngine's own `is_medicare_eligible` formula handles this internally; the practical screener-facing implementation (matching KS/IL/TX precedent) assumes age ≥ 65 as the age-eligible path and accepts under-65 disability-based cases as a gap.
   - **Additional Medicare-pathway limitations (confirmed, not modeled)**:
     - **Conditional Part A is a QMB-only pathway.** Confirmed in two places in Missouri's manual: [0865.010.05.15](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0865-000-00/0865-010-00/0865-010-05/0865-010-05-15/) ("Individuals age 65 and over who are eligible for Part A coverage only if they pay a premium, may conditionally enroll in Part A pending a determination of eligibility for QMB... Part A Conditional Enrollment status is not valid Part A eligibility for the SLMB program... SLMB cannot be approved for an individual with conditional Medicare Part A") and independently restated at [0870.010.00](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0870-000-00/0870-010-00/) ("Conditional Part A Medicare is only granted to those who are potentially eligible for the QMB program. SLMB will not pay for Medicare Part A"). PE's `is_medicare_eligible` and the screener's `insurance.medicare` field don't distinguish "conditional" from standard Part A enrollment, so this pathway distinction isn't tested — document as a limitation rather than adding a scenario the screener can't actually exercise.
     - **Part B Immunosuppressive Drug (Part B-ID) pathway not modeled.** 42 CFR § 435.123(b) added a newer MSP pathway: people enrolled only in the limited Part B-ID benefit (post-kidney-transplant coverage of immunosuppressive drugs, for people who lost full Medicare 36 months after transplant) can qualify for QMB-equivalent help with just that premium. Confirmed this is **not present anywhere in PolicyEngine's `policyengine-us` source** (no `immunosuppressive`/`part_b_id` reference in the codebase) — document as both an eligibility and value limitation (see Benefit Value section) rather than modeling it.

2. **Income at or below 135% of the Federal Poverty Level (FPL), tiered into three levels**
   - Screener fields: `calc_gross_income("monthly", ["all"])`, `household_size`, minus SSI-methodology disregards ($20/mo general + $65/mo earned + 50% of remaining earned income)
   - **Missouri-specific assistance-group rule not modeled by PE (documented limitation)**: Missouri's manual (0865.010.10.05) states QMB eligibility, while determined per-individual, considers the income and resources of "the claimant; the claimant's spouse, if living together; and Part A eligible dependent children in the home." Missouri's SLMB manual (0870.010.00) requires meeting "all eligibility requirements of the QMB program except for the income limit," so this assistance-group rule carries over to SLMB. PolicyEngine's `msp_countable_income` and `msp_asset_eligible` only combine income/resources across the SSI **marital unit** (claimant + spouse) — there is no PE concept of a Part-A-eligible dependent child expanding the assistance group. This is a genuine Missouri rule PE does not currently reflect; document it as a PE limitation rather than attempting to model it, since neither PE nor the screener has a "dependent child's Medicare status" field.
   - **Missouri-specific income methodology not modeled by PE (documented limitation)**: PolicyEngine's `msp_countable_income` applies only the generic national SSI exclusions listed above. Missouri's own QMB manual (0865-010-10-20) additionally (a) applies all Medical Assistance income exemptions, (b) excludes specific state cash-grant payments (Temporary Assistance, SP, BP, SAB, SNC) from countable income, and (c) temporarily disregards each January's OASDI/SSI COLA increase until the updated FPL takes effect in April (MO Senate Bill 577, 2007). None of these three MO-specific rules are represented in PE's formula. Practical effect: PE will very slightly understate MSP-countable income (i.e. slightly undercount eligibility) for applicants who (a) receive one of the excluded cash grants, or (b) apply in Jan–Mar of a year with a fresh COLA increase. This is a PE limitation, not a spec error — document rather than attempt to model, since the screener has no field for cash-grant-type income or application month precision.
   - Source: [MO DSS — QMB Income Exemptions/Deductions](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0865-000-00/0865-010-00/0865-010-10/0865-010-10-20/)
   - Tiers — **verified by calling PolicyEngine's live production API directly** (`household.api.policyengine.org`, model version `1.784.3`, the exact endpoint and model version MFB's calculator calls today), not just read from source, because the two disagree (see note below):
     - **QMB**: countable income ≤ 100% FPL (confirmed: $1,330/mo countable is QMB; $1,331/mo is SLMB, for household size 1)
     - **SLMB**: countable income > 100% and **≤ 120%** FPL (confirmed: $1,596/mo countable — exactly 120% FPL — is still SLMB; $1,597/mo is QI)
     - **QI**: countable income **> 120%** and < 135% FPL, **and not otherwise eligible for full MO HealthNet** (confirmed: $1,795/mo countable is QI; $1,796/mo is ineligible — the true cutoff is $1,795.50 = 135% of $1,330, so this lands correctly on the "less than 135%" side for both whole-dollar values)
   - **Important discrepancy, resolved in favor of the live API**: PolicyEngine's own **unreleased `master`-branch source** (`is_slmb_eligible`/`is_qi_eligible` in `policyengine_us/variables/gov/hhs/medicare/savings_programs/category/`) already implements the CFR-exact boundary (SLMB `< 120%`, QI `>= 120%`, moving the 120% edge case into QI) — and that source is what a first-pass reading of "the code" turns up, which is what an earlier draft of this spec did. But **the currently-deployed, callable API (what `MoMsp`/`Msp` actually hits in production) has not yet shipped that change** and still treats exactly 120% as SLMB. Since MFB's calculator sends `"version": "current"` (no version pin for this program) and reads whatever's live, **the live behavior — not the master-branch source, and not the CFR text in isolation — is what a QA pass against the real calculator will see.** If PolicyEngine promotes their master-branch fix into a new default release, this boundary will silently move (SLMB→QI at exactly 120%) with no MFB code change required; the dollar value is identical either way ($202.90), so only the category label would change. Re-run the two boundary scenarios below after any PolicyEngine version bump to confirm which side of 120% the live API currently lands on.
   - **Re-confirmed at implementation time (2026-08-12), with the version numbers that explain the split.** MFB now pins PolicyEngine to **`1.786.5`**, and at that version exactly 120% FPL still resolves to **SLMB** ($1,616/mo gross → $1,596/mo countable → SLMB; $1,617/mo → QI). So the spec text above remains correct for what we actually serve. The reason a source reading suggests otherwise: the local `policyengine-us` checkout is at **`1.794.0`**, which is *ahead of our pin*, and its `is_slmb_eligible` / `is_qi_eligible` do implement the CFR-exact boundary (SLMB `< 120%`, QI `>= 120%`) — that change landed in PE's "Fix MSP income and resource eligibility logic" commit. **Reading the checked-out PE source therefore describes a version we do not run.** The boundary flips to QI only when MFB's pin moves past that release; the dollar value ($202.90/mo) is unchanged either way, so only the category label moves. Scenario 9 asserts the category precisely so this surfaces as a visible test update on the next pin bump rather than a silent change.
   - Source: 42 U.S.C. § 1396a(a)(10)(E); 42 U.S.C. § 1396d(p)(3); 42 CFR § 435.123/.124/.125 (describes the *target* CFR-exact boundary, not yet live); PolicyEngine live API (`household.api.policyengine.org/us/calculate`, model `1.784.3`, verified directly — see Source Documentation)
   - Missouri's own published income-limit table (MO HealthNet Non-MAGI chart, 07/2026) uses "income under X%" language for all three tiers and its manual separately describes SLMB2/QI as "more than 120%" — that phrasing actually **matches** the live PE behavior above (SLMB extends through 120%, QI starts above it), so there is no Missouri-specific Δ here: Missouri's own wording and PE's live behavior agree; it's PE's own unreleased future source that disagrees with both.
   - **QI Priority Criteria (federal, not MO-specific, and not modeled)**: QI enrollment nationwide is first-come-first-served against an annual capped federal allotment (Social Security Act §1902(a)(10)(E)(iv), §1933 — the QI provision Missouri's own manual cites as QI's legal basis at 0870.005.00), with priority given to people who received QI the prior year. This is not spelled out explicitly in Missouri's own manual text (searched 0870.005–0870.045), but it's confirmed federal law governing every state's QI program including Missouri's. PolicyEngine and MFB's screener have no concept of application timing or a funding allotment, so this is a permanent, non-MO-specific documented limitation — not a gap worth a test scenario.

3. **Resource (asset) test applies in Missouri — not waived**
   - Screener field: `household_assets`
   - Limits (2026): **$9,950 individual / $14,910 couple** — same national limits PolicyEngine already uses (`gov.hhs.medicare.savings_programs.eligibility.asset.individual` / `.couple`)
   - Source: this is the ticket's flagged state-keyed input — PolicyEngine's `gov.hhs.medicare.savings_programs.eligibility.asset.applies` parameter has `MO: true` (since 2024-01-01), meaning the asset test is not waived in Missouri. **This is the actual MO-specific Δ**: a MO calculator must pass `state_code: MO` into PE's `msp` computation so this parameter resolves correctly to "applies," rather than defaulting to a waived state's behavior.
   - Exclusions (not counted toward the limit): primary home, one vehicle, household goods, burial funds up to $1,500, life insurance with face value up to $1,500 (PolicyEngine's `ssi_countable_resources` applies the current, generic federal SSI resource-counting rules — same figures PE uses for every state).
   - **Correction from initial draft**: this list was previously cited as "per KS precedent." Missouri's own manual (0865.010.15) instead anchors QMB resource-counting to "anything considered as available under the December 1973 eligibility guidelines for aged and disabled persons," with current exclusion detail in **MHABD Appendix J** — cite Missouri's own manual, not another state's spec, going forward. **Decision**: two direct attempts to retrieve Appendix J's specific dollar exclusions (burial fund, life insurance face value) from Missouri's published manual PDFs returned only the general Non-MAGI income/resource *limit* tables (already reflected above), not the underlying exclusion-detail appendix content — those specific dollar figures are not published in a form reachable outside Missouri's internal case-management system. Given PE's resource-counting formula (`ssi_countable_resources`) is a single generic national implementation shared by every state (not state-keyed), and no evidence surfaced of Missouri publishing a *different* dollar figure than the standard federal SSI $1,500/$1,500 exclusions, the implementation uses PE's figures as-is. This is a final decision, not an open question — if a future engagement with Missouri DSS surfaces a differing published figure, that would be a new, separate finding at that time.
   - Screener limitation (not MO-specific): `household_assets` is a single household-wide field, not split by marital unit, so a couple's assets are already combined by construction — matches PE's couple-limit application when a spouse is present.

4. **Not concurrently eligible for full MO HealthNet (Medicaid) — QI only**
   - Screener fields: `has_medicaid` / current-benefits selection
   - Source: 42 U.S.C. § 1396a(a)(10)(E)(iv); PolicyEngine `is_qi_eligible` explicitly excludes anyone `is_medicaid_eligible`
   - QMB and SLMB have no such exclusion — a MO HealthNet recipient can still receive QMB or SLMB concurrently (confirmed both by PE's formulas and MO's own IM-4 MSP consumer flyer).

5. **Missouri residency**
   - Screener field: state selection (implicit, white-label gated)
   - Source: MO IM-4 MSP flyer ("Be a Missouri Resident (and plan to stay, to qualify for help)")

6. **U.S. citizen or qualified non-citizen (all three tiers)**
   - Screener field: citizenship/immigration-status field (config `program.legal_status_required`: `citizen`, `gc_5plus`, `refugee`, `otherWithWorkPermission`)
   - **Correction from initial draft**: this criterion was omitted from the Eligibility Criteria prose even though the config already implements it correctly. Missouri's own MO HealthNet Non-MAGI eligibility chart lists "U.S. citizen or qualified noncitizen" as a requirement for QMB, and states SLMB/QI eligibility is "same as QMB, other than income and resource limits" — i.e. the citizenship requirement applies to all three tiers. No config change needed; this closes a spec/config documentation gap only.
   - Source: [MO HealthNet Eligibility for Non-MAGI Programs (07/2026)](https://dssmanuals.mo.gov/wp-content/uploads/2018/10/appendix_k.pdf)

---

## Benefit Value

PolicyEngine's `msp` variable (monthly, per person) = `msp_benefit_value`, computed as:
- **QMB**: `base_part_a_premium` + `base_part_b_premium`
- **SLMB**: `base_part_b_premium` only
- **QI**: `base_part_b_premium` only

**2026 Part B base premium: $202.90/month** (`gov.hhs.medicare.part_b.base_premium`, 2026-01-01 value — up from $185.00 in 2025).

**Part A premium is $0/month for ~99% of beneficiaries** (`base_part_a_premium` is zeroed whenever `is_premium_free_part_a` is true, which applies to anyone with 40+ quarters of Medicare-covered employment — the overwhelming majority of retirees). This means in the standard/golden-path case, **QMB, SLMB, and QI all resolve to the same $202.90/month value** — the tiers differ in *who qualifies*, not in the headline dollar amount, for the typical applicant.

- For the rare applicant without premium-free Part A (30–39 quarters: **+$311/mo**; under 30 quarters: **+$565/mo**, both 2026 values), QMB's value would be higher than SLMB/QI's. The screener has no field for "quarters of Medicare-covered employment," so — matching the existing calculator's implicit assumption and KS/IL/TX precedent — implementation should assume premium-free Part A as the default case and treat the non-premium-free Part A scenario as an accepted, documented gap (same class of gap as the under-65-disability Medicare pathway above).
- **Not included in `msp`**: QMB's Medicare cost-sharing (coinsurance/deductible) coverage is a *separate* PolicyEngine variable (`qmb_cost_sharing`, using a flat 20% cost-sharing approximation rate) that rolls into the annual `msp_cost` total but is **not** part of the monthly `msp`/`msp_benefit_value` figure.
- **Committed methodology (was "Recommend surfacing..." in the initial draft — now settled)**: MFB displays PolicyEngine's monthly `msp` premium value as the headline dollar amount. QMB's displayed value includes the modeled Part A + Part B premium amount; SLMB/QI's displayed value includes Part B only. QMB's Medicare cost-sharing protection is described qualitatively in the program description (already done) but is **not** added into the displayed `msp` dollar figure.
- **Part B-ID value limitation (not modeled)**: CMS sets the 2026 standard Part B Immunosuppressive Drug (Part B-ID) premium at **$121.60/month** — a separate, lower figure from the standard $202.90/month Part B premium. Since PolicyEngine doesn't model the Part B-ID eligibility pathway at all (see Eligibility Criteria, criterion 1), it correspondingly can't produce this $121.60 value. Document as a paired eligibility + value limitation; do not attempt to hand-calculate it outside PE.

---

## Implementation

- ✅ Evaluable: Medicare Part A enrollment (age ≥ 65 path), income tiering (QMB ≤100% / SLMB >100–≤120% / QI >120–<135% FPL — the live-API-verified boundaries; see criterion 2), asset test (applies in MO, current 2026 limits), QI-vs-Medicaid exclusion, MO residency, citizenship/legal status (config already correct; now also documented in prose).
- ⚠️ Known limitations, **not MO-specific** (shared with KS/IL/TX precedent): under-65 disability/ESRD-based Medicare eligibility not captured; "quarters of Medicare-covered employment" not captured, so non-premium-free Part A cases (a minority) aren't distinguished; QI's first-come-first-served federal allotment/priority rule not modeled (no application-timing concept exists in PE or the screener).
- ⚠️ Known limitations, **MO-specific, confirmed against MO DSS manuals** (new — not previously documented): (1) Missouri's QMB/SLMB assistance group additionally considers a Part-A-eligible dependent child's income/resources, which PE's marital-unit-only model doesn't capture; (2) Missouri's QMB income methodology applies state-specific cash-grant exclusions and a Jan–Mar COLA disregard that PE's generic national SSI methodology doesn't apply; (3) conditional Part A is a QMB-only Medicare pathway in Missouri (confirmed explicitly barred for SLMB) — not distinguishable by the screener; (4) the federal Part B-ID pathway (42 CFR 435.123(b)) is entirely unmodeled by PE. Resource-exclusion citation was corrected from a borrowed KS precedent to Missouri's own manual (0865.010.15 / MHABD Appendix J); the specific dollar exclusions in that appendix aren't published outside Missouri's internal system, so PE's generic SSI figures are used as-is — a settled decision, not an open item.
- ✅ Implemented: `MoMsp` calculator already exists in `benefits-api` (`programs/programs/mo/pe/member.py`), subclassing the shared federal `Msp` PE calculator exactly like `KsMsp`/`TxMsp`/`IlMsp`, with `MoStateCodeDependency` + `Medicaid.pe_inputs` added. Verified directly by reading the calculator source and its test suite (`test_member.py::TestMoMspWiring`) — this is not a to-be-built component.
- **Verified end-to-end against PolicyEngine's live API**, not just against source code: all 8 original acceptance scenarios plus the two boundary scenarios below were run against `household.api.policyengine.org` (model `1.784.3`) using `MoMsp`'s exact `pe_inputs`, and every eligibility/category/dollar-value result matched this spec's claims (after the boundary correction above).
- The only eligibility criterion requiring a MO-specific PE input remains the asset-test-applies state parameter (`state_code: MO`); MO's income limits match the federal floor exactly. The MO-specific *gaps* above are documentation/limitations, not additional PE inputs to configure. Config JSON (`mo_msp_initial_config.json`) was statically checked against `import_program_config.py`'s validation rules — see verdict at the end of this document.

---

## Source Documentation

- [MO IM-4 MSP consumer flyer](https://dssmanuals.mo.gov/wp-content/uploads/2020/09/im-4msp.pdf) (08/2024 revision)
- [MO HealthNet Eligibility for Non-MAGI Programs (07/2026)](https://dssmanuals.mo.gov/wp-content/uploads/2018/10/appendix_k.pdf) — QMB/SLMB/QI income & resource limits, citizenship requirement
- [MO DSS Manual 0865.010.10.05 — QMB Assistance Group](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0865-000-00/0865-010-00/0865-010-10/0865-010-10-05/)
- [MO DSS Manual 0865.010.10.20 — QMB Income Exemptions/Deductions](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0865-000-00/0865-010-00/0865-010-10/0865-010-10-20/)
- [MO DSS Manual 0865.010.15 — QMB Resources](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0865-000-00/0865-010-00/0865-010-15/)
- [MO DSS Manual 0865.010.05.15 — Part A Conditional Enrollment](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0865-000-00/0865-010-00/0865-010-05/0865-010-05-15/)
- [MO DSS Manual 0870.010.00 — SLMB/QI Eligibility Requirements](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0870-000-00/0870-010-00/)
- [MO DSS Manual 0870.005.00 — QI Legal Basis](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0870-000-00/0870-005-00/)
- [MO Benefit Program Income Limits (effective 2026-04-01)](https://mydss.mo.gov/benefit-program-income-limits)
- [MO DMH — QMB/SLMB Coverage](https://dmh.mo.gov/medicaid-eligibility/qmb-slmb-coverage) (secondary source)
- [CMS 2026 Medicare Parts A & B Premiums and Deductibles](https://www.cms.gov/newsroom/fact-sheets/2026-medicare-parts-b-premiums-deductibles) — standard Part B premium $202.90/mo, Part B-ID premium $121.60/mo
- 42 U.S.C. § 1396a(a)(10)(E), § 1396d(p) — federal MSP statute
- [42 CFR § 435.123](https://www.law.cornell.edu/cfr/text/42/435.123) (QMB, incl. Part B-ID pathway), [§ 435.124](https://www.law.cornell.edu/cfr/text/42/435.124) (SLMB boundary), [§ 435.125](https://www.law.cornell.edu/cfr/text/42/435.125) (QI boundary)
- Social Security Act § 1902(a)(10)(E)(iv), § 1933 (Balanced Budget Act of 1997) — QI's federal allotment/priority basis
- PolicyEngine source (`PolicyEngine/policyengine-us`): `variables/gov/hhs/medicare/savings_programs/{msp,msp_benefit_value,msp_cost}.py`, `.../category/{msp_category,is_qmb_eligible,is_slmb_eligible,is_qi_eligible}.py`, `.../income/msp_countable_income.py`, `.../eligibility/msp_asset_eligible.py`; `parameters/gov/hhs/medicare/savings_programs/eligibility/asset/applies.yaml`; `parameters/gov/hhs/medicare/{part_a,part_b}/*.yaml` — verified directly by reading source, not assumed from documentation

---

## Acceptance Criteria

- [ ] Scenario 1 (Single retiree, low income, no significant assets — QMB, golden path): User should be **eligible** — $202.90/month
- [ ] Scenario 2 (Single retiree, income 100–120% FPL — SLMB): User should be **eligible** — $202.90/month
- [ ] Scenario 3 (Single retiree, income 120–135% FPL, no Medicaid — QI): User should be **eligible** — $202.90/month
- [ ] Scenario 4 (Single retiree, assets above the $9,950 limit — asset-test-applies check): User should be **ineligible**
- [ ] Scenario 5 (Married couple, combined income/assets within couple limits — QMB): User should be **eligible** — $202.90/month per eligible spouse
- [ ] Scenario 6 (Applicant age 60, not on Medicare — Medicare-enrollment gate): User should be **ineligible**
- [ ] Scenario 7 (Income in the QI band, but already has full MO HealthNet — QI categorical exclusion): User should be **ineligible**
- [ ] Scenario 8 (Income above 135% FPL — too high for any MSP tier): User should be **ineligible**
- [ ] Scenario 9 (Income exactly at 120% FPL — SLMB/QI boundary): User should be **eligible as SLMB** (live PE behavior, confirmed 2026-08-06 — not QI, despite CFR text and PE's future source suggesting otherwise), not eligible as QI — $202.90/month
- [ ] Scenario 10 (Income exactly at 135% FPL — QI upper boundary): User should be **ineligible** (135% itself is the cutoff, not an included value) — confirmed against live PE

---

## Test Scenarios

> Every eligible scenario asserts the same $202.90/month figure (2026 Part B base premium, premium-free Part A assumed) — a scenario breaks if MO's calculator doesn't pick up the current-year Part B premium or doesn't correctly tier QMB/SLMB/QI.

### Scenario 1: Single Retiree, Low Income, No Significant Assets — QMB, Golden Path
**What we're checking**: A retiree with income well under 100% FPL and minimal countable assets qualifies for the top MSP tier (QMB).
**Expected**: Eligible — $202.90/month

**Steps**:
- **Location**: Enter ZIP code `65101` (Jefferson City), Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,000` per month, Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Assets**: Household resources: `$3,000`
- **Current Benefits**: Select no current benefits

**Why this matters**: The most common MSP pathway — a low-income Medicare-enrolled senior with modest savings, well under both the 100% FPL income line ($1,330/mo for a household of 1) and the $9,950 individual asset limit.

---

### Scenario 2: Single Retiree, Income 100–120% FPL — SLMB
**What we're checking**: Income above the QMB ceiling but within the SLMB band still qualifies, at the same $ value (Part B premium only, same as QMB's Part B portion since Part A is premium-free).
**Expected**: Eligible — $202.90/month

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,500` per month (~113% FPL for household of 1), Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Assets**: Household resources: `$3,000`

**Why this matters**: Validates the SLMB income band (100–120% FPL, i.e. $1,330–$1,596/mo for household of 1) is correctly captured as its own eligible tier rather than falling through to ineligible once income clears the QMB line.

---

### Scenario 3: Single Retiree, Income 120–135% FPL, No Medicaid — QI
**What we're checking**: Income in the top MSP band (QI) with no full Medicaid coverage.
**Expected**: Eligible — $202.90/month

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,700` per month (~128% FPL for household of 1), Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Assets**: Household resources: `$3,000`
- **Current Benefits**: Select no current benefits

**Why this matters**: Validates the QI band (120–135% FPL, $1,596–$1,796/mo for household of 1) is correctly captured as its own eligible tier.

---

### Scenario 4: Single Retiree, Assets Above the $9,950 Limit — Asset Test Applies
**What we're checking**: MO does **not** waive the MSP asset test (`applies.yaml` MO: true) — a household otherwise income-eligible is still denied for excess countable resources. This is the actual MO-specific Δ the ticket flagged.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,000` per month, Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Assets**: Household resources: `$15,000` (excludes home/vehicle — this is countable savings/investments only)

**Why this matters**: Directly tests the parameter this discovery ticket exists to confirm. If MO were mistakenly implemented as an asset-test-waived state (like neighboring states that flipped to waived in 2024), this household would incorrectly show as eligible.

---

### Scenario 5: Married Couple, Combined Income/Assets Within Couple Limits — QMB
**What we're checking**: A married couple's combined resources are checked against the couple limit ($14,910), and both spouses are Medicare-enrolled and QMB-eligible.
**Expected**: Eligible — $202.90/month per eligible spouse ($405.80/month household total)

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `2`
- **Person 1 (Head of Household)**: Birth month/year: `March 1953` (age 73), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$900` per month, Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Person 2 (Spouse)**: Birth month/year: `July 1955` (age 71), Relationship: `Spouse`, Has income: `Yes`, Social Security income: `$800` per month, Insurance: `Medicare`
- **Assets**: Household resources: `$10,000` (under the $14,910 couple limit, over the $9,950 individual limit)

**Why this matters**: Confirms the couple asset limit (not the individual limit) applies once a spouse is present, and that the calculator scales value per eligible person rather than capping at one premium per household.

---

### Scenario 6: Applicant Age 60, Not on Medicare — Medicare-Enrollment Gate
**What we're checking**: A near-retirement-age applicant who isn't yet Medicare-enrolled and has no disability-based early eligibility is excluded, regardless of income.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1966` (age 60), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,000` per month, Citizenship: `U.S. Citizen`, Insurance: none selected

**Why this matters**: Validates the Medicare Part A enrollment gate (criterion 1) — MSP only helps with Medicare costs, so a non-Medicare-enrolled applicant cannot qualify no matter how low their income is.

---

### Scenario 7: Income in the QI Band, But Already Has Full MO HealthNet — QI Categorical Exclusion
**What we're checking**: QI (unlike QMB/SLMB) is explicitly unavailable to anyone with full Medicaid/MO HealthNet coverage.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,700` per month (~128% FPL — QI band), Citizenship: `U.S. Citizen`, Insurance: `Medicare`, `Medicaid`
- **Current Benefits**: Select `Medicaid`

**Why this matters**: Distinguishes QI from QMB/SLMB, which have no such exclusion (a MO HealthNet recipient can still get QMB or SLMB). Tests a code path unique to the QI tier.

---

### Scenario 8: Income Above 135% FPL — Too High for Any MSP Tier
**What we're checking**: Income above even the QI ceiling disqualifies the applicant from all three tiers.
**Expected**: Not eligible

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,900` per month (~143% FPL for household of 1), Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Assets**: Household resources: `$3,000`

**Why this matters**: Confirms the top income ceiling (135% FPL) is enforced as a hard cutoff, not just a soft "highest tier" — a household this far over should get nothing, not a reduced QI benefit.

---

### Scenario 9: Income Exactly at the 120% FPL Boundary — Must Resolve to SLMB (Live PE Behavior), Not QI
**What we're checking**: This spec's own first-pass "fix" got this backwards — reading 42 CFR text and PolicyEngine's *unreleased* `master`-branch source suggested 120% should belong to QI. A direct call to PolicyEngine's actual **live production API** (verified 2026-08-06, model `1.784.3`) proved the opposite is currently true: countable income of exactly $1,596/mo (120% FPL for household size 1) resolves to **SLMB**, and QI only starts at $1,597/mo. This scenario pins that live behavior so it's caught if it ever silently changes.
**Expected**: Eligible as **SLMB** — $202.90/month (not QI). A companion check one dollar higher ($1,617/mo gross → $1,597/mo countable) should resolve to **QI**, same $202.90/month — run both to confirm the exact crossover point, not just one side of it.

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,616` per month (100% FPL for household of 1 is $1,330/mo; after PE's $20/mo general SSI disregard, countable income = $1,596/mo = exactly 120% FPL), Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Current Benefits**: Select no current benefits
- **Assets**: Household resources: `$3,000`

**Why this matters**: A pure boundary test, and a live-vs-source discrepancy worth pinning explicitly. If PolicyEngine promotes their `master`-branch fix into a new default release, this scenario's expected category will flip from SLMB to QI at the same dollar value — assert `msp_category` (or the equivalent MFB-facing category label), not just the dollar amount, so a future PE version bump surfaces as a visible, intentional test update rather than a silent behavior change.

---

### Scenario 10: Income At the 135% FPL Ceiling — Must Be Ineligible
**What we're checking**: 135% FPL is an exclusive ceiling (`< 135%`, per 42 CFR 435.125(b): "less than 135 percent"), not an included endpoint. **Confirmed against PolicyEngine's live production API** (2026-08-06): countable income of $1,795/mo is still QI-eligible; $1,796/mo is not. (The true unrounded cutoff is $1,795.50 = 135% of $1,330 — both whole-dollar test points land correctly on either side of it, and this is the one boundary where the live API and PE's future/unreleased source agree, unlike Scenario 9's 120% edge.)
**Expected**: Not eligible (income at/above the QI ceiling)

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,816` per month (after the $20/mo disregard, countable income = $1,796/mo — Missouri's own published 135% FPL figure), Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Assets**: Household resources: `$3,000`

**Why this matters**: Confirms the top income ceiling (135% FPL) is enforced as a hard, exclusive cutoff, not a soft/highest-tier catch-all.

---

## Verification Log (2026-08-06)

This spec was re-verified end-to-end after a Discovery-review flagged multiple issues in the prior draft. Every claim below was checked against a primary source (live API, actual repo source, or a state manual) — nothing here is inferred or assumed. Sources: PolicyEngine's live `household.api.policyengine.org` (model `1.784.3`), the `benefits-api` repo at commit `679dd92` (2026-07-30), and the MO DSS manual pages cited throughout.

### Config static check (`mo_msp_initial_config.json` vs. `import_program_config.py`)

| Rule | Config value | Result |
|---|---|---|
| Required top-level fields (`white_label`, `program_category`, `program`) | all present | ✅ Pass |
| `white_label.code` present | `"mo"` | ✅ Pass |
| `WhiteLabel` "mo" exists in DB | — | ⚠️ Needs live DB to confirm — but "mo" is already referenced by 4 other live MO configs (WIC, Head Start, Early Head Start, NSLP), so this is low-risk |
| `program.name_abbreviated` present, matches calculator registry | `"mo_medicare_savings"` | ✅ Pass — matches `mo_member_calculators["mo_medicare_savings"] == MoMsp` in the actual repo (`test_member.py`) |
| Program doesn't already exist for this white label (or `--override` needed) | — | ⚠️ Needs live DB — no `mo_msp_initial_config.json` exists yet in the repo's own data folder, so this is very likely a fresh import |
| `program_category.external_name` present; if new, `icon`+`name` required | `"mo_healthcare"`, icon `"health_care"`, name `"Health Care"` | ✅ Pass either way — no existing MO config uses `mo_healthcare` yet (MO's other configs use `mo_child_care`/`mo_food`), so this creates a new category, but it exactly matches KS's identical, already-live `ks_healthcare`/`"Health Care"`/`"health_care"` pattern |
| `program.year` resolves to a `FederalPoveryLimit` row | `"2026"` | ⚠️ Needs live DB (soft warning only, not a hard failure if missing) — identical value already used by KS's live, working `ks_msp_initial_config.json` |
| `legal_status_required` codes exist | `citizen`, `gc_5plus`, `refugee`, `otherWithWorkPermission` | ✅ Very low risk — each code is already used in 87–115 other configs in this repo |
| `base_program` is a valid `BaseProgram` choice | `"medicare_savings"` | ✅ Pass — confirmed present in `BaseProgram` choices via repo migrations |
| All 10 translatable `program` fields match `Program.objects.translated_fields` exactly | `description`, `description_short`, `name`, `learn_more_link`, `apply_button_link`, `apply_button_description`, `estimated_delivery_time`, `estimated_application_time`, `estimated_value`, `website_description` | ✅ Pass — exact match, nothing silently dropped |
| Documents: `external_name` + `text` present for all 8 (new-document requirement) | all 8 present | ✅ Pass |
| Navigator: `external_name`, `name`, `email`, `description`, `assistance_link` keys present | all present (note: `email` is an empty string — passes the *presence* check the importer runs, but is empty; confirm intentional, MO SHIP's contact is phone-based per `phone_number`) | ✅ Pass (structural) |
| `"value_type": "benefit"` key | present in config | ℹ️ No-op — `Program` has no `value_type` model field; the importer silently ignores this key. Harmless (shared by 5 other configs in the repo), not a defect, doesn't need removing |

**Verdict: Ready for devs.** No hard-failure rules are violated. The only unresolved items are DB-existence checks that can't be verified without a live database, and each is corroborated by an already-live sibling config using the identical value.

### Live PolicyEngine API verification (all 10 test scenarios)

Called `household.api.policyengine.org/us/calculate` directly using `MoMsp`'s actual `pe_inputs` (confirmed from `programs/programs/federal/pe/member.py` + `programs/programs/mo/pe/member.py`), not assumed field names.

| Scenario | Sent | PE returned | Spec claims | Match? |
|---|---|---|---|---|
| 1 — QMB golden path | $1,000/mo, $3,000 assets | QMB, $202.90 | QMB, $202.90 | ✅ |
| 2 — SLMB band | $1,500/mo | SLMB, $202.90 | SLMB, $202.90 | ✅ |
| 3 — QI band | $1,700/mo, no Medicaid | QI, $202.90 | QI, $202.90 | ✅ |
| 4 — over asset limit | $1,000/mo, $15,000 assets | Ineligible | Ineligible | ✅ |
| 5 — married couple | $900+$800/mo, $10,000 assets | Both QMB, $202.90 each | Both QMB, $202.90 each | ✅ |
| 6 — age 60, no Medicare | $1,000/mo | Ineligible | Ineligible | ✅ |
| 7 — QI band + Medicaid | $1,700/mo + Medicaid | Ineligible | Ineligible | ✅ |
| 8 — above 135% FPL | $1,900/mo | Ineligible | Ineligible | ✅ |
| 9 — exactly 120% FPL | $1,616/mo (countable $1,596) | **SLMB**, $202.90 | Corrected to SLMB (was wrongly QI) | ✅ (after fix) |
| 9-companion — $1/mo above | $1,617/mo (countable $1,597) | QI, $202.90 | QI, $202.90 | ✅ |
| 10 — exactly 135% FPL | $1,816/mo (countable $1,796) | Ineligible | Ineligible | ✅ |

All 10 scenarios (plus the Scenario 9 companion point) now match live PolicyEngine output exactly. The only discrepancy found (Scenario 9's boundary) was in this spec's own prior draft, not in the calculator — it's been corrected above.

---

## Program Configuration
File: `mo_msp_initial_config.json`

---

## Implementation Verification Log (2026-08-12, PolicyEngine `1.786.5`)

Run at implementation time through the **actual `MoMsp` calculator** (not hand-built API payloads):
real `Screen` / `HouseholdMember` / `IncomeStream` / `Insurance` rows were created for each
scenario and passed to `calc_pe_eligibility`, so the inputs are exactly what the screener sends.
The model version is MFB's pinned `1.786.5`, read from `PolicyEngineConfig`.

Values below are **yearly** (the calculator's native output). $2,434.80/yr = $202.90/mo × 12,
the 2026 standard Part B premium — matching every eligible scenario's expected monthly figure.

| Scenario | Expected | Measured (1.786.5) | Category | Match |
|---|---|---|---|---|
| 1 — QMB golden path ($1,000/mo, $3k assets) | Eligible, $202.90/mo | Eligible, $2,434.80/yr | QMB | ✅ |
| 2 — SLMB band ($1,500/mo) | Eligible, $202.90/mo | Eligible, $2,434.80/yr | SLMB | ✅ |
| 3 — QI band ($1,700/mo, no Medicaid) | Eligible, $202.90/mo | Eligible, $2,434.80/yr | QI | ✅ |
| 4 — over asset limit ($15,000) | Ineligible | Ineligible, $0 | NONE | ✅ |
| 5 — married couple ($900 + $800/mo, $10k assets) | Eligible, $202.90/mo each | Eligible, $4,869.60/yr household | QMB + QMB | ✅ |
| 6 — age 60, no Medicare | Ineligible | Ineligible, $0 | NONE | ✅ |
| 7 — QI band + Medicaid | Ineligible | Ineligible, $0 | NONE | ✅ |
| 8 — above 135% FPL ($1,900/mo) | Ineligible | Ineligible, $0 | NONE | ✅ |
| 9 — exactly 120% FPL ($1,616/mo) | Eligible as **SLMB** | Eligible, $2,434.80/yr | **SLMB** | ✅ |
| 9b — one dollar above ($1,617/mo) | Eligible as **QI** | Eligible, $2,434.80/yr | **QI** | ✅ |
| 10 — at 135% FPL ($1,816/mo) | Ineligible | Ineligible, $0 | NONE | ✅ |

**11/11 match, $0 delta.** Confirmed alongside the run:

- **MO's asset test applies.** Scenario 4 flips to ineligible purely on assets, which only
  happens because `MoStateCodeDependency` resolves MO's `asset.applies = true`. This is the one
  genuine MO delta, and it is exercised rather than merely asserted.
- **The 120% boundary is SLMB at our pinned version** (Scenarios 9 / 9b bracket the crossover at
  exactly one dollar). See the version note on criterion 2 for why PE's checked-out source reads
  differently.
- **Per-person scaling is correct.** Scenario 5 returns exactly double the single-person value,
  confirming the value is not capped at one premium per household.
- **Premium-free Part A holds.** Every eligible tier returns the Part B premium alone; QMB is not
  inflated by a Part A premium, because `MedicareQuartersOfCoverageDependency` sends 40 quarters.

Unit tests covering this wiring live in `programs/programs/mo/pe/tests/test_member.py`
(`TestMoMspWiring`, `TestMoMspPeInput`). Per the current testing standard, no VCR cassettes were
written; the PE-sourced figures above are the live verification of record.
