# Working Healthy (KS) — Eligibility Specification

## Program Details

- **Program:** Working Healthy (WH) — Kansas's Medicaid buy-in for workers with disabilities.
- **State / White Label:** KS / `ks`
- **Calculator type:** MFB Custom (PE models the sibling program for IL only — `il_hbwd_person`; built in-house using the `awd_medicaid` calculator as the primary precedent)
- **Benefit type:** Health Care (Medicaid coverage)
- **Config year:** 2026 (FPL-based program)

---

## Implementation Coverage

The income, resource, age, employment, disability, insurance, and SSI criteria are all measured by the screener (some with an inclusive assumption on a sub-attribute — e.g. FICA-covered status, minimum-wage rate, asset exemptions). Citizenship (C9) is enforced by the `legal_status_required` config, and KS residency (C7) by white-label routing — neither is a calculator check. The only **true data gaps** (no screener field at all) are the formal SSA disability determination (C2) and the fraud-conviction bar (C10), both handled by inclusive assumption + verification at application. No criterion is blocked.

---

## Eligibility Criteria

1. **Age 16 through 64**
- Screener fields: `birth_year`, `birth_month`
- Source: KEESM §2664.2 (Age and Blindness/Disability Requirements) — coverage runs through the end of the month of the 65th birthday.
- **Handling:** Fully collected via `birth_year` + `birth_month` (the screener derives age from these; the raw `age` field is deprecated for spec criteria). Evaluate the derived age against the 16–64 band (inclusive of the 64-through-end-of-65th-birthday-month rule). No data gap.

