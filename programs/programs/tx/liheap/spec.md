# Implement LIHEAP (TX) Program

## Program Details

- **Program**: LIHEAP (TX Comprehensive Energy Assistance Program / CEAP)
- **State**: TX
- **White Label**: tx
- **Research Date**: 2026-06-09

---

## Eligibility Criteria

1. **Household gross income must be at or below 150% of the Federal Poverty Level (FPL)**

   - Screener fields:
     - `household_size`
     - `income` (all types via `calc_gross_income`)
   - Source: TX LIHEAP State Plan FFY 2026 (incl. Amendment #1, apprvd 2026-02-18), Sections 2.1 and 3.1; 10 TAC §6.307(a) (verified — full text: "income eligibility level is at or below 150% of the federal poverty level in effect at the time the customer makes an application"); https://liheapch.acf.gov/delivery/income_eligibility.htm
   - Notes: 2026 FPL tables apply (mandatory for FFY 2026 per LIHEAP Clearinghouse income_eligibility.htm). Income eligibility threshold is 150% FPL for all components (heating, cooling, crisis, weatherization). Verified against PolicyEngine `gov.states.tx.tdhca.ceap.income_limit` (1.5 × FPG; cites 10 TAC §6.307). Benefit tiers are separately defined at 10 TAC §6.309(e).

2. **Categorical eligibility: Households where at least one member receives TANF, SSI, SNAP, or needs-tested veterans' benefits (VA pension) are categorically income-eligible**

   - Screener fields:
     - `has_tanf`
     - `has_ssi`
     - `has_snap`
     - `income_streams[].type === 'veteran'` (Veteran's Pension or Benefits under Government Benefits income category)
   - Source: 42 U.S.C. § 8624(b)(2)(A); 10 TAC §6.307(b) (verified — lists exactly SSI, Means-Tested Veterans Program payments, SNAP, and TANF); TX LIHEAP State Plan FFY 2026, Sections 1.4 and 1.6; https://liheapch.acf.gov/delivery/income_categorical.htm
   - Notes: Categorically eligible households bypass the income check for eligibility determination. Income is still collected and used to determine benefit tier. For VA pension: we treat any `veteran` income stream as the qualifying pathway — an inclusivity assumption. VA pension (means-tested) qualifies; VA compensation (not means-tested) technically does not, but the screener cannot distinguish between them. Surface in program description: "Households receiving VA pension benefits may qualify automatically."

3. **Must reside in the state of Texas**

   - Screener fields:
     - `zipcode`
     - `county`
   - Source: TX LIHEAP State Plan FFY 2026, Section 8 (Agency Designation); 42 U.S.C. § 8622(5)

4. **Household must be responsible for paying home energy costs (directly or as part of rent)** ⚠️ *data gap*

   - Screener fields: none
   - Source: 42 U.S.C. § 8622(6) definition of 'home energy'; 10 TAC §6.309(i)(1) and (i)(7) (verified — assistance is structured as payments against the household's energy bills/consumption history, or to landlords for renters who pay utilities indirectly; no standalone TAC eligibility criterion exists — the obligation requirement is implicit in the payment structure); TX LIHEAP State Plan FFY 2026
   - Notes: The applicant must have a home energy cost obligation — either paying a utility directly or having energy costs included in rent. This includes renters whose landlord bills energy costs as part of rent (confirmed: per 10 TAC §6.309(i)(7), quoted in State Plan §2.3, subrecipients may pay landlords on behalf of renters who pay utilities indirectly). Households in institutions where energy is fully covered by the institution (nursing homes, prisons, dormitories) are excluded as they would not have a personal energy cost obligation. The screener does not collect this information. For the calculator, we assume all households are responsible for their own energy costs — an inclusivity assumption. Users in fully-subsidized institutional housing who don't pay energy costs will need to self-select out. Surface in program description: "You must be responsible for paying your own energy bills — either directly or through your rent."
   - Related shared-meter rule (10 TAC §6.307(f), quoted in State Plan §2.2): a dwelling unit cannot be served if its meter is shared with another household that is not part of the application (unless they apply together as one household). Not capturable by the screener — same inclusivity assumption applies; affected households are an edge case.
   - Screener improvement: Add a follow-up yes/no question triggered when heating or cooling expense > $0: "Is your household responsible for paying its own energy bills?" Proposed field: `pays_own_energy_bills` (household level).

5. **Household must not have already received LIHEAP assistance for the current program year** (partially evaluable)

   - Screener fields: `has_tx_liheap` (proposed — pending addition to TX white label existing benefits config; no generic `has_liheap` field exists in the system today)
   - Source: 10 TAC §6.309(b) (verified — total annual benefit capped at $12,600 per Program Year, not including arrears), §6.309(e) (per-component annual maximums), §6.309(i)(1)(B)–(C) (vulnerable households: remaining bills within the Program Year; non-vulnerable: up to six remaining bills); TX LIHEAP State Plan FFY 2026
   - Notes: Partially evaluable — if the household indicates current LIHEAP receipt in the existing benefits step, the screener can exclude them. Prior receipt in the same program year that isn't declared by the user cannot be verified. Assumption: household has not previously received LIHEAP this program year unless declared. Nuance per §6.309(i)(1): this is not literally a one-payment rule — benefits are paid against bills over the year up to the tier maximum (vulnerable households: all remaining bills; non-vulnerable: up to six) — but a household already enrolled this program year has its benefit in use, so excluding it from results remains correct. Surface in program description: "If you have already received LIHEAP this program year, you are not eligible to reapply."
   - Screener improvement: Add LIHEAP to TX existing benefits step under a new "Housing & Utilities" category. Field: `has_tx_liheap` (new — the existing field is `has_il_liheap`, which is IL-specific; TX needs its own per the white-label field pattern).

6. **Crisis assistance: Household must have a qualifying home energy crisis to access the crisis component** (partially evaluable)

   - Screener fields: `electricity_is_disconnected`, `has_past_due_energy_bills` (frontend-only fields, currently Energy Calculator flow only — not yet available in standard screener)
   - Source: 10 TAC §6.310; TX LIHEAP State Plan FFY 2026, Section 4
   - Notes: This criterion gates the crisis component only — not the main utility assistance program. Crisis assistance is available to households that have lost service or are in immediate danger of losing service under one of three conditions (10 TAC §6.301, State Plan §4.2): extreme weather (48-hour response), disaster (48-hour response), or life-threatening crisis (18-hour response). A disconnect notice qualifies as "in immediate danger of losing service." **Crisis maximums are tiered by the same income brackets as utility assistance** ($1,800 / $1,500 / $1,200 per component per 10 TAC §6.309(e), confirmed State Plan §4.7) — "up to $1,800" is the 0–50% FPG maximum, not a flat cap. Initial assistance payments that include arrears do not count toward the $12,600 annual cap (State Plan §4.7). Partially evaluable: `electricity_is_disconnected` and `has_past_due_energy_bills` exist in the Energy Calculator flow but not the standard screener. Assumption: no crisis unless declared by user. Surface in program description: "If your electricity or gas has been shut off, or you have a disconnect notice or past-due bill, you may qualify for additional crisis assistance of up to $1,800."
   - Screener improvement: Surface `electricity_is_disconnected` and `has_past_due_energy_bills` from the Energy Calculator into the standard screener as yes/no questions in the Utilities section of the Expenses step.

7. **At least one household member must be a U.S. citizen, U.S. national, or Qualified Alien** (handled via results-page citizenship filter)

   - Screener fields: none directly — enforced by `legal_status_required` in the program config (MFB results-page citizenship filter)
   - Source: 10 TAC §6.307(g) (verified — full text: "Unqualified Aliens are not eligible to receive CEAP benefits," except certain crisis items per §6.310(c)(4) and (d); "Mixed Status Households shall not be denied CEAP assistance based solely on the presence of a non-qualified member, except if the member is the sole member of the Household"; status documented per 10 TAC §1.410 and verified via SAVE); TX LIHEAP State Plan FFY 2026 Amendment #1, Section 4.3; 8 U.S.C. § 1611 (PRWORA)
   - Notes: The config sets `legal_status_required: [citizen, gc_5plus, gc_5less, refugee, otherWithWorkPermission]`. Note `otherWithWorkPermission` is broader than "Qualified Alien" (e.g., DACA recipients have work permission but are not qualified aliens) — retained as an inclusivity assumption since mixed-status households qualify as long as at least one member has qualified status (§6.307(g)). `non_citizen` (undocumented) is excluded — correct per the rule, since a sole-member unqualified household is ineligible.
   - Mixed-status benefit pro-ration (10 TAC §6.309(c)–(d), not modeled): income of ALL members 18+ is counted including unqualified aliens, but unqualified aliens are EXCLUDED from household size for eligibility/benefit determination, and categorical/vulnerable status held only by unqualified members doesn't count. The screener doesn't capture per-member immigration status, so PE evaluates the full household — an inclusivity assumption that may overstate the benefit tier for mixed-status households.

---

## Priority Criteria

These criteria do not gate eligibility — they affect processing priority and benefit-payment treatment among eligible households. Verified against State Plan §§2.3, 3.3, and 4.7: priority applies to the heating, cooling, AND crisis components. Per 10 TAC §6.307(e), **High Energy Burden is the highest-rated item** in sliding-scale priority determinations. "Young children" means under age 6 per the Vulnerable Population definition in 10 TAC §6.2. Households with a vulnerable member (elderly, disabled, young child) also have no limit on the number of benefit payments within the year, though tier maximums still apply (State Plan §2.4).

1. **Households with elderly members (age 60 or older)**
   - Screener fields: `birth_month`, `birth_year` (derived `age`)
   - Source: 42 U.S.C. § 8624(b)(5); TX LIHEAP State Plan FFY 2026, Sections 2.4 and 3.4; 10 TAC §6.307(e)

2. **Households with disabled members**
   - Screener fields: `disabled` (HouseholdMember)
   - Source: 42 U.S.C. § 8624(b)(5); TX LIHEAP State Plan FFY 2026; 10 TAC §6.307(e)

3. **Households with young children (under age 6)**
   - Screener fields: `birth_month`, `birth_year` (derived `age`)
   - Source: 42 U.S.C. § 8624(b)(5); TX LIHEAP State Plan FFY 2026; 10 TAC §6.307(e)

4. **Households with high energy burden or high energy consumption**
   - Screener fields: `income` (all types via `calc_gross_income`), `expenses` (energy-related)
   - Source: 42 U.S.C. § 8624(b)(5); TX LIHEAP State Plan FFY 2026; 10 TAC §6.307(e)

---

## Benefit Value

The benefit is a variable annual amount based on household income as a percentage of the Federal Poverty Guidelines (FPG), administered through the Utility Assistance component. PE calculates the benefit as `min(tier_maximum, energy_expenses)` using reported heating and cooling expenses — consistent with MFB precedent for energy programs.

> **Important for testing:** Because PE caps the benefit at reported energy expenses, every eligible test scenario must include a heating or cooling expense of at least `tier_maximum / 12` per month — otherwise PE returns $0. All eligible scenarios below include **heating `$200/month`** ($2,400/year, ≥ all tier maximums).

> ⚠️ **Known PE income-definition gap:** PE's `tx_ceap` computes income as `irs_gross_income` (IRC §61), which counts only the *taxable* portion of Social Security (≈ $0 at these income levels) and excludes SSI entirely. TDHCA's actual rules (10 TAC §6.4; State Plan §1.9) count **gross** SSA benefits and SSI. Expected values below follow the program rules; until the PE income measure is aligned, scenarios whose income is mostly Social Security or SSI (S1, S6, S8, S13) will return **$1,800** from the live calculator instead of the values below. Wage-based scenarios are unaffected (MFB maps wages → `irs_employment_income` ✓), and VA pension is unaffected (`veteran` → `taxable_pension_income`, which IS counted ✓). See Open Dev Items.

**Methodology — income tier maximums (2026):**

- 0–50% FPG → maximum **$1,800/year**
- 51–75% FPG → maximum **$1,500/year**
- 76–150% FPG → maximum **$1,200/year**

**Additional components (not calculated by PE — surface in program description):**

- Crisis Assistance → up to **$1,800** additional, tiered by the same income brackets ($1,800 / $1,500 / $1,200 per component) — requires qualifying crisis condition per 10 TAC §6.310
- HVAC repair/replacement → up to **$9,000** (per 10 TAC §6.309 and §6.311)
- Total household cap → **$12,600/year**

**Value format:** `estimated_annual`

**Sources:** 10 TAC §6.309(e); TX LIHEAP State Plan FFY 2026, Sections 2.6 and 3.6, and Amendment #1 (apprvd 2026-02-18 — tier maximums, crisis, HVAC, and $12,600 cap reconfirmed); https://liheapch.acf.gov/tables/benefits.htm; TX_BenefitMatrix_Heat-Cool_2026.pdf (https://liheapch.acf.gov/docs/2026/benefits-matricies/TX_BenefitMatrix_Heat-Cool_2026.pdf). Verified against PolicyEngine parameters `gov.states.tx.tdhca.ceap.utility_assistance.max_amount` (1,800 / 1,500 / 1,200 effective 2025-01-01).

---

## Implementation Coverage

- ✅ Fully evaluable: 3 (income threshold, categorical eligibility, TX residency)
- ✅ Handled by platform: 1 (legal status — results-page citizenship filter via `legal_status_required`)
- ⚠️ Partially evaluable: 2 (prior LIHEAP receipt, crisis assistance)
- ⚠️ Data gap (inclusivity assumption): 1 (energy cost responsibility, incl. shared-meter rule)

3 of 7 criteria are fully evaluable with current screener fields, plus 1 handled by the platform's citizenship filter. The core evaluable criteria cover income eligibility (150% FPL), categorical eligibility via TANF/SSI/SNAP/VA pension, and Texas residency. Energy cost responsibility is handled via an inclusivity assumption. Prior LIHEAP receipt and crisis assistance are partially evaluable through the existing benefits step and frontend-only Energy Calculator fields respectively.

**Income counting note:** State Plan §1.8 confirms TX uses **gross income** (with exceptions for self-employment/farm/gambling income per 10 TAC §6.4) — consistent with `calc_gross_income`. The §1.9 countable-income checklist's checkbox states do not survive PDF text extraction; itemized countable/excluded income types could not be verified line-by-line.

**PE coverage note:** `tx_ceap_eligible` currently implements categorical eligibility for TANF, SNAP, and SSI only. VA pension is not yet implemented — see Open Dev Items.

---

## Research Sources

- [[Provided] TX_Plan_2026.pdf](https://liheapch.acf.gov/docs/2026/state-plans/TX_Plan_2026.pdf)
- [TDHCA 2026 LIHEAP State Plan (apprvd 9-18-2025)](https://www.tdhca.texas.gov/sites/default/files/community-affairs/docs/2026-LIHEAP-STATE-PLAN-apprvd-09-18-2025.pdf)
- [TDHCA 2026 LIHEAP State Plan Amendment #1 (apprvd 2-18-2026)](https://www.tdhca.texas.gov/sites/default/files/community-affairs/docs/26-LIHEAP-Plan-Amend1.pdf) — verified 2026-06-10: 150% FPL limit, categorical eligibility (SNAP/TANF/SSI/means-tested veterans), and benefit tiers unchanged
- [[Provided] income_eligibility.htm](https://liheapch.acf.gov/delivery/income_eligibility.htm)
- [[Provided] income_categorical.htm](https://liheapch.acf.gov/delivery/income_categorical.htm)
- [[Provided] benefits.htm](https://liheapch.acf.gov/tables/benefits.htm)
- [[Provided] TX_BenefitMatrix_Heat-Cool_2026.pdf](https://liheapch.acf.gov/docs/2026/benefits-matricies/TX_BenefitMatrix_Heat-Cool_2026.pdf)

---

## Acceptance Criteria

All eligible scenarios assume **heating expense `$200/month`** is entered in the Expenses step (required for PE to return a non-zero value — see Benefit Value).

- [ ] Scenario 1 (Clearly Eligible Low-Income Elderly Household): User should be **eligible** with **$1,500/year** ⚠️ *PE income-definition gap: live calculator will return $1,800 until resolved*
- [ ] Scenario 2 (Minimally Eligible Single Adult at Income Ceiling): User should be **eligible** with **$1,200/year**
- [ ] Scenario 3 (Family of 4 with Income Just Below 150% FPL): User should be **eligible** with **$1,200/year**
- [ ] Scenario 4 (VA Pension Categorical Eligibility): User should be **eligible** with **$1,500/year** ⚠️ *pending VA pension PE contribution*
- [ ] Scenario 5 (Family of 3 with Income Just Above 150% FPL — Ineligible): User should be **ineligible**
- [ ] Scenario 6 (Person Exactly Age 60 — Elderly Priority Threshold): User should be **eligible** with **$1,200/year** ⚠️ *PE income-definition gap: live calculator will return $1,800 until resolved*
- [ ] Scenario 7 (Person Age 59 — Just Below Elderly Priority Threshold): User should be **eligible** with **$1,200/year**
- [ ] Scenario 8 (Person Age 78 — Well Above Elderly Priority Threshold): User should be **eligible** with **$1,200/year** ⚠️ *PE income-definition gap: live calculator will return $1,800 until resolved*
- [ ] Scenario 9 (Household with Young Child — Under-6 Priority): User should be **eligible** with **$1,200/year**
- [ ] Scenario 10 (Household Already Receiving LIHEAP — Exclusion Check): User should be **ineligible** ⚠️ *pending `has_tx_liheap` addition to TX config*
- [ ] Scenario 11 (SNAP Categorical Eligibility): User should be **eligible** with **$1,200/year**
- [ ] Scenario 12 (Mixed Household — High-Income Working Adult): User should be **ineligible**
- [ ] Scenario 13 (Multiple Priority Members — Elderly, Disabled, Young Child): User should be **eligible** with **$1,200/year** ⚠️ *PE income-definition gap: live calculator will return $1,800 until resolved (PE counts only the wages — 37.2% FPL)*
- [ ] Scenario 14 (Household of 1 with Zero Income): User should be **eligible** with **$1,800/year**

Expected values reflect TDHCA program rules (gross income incl. SSA benefits and SSI per 10 TAC §6.4 and State Plan §1.9). Scenarios flagged with the PE income-definition gap will diverge in the live calculator until the PE income measure is aligned — see the Benefit Value note and Open Dev Items.

---

## Test Scenarios

### Scenario 1: Clearly Eligible Low-Income Elderly Household in Texas

**What we're checking**: Elderly couple with low income in the 51–75% FPL tier, receiving SSI — meets income, categorical eligibility (SSI), TX residency, and elderly priority criteria. Golden path scenario covering the middle benefit tier.

**Expected**: Eligible, **$1,500/year**

**Steps**:
- **Location**: ZIP `78702`, county `Travis`
- **Household**: 2 people
- **Person 1**: Birth `March 1958` (age 68), head of household, Social Security Retirement `$700/month`
- **Person 2**: Birth `July 1960` (age 65), spouse, SSI `$500/month`
- **Expenses**: Heating `$200/month`
- **Current Benefits**: SSI → Yes

**Why this matters**: Golden path scenario for an elderly couple. Combined income $1,200/month = $14,400/year. 2026 FPL for HH2 = $21,640; 66.5% FPL → 51–75% tier → $1,500/year. Validates SSI categorical eligibility and elderly priority. Covers the 51–75% benefit tier not represented in other scenarios.

---

### Scenario 2: Minimally Eligible Single Adult at Income Ceiling

**What we're checking**: Single adult with gross income exactly at the 150% FPL ceiling for HH1, no priority categories — verifies bare minimum eligibility

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `79901`, county `El Paso`
- **Household**: 1 person
- **Person 1**: Birth `September 1991` (age 34), head of household, not disabled, no priority categories, wages `$1,995/month`
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: Tests the income ceiling is inclusive (at or below). 2026 FPL for HH1 = $15,960; 150% = $23,940/year = $1,995/month. At exactly 150% FPL → 76–150% tier → $1,200/year. Confirms priority categories are not required for basic eligibility.

---

### Scenario 3: Family of 4 with Income Just Below 150% FPL Threshold

**What we're checking**: Household of 4 with gross income $60 below the 150% FPL annual threshold is correctly determined eligible

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `75201`, county `Dallas`
- **Household**: 4 people
- **Person 1**: Birth `March 1988` (age 38), head of household, wages `$3,270/month`
- **Person 2**: Birth `July 1990` (age 35), spouse, wages `$850/month`
- **Person 3**: Birth `January 2018` (age 8), child, no income
- **Person 4**: Birth `September 2021` (age 4), child, no income
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: Boundary test for a larger household. Combined income $4,120/month = $49,440/year. 2026 FPL for HH4 = $33,000; 150% = $49,500. At 149.8% FPL → 76–150% tier → $1,200/year. Confirms the system doesn't incorrectly exclude households at the margin.

---

### Scenario 4: VA Pension Categorical Eligibility

**What we're checking**: Household with a veteran receiving VA pension income is categorically eligible via the `veteran` income stream type

**Expected**: Eligible, **$1,500/year** ⚠️ *pending VA pension addition to `tx_ceap_eligible` in PolicyEngine (see Open Dev Items); until then this household still passes the 150% FPL income test, so eligibility holds — but the categorical branch itself is not exercised*

**Steps**:
- **Location**: ZIP `78701`, county `Travis`
- **Household**: 1 person
- **Person 1**: Birth `April 1958` (age 68), head of household, Government Benefits → Veteran's Pension or Benefits `$800/month`
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: Tests the VA pension categorical eligibility pathway per 42 U.S.C. § 8624(b)(2)(A). Income $800/month = $9,600/year; 60.2% of 2026 FPL for HH1 ($15,960) → 51–75% tier → $1,500/year. Screener captures this via `income_streams[].type === 'veteran'`. Distinct from VA health care or VA compensation.

---

### Scenario 5: Family of 3 with Income Just Above 150% FPL Threshold — Ineligible

**What we're checking**: Household of 3 with gross income just over the 150% FPL threshold is correctly determined ineligible

**Expected**: Ineligible

**Steps**:
- **Location**: ZIP `75201`, county `Dallas`
- **Household**: 3 people
- **Person 1**: Birth `March 1988` (age 38), head of household, wages `$2,900/month`
- **Person 2**: Birth `July 1990` (age 35), spouse, wages `$600/month`
- **Person 3**: Birth `September 2016` (age 9), child, no income
- **Current Benefits**: None (no TANF, SSI, or SNAP)

**Why this matters**: Critical ineligible boundary test. Combined income $3,500/month = $42,000/year. 2026 FPL for HH3 = $27,320; 150% = $40,980. At 153.7% FPL — just over the limit with no categorical eligibility pathway → correctly ineligible.

---

### Scenario 6: Person Exactly Age 60 — Elderly Priority Threshold

**What we're checking**: Household member exactly age 60 correctly receives elderly priority designation per 42 U.S.C. § 8624(b)(5). Note: priority status does not gate eligibility — this person is income-eligible regardless of age. Tests that the elderly flag is applied at exactly age 60, not 61.

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `78701`, county `Travis`
- **Household**: 1 person
- **Person 1**: Birth `January 1966` (age 60), head of household, Social Security Retirement `$1,200/month`
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: Boundary test for elderly priority designation. Income $1,200/month = $14,400/year; 90.2% of 2026 FPL for HH1 ($15,960) → 76–150% tier → $1,200/year. Catches off-by-one errors in age calculations at the exact 60-year threshold.

---

### Scenario 7: Person Age 59 — Just Below Elderly Priority Threshold

**What we're checking**: Person aged 59 does not receive elderly priority designation but remains income-eligible. Complements Scenario 6 — confirms the elderly boundary is exactly 60, not 59.

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `77001`, county `Harris`
- **Household**: 1 person
- **Person 1**: Birth `March 1967` (age 59), head of household, wages `$1,500/month`
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: Confirms the off-by-one boundary from the other direction. Income $1,500/month = $18,000/year; 112.8% of 2026 FPL for HH1 ($15,960) → 76–150% tier → $1,200/year. Person is eligible on income grounds but should not receive elderly priority flag.

---

### Scenario 8: Person Age 78 — Well Above Elderly Priority Threshold

**What we're checking**: Person well above the age 60 elderly threshold is correctly identified as eligible with elderly priority status. Complements Scenario 6 by confirming the flag works broadly, not just at the boundary.

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `79901`, county `El Paso`
- **Household**: 1 person
- **Person 1**: Birth `January 1948` (age 78), head of household, Social Security Retirement `$1,100/month`, Medicare
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: A 78-year-old on fixed Social Security is a core LIHEAP target population. Income $1,100/month = $13,200/year; 82.7% of 2026 FPL for HH1 ($15,960) → 76–150% tier → $1,200/year. Confirms elderly priority is reliably assigned beyond the boundary, not just at it.

---

### Scenario 9: Household with Young Child — Under-6 Priority Designation

**What we're checking**: Household containing a child under age 6 correctly receives young child priority designation per 42 U.S.C. § 8624(b)(5) and TX LIHEAP State Plan FFY 2026

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `77001`, county `Harris`
- **Household**: 2 people
- **Person 1**: Birth `March 1980` (age 46), head of household, wages `$1,800/month`
- **Person 2**: Birth `September 2020` (age 5), child, no income
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: Tests that a household with a child under 6 correctly receives young child priority status. Income $1,800/month = $21,600/year; 99.8% of 2026 FPL for HH2 ($21,640) → 76–150% tier → $1,200/year. Priority status doesn't gate eligibility but should be flagged correctly.

---

### Scenario 10: Household Already Receiving LIHEAP — Exclusion Check

**What we're checking**: Household currently receiving LIHEAP is correctly excluded from results

**Expected**: Ineligible

⚠️ *Not currently testable — requires `has_tx_liheap` to be added to the TX existing benefits config under a new "Housing & Utilities" category (screener gap 2). Retain for testing once that gap is addressed.*

**Steps**:
- **Location**: ZIP `75201`, county `Dallas`
- **Household**: 2 people
- **Person 1**: Birth `March 1960` (age 66), head of household, Social Security Retirement `$900/month`
- **Person 2**: Birth `July 1962` (age 63), spouse, Social Security Retirement `$750/month`
- **Current Benefits**: LIHEAP → Yes

**Why this matters**: Households already receiving LIHEAP should not be prompted to reapply. Combined income $1,650/month = $19,800/year; 91.5% of 2026 FPL for HH2 ($21,640) → would be eligible on income grounds, making the exclusion logic critical to test correctly.

---

### Scenario 11: SNAP Categorical Eligibility

**What we're checking**: Household receiving SNAP is categorically eligible for LIHEAP regardless of income verification, per 42 U.S.C. § 8624(b)(2)(A)

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `78701`, county `Travis`
- **Household**: 3 people
- **Person 1**: Birth `March 1990` (age 36), head of household, wages `$1,800/month`
- **Person 2**: Birth `July 1992` (age 33), spouse, wages `$1,200/month`
- **Person 3**: Birth `January 2022` (age 4), child, no income
- **Expenses**: Heating `$200/month`
- **Current Benefits**: SNAP → Yes

**Why this matters**: Tests the SNAP categorical eligibility pathway. Combined income $3,000/month = $36,000/year; 131.8% of 2026 FPL for HH3 ($27,320) → 76–150% tier → $1,200/year. Income is within the limit so this also passes the income test, but the key branch being tested is categorical eligibility. Household also has a child under 6, triggering young child priority.

---

### Scenario 12: Mixed Household — Elderly Disabled Member with High-Income Working Adult

**What we're checking**: Total household gross income is aggregated across all members against the household-size-appropriate FPL threshold, even when the household contains members with priority status

**Expected**: Ineligible

**Steps**:
- **Location**: ZIP `78745`, county `Travis`
- **Household**: 4 people
- **Person 1**: Birth `March 1960` (age 66), head of household, **disabled**, Social Security Retirement `$900/month`
- **Person 2**: Birth `August 1990` (age 35), child (adult — select "Child"), wages `$4,200/month`
- **Person 3**: Birth `January 1993` (age 33), daughter-in-law (select "Other"), wages `$1,500/month`
- **Person 4**: Birth `November 2022` (age 3), grandchild (select "Grandchild"), no income
- **Current Benefits**: None (no TANF, SSI, or SNAP)

**Why this matters**: Confirms that priority criteria (elderly, disabled, young child) do not bypass the income eligibility requirement. Combined income $6,600/month = $79,200/year; 240% of 2026 FPL for HH4 ($33,000) → correctly ineligible regardless of vulnerable household members.

---

### Scenario 13: Multiple Priority Members — Elderly, Disabled, and Young Child

**What we're checking**: Household with members triggering multiple priority criteria simultaneously (elderly disabled head, elderly spouse, young child) is correctly identified as eligible with all priority flags applied

**Expected**: Eligible, **$1,200/year**

**Steps**:
- **Location**: ZIP `78201`, county `Bexar`
- **Household**: 5 people
- **Person 1**: Birth `February 1958` (age 68), head of household, **disabled**, Social Security Retirement `$1,100/month`
- **Person 2**: Birth `October 1960` (age 65), spouse, Social Security Retirement `$900/month`
- **Person 3**: Birth `March 1990` (age 36), child (adult — select "Child"), wages `$1,200/month`
- **Person 4**: Birth `July 1996` (age 29), other, no income
- **Person 5**: Birth `November 2023` (age 2), grandchild (select "Grandchild"), no income
- **Expenses**: Heating `$200/month`
- **Current Benefits**: SSI → Yes

**Why this matters**: Tests a multi-generational household where three distinct priority flags apply simultaneously — elderly (68, 65), disabled, and young child (age 2). Income $3,200/month = $38,400/year; 99.3% of 2026 FPL for HH5 ($38,680) → 76–150% tier → $1,200/year. Also validates SSI categorical eligibility alongside income-based eligibility.

---

### Scenario 14: Household of 1 with Zero Income

**What we're checking**: Single adult with no income is correctly identified as eligible at the maximum benefit tier

**Expected**: Eligible, **$1,800/year**

**Steps**:
- **Location**: ZIP `79901`, county `El Paso`
- **Household**: 1 person
- **Person 1**: Birth `September 1991` (age 34), head of household, no income sources
- **Expenses**: Heating `$200/month`
- **Current Benefits**: None

**Why this matters**: Edge case testing the absolute minimum income boundary. $0 income = 0% of 2026 FPL for HH1 ($15,960) → 0–50% tier → $1,800/year — the maximum benefit. Heating expense of $200/month ($2,400/year) exceeds the $1,800 tier maximum, so PE returns the full tier amount. Confirms the calculator handles zero income correctly and that the most vulnerable applicants with no income receive the highest tier benefit.

---

## Pre-Handoff Notes (Dev Items)

1. **PE contribution — VA pension:** Add `veteran` income stream to `tx_ceap_eligible.py` (current categorical formula: TANF | SNAP | SSI only).
2. **PE contribution — income measure:** `tx_ceap`/`tx_ceap_eligible` use `irs_gross_income`, which counts only taxable Social Security and excludes SSI — contrary to 10 TAC §6.4 / State Plan §1.9 (gross income incl. SSA benefits and SSI). Until fixed, SS/SSI-income households are shown the $1,800 tier regardless of actual tier (affects acceptance Scenarios 1, 6, 8, 13). Raise alongside item 1.
3. **Screener gap:** Add `has_tx_liheap` to the TX white-label existing-benefits step under a new "Housing & Utilities" category (no generic `has_liheap` exists; `has_il_liheap` is IL-specific). Unblocks Scenario 10.
4. **Screener gap:** Surface `electricity_is_disconnected` / `has_past_due_energy_bills` from the Energy Calculator into the standard screener (crisis component).
5. **Screener gap (optional):** `pays_own_energy_bills` household-level question (criterion 4 data gap).
6. **Import pre-check:** Confirm a 2026 `FederalPoveryLimit` row exists — the importer only *warns* if `year` lookup fails, which would silently ship the program with no income test. Run with `--dry-run` first.
7. **Verify:** `show_in_has_benefits_step: false` — check whether the SNAP Heat-and-Eat exception applies.
8. **Optional admin update:** The reused `211_texas` navigator (shared with `tx_wap`) has a non-E.164 phone and empty email; improved contact info (phone `+18775417905`, email `211@hhs.texas.gov`, "press Option 1") must be applied via admin — the importer does not update existing navigators.

---

## Source Documentation

- https://liheapch.acf.gov/docs/2026/state-plans/TX_Plan_2026.pdf
- https://www.tdhca.texas.gov/sites/default/files/community-affairs/docs/2026-LIHEAP-STATE-PLAN-apprvd-09-18-2025.pdf
- https://www.tdhca.texas.gov/sites/default/files/community-affairs/docs/26-LIHEAP-Plan-Amend1.pdf
- https://liheapch.acf.gov/delivery/income_eligibility.htm
- https://liheapch.acf.gov/delivery/income_categorical.htm
- https://liheapch.acf.gov/tables/benefits.htm
- https://liheapch.acf.gov/docs/2026/benefits-matricies/TX_BenefitMatrix_Heat-Cool_2026.pdf
