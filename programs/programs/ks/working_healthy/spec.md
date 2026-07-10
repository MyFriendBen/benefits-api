# Working Healthy (KS) — Eligibility Specification

## Program Details

- **Program:** Working Healthy (WH) — corrected 2026-07-07 from "KanCare for Workers with Disabilities (Working Healthy)"; that phrasing never appears in any primary source checked (KEESM, KanCare's own page title, F-8) or in a fresh search this session — Kansas consistently calls it "Working Healthy." Likely an unreflective carry-over from the Linear ticket title rather than a deliberate MFB clarity choice.
- **State / White Label:** KS / `ks`
- **Calculator type:** MFB Custom (PE models the sibling program for IL only — `il_hbwd_person`; build in-house using the `awd_medicaid` calculator as the primary precedent)
- **Benefit type:** Health Care (Medicaid coverage)
- **Config year:** 2026 (FPL-based program)
- **Research date:** 2026-06-15 · **Reviewed:** 2026-06-16

---

## Implementation Coverage

8 of 10 eligibility criteria are screener-evaluable (with the documented assumptions below); citizenship (C9) is handled via `legal_status_required` in the config alone (corrected 2026-07-07 — there is no calculator-level enforcement anywhere in the codebase; the config list is the entire mechanism, and was narrowed accordingly) — not a screener gate and not a data gap. Fraud conviction (C10, added 2026-07-06) is a real but not screener-measurable exclusion, handled via an inclusivity assumption. No criterion is blocked — every screener-unmeasurable input is handled via an inclusivity assumption, description surfacing, or a logged (optional) screener proposal.

---

## Eligibility Criteria

1. **Age 16 through 64**
- Screener fields: `birth_year`, `birth_month`
- Source: KEESM §2664.2 (Age and Blindness/Disability Requirements) — coverage runs through the end of the month of the 65th birthday.
- **Handling:** Fully collected via `birth_year` + `birth_month` (the screener derives age from these; the raw `age` field is deprecated for spec criteria). Evaluate the derived age against the 16–64 band (inclusive of the 64-through-end-of-65th-birthday-month rule). No data gap.

2. **Has a qualifying disability or blindness** ⚠️ *partial data gap (formal determination)*
- Screener fields: `long_term_disability`, `visually_impaired`
- Source: KEESM §2664.2 → §2662. SSA standard: a medically determinable physical/mental impairment expected to last ≥12 months (or result in death); blindness = 20/200 or less in the better eye. Receipt of SSDI or disability-based SSI automatically satisfies the standard. **Confirmed verbatim 2026-07-07** against a direct user-provided copy of §2662's current text — exact match on all three points, including the "SSDI or disability-based SSI satisfies the standard" language. Note: §2662 also defines a separate, lower MediKan-specific disability tier (Tier 2) — not applicable here, since Working Healthy requires the full SSA standard (Tier 1), not the MediKan standard.
- **Handling:** Use the self-reported `long_term_disability` / `visually_impaired` flags as the screening proxy (matching the `awd_medicaid` precedent) — **not** the generic `disabled` flag, which may reflect a short-term condition. Formal SSA/DDS determination happens at application; surface "proof of disability (SSI/SSDI award letter or doctor's statement)" in the program description so applicants not already on SSI/SSDI know it may be required.

3. **Currently employed with earned income** ⚠️ *data gap (FICA/SECA withholding)*
- Screener fields: `has_income`, `income_streams` (earned types: wages, self-employment)
- Source: KEESM §2664.3 (Earned Income Requirement). Earned income must be FICA/SECA-covered.
- **Handling:** Treat any reported earned income stream (`wages` / `selfEmployment`) as meeting the employment requirement. The screener does not capture FICA/SECA withholding, so **assume reported earnings are FICA/SECA-covered** (true for the large majority); actual verification occurs at application. Members with no earned income (e.g., SSDI/SSI only) fail this criterion.

4. **Earnings meet the floor**
- Screener fields: `income_streams` (earned)
- Source: KEESM §2664.3. Earned income must be at/above the federal hourly minimum wage, and countable earned income must exceed the standard earned-income disregard ($65/month).
- **Handling:** Derive from the reported wage amount; compare monthly countable earned income to the $65 disregard floor. ⚠️ *Minor data gap:* the screener only captures an hourly *rate* when income frequency is `hourly` — for monthly/yearly wage entries it can't verify the "at/above federal minimum wage" rate, so **assume the minimum-wage-rate condition is met** (inclusive default; verified at application). Very low gig earnings below $65/mo countable would not qualify — acceptable for screening. *Screener-improvement considered (capture hours for salaried entries) → declined: low value, sibling precedent declined it.*

5. **Countable income at or below 300% of the Federal Poverty Level** for the assistance-plan size ⚠️ *data gaps (IRWE/BWE/SSI-deeming)*
- Screener fields: `income_streams`, `household_size`
- Source: KEESM §2664.4 (Financial Requirements) → §7430(4) (Working Healthy standards are poverty-level based); **standard amounts in Appendix F-8, which is the sole authoritative live source for the dollar figures** (confirmed 2026-07-06: §7430 itself now reads "Reserved" in the live DCF manual, Rev 125 effective ~2026-07-01 — this is not a defect, KEESM §5120 already directs readers to F-8 on the KanCare/KDHE site rather than restating figures in the numbered DCF sections, and DCF appears to be consolidating in that direction).
- Methodology (follow the `awd_medicaid` precedent — *confirmed against its source code 2026-06-16*): countable earned = (annual earned − $65) × 0.5; countable unearned = annual unearned − $20; eligible if (countable earned + countable unearned) ≤ FPL[assistance-plan size] × 3.0. The $65/$20 are applied as flat annual deductions exactly as awd_medicaid does (a conservative simplification of the SSI monthly disregards). 2026 individual limit ≈ $47,880/yr ($3,990/mo).
- **Handling:** Apply the standard earned/unearned disregards above only. **IRWE, BWE, and SSI couple-deeming are not collected**, so the calculator may slightly *overestimate* countable income for affected applicants (errs toward false negatives, the conservative direction). Surface in the program description that disability-related work expenses can lower countable income, so applicants who look over-income still apply. The **assistance-plan size is individual-centric** (single → 1-person; married couple → 2-person; child under 18 living with parents → 2-person). *Citation correction, refined 2026-07-07 (supersedes the 2026-07-06 blanket withdrawal below): a direct user-provided copy of the current §2664 text confirms §2664.1 DOES explicitly invoke §4310 for Working Healthy — "the assistance planning rules of 4310 are also applicable. LTC and HCBS recipient spouses and parents are not included in the plan. Spouses or parents who otherwise meet the requirements of the MS program... shall have a separate plan, but are not excluded from the plan." So §4310 is real and applicable — but what it governs is **who counts as part of the family group** (excluding LTC/HCBS spouses and parents; handling separate-MS-plan spouses), not a stated **number-of-persons sizing rule for the income test**. The explicit "1 person plan for a single individual, 2-3 person plan for a married couple or a minor living with parents" sizing convention appears only in §2664.5's NOTE, which is written for **premium** determination. No KEESM text found states that the same 2-3-person convention applies to the *income* test specifically — MFB's use of individual-centric sizing there (single → 1-person; married couple → 2-person; child under 18 living with parents → 2-person) is a reasonable extension of the premium-test convention to a closely related determination on the same "plan," but remains **MFB's own policy choice**, not a directly-cited income-test rule. It's still the defensible choice: a 3-person bracket would only raise the FPL ceiling (admit more income), so the 2-person bracket errs toward the stricter result (false negatives, not false positives).* **⚠️ Data gap, resolved 2026-07-07 (LTC/HCBS spouse exclusion from the plan):** §2664.1's text above also states LTC/HCBS recipient spouses and parents are excluded from the assistance plan — meaning a WH applicant whose *spouse* is themselves an LTC/HCBS recipient should size as 1-person, not 2-person, for this income test. The screener has no field distinguishing an LTC/HCBS recipient spouse from any other Medicaid-insured spouse (the same gap already noted for the applicant's own institutional status in Criterion 8). **Resolution: assume the spouse is not an LTC/HCBS recipient and keep 2-person sizing** — the inclusive direction, since 2-person gives the higher (more admitting) FPL ceiling. This is an edge case (requires the applicant to be eligible, married, AND have a spouse independently on LTC/HCBS) and is not expected to affect any documented test scenario. *Screener-improvement considered (IRWE expense field) → declined: complex to self-report, niche; SSI couple-deeming isn't a collectable field, it's a calculation method.* *Verified directly against F-8 (rev. 04-26, "Income Standards for Working Healthy"):* 1-person **$3,990/mo**, 2-person **$5,410/mo**, 3-person **$6,830/mo**, +$1,420 per extra person — labeled the "monthly 300% poverty level standard." Consistent with the official KanCare page (300% FPL) and §7430(4) (FPL basis). Fully confirmed — no open item.