2. **Has a qualifying disability or blindness** — *measured via self-report; formal SSA determination is a true data gap (no screener field)*
- Screener fields: `long_term_disability`, `visually_impaired`
- Source: KEESM §2664.2 → §2662. SSA standard: a medically determinable physical/mental impairment expected to last ≥12 months (or result in death); blindness = 20/200 or less in the better eye. Receipt of SSDI or disability-based SSI automatically satisfies the standard. (§2662's separate, lower MediKan Tier-2 disability standard does not apply — Working Healthy requires the full SSA standard.)
- **Handling:** Use the self-reported `long_term_disability` / `visually_impaired` flags as the screening proxy (matching the `awd_medicaid` precedent) — **not** the generic `disabled` flag, which may reflect a short-term condition. Formal SSA/DDS determination happens at application; surface "proof of disability (SSI/SSDI award letter or doctor's statement)" in the program description so applicants not already on SSI/SSDI know it may be required.

3. **Currently employed with earned income** — *measured via earned income streams; FICA/SECA-covered status is an inclusive assumption*
- Screener fields: `has_income`, `income_streams` (earned types: wages, self-employment)
- Source: KEESM §2664.3 (Earned Income Requirement). Earned income must be FICA/SECA-covered.
- **Handling:** Treat any reported earned income stream (`wages` / `selfEmployment`) as meeting the employment requirement. The screener does not capture FICA/SECA withholding, so **assume reported earnings are FICA/SECA-covered** (true for the large majority); actual verification occurs at application. Members with no earned income (e.g., SSDI/SSI only) fail this criterion.

4. **Earnings meet the floor**
- Screener fields: `income_streams` (earned)
- Source: KEESM §2664.3. Earned income must be at/above the federal hourly minimum wage, and countable earned income must exceed the standard earned-income disregard ($65/month).
- **Handling:** Derive from the reported wage amount; compare monthly countable earned income to the $65 disregard floor. *Limitation:* the screener only captures an hourly *rate* when income frequency is `hourly` — for monthly/yearly wage entries it can't verify the "at/above federal minimum wage" rate, so **assume the minimum-wage-rate condition is met** (inclusive default; verified at application). Very low gig earnings below $65/mo countable would not qualify — acceptable for screening.

5. **Countable income at or below 300% of the Federal Poverty Level** for the assistance-plan size — *fully measured; IRWE/BWE/SSI-deeming disregards not collected (conservative)*
- Screener fields: `income_streams`, `household_size`
- Source: KEESM §2664.4 (Financial Requirements) → §7430(4) (Working Healthy standards are poverty-level based); the standard dollar amounts live in Appendix F-8 (KEESM §5120 directs readers to F-8 rather than the numbered DCF sections, which now read "Reserved").
- Methodology (follows the `awd_medicaid` precedent): countable earned = (annual earned − $65) × 0.5; countable unearned = annual unearned − $20; eligible if (countable earned + countable unearned) ≤ FPL[assistance-plan size] × 3.0. The $65/$20 are flat annual deductions (a conservative simplification of the SSI monthly disregards). 2026 individual limit ≈ $47,880/yr ($3,990/mo).
- **Handling:** Apply the standard earned/unearned disregards (methodology above) only. **IRWE, BWE, and SSI couple-deeming are not collected** (IRWE/BWE are niche self-reported disregards; SSI couple-deeming is a calculation method, not a screener field), so the calculator may slightly *overestimate* countable income for affected applicants — conservative, erring toward false negatives. Surfaced in the program description (disability-related work expenses can lower countable income).
- **Assistance-plan sizing:** individual-centric — single → 1-person; married couple → 2-person; child under 18 living with parents → 2-person. This is MFB's policy choice: §2664.5's NOTE states this convention for the *premium* determination; extending it to the income test is a reasonable application to the same "plan," and the 2-person bracket errs stricter (a 3-person bracket would only raise the FPL ceiling). Per §2664.1 (→ §4310), an LTC/HCBS-recipient spouse is excluded from the plan (would size the applicant as 1-person), but the screener can't distinguish an LTC/HCBS-recipient spouse from any other Medicaid-insured spouse, so **assume the spouse is not an LTC/HCBS recipient and keep 2-person sizing** (inclusive — higher FPL ceiling; a rare edge case).
- **Income standards (F-8, "Income Standards for Working Healthy"):** 1-person $3,990/mo, 2-person $5,410/mo, 3-person $6,830/mo, +$1,420 per extra person — the "monthly 300% poverty level standard."

6. **Countable resources at or below $15,000 (for any size family group)** — *measured via `household_assets`; specific asset exemptions not itemized (conservative)*
- Screener fields: `household_assets`
- Source: F-8 (rev. 04-26, Resource Standards): Working Healthy = **$15,000**, does **not** scale with household size. Retirement funds (§5430(20), which explicitly names Working Healthy) and Individual Development Account balances (§6410(34)) are exempt. (KEESM §5130 now reads "Reserved" in the live manual; F-8 is the authoritative source.)
- **Handling:** Compare `household_assets` against the $15,000 flat limit. The screener captures a single total and **cannot break out the retirement/IDA exemptions**, so the figure may slightly *overcount* countable resources (conservative, rare false negatives); exemptions are applied at application. Surfaced in the program description ("some savings, like retirement accounts, may not count toward the limit").

7. **Kansas resident** — *enforced by white-label routing, not this calculator*
- Screener fields: `zipcode`, `county`
- Source: KEESM §2664.1 → §2150 (Residency): "A resident is one who is living in the state voluntarily and not for a temporary purpose (i.e., with no intention of leaving)."
- **Handling:** The KS white label only serves KS residents, so residency is guaranteed upstream — the calculator performs no residency check. (§2150's "intent to remain" standard isn't screener-measurable regardless; assumed genuine and verified at application.)

8. **Not otherwise covered by full Medicaid through another category (and not receiving HCBS waiver services)** — *measured via insurance + SSI; institutional residence is an inclusive assumption*
- Screener fields: `insurance` (Medicaid), `income_streams` (SSI)
- Source: KEESM §2664 (intro); KanCare Working Healthy program page (eligibility list: "Not be receiving Home and Community Based Services," "Not be an SSI recipient," "Not be living in a nursing facility"). SSI recipients and 1619(b) deemed recipients remain in the SI program and are not eligible for Working Healthy. Employed applicants are considered for Working Healthy first.
- **Handling:** Require member `insurance` of none/employer/private (excludes those reporting current Medicaid/Medicare), following `awd_medicaid`. The SSI exclusion is derivable from a reported SSI income stream. **HCBS-waiver recipients are also excluded** by the official eligibility list; because HCBS recipients receive their services through Medicaid, the same `insurance` = Medicaid check catches them — no separate screener field is needed. **Institutional residence** (Working Healthy excludes long-term nursing-facility residents) is *not* collected — assume community-dwelling (the correct default for ~all self-serve users; the inverse of the SSPP failure mode, so safe). The community-residence requirement is **surfaced in the program description** so facility residents understand they aren't eligible. "Consider Working Healthy first" routing is an application-time step.

9. **U.S. citizen or qualified immigrant, subject to the federal 5-year bar for most green-card holders**
- Screener fields: handled via `legal_status_required` config (not a screener or calculator gate)
- Source: KEESM §2664.1 → §2140 (Citizenship and Alienage) → §2142: 15 qualified-non-citizen categories exempt from any wait, plus 3 categories (including ordinary LPRs) subject to a 5-year wait.
- **Handling:** No calculator in `benefits-api` checks immigration status; `legal_status_required` is a `Program`-level filter and is the sole restriction mechanism, so it must encode the actual rule. Set to `["citizen", "refugee", "gc_5plus", "otherWithWorkPermission"]` — excluding `non_citizen` (undocumented/DACA, ineligible for non-emergency Medicaid) and `gc_5less` (LPR under the 5-year bar). `refugee` is the platform's merged "Refugee/Asylee" bucket and `otherWithWorkPermission` ("Other Lawful") is the broad catch-all for the remaining §2142.1 categories (COFA, VAWA, humanitarian parolees). Matches TX's adult-Medicaid precedent (`["citizen", "gc_5plus", "refugee"]`). This is a config-level restriction, not a data gap.

10. **Not convicted of medical assistance fraud** — ⚠️ *true data gap (no screener field)*
- Screener fields: none
- Source: KEESM §2664.1 (General Eligibility Requirements): "Persons convicted of medical assistance fraud per 11221(5) are not eligible."
- **Handling:** The screener has no field for a fraud conviction and it is an exceedingly rare bar; **assume not fraud-convicted** (inclusivity assumption). Not surfaced in the program description (too sensitive/rare); verified at application.
- **Not a criterion:** current incarceration/inmate status. Incarceration suspends Medicaid *payment*, not *eligibility* — a Medicaid-eligible person keeps eligibility while incarcerated — so it is correctly not modeled as an exclusion.

---

## Priority Criteria

**None.** Working Healthy is an entitlement Medicaid buy-in — applicants who meet the criteria are covered, with no waitlist or priority ranking. (The separate *WORK* personal-care-services companion program can have capacity limits, but that is out of scope for this ticket.)

---

## Benefit Value

- **Shape:** Insurance coverage (full Medicaid benefit package; no managed care, no spenddown).
- **Methodology:** the value is the actual cost of the Working Healthy program in Kansas — total program expenditure ÷ average enrollment, from KDHE's Medical Assistance Report (MAR), which tracks Working Healthy as its own population line (separate from SSI Blind/Disabled and Medically Needy Blind/Disabled, the groups that hold most LTSS/HCBS users). For each eligible household member, assign this per-enrollee figure and sum across eligible members. Because the MAR isolates the Working Healthy population, this excludes the LTSS/institutional enrollees that inflate a general disabled-Medicaid average.
- **Value:** **$19,051/year per eligible member** — KS MAR, FY2025 (Jul 2024–Jun 2025): $24,879,015 cumulative Working Healthy expenditure ÷ 1,306 average monthly beneficiaries. Two eligible members → $38,102/year. Stored and displayed as the **annual** value (`value_format: "estimated_annual"`).
- **Premium:** F-8 p.5's premium table gives $0-premium net-income ceilings of $2,993 (1-person) and $4,058 (2- and 3-person) — ~225% of the 1-/2-person 100% FPL benchmark and ~178% of the 3-person benchmark. Above those ceilings, premiums scale from $124 up to $205/month depending on net income and household size (full table in F-8 p.5). American Indian/Alaska Native members are exempt (KEESM §2664.5). The premium is **not** netted from the gross coverage value; it is surfaced in the program description as a potential monthly cost, not calculated. (Net value to a non-AI/AN enrollee is lower by their premium — tribal affiliation isn't collected, a known Benefit-Value gap.)
- **Config:** `estimated_value` = "" (calculator outputs the value); `value_type` = "benefit"; `value_format` = "estimated_annual"; `base_program` = "medicaid".

