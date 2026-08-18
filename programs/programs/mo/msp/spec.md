# Implement Medicare Savings Program (MO)

## Program Details

- **Program**: Medicare Savings Program (MSP) — QMB / SLMB / QI
- **State**: MO
- **White Label**: mo
- **Implementation**: PolicyEngine (`msp` variable, category sub-variable `msp_category`: QMB > SLMB > QI priority). Eligibility (age/Medicare enrollment, income, asset test) and benefit value are computed by PolicyEngine; the only state-keyed **PE input** is `state_code: MO`, which resolves PE's asset-test-applies parameter. Missouri does have several additional state-specific policy nuances beyond that PE input. Those are not configurable through PolicyEngine and are recorded under Implementation as gaps.
- **Engine + Tier**: PE, Fed (elig varies)
- **Part B premium (2026)**: $202.90/month

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
   - Tiers (household of 1 figures use the 2026 FPL of $1,330/mo):
     - **QMB**: countable income ≤ 100% FPL
     - **SLMB**: countable income > 100% and ≤ 120% FPL
     - **QI**: countable income > 120% and < 135% FPL, and not otherwise eligible for full MO HealthNet
   - The 135% ceiling is exclusive (42 CFR 435.125(b), "less than 135 percent").
   - **The 120% boundary belongs to SLMB, not QI.** 42 CFR and PolicyEngine's newer source both
     place exactly 120% in QI, but the PolicyEngine version MFB serves resolves it to SLMB; QI
     starts one dollar higher. The dollar value is identical either way ($202.90/mo) — only the
     category label differs. Scenarios 9 and 9b assert the category on both sides of the
     crossover, so a PolicyEngine version bump that moves this boundary surfaces as a visible
     test update rather than a silent change.
   - Missouri's own manual describes SLMB2/QI as "more than 120%", which matches the behavior above — SLMB extends through 120% and QI starts above it. There is no Missouri-specific delta in the tiers.
   - **QI Priority Criteria (federal, not MO-specific, and not modeled)**: QI enrollment nationwide is first-come-first-served against an annual capped federal allotment (Social Security Act §1902(a)(10)(E)(iv), §1933 — the QI provision Missouri's own manual cites as QI's legal basis at 0870.005.00), with priority given to people who received QI the prior year. This is not spelled out explicitly in Missouri's own manual text (searched 0870.005–0870.045), but it's confirmed federal law governing every state's QI program including Missouri's. PolicyEngine and MFB's screener have no concept of application timing or a funding allotment, so this is a permanent, non-MO-specific documented limitation — not a gap worth a test scenario.