6. **Countable resources at or below $15,000 (for any size family group)** ⚠️ *minor data gap (exemptions)*
- Screener fields: `household_assets`
- Source: KEESM §5130 — "$15,000 for any size family group" (note: the limit does **not** scale with household size; confirmed verbatim live 2026-07-06 against the `Nov_2022_Output` archive — **§5130 itself now reads "Reserved" in the live DCF manual, Rev 125 effective ~2026-07-01**, consistent with §7430's move above; F-8 is the authoritative live source). **Confirmed directly in F-8 (rev. 04-26, Resource Standards): Working Healthy = $15,000**. Retirement funds (§5430(20)) and Individual Development Account balances (§6410(34)) are exempt — both re-verified verbatim live 2026-07-06, and §5430(20) explicitly names Working Healthy. (A prior draft of this criterion also claimed an LTC Partnership policyholder disregard; removed 2026-07-07 — no citation was ever attached to that clause and it couldn't be independently verified. F-8's resource standards page has no LTC Partnership line; if this needs to be modeled later, it requires its own citation first.)
- **Handling:** Compare `household_assets` against the $15,000 flat limit. The screener captures a single total and **cannot break out the retirement/IDA exemptions**, so the figure may slightly *overcount* countable resources (conservative, rare false negatives). Exemptions are applied at application. **Surfaced in the program description** ("some savings, like retirement accounts, may not count toward the limit") so applicants who look over-asset still apply. A cross-program screener-question change to exclude retirement/IDA funds was **considered and declined 2026-07-07** — see Inclusivity Assumptions below (WA HCV precedent: asset-type breakdown adds friction without reliably matching any one program's rules).

7. **Kansas resident** ⚠️ *minor data gap (residency intent)* — reclassified 2026-07-07
- Screener fields: `zipcode`, `county`
- Source: KEESM §2664.1 → §2150 (Residency): "A resident is one who is living in the state voluntarily and not for a temporary purpose (i.e., with no intention of leaving)."
- **Handling:** Derive from `zipcode` / `county`. §2150's actual standard is about **intent to remain**, which the screener cannot measure — `zipcode`/`county` only confirm current location, not intent. Previously described as "not a current data gap requiring action"; reclassified here for consistency with how every other screener-unmeasurable input in this spec is handled: **assume genuine residency intent** (inclusive default — true for ~all self-serve users; a person deliberately relocating short-term to game a Medicaid buy-in program is a vanishingly rare edge case). Intent is verified at application, not in the screener. No description surfacing needed (too rare/low-value to lead with).

8. **Not otherwise covered by full Medicaid through another category (and not receiving HCBS waiver services)**
- Screener fields: `insurance` (Medicaid), `income_streams` (SSI)
- Source: KEESM §2664 (intro); KanCare Working Healthy program page (eligibility list: "Not be receiving Home and Community Based Services," "Not be an SSI recipient," "Not be living in a nursing facility"). SSI recipients and 1619(b) deemed recipients remain in the SI program and are not eligible for Working Healthy. Employed applicants are considered for Working Healthy first.
- **Handling:** Require member `insurance` of none/employer/private (excludes those reporting current Medicaid/Medicare), following `awd_medicaid`. The SSI exclusion is derivable from a reported SSI income stream. **HCBS-waiver recipients are also excluded** by the official eligibility list; because HCBS recipients receive their services through Medicaid, the same `insurance` = Medicaid check catches them — no separate screener field is needed. **Institutional residence** (Working Healthy excludes long-term nursing-facility residents) is *not* collected — assume community-dwelling (the correct default for ~all self-serve users; the inverse of the SSPP failure mode, so safe). The community-residence requirement is **surfaced in the program description** so facility residents understand they aren't eligible. "Consider Working Healthy first" routing is an application-time step.

9. **U.S. citizen or qualified immigrant, subject to the federal 5-year bar for most green-card holders**
- Screener fields: handled via `legal_status_required` config (not a screener gate, and — corrected 2026-07-07 — not a calculator gate either; see below)
- Source: KEESM §2664.1 → §2140 (Citizenship and Alienage) → §2142 (qualified non-citizen categories, fetched in full 2026-07-07: 15 categories exempt from any wait, plus 3 categories — including ordinary lawful permanent residents — subject to a 5-year wait from the date qualified status was obtained).
- **Handling, corrected 2026-07-07 (the previous version of this criterion was factually wrong):** the claim that "the calculator enforces the citizen/qualified-immigrant rule" does not hold — checked directly against `awd_medicaid` (the precedent calculator) and the platform architecture: **no calculator anywhere in `benefits-api` checks immigration/legal status.** `legal_status_required` is a `Program`-level filter, not a per-member calculator check — the value comes from a user-selected results-page filter chip (`citizenshipFilterConfig.tsx`), not a household-member intake question; several other program specs confirm "the screener has no citizenship/immigration field." There is no calculator-level layer catching anything the config list admits. Given that, `legal_status_required` must itself encode the actual restriction. **Narrowed from all 6 values to `["citizen", "refugee", "gc_5plus", "otherWithWorkPermission"]`** — removing `non_citizen` (the platform's own frontend defines this as "Undocumented," including DACA — never eligible for non-emergency Medicaid) and `gc_5less` (LPR under 5 years — federally barred absent an exemption WH doesn't carry). Matches the closest cross-program precedent in the codebase: TX's adult Medicaid parents/caretakers category uses `["citizen", "gc_5plus", "refugee"]`, also excluding `gc_5less`.
  - **On the four kept values — checked against MFB's own frontend definitions, not just inferred by elimination:** `citizen` and `gc_5plus` are unambiguous. `refugee` is confirmed to be a *merged* bucket — the platform's own UI labels it "Refugee/**Asylee**" ("individuals granted refugee or asylee status") — so it already covers asylees, one of KEESM §2142.1's exempt categories, by design. `otherWithWorkPermission` is labeled **"Other Lawful"** ("other lawfully present noncitizens with authorization to live or work in the U.S.") — an intentionally broad catch-all meant to sweep in the remaining §2142.1 categories (COFA citizens, VAWA petitioners, humanitarian parolees, etc.), not a narrow specific status.
  - **Residual, platform-level caveat (not specific to this ticket):** a different program's spec (`wa/ssi`) documents that this breadth doesn't always hold for *PolicyEngine-backed* programs — PE's own separate qualified-noncitizen categories aren't fully captured by the `refugee` chip there, a documented "under-counting limitation." This doesn't transfer to Working Healthy, which is MFB Custom (no PE variable involved) — but no single source in the codebase gives a verified, line-by-line mapping of all of §2142.1's 15 exempt categories onto MFB's 4 kept buckets. That's a platform-schema question, not something resolvable within this one ticket.
  - Documentation provided at application. This is not a data gap — it's a config-level restriction, now corrected to actually restrict.

10. **Not convicted of medical assistance fraud** ⚠️ *data gap (not screener-measurable)* — added 2026-07-06
- Screener fields: none
- Source: KEESM §2664.1 (General Eligibility Requirements), which states general-eligibility items including "act in own behalf, cooperation, SSN, citizenship and alienage, and residency" and explicitly: "Persons convicted of medical assistance fraud per 11221 **(5)** are not eligible." Subsection number corrected 2026-07-07: an earlier AI-summarized fetch of the `Aug_2023_Output` snapshot reported "(3)"; a direct user-provided copy of the current §2664 text, plus the earlier `Aug_2018_Output` archive, both independently read "(5)" — (5) is used as the more reliable, directly-quoted figure.
- **Handling:** This is a genuine, if narrow, eligibility bar — not merely an administrative step — so it's listed as its own criterion rather than folded into the Data Gaps table's administrative row (which it previously was, incorrectly conflated with SSN/assignment-of-rights). The screener has no field for a fraud conviction, and it is an exceedingly rare edge case; **assume not fraud-convicted** (inclusivity assumption — the same direction as the other unmeasurable criteria in this spec). Not surfaced in the program description (too sensitive/rare to lead with); verified at application via the standard KanCare eligibility process.
- **Also confirmed NOT a criterion (checked explicitly 2026-07-06):** current incarceration/inmate status. Per KEESM and federal Medicaid rules, incarceration suspends *payment* for services, not *eligibility* itself — a Medicaid-eligible person retains eligibility while incarcerated and coverage reactivates on release without a new application. Correctly not modeled as an eligibility exclusion anywhere in this spec.

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

*The 17 scenarios below cover all major eligibility branches: the golden-path eligible case, an ineligible case per each major exclusion criterion, boundary/edge values, multi-member, and the SSI/HCBS mutex. Eligible value = $19,051/year per eligible member (annual); $38,102/year for a 2-member eligible household.*

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

### Scenario 2: Minimally eligible — barely meets all thresholds

**What we're checking**: Applicant who just clears every floor: exactly age 16, minimal employment income, confirmed disability.
**Expected**: Eligible, value $19,051/year

**Steps**:

* **Location**: Enter ZIP code `66002`, Select county `Atchison`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `June 2010` (age 16), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$200`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$500`

**Why this matters**: Tests minimum age and minimal employment together. Any earned income above the $65/mo disregard satisfies §2664.3; countable income is negligible, so the member is eligible at the edge.

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

**Why this matters**: Countable earned = int(($102,000 − $65) × 0.5) = $50,967 (truncated) > $47,880. Regression test for the corrected FPL basis + earned-income disregard (the prior 300% FBR figure was wrong).

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

### Scenario 10: Age exactly 16 — minimum age threshold

**What we're checking**: Whether a person who is exactly 16 (the minimum age) qualifies.
**Expected**: Eligible, value $19,051/year

**Steps**:

* **Location**: Enter ZIP code `66502`, Select county `Riley`
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 2010` (age 16), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$1,000`

**Why this matters**: §2664.2 sets the minimum age at 16, inclusive. Confirms the age floor does not reject a 16-year-old who otherwise qualifies.

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

### Scenario 17: Non-Kansas resident — ineligible

**What we're checking**: Disabled, employed, within limits, but residing outside Kansas.
**Expected**: Not eligible

**Steps**:

* **Location**: Enter ZIP code `64106` (Kansas City, **Missouri**)
* **Household**: Number of people: `1`
* **Person 1**: Birth month/year: `March 1986` (age 40), Relationship: `Head of Household`, Disability: `Yes`, Currently employed: `Yes`, Monthly wages: `$1,800`, Citizenship: `US Citizen`, Insurance: `None`
* **Assets**: `$5,000`

**Why this matters**: §2664.1 → §2150 — Working Healthy is a Kansas Medicaid program; a non-KS resident is ineligible. Documented for traceability; in practice the KS white-label only serves KS residents, so this is enforced by routing rather than the calculator (no calculator-level unit test).

---

## Data Gaps & Handling

| Item | Handling assumption (for calculator code comments) |
|---|---|
| Minimum-wage-rate verification (C4) | Added 2026-07-07 — previously inline-only, missing from this table. Screener only captures an hourly rate for `hourly`-frequency income; monthly/yearly entries can't be checked against the federal minimum wage. Assume the minimum-wage-rate condition is met (inclusive default); verified at application. |
| Formal disability determination (C2) | Self-reported `long_term_disability`/`visually_impaired` used as proxy; SSA/DDS determination occurs at application. |
| FICA/SECA withholding (C3) | Assume reported earned income is FICA/SECA-covered. |
| IRWE / BWE / SSI couple-deeming (C5) | Not collected; apply standard earned ($65 + 50%) and unearned ($20) disregards only. May overstate countable income for some applicants (rare false negatives). **Surfaced in description** (work expenses can lower countable income). |
| LTC/HCBS recipient spouse exclusion from the plan (C5) | Added 2026-07-07. §2664.1 excludes an LTC/HCBS recipient spouse from the assistance plan (would size the applicant as 1-person, not 2-person). Screener can't distinguish an LTC/HCBS recipient spouse from any other Medicaid-insured spouse. Assume the spouse is not an LTC/HCBS recipient and keep 2-person sizing (inclusive — higher FPL ceiling). Edge case; not expected to affect any documented scenario. |
| Retirement / IDA resource exemptions (C6) | Screener captures one asset total and can't exclude exempt retirement/IDA funds, so it may overcount countable resources (rare false negatives). Exemptions applied at application. **Surfaced in description** (some savings may not count). |
| Residency intent (C7) | Added 2026-07-07 — reclassified from "not a data gap" for consistency. §2150 requires intent to remain, not just current location; `zipcode`/`county` can't measure intent. Assume genuine residency intent (inclusive default); verified at application. |
| HCBS-waiver enrollment (C8) | Not collected directly. HCBS recipients receive services through Medicaid, so the `insurance` = Medicaid check excludes them; no separate field needed. |
| Institutional (nursing-facility) residence (C8) | Not collected. Working Healthy excludes long-term facility residents, but the screener assumes community-dwelling (the correct default for ~all self-serve users; inverse of the SSPP failure mode). Rare false positives possible. **Surfaced in description** (community-residence requirement). |
| Medical assistance fraud conviction (C10) | Not collected; real but exceedingly rare eligibility bar (KEESM §2664.1 → §11221(5)). Assume not fraud-convicted (inclusivity assumption). Not surfaced in description (too sensitive/rare to lead with); verified at application. |
| SSN, assignment of rights, inmate status | Administrative/procedural only — **not eligibility criteria**, confirmed 2026-07-06. SSN/assignment are non-eligibility application steps. Inmate status specifically confirmed NOT an eligibility exclusion: incarceration suspends Medicaid *payment*, not *eligibility* (a Medicaid-eligible person keeps eligibility while incarcerated). No screener field needed for any of these three. |

### Inclusivity assumptions (resolved without a screener question)

After review, **none of these gaps warrant a new screener field for this program.** They are handled as follows:

- **FICA/SECA coverage, minimum-wage rate, LTC/HCBS recipient spouse status, residency intent, fraud conviction** → inclusivity assumptions baked into the calculator only (assume FICA-covered; assume the wage rate meets minimum wage; assume a married applicant's spouse is not an LTC/HCBS recipient, keeping 2-person sizing; assume genuine residency intent; assume not fraud-convicted). All five are too niche, too rare, or (for fraud conviction) too sensitive to surface to users.
- **Surfaced in the program description** (so affected users still apply or understand a limit the screener can't check):
1. Income/work expenses (false-negative): "You may still qualify even if your income or savings look too high. Certain disability-related work expenses can be subtracted from the income that counts…"
2. Asset exemptions (false-negative): "…and some savings — like retirement accounts — may not count toward the savings limit."
3. Disability proof: "You may need to show proof of your disability, such as an SSI or SSDI award letter or a doctor's statement."
4. Community residence (false-positive expectation-setting): "To get this coverage you must live in the community, not a long-term care facility."
- **Screener-improvement candidates — both considered and declined, closed 2026-07-07** (previously logged as open/monitoring; resolved per user decision):
- `housing_situation` (institutional residence) → **declined, reasoning corrected 2026-07-07**. Originally framed as "no other program needs it" — checked the repo and that's not the right reason. `housing_situation` exists on the `Screen` model but is confirmed, across at least 7 other program specs (`tx/head_start`, `tx/ccad`, `tx/early_head_start`, `wa/nslp`, `wa/senior_disabled_pte`, `wa/head_start`, `wa/hcv`), as **not currently collected from users during screening anywhere** — it's a repo-wide infrastructure gap (the field isn't wired into the screener UI at all), not a case of an available capability nobody's chosen to use. Declining to build KS-specific UI/collection for a single program when this is already a known, cross-program gap remains the right call — but revisit if/when a broader fix (e.g., `wa/hcv`'s suggested real-property follow-up question) actually ships, since that would make the field usable here too.
- `household_assets` retirement/IDA-exclusion wording → **declined**. A near-identical proposal was already considered and rejected for WA HCV (`wa/hcv/spec.md`): "asset-type breakdown adds significant user friction without reliably matching any one program's asset rules." The same reasoning applies here — a generic retirement/IDA carve-out on the shared assets question would need to match this program's exemption plus SSI's, MSP's, and others', none of which share the same exempt-asset list, while adding friction to every screener session regardless of program.

---

## Implementation Notes

- **`estimated_application_time` basis, moved here from the review changelog 2026-07-07 (was never in a durable artifact before now):** "30 - 60 minutes" is a grounded estimate, not an AI-invented figure. No official completion time is published anywhere for the KanCare application (checked the Apply Now/Eligibility pages, FAQ, KEES portal, and the Working Healthy fact sheet). The Working Healthy application is the standard KanCare Medical Assistance application via the KEES self-service portal — full household composition, earned *and* unearned income, and (because this is a disability/asset-tested, non-MAGI pathway) a resources/assets section, which is materially longer than a MAGI children/family application. Benchmark: the ACA/Marketplace streamlined application is CMS-benchmarked at ~45 minutes for a single applicant; asset-tested disability Medicaid applications run longer due to the added resource and disability reporting. 30–60 minutes is reasonable and conservative at the top of the range. Still worth a navigator confirming a real-world number to update in admin later.
- **Eligibility-logic precedent:** `co/medicaid/adult_with_disability/calculator.py` (`awd_medicaid`) — reuse its structure (per-member eligibility, disability check via `long_term_disability`/`visually_impaired`, insurance-types check, and the SSI-disregard income test). **Income methodology confirmed against the awd_medicaid source (2026-06-16):** it computes `earned = max(0, (calc_gross_income("yearly", ["earned"]) − 65) × 0.5)` and `unearned = calc_gross_income("yearly", ["unearned"]) − 20`, i.e. a **flat $65 / $20 deduction applied to the annual figure** (not the SSI monthly $65/$20 annualized). The spec mirrors this exactly so KS stays consistent with the precedent; the deduction errs conservative (slightly higher countable income) and does not change any test outcome.
- **Differences KS must implement vs. `awd_medicaid` (it does NOT have these):**
  - **Income multiplier 3.0**, not awd_medicaid's `max_income_percent = 4.5` (CO uses 450% FPL; KS Working Healthy is 300%).
  - **Add a max age of 64** — awd_medicaid only sets `min_age = 16` (no upper bound). KS eligibility runs 16 through end-of-month-of-65th-birthday.
  - **Add an earned-income / employment requirement** — awd_medicaid has *no* employment gate. KS requires current earned income (`wages`/`selfEmployment`) with gross **> $65/month**; members with no earned income (SSDI/SSI only) or gross earned ≤ $65/mo fail. This drives the primary-exclusion (Sc 3) and earnings-floor (Sc 16) cases.
  - **Add a $15,000 flat resource test** — awd_medicaid has *no* resource check at all. Compare `household_assets` ≤ $15,000 (does not scale with size).
  - **Add the SSI exclusion** — exclude members reporting an `sSI` income stream (and 1619(b)); awd_medicaid relies only on the `medicaid_eligible`/insurance check.
  - **Assistance-plan (individual-centric) sizing for the FPL bracket** — awd_medicaid uses raw `self.screen.household_size`; KS must derive the §2664.5 assistance-plan size (single→1, couple→2, child<18 w/ parents→2) for the FPL lookup.
  - **Do NOT reuse `member_amount` (`310 × 12` = $3,720/yr)** for value — use the KFF per-enrollee figure below.
- **Value methodology — not a shipped precedent (corrected 2026-07-07):** per-enrollee KFF coverage value summed across eligible members (not a flat nominal amount) — matches the equally-unimplemented `wa_apple_health_hwd` draft (MFB-790), but this valuation pattern doesn't exist in any shipped MFB calculator (every implemented Medicaid/health-insurance program uses a flat nominal `member_amount` instead — see Benefit Value section for the full check). Dev: confirm this approach with the team before merging, since it would be the first production use of this pattern.
- **PE reference:** `il_hbwd_person` (IL HBWD) for the buy-in pattern; PE does not model KS Working Healthy.
- **Config year:** 2026.
- **Registry-key reminder (added 2026-07-07):** `name_abbreviated: "ks_working_healthy"` must match the Python registration key **exactly** when the calculator is implemented (e.g. in `programs/programs/ks/__init__.py`) — a mismatch fails the eligibility lookup silently, with no error. This was flagged in the original discovery notes but never made it into this artifact itself until now.
- **Shared KS-launch blocker, confirmed 2026-07-07 — not specific to this ticket:** `"ks"` is not registered as a white label anywhere in `benefits-api`. `configuration/white_labels/__init__.py`'s `white_label_config` dict only contains `_default, co, cesn, il, ma, nc, tx, wa` — no `ks.py` exists, and no `WhiteLabel` database row for `"ks"` exists in any migration or fixture. `white_label.code: "ks"` in this config is the correct value regardless — this isn't a defect in this artifact — but **no KS program can go live until someone adds a `ks.py` config class and creates the DB `WhiteLabel` row, once, for the whole state.** MFB-1054 (KS KanCare Medicaid) and MFB-1055 (KS CHIP) are both currently in progress and will hit the identical blocker. Recommend tracking this at the KS: Launch project level rather than re-discovering it independently on each KS ticket.
- **Out of scope, decided 2026-07-07 (documented so it isn't silently absent):** the following §2664 provisions are intentionally **not modeled** by this calculator, because they govern ongoing case management after initial eligibility rather than the point-in-time eligibility determination the screener performs:
  - The 6-month desk review / premium recalculation cycle (§2664.4(3), §2664.5).
  - The 4-month temporary-unemployment coverage extension (§2664.7).
  - Premium billing, delinquency, and appeals mechanics (§2664.5).
  - Transition-between-coverage-type budgeting rules when WH ends (§2664.6).
  - The mandatory HIPPS referral (§2912) — a required post-enrollment administrative referral with no eligibility or value impact; not modeled, not surfaced in the description.
  - Determination-order precedence between Working Healthy and regular MS/spenddown-free Medicaid ("if the MS determination results in no spenddown, the client is placed in MS/spenddown, not Working Healthy," §2664 intro) — MFB's screener shows possible eligibility across programs rather than adjudicating which single program a household is ultimately placed into; a household may correctly show as possibly-eligible for both Working Healthy and regular KanCare Medicaid (MFB-1054, tracked separately).

---

## Sources (verified against primary text 2026-06-15; key dollar figures re-verified 2026-06-16 and again 2026-07-06)

- KEESM §2664 — Working Healthy (eligibility, earned income, premiums, exclusions): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2664.htm (URL is the archived snapshot; the full current text — all of §2664 through §2664.7 — was independently confirmed 2026-07-07 via a direct user-provided copy, verbatim match)
- KEESM §2664.1 → §11221(5) — medical assistance fraud conviction bar (added 2026-07-06, subsection corrected 2026-07-07 against a direct user-provided copy of the current §2664 text): https://khap.kdhe.ks.gov/KEESM/Aug_2023_Output/keesm2664.htm
- KEESM §7430(4) — Working Healthy income standards (FPL basis): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm7430.htm (confirmed 2026-07-06: this section now reads "Reserved" in the live manual — see citation-currency finding #1 below; F-8 is the authoritative live source for the actual figures)
- KEESM §5130 — Resources ($15,000 for any size family group): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm5000.htm (same "Reserved" status confirmed live 2026-07-06 — see finding #1 below)
- KEESM §2662 — Disability/blindness definition: https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2660.htm (confirmed verbatim 2026-07-07 against a direct user-provided copy of the current text — exact match, no changes)
- KEESM §7240 — Countable income / disregards (methodology): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm7240.htm (fetched live this session — confirmed heading "7240 Income Deductions" with the $65 and $20 disregard sentences verbatim)
- KEESM §2150 — Residency: https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2150.htm (fetched live this session, twice — first confirming heading "2150 Residence" verbatim, then a full re-pull 2026-07-07 covering §2151 (duplicate-benefits/interstate-move rule, doesn't apply to MediKan) and §2152 (institutionalized-persons residency) — neither changes Criterion 7, since §2152 only concerns people already excluded from WH via the separate institutional-residence criterion)
- KEESM §2140 → §2142 — Citizenship and Alien Status: https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm2140.htm (fetched live this session, twice — first confirming heading "2140 Citizenship and Alien Status" verbatim, then a full re-pull 2026-07-07 covering §2141/§2141.1 (citizenship definitions) and §2142/§2142.1/§2142.2 (the full 15-category qualified-non-citizen list plus the 3-category 5-year-wait list). **Correction, same day:** this full pull is what surfaced the actual finding — WH's `legal_status_required` should NOT be the standard 6-value convention. Checked directly against `awd_medicaid` and the platform architecture: no calculator anywhere enforces immigration status, so the config list is the sole restriction mechanism. Narrowed to `["citizen", "refugee", "gc_5plus", "otherWithWorkPermission"]` — see Criterion 9 for full reasoning.)
- KEESM §5430(20) — Pension/retirement fund resource exemption (explicitly names Working Healthy): https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm5430.htm (fetched live this session — verbatim, explicitly names Working Healthy)
- KEESM §6410(34) — Individual Development Account resource/income exemption: https://khap.kdhe.ks.gov/KEESM/Nov_2022_Output/keesm6410.htm (fetched live this session — verbatim, "IDAs are exempt resources for all programs")
- **F-8 Kansas Medical Standards, rev. 04-26 (current; user-provided PDF, verified directly 2026-07-06)** — confirms verbatim: Working Healthy income standards $3,990 / $5,410 / $6,830 / +$1,420 = "monthly 300% poverty level standard" (p.5); resource limit $15,000, no couple-scaling (p.8); federal tax deductions inapplicable to Working Healthy (p.6); premium brackets by household size (p.5). Supersedes the earlier "rev. 07-26" citation, which was never independently confirmed and is now corrected to the actual current revision label.
- KanCare Working Healthy page — confirms the **300% FPL** income limit, age 16–64, SSA-determined disability, >$65/mo + FICA/SECA earned income, not-SSI, not-HCBS, not-nursing-facility, and the **$15,000** resource limit: https://www.kancare.ks.gov/members/benefits-services/working-healthy (⚠️ **not independently re-verified this session** — every automated fetch attempt against this URL returned 403, confirmed multiple times across multiple rounds; this citation rests on a human's direct confirmation from 2026-06-17, now three weeks old)
- Kansas Medical Assistance Report (MAR), FY2025, KDHE Division of Health Care Finance — https://www.kdhe.ks.gov/ArchiveCenter/ViewFile/Item/2842 . Benefit value source: "Working Healthy" row on the "Beneficiaries by Population Group" table (Monthly Average = 1,306) and "Expenditures by Population Group" table (Fiscal Year-to-Date Total = $24,879,015); $24,879,015 ÷ 1,306 = $19,051/enrollee. Current/future MAR editions: https://www.kdhe.ks.gov/229/Data-Reports
- HHS 2026 Poverty Guidelines (basis for the 300% FPL standards): https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines (⚠️ **not independently fetched this session** — this URL redirected to an unblock/verification page that was never followed up on; the 300%-FPL dollar figures it underpins are instead cross-validated via the `benefits-api` repo's own `FplCache` 2026 table, an independent source that reproduces them to the dollar)

**Citation-currency findings — fully resolved 2026-07-06:**

1. **Confirmed and now closed:** all `khap.kdhe.ks.gov/KEESM/Nov_2022_Output/...` URLs are an archived snapshot, not the live DCF manual (Revision 125, effective ~2026-07-01). §5130 and §7430 — the two DCF section numbers Criteria 5–6 originally pointed to — now literally read **"Reserved"** in the live manual (verified directly). This is not a defect: KEESM §5120 already directed readers to the **F-8 appendix** for these figures, not the numbered DCF sections, so their vacancy just reflects DCF consolidating around F-8 as the single owner of these numbers. Criteria 5 and 6 cite F-8 as the primary source; the DCF section numbers are kept as historical/structural context only.
2. **F-8 itself — closed 2026-07-06.** The current F-8 (rev. **04-26**, not the previously-cited "07-26" — corrected) was provided directly and verified verbatim against every load-bearing claim in this spec: the $3,990/$5,410/$6,830/+$1,420 income standards, the "300% poverty level standard" label, the $15,000 resource limit (no couple-scaling), and the inapplicability of federal tax deductions to Working Healthy all match exactly (p.5, p.8, p.6 respectively). **One correction fell out of this check:** the premium-trigger claim ("above 100% FPL") was wrong — F-8's premium brackets are actually ~225% FPL (1-/2-person) and ~178% FPL (3-person); fixed in the Benefit Value section above.
3. **§4310 status, refined 2026-07-07:** a direct user-provided copy of the current §2664.1 text confirms §4310's "assistance planning rules" genuinely apply to Working Healthy (governing family-group composition — e.g., excluding LTC/HCBS spouses/parents from the plan), so round 9's blanket withdrawal of §4310 was too broad. What §4310 does *not* provide — confirmed both by that text and independently by F-8 p.4, which cites §4310 + §7430(6) for **MediKan's** own single-adult/married-couple filing unit — is a stated number-of-persons sizing rule for Working Healthy's *income test* specifically. That specific "1-person / 2-3-person" convention appears only in §2664.5's premium-level NOTE. MFB's individual-centric income-test sizing remains a documented policy choice (a reasonable extension of the premium convention), not a directly-cited income-test rule — see Criterion 5 for the full reasoning.
4. **Confirmed stable across 5+ years of snapshots** (2018 through Aug 2023) for everything not covered by the F-8 re-fetch above: age 16–64, $65/mo disregard + FICA/SECA + minimum-wage requirement, disability standard, SSI/HCBS/nursing-facility exclusions.

**Second-order citations, audited 2026-07-07, updated same day after §2142 was fetched — not
independently fetched, and why that's acceptable:**
A full pass through every "§" reference in this document (not just the top-level Sources list) found
sections that other verified text *points to*, but whose own content wasn't independently fetched at
the time. §2142 was subsequently fetched in full (see the §2140 Sources entry above) and is no longer
in this list. What remains genuinely unfetched:
- **§8200 (HCBS)** and **§8113 (nursing-facility temporary-stay criteria)** — cited inside the verified
  §2664 text as the basis for the HCBS/nursing-facility exclusions in Criterion 8. The operative rule
  ("not eligible for HCBS," "not eligible if in a nursing facility beyond the temporary-stay period") is
  already stated directly in the verified §2664 text; §8200/§8113 would only add the underlying
  definitions of HCBS/temporary-stay, not change the rule itself.
- **§11221 itself** and **§2912 (HIPPS) itself** — cited inside the verified §2664.1/§2664 text as the
  basis for the fraud-conviction bar and the HIPPS referral, respectively. Both provisions are already
  fully specified by the citing text (a conviction excludes; a referral is required); §11221/§2912 would
  only add detail on a penalty/program this spec doesn't otherwise model (HIPPS is explicitly out of
  scope — see Implementation Notes).

None of these remaining four are load-bearing on their own — each sits one hop behind an
already-verified, already-operative citation. Also removed one uncited claim (an "LTC Partnership"
resource disregard in Criterion 6) that had no citation at all and couldn't be independently verified —
rather than leave it unverified, it's removed; re-add only with a citation if it turns out to matter.

**No open sourcing items remain.**