---

## Test Scenarios

*The 22 scenarios below cover all major eligibility branches: the golden-path eligible case, an ineligible case per each major exclusion criterion, boundary/edge values, both disability paths (long-term disability and blindness), multi-member, assistance-plan sizing (minor-with-parent under both relationship codings, and the unaccompanied-minor 1-person case), and the full mutex set — the already-on-Medicaid case (Sc 9), the SSI/HCBS mutex (Sc 15), and the **children's-Medicaid mutex for a low-income minor** (Sc 2 and Sc 10). Eligible value = $19,051/year per eligible member (annual); $38,102/year for a 2-member eligible household. (KS residency isn't a scenario here — it's enforced by white-label routing, not the calculator.)*

**Criterion 8 mutex depends on regular KanCare eligibility, which is evaluated live.** Working Healthy excludes anyone who qualifies for full Medicaid through another category (`household_eligible` → `medicaid_eligible()`, which reads the `ks_medicaid` result computed on the same screen). Two everyday shapes trip this: an **age-16–18 minor at low income** qualifies for children's KanCare Medicaid (older-child pathway, ≤138% FPL) and a **low-income disabled adult** qualifies for the ABD pathway (countable income ≤ the SSI FBR **and** assets ≤ $2,000). Both are excluded from Working Healthy by design — regular Medicaid is the better coverage and WH is the buy-in for those who earn too much for it. Scenarios that intend to test a WH *edge* (minimum age, the earned-income floor) must therefore put the household **above** the regular-Medicaid threshold, or they are really testing the mutex, not the edge. Sc 2/10 test the minor mutex; Sc 21/22 test the age and earned-income edges with the mutex deliberately not firing.*