3. **Resource (asset) test applies in Missouri — not waived**
   - Screener field: `household_assets`
   - Limits (2026): **$9,950 individual / $14,910 couple** — same national limits PolicyEngine already uses (`gov.hhs.medicare.savings_programs.eligibility.asset.individual` / `.couple`)
   - Source: this is the ticket's flagged state-keyed input — PolicyEngine's `gov.hhs.medicare.savings_programs.eligibility.asset.applies` parameter has `MO: true` (since 2024-01-01), meaning the asset test is not waived in Missouri. **This is the actual MO-specific Δ**: a MO calculator must pass `state_code: MO` into PE's `msp` computation so this parameter resolves correctly to "applies," rather than defaulting to a waived state's behavior.
   - Exclusions (not counted toward the limit): primary home, one vehicle, household goods, burial funds up to $1,500, life insurance with face value up to $1,500 (PolicyEngine's `ssi_countable_resources` applies the current, generic federal SSI resource-counting rules — same figures PE uses for every state).
   - Missouri anchors QMB resource-counting to "anything considered as available under the December 1973 eligibility guidelines for aged and disabled persons" (manual 0865.010.15), with exclusion detail in MHABD Appendix J. Appendix J's specific dollar exclusions are not published outside Missouri's internal case-management system, and PolicyEngine's resource formula is a single generic national implementation rather than a state-keyed one, so its standard federal SSI figures are used.
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
   - Missouri's own MO HealthNet Non-MAGI eligibility chart lists "U.S. citizen or qualified noncitizen" as a requirement for QMB, and states SLMB/QI eligibility is "same as QMB, other than income and resource limits" — i.e. the citizenship requirement applies to all three tiers.
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
- **Displayed value**: MFB displays PolicyEngine's monthly `msp` premium value as the headline dollar amount. QMB's displayed value includes the modeled Part A + Part B premium amount; SLMB/QI's displayed value includes Part B only. QMB's Medicare cost-sharing protection is described qualitatively in the program description but is **not** added into the displayed `msp` dollar figure.
- **Part B-ID value limitation (not modeled)**: CMS sets the 2026 standard Part B Immunosuppressive Drug (Part B-ID) premium at **$121.60/month** — a separate, lower figure from the standard $202.90/month Part B premium. Since PolicyEngine doesn't model the Part B-ID eligibility pathway at all (see Eligibility Criteria, criterion 1), it correspondingly can't produce this $121.60 value. Document as a paired eligibility + value limitation; do not attempt to hand-calculate it outside PE.

---

## Implementation Coverage

`MoMsp` subclasses the shared federal `Msp` PolicyEngine calculator, adding the MO state code
and the Medicaid inputs, the same shape as the KS / TX / IL MSP calculators. The state code is
the only MO-keyed input; MO's income limits match the federal floor exactly.

- ✅ **Evaluable criteria**: Medicare Part A enrollment (age ≥ 65 path), income tiering
  (QMB / SLMB / QI), the asset test, the QI-vs-Medicaid exclusion, MO residency, and
  citizenship / legal status.
- ⚠️ **Data gaps, not MO-specific** (shared with the KS / IL / TX implementations): under-65
  disability- or ESRD-based Medicare eligibility, which the screener has no field for; quarters
  of Medicare-covered employment, so applicants without premium-free Part A are not
  distinguished and premium-free Part A is assumed; and QI's first-come-first-served federal
  allotment and prior-year priority rule, since neither PolicyEngine nor the screener has a
  concept of application timing.
- ⚠️ **Data gaps, MO-specific**: Missouri's QMB/SLMB assistance group also counts a
  Part-A-eligible dependent child's income and resources, while PolicyEngine combines across the
  SSI marital unit only and neither it nor the screener knows a dependent child's Medicare
  status. Missouri's QMB income methodology excludes specific state cash-grant payments and
  disregards each January's COLA until the updated FPL takes effect in April, where PolicyEngine
  applies only the generic national SSI exclusions — so it slightly understates countable income
  for those applicants. Conditional Part A is a QMB-only pathway in Missouri and is expressly
  barred for SLMB, but the screener's Medicare field does not distinguish it from standard Part A
  enrollment. The Part B-ID pathway of 42 CFR 435.123(b) is absent from PolicyEngine, so neither
  that eligibility route nor its lower premium is produced.

Missouri anchors its resource-counting rules to its own manual (0865.010.15 / MHABD Appendix J).
The specific dollar exclusions in that appendix are not published outside Missouri's internal
system, and PolicyEngine's resource formula is a single generic national implementation, so its
standard federal SSI figures are used.

---

## Research Sources

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
- [ ] Scenario 9 (Income exactly at 120% FPL — SLMB/QI boundary): User should be **eligible as SLMB** (not QI) — $202.90/month
- [ ] Scenario 10 (Income exactly at 135% FPL — QI upper boundary): User should be **ineligible** (135% itself is the cutoff, not an included value)

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

### Scenario 9: Income Exactly at the 120% FPL Boundary — SLMB, Not QI
**What we're checking**: The exact SLMB/QI crossover. At the PolicyEngine version MFB serves,
countable income of exactly $1,596/mo (120% FPL for household size 1) resolves to **SLMB**; QI
starts at $1,597/mo.
**Expected**: Eligible as **SLMB** — $202.90/month (not QI). A companion check one dollar higher ($1,617/mo gross → $1,597/mo countable) should resolve to **QI**, same $202.90/month — run both to confirm the exact crossover point, not just one side of it.

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,616` per month (100% FPL for household of 1 is $1,330/mo; after PE's $20/mo general SSI disregard, countable income = $1,596/mo = exactly 120% FPL), Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Current Benefits**: Select no current benefits
- **Assets**: Household resources: `$3,000`

**Why this matters**: A pure boundary test. Assert the category, not just the dollar amount — 42 CFR and PolicyEngine's newer source place this point in QI, so a PolicyEngine version bump will flip the expected category at the same dollar value, and that should surface as a visible test update.

---

### Scenario 10: Income At the 135% FPL Ceiling — Must Be Ineligible
**What we're checking**: 135% FPL is an exclusive ceiling (42 CFR 435.125(b), "less than 135 percent"), not an included endpoint. Countable income of $1,795/mo is still QI-eligible; $1,796/mo is not. The unrounded cutoff is $1,795.50.
**Expected**: Not eligible (income at/above the QI ceiling)

**Steps**:
- **Location**: Enter ZIP code `65101`, Select county `Cole`
- **Household**: Number of people: `1`
- **Person 1 (Head of Household)**: Birth month/year: `March 1955` (age 71), Relationship: `Head of Household`, Has income: `Yes`, Social Security income: `$1,816` per month (after the $20/mo disregard, countable income = $1,796/mo — Missouri's own published 135% FPL figure), Citizenship: `U.S. Citizen`, Insurance: `Medicare`
- **Assets**: Household resources: `$3,000`

**Why this matters**: Confirms the top income ceiling (135% FPL) is enforced as a hard, exclusive cutoff, not a soft/highest-tier catch-all.