### Scenario 1: Clearly eligible disabled worker

**What we're checking**: Typical applicant who meets all criteria — KS resident, disabled, employed, age 16–64, income and resources within limits.
**Expected**: Eligible, value $19,051/year (1 × $19,051)

**Steps**:

* **Location**: Enter ZIP code `66612`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: Baseline happy path. Countable earned income (int(($21,600 − $65) × 0.5) = $10,767/yr — the calculator truncates with `int()`) is well under the 2026 individual limit ($47,880), assets are under $15,000, and the member is a disabled worker — eligible on every dimension.

---

### Scenario 2: Low-income minor covered by children's Medicaid — ineligible (mutex)

**What we're checking**: A disabled, working, age-16 applicant at low income who *independently qualifies for children's KanCare Medicaid*. Working Healthy's Criterion-8 mutex must exclude them — regular Medicaid is the better coverage, and WH is the buy-in for those who earn too much for it.
**Expected**: Not eligible (routes to children's KanCare Medicaid instead)

**Steps**:

* **Location**: Enter ZIP code `66002`, Select county `Atchison`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 2010` (age 16), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$200`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$500`

**Why this matters**: A 16-year-old at $200/mo is far under the children's-Medicaid older-child ceiling (6–18, ≤138% FPL), so `ks_medicaid` returns eligible and the WH `medicaid_eligible()` mutex fires (KEESM §2664 intro — "not otherwise covered by full Medicaid"). This is the everyday case a naive "minimally eligible minor" reading misses: a low-income working disabled minor belongs on children's Medicaid, not the buy-in. The age-16 *floor* itself is tested — without the mutex — in Scenario 21. (Discovery gap corrected: MFB-1066 staging QA flagged that the original spec expected Eligible here and in Sc 10, but the calculator correctly returns Not eligible.)

---

### Scenario 3: Disabled but not currently working — ineligible

**What we're checking**: Disabled applicant with SSDI income only and no earned income — fails the employment requirement.
**Expected**: Not eligible (would route to ABD/spenddown Medicaid instead)

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `No`, Monthly SSDI: `$1,200`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: §2664.3 requires verified earned income — current employment is Working Healthy's defining gate. A disabled person not working is the most representative exclusion (mirrors the WA HWD sibling's primary-exclusion case).

---

### Scenario 4: Not disabled — ineligible

**What we're checking**: A working adult with no qualifying disability.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66612`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `No`, Currently employed: `Yes`, Monthly wages: `$1,800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: §2664.2 requires SSA-level disability or blindness. The disability flag is the screening gate; without it, ineligible.

---

### Scenario 5: Income just under 300% FPL — eligible (edge)

**What we're checking**: Disabled worker whose countable income lands just below the 300% FPL ceiling.
**Expected**: Eligible, value $19,051/year

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 1981` (age 44), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$7,900`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: Countable earned = int(($94,800 − $65) × 0.5) = $47,367 (truncated), just under the 2026 individual limit ($47,880). Confirms the ceiling is inclusive just below and that the earned-income disregard is applied (gross wages alone would falsely exceed the limit).

---

### Scenario 6: Income over 300% FPL — ineligible

**What we're checking**: Disabled worker whose countable income exceeds the 300% FPL ceiling.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 1981` (age 44), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$8,500`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: Countable earned = int(($102,000 − $65) × 0.5) = $50,967 (truncated) > $47,880. Confirms the 300% FPL ceiling and the earned-income disregard from the ineligible side.

---

### Scenario 7: Resources exactly $15,000 — eligible (edge)

**What we're checking**: Disabled worker with countable resources exactly at the limit.
**Expected**: Eligible, value $19,051/year

**Steps**:

* **Location**: Enter ZIP code `66612`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$15,000`

**Why this matters**: §5130 sets the Working Healthy resource limit at $15,000 for any size family group; the limit is inclusive at exactly $15,000.

---

### Scenario 8: Resources over $15,000 — ineligible

**What we're checking**: Disabled worker with countable resources above the limit.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66612`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$20,000`

**Why this matters**: §5130 — $20,000 exceeds the $15,000 limit. (Note: retirement funds and IDA balances are exempt and would not count toward this total.)

---

### Scenario 9: Already enrolled in full Medicaid — ineligible (mutex)

**What we're checking**: Disabled, employed, within limits, but already covered by full Medicaid through another category.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66604`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 1986` (age 39), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,200`, Citizenship: `US Citizen`, Insurance: `Medicaid (currently enrolled)`
* **Assets**: `$3,000`

**Why this matters**: §2664 (intro) — Working Healthy is for those not otherwise covered by full Medicaid; the calculator requires insurance of none/employer/private (excludes current Medicaid/Medicare). SSI/1619(b) recipients and HCBS-waiver recipients are excluded on the same basis.

---

### Scenario 10: Low-income minor covered by children's Medicaid — ineligible (mutex, higher income)

**What we're checking**: The same children's-Medicaid mutex as Scenario 2, at a higher (but still Medicaid-eligible) earned income, to confirm the exclusion isn't an artifact of the near-zero income in Sc 2.
**Expected**: Not eligible (routes to children's KanCare Medicaid instead)

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 2010` (age 16), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$1,000`

**Why this matters**: At $800/mo a single 16-year-old is still well under the children's-Medicaid older-child ceiling (138% FPL HH1 ≈ $1,769/mo of MAGI income), so `ks_medicaid` is eligible and the WH mutex fires. Confirms the exclusion holds across the low-income band, not just at the Sc 2 floor. The age-16 *eligibility* edge (a 16-year-old who is **not** Medicaid-eligible) is Scenario 21. (Discovery gap corrected per MFB-1066 staging QA — the original spec wrongly expected Eligible.)

---

### Scenario 11: Age 15 — below minimum age — ineligible

**What we're checking**: A 15-year-old, one year below the minimum.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `September 2010` (age 15), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$1,000`

**Why this matters**: §2664.2 — below the age-16 floor, ineligible regardless of disability and employment.

---

### Scenario 12: Age exactly 64 — maximum age — eligible

**What we're checking**: A person at the upper age boundary.
**Expected**: Eligible, value $19,051/year

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `January 1962` (age 64), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,200`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: §2664.2 — eligibility runs through the end of the month of the 65th birthday, so age 64 is eligible.

---

### Scenario 13: Age 65 — above maximum age — ineligible

**What we're checking**: A person who has reached 65.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `January 1961` (age 65), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,200`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: §2664.2 — beyond the age-64 ceiling, ineligible (would route to Medicare/aged Medicaid pathways).

---

### Scenario 14: Multi-member — two disabled working spouses — eligible

**What we're checking**: A 2-person household where both members independently meet all criteria; value aggregates across both.
**Expected**: Eligible (both), value $38,102/year (2 × $19,051)

**Steps**:

* **Location**: Enter ZIP code `66044`, Select county `Douglas`
* **Household**: Number of people: `2`
* **Person 1**: Birth month/year: `March 1984` (age 42), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,200`, Citizenship: `US Citizen`, Insurance: `None`
* **Person 2**: Birth month/year: `September 1990` (age 35), Relationship: `Spouse`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$950`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$8,000`

**Why this matters**: Working Healthy is individual-level. Each member is evaluated independently and each eligible member contributes the per-enrollee value, so the household value sums to $38,102/year.

---

### Scenario 15: SSI recipient — ineligible (mutex)

**What we're checking**: Disabled, employed, within income/resource limits, but receiving SSI. SSI recipients remain in the SI program and are excluded from Working Healthy.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `66612`, Select county `Shawnee`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,200`, Monthly SSI: `$700`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$2,000`

**Why this matters**: §2664 (intro) — SSI recipients (and 1619(b) deemed recipients) are excluded even when they are working and otherwise within limits. This is distinct from the already-on-Medicaid case (Sc 9) and the not-working case (Sc 3): here the disqualifier is the reported `sSI` income stream. The KS calculator must add this exclusion (awd_medicaid does not check it explicitly).

---

### Scenario 16: Earnings below the $65/month floor — ineligible

**What we're checking**: Disabled applicant with earned income, but gross monthly earnings at or below the $65/month floor — fails the minimum-earnings requirement.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$50`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$2,000`

**Why this matters**: KEESM §2664.3 / KanCare — eligibility requires "earning more than $65 per month." $50/mo gross is below the floor, so the member is ineligible despite having earned income. Exercises the C4 lower bound (distinct from Sc 3, which has no earned income at all). The KS calculator must enforce gross monthly earned > $65 (awd_medicaid has no employment/earnings floor).

---

### Scenario 17: Legally blind qualifying path — eligible

**What we're checking**: The disability requirement (C2) is satisfied by **blindness** via `visually_impaired`, independently of `long_term_disability` — the other branch of the disability OR.
**Expected**: Eligible, value $19,051/year

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, `visually_impaired`: `Yes`, `long_term_disability`: `No`, Currently employed: `Yes`, Monthly wages: `$1,200`, Insurance: `None`
* **Assets**: `$3,000`

**Why this matters**: KEESM §2664.2 → §2662 treats blindness as a qualifying status distinct from disability. Confirms the calculator qualifies a blind-only applicant; a bug that only honored `long_term_disability` would wrongly deny them.

---

### Scenario 18: Minor living with a parent — 2-person sizing (child coding) — eligible

**What we're checking**: A minor (<18) living with their parent sizes as a **2-person** assistance plan for the income test. Here the minor is the head's **child** (the common relationship coding). The income is chosen to land **between** the 1-person and 2-person 300%-FPL ceilings, so the result depends on getting the sizing right.
**Expected**: Eligible, value $19,051/year (minor only)

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `2`
* **Person 1** (parent): Birth month/year: `March 1980` (age 46), Relationship: `Head of Household`, no earned income, Insurance: `None`
* **Person 2** (minor applicant): Birth month/year: `March 2009` (age 17), Relationship: `Child`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$8,300`, Insurance: `None`
* **Assets**: `$2,000`

**Why this matters**: The minor's countable earned income (int(($99,600 − $65) × 0.5) = $49,767) exceeds the 1-person 300%-FPL ceiling ($47,880) but is under the 2-person ceiling ($64,920). Correct 2-person sizing (minor living with a parent) makes them eligible; 1-person sizing would wrongly deny them. This is the common coding (minor = head's `child`), which a naive "look for a member coded `parent`" check would miss.

---

### Scenario 19: Minor living with a parent — 2-person sizing (parent coding) — eligible

**What we're checking**: The same minor-with-parent case under the **inverted** relationship coding — the minor is the `Head of Household` and the adult is coded `Parent`. Must produce the **same** 2-person sizing and the same result as Scenario 18.
**Expected**: Eligible, value $19,051/year (minor only)

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `2`
* **Person 1** (minor applicant): Birth month/year: `March 2009` (age 17), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$8,300`, Insurance: `None`
* **Person 2** (parent): Birth month/year: `March 1980` (age 46), Relationship: `Parent`, no earned income, Insurance: `None`
* **Assets**: `$2,000`

**Why this matters**: Relationships are stored relative to the head, so a minor-with-parent household can be coded either way (Sc 18 vs. this). Both must size to 2-person; testing only one coding would leave the other branch of `_assistance_plan_size` uncovered.

---

### Scenario 20: Unaccompanied minor, no parent present — 1-person sizing — ineligible

**What we're checking**: A minor (<18) with **no** parent-figure in the household sizes as a **1-person** plan (the parent-present condition must actually gate — it isn't "every minor gets 2-person").
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1** (minor applicant): Birth month/year: `March 2009` (age 17), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$8,300`, Insurance: `None`
* **Assets**: `$2,000`

**Why this matters**: Same $8,300/mo income as Sc 18–19, but with no parent present the plan is 1-person, so countable $49,767 exceeds the 1-person ceiling ($47,880) → ineligible. Confirms the sizing bites in both directions and that "minor living with a parent" is a real condition, not a blanket 2-person rule for all minors.

---

### Scenario 21: Age exactly 16, above children's-Medicaid income — eligible (age floor, mutex not firing)

**What we're checking**: The age-16 minimum-age floor from the *eligible* side, isolated from the children's-Medicaid mutex. A 16-year-old whose household income is **above** the children's-Medicaid older-child ceiling (so `ks_medicaid` is not eligible and Criterion 8 does not fire) but still within Working Healthy's 300% FPL limit. This is the eligible-edge test that Scenario 10 used to (incorrectly) claim.
**Expected**: Eligible, value $19,051/year (minor only)

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `2`
* **Person 1** (parent): Birth month/year: `March 1980` (age 46), Relationship: `Head of Household`, no earned income, Insurance: `None`
* **Person 2** (minor applicant): Birth month/year: `March 2010` (age 16), Relationship: `Child`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$8,300`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$2,000`

**Why this matters**: §2664.2 sets the minimum age at 16, inclusive — a qualifying 16-year-old must be eligible. At $8,300/mo the minor is far over the children's-Medicaid older-child ceiling (138% FPL), so the mutex does **not** fire; the minor-with-parent 2-person sizing (Sc 18) puts countable income ($49,767) under the 2-person 300%-FPL ceiling ($64,920), so Working Healthy admits them. This is the honest age-16 floor test: unlike the original Sc 10 (which tripped the mutex), the only thing keeping a *younger* applicant out here would be the age gate. Pairs with Sc 11 (age 15 → ineligible).

---

### Scenario 22: Minimum earned income above the $65 floor, not Medicaid-eligible — eligible (earned floor, mutex not firing)

**What we're checking**: The $65/month earned-income floor from the *eligible* side — an applicant just above the floor who does **not** qualify for regular Medicaid, so the mutex doesn't mask the result. A disabled adult with minimal earned income but countable resources over the ABD Medicaid limit ($2,000) and under the Working Healthy limit ($15,000).
**Expected**: Eligible, value $19,051/year

**Steps**:

* **Location**: Enter ZIP code `67202`, Select county `Sedgwick`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$100`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: $100/mo gross earned is just over the $65 floor (§2664.3), so the employment gate passes and countable income is negligible — WH-eligible on income and age. The $5,000 in assets *fails* the ABD Medicaid asset test ($2,000 individual limit) so `ks_medicaid` is **not** eligible and the mutex doesn't fire, but is well under the $15,000 Working Healthy resource limit. This isolates the earned-floor's eligible side, complementing Sc 16 (earnings **below** the floor → ineligible). Without the asset spread, a low-income disabled adult would qualify for ABD Medicaid and be excluded by the mutex — exactly the trap that Sc 2/10 fell into.

---

## Program Description Surfacing

Assumptions and limitations are documented inline with each eligibility criterion above. Where a screener limitation could turn an eligible applicant away (or set a wrong expectation), it's addressed in the program `description`:

1. **Income/work expenses** (false-negative): "You may still qualify even if your income or savings look too high. Certain disability-related work expenses can be subtracted from the income that counts…"
2. **Asset exemptions** (false-negative): "…and some savings — like retirement accounts — may not count toward the savings limit."
3. **Disability proof**: "You may need to show proof of your disability, such as an SSI or SSDI award letter or a doctor's statement."
4. **Community residence** (false-positive expectation-setting): "To get this coverage you must live in the community, not a long-term care facility."

SSN, assignment of rights, and inmate status are administrative/procedural, not eligibility criteria, and are not screened.

---

## Implementation Notes

- **Eligibility-logic precedent:** `co/medicaid/adult_with_disability/calculator.py` (`awd_medicaid`) — reuse its structure (per-member eligibility, disability check via `long_term_disability`/`visually_impaired`, insurance-types check, and the SSI-disregard income test). Its income methodology: `earned = max(0, (calc_gross_income("yearly", ["earned"]) − 65) × 0.5)` and `unearned = calc_gross_income("yearly", ["unearned"]) − 20` — a flat $65 / $20 deduction applied to the annual figure. Working Healthy mirrors this; the deduction errs conservative (slightly higher countable income).
- **Differences Working Healthy implements on top of `awd_medicaid`:**
  - **Income multiplier 3.0** (300% FPL), not awd_medicaid's 4.5.
  - **Max age of 64** — awd_medicaid has no upper bound. Eligibility runs 16 through the end of the month of the 65th birthday.
  - **Earned-income / employment requirement** — awd_medicaid has no employment gate. Requires current earned income (`wages`/`selfEmployment`) with gross **> $65/month**; no earned income (SSDI/SSI only) or ≤ $65/mo fails (drives Sc 3 and Sc 16).
  - **$15,000 flat resource test** — awd_medicaid has no resource check. Compare `household_assets` ≤ $15,000 (does not scale with size).
  - **SSI exclusion** — exclude members reporting an `sSI` income stream (and 1619(b)).
  - **Assistance-plan (individual-centric) sizing for the FPL bracket** — awd_medicaid uses raw `household_size`; Working Healthy derives the plan size (single→1, couple→2, child<18 w/ parents→2).
  - **Value:** do NOT reuse awd_medicaid's `member_amount`; use $19,051/yr per eligible member (see Benefit Value).
- **PE reference:** `il_hbwd_person` (IL HBWD) for the buy-in pattern; PE does not model KS Working Healthy.
- **`estimated_application_time` ("30 - 60 minutes"):** no official completion time is published for the KanCare application. Working Healthy uses the standard KanCare Medical Assistance application (KEES self-service portal), which — as a disability/asset-tested, non-MAGI pathway with a resources section — runs longer than a MAGI children/family application (CMS benchmarks the streamlined ACA application at ~45 min). 30–60 minutes is a conservative estimate; a navigator can confirm a real-world figure later.
- **Out of scope — not modeled** (these govern ongoing case management, not the point-in-time eligibility determination the screener performs):
  - The 6-month desk review / premium recalculation cycle (§2664.4(3), §2664.5).
  - The 4-month temporary-unemployment coverage extension (§2664.7).
  - Premium billing, delinquency, and appeals mechanics (§2664.5).
  - Transition-between-coverage-type budgeting rules when WH ends (§2664.6).
  - The mandatory HIPPS referral (§2912) — a required post-enrollment administrative referral with no eligibility or value impact; not modeled, not surfaced in the description.
  - Determination-order precedence between Working Healthy and regular MS/spenddown-free Medicaid ("if the MS determination results in no spenddown, the client is placed in MS/spenddown, not Working Healthy," §2664 intro) — MFB's screener shows possible eligibility across programs rather than adjudicating which single program a household is ultimately placed into; a household may correctly show as possibly-eligible for both Working Healthy and regular KanCare Medicaid (MFB-1054, tracked separately).

---

## Sources

- KEESM §2664 — Working Healthy (eligibility, earned income, premiums, exclusions): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2664.htm
- KEESM §2664.1 → §11221(5) — medical assistance fraud conviction bar: https://khap.kdhe.ks.gov/KEESM/Aug_2023_Output/keesm2664.htm
- KEESM §7430(4) — Working Healthy income standards (FPL basis). Now "Reserved" in the live manual; F-8 is the authoritative source for the figures.
- KEESM §5130 — Resources ($15,000 for any size family group). Also "Reserved" in the live manual; see F-8.
- KEESM §2662 — Disability/blindness definition (SSA standard): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2660.htm
- KEESM §7240 — Countable income / disregards methodology ($65 earned, $20 unearned): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm7240.htm
- KEESM §2150 — Residency: https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2150.htm
- KEESM §2140–§2142 — Citizenship and Alien Status (qualified-non-citizen categories and the 5-year-wait list): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2140.htm
- KEESM §5430(20) — Pension/retirement fund resource exemption (explicitly names Working Healthy): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm5430.htm
- KEESM §6410(34) — Individual Development Account resource/income exemption: https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm6410.htm
- **F-8 Kansas Medical Standards (rev. 04-26)** — Working Healthy income standards $3,990 / $5,410 / $6,830 / +$1,420 "monthly 300% poverty level standard" (p.5); $15,000 resource limit, no couple-scaling (p.8); federal tax deductions inapplicable to Working Healthy (p.6); premium brackets by household size (p.5).
- KanCare Working Healthy page — 300% FPL income limit, age 16–64, SSA-determined disability, >$65/mo + FICA/SECA earned income, not-SSI, not-HCBS, not-nursing-facility, $15,000 resource limit: https://www.kancare.ks.gov/members/benefits-services/working-healthy
- Kansas Medical Assistance Report (MAR), FY2025, KDHE Division of Health Care Finance — https://www.kdhe.ks.gov/ArchiveCenter/ViewFile/Item/2842 . Benefit value source: "Working Healthy" row on the "Beneficiaries by Population Group" table (Monthly Average = 1,306) and "Expenditures by Population Group" table (Fiscal Year-to-Date Total = $24,879,015); $24,879,015 ÷ 1,306 = $19,051/enrollee. Current/future editions: https://www.kdhe.ks.gov/229/Data-Reports
- HHS 2026 Poverty Guidelines (basis for the 300% FPL standards): https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines
