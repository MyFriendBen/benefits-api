# Texas Family Planning Program (FPP) — Custom Calculator Spec

- **Program:** Family Planning Program (FPP)
- **State:** TX (`tx`)
- **name_abbreviated:** `tx_fpp`
- **Tickets:** MFB-1088 (custom-calculator migration), MFB-1325 (FPP Policy Manual countable-income rules)
- **Calculator:** `programs/programs/tx/fpp/calculator.py` (`TxFpp`)

## Background

FPP is a state-funded HHSC program offering free or low-cost reproductive and preventive
health care to Texans through age 64. It was previously screened via a PolicyEngine
calculator (`tx_fpp_benefit`). It has been migrated to a **custom calculator** so the
§4140 adjunctive income bypass — which depends on MFB enrollment flags PolicyEngine cannot
see — can be enforced directly, and so the §4100 insurance rule can be relaxed from the
prior strict "no insurance" filter to a Medicaid-only exclusion.

## Eligibility Criteria

1. **Age 64 or younger** (§4130)
   - Screener fields: `birth_year` + `birth_month` (→ `member.age`)
   - No minimum age — the FPP Policy Manual states only "64 or younger" (§4130, upper
     bound only). Members with no recorded age are not counted.

2. **Countable income at or below 250% FPL** (§4130), **OR adjunctive income eligibility** (§4140)
   - Income limit = `2.5 × FPL(household_size)` for the program's FPL year (2026)
     (`self.program.year.get_limit(household_size)`).
   - **Countable income is not a flat gross total** — it follows the FPP Policy Manual
     "Definition of Income" (Rev 24-2, Oct. 15, 2024) and §4140, computed in
     `_countable_income()`. It is `adult_earned + unearned + countable_child_support −
     child_support_paid`, floored at 0:
     - **adult_earned** — earned income (`wages`, `selfEmployment`) summed only for members
       age ≥ 18. A child's earned income is **exempt** (`child_age_threshold = 18`, per §4140 /
       1 TAC §382.109).
     - **unearned** — unearned income *except* child support received (see the limitation below).
     - **countable_child_support** — `max(0, child_support_received − disregard)`. Per the
       Definition of Income: *"Count income after deducting **$75** from the total monthly child
       support payments the household receives."* Received child support ("Child Support
       (Received)") at or under $900/yr counts as $0.
     - **child_support_paid** — legally obligated child support paid by a household member is
       **deducted** (§4140 Step 2); read from the `childSupport` expense.
   - ⚠️ **Known limitation — exempt income types not yet excluded.** The Definition of Income
     "Types of Income" table marks several types **Exempt** that `_countable_income()` still
     counts through the broad `unearned` bucket — notably **SSI**, **TANF**, **dividends/interest
     (`investment`)**, **EITC**, and various assistance / adoption / foster-care / in-kind
     payments. The `exclude=` argument on `calc_gross_income` supports fixing this (an
     FPP-exempt income-type list); it is a tracked follow-up, not implemented here. Effect: the
     calc over-counts income for a narrow set of households and can under-approve at the margin.
   - **§4140 bypass** — enrollment in any of the following makes the household income-eligible
     regardless of the countable-income test:
     - SNAP — `screen.has_benefit("tx_snap")`
     - WIC — `screen.has_benefit("tx_wic")`
     - CHIP (applicant or their child) — `screen.has_insurance_types(("chp",))` (per-member
       insurance; `tx_chip` is a PE eligibility program, never a current-benefit tile, so
       `has_benefit("tx_chip")` is always False)
     - ⚠️ *data gap:* CHIP Perinatal, the 4th §4140 program, is not collected by the screener.

3. **Not enrolled in (full) Medicaid** (§4100)
   - Screener fields: `member.insurance` (`medicaid` flag)
   - Only the full-Medicaid insurance flag disqualifies. Notably:
     - **Emergency Medicaid** recipients are classified as underinsured and remain eligible
       (separate `emergency_medicaid` flag — intentionally not matched).
     - **Employer / private / CHIP** coverage does **not** disqualify. Per §4200, insured
       clients still qualify if they have a confidentiality concern OR an annual deductible
       > 5% of annual income. The screener cannot capture those conditions, so insured
       (non-Medicaid) clients are included and the §4200 caveat is surfaced in the program
       description copy.

4. **Texas residency** (§4130) — handled automatically by the TX white label; not re-checked.

5. **Citizenship / immigration status — not required** (§4130)
   - `legal_status_required` includes all six values (no restriction). Per §4130, Form 1065,
     and TMPPM Vol. 2 §1.1, FPP is available regardless of immigration status. (Team decision:
     relax the prior restrictive filter.)

## Benefit Value

- **$266.84 / year per eligible member** (annual). Source: TX HHS Women's Health Programs
  Report FY2024 — total expenditures $78,705,897 ÷ 294,954 clients served = $266.84 average
  annual benefit per participant.
- The household total is the sum across eligible members (e.g., two eligible members →
  `trunc(266.84 × 2) = 533`).

## Screener Field Mapping Summary

| Criterion | Fields | Notes |
|-----------|--------|-------|
| Age ≤ 64 | `birth_year`, `birth_month` | per-member; None-safe |
| Countable income ≤ 250% FPL | per-member `calc_gross_income(["earned"])` (adults only), screen `["unearned"]` / `["childSupport"]`, `calc_expenses(["childSupport"])`, `household_size`, `program.year` | per FPP Definition of Income (Rev 24-2) + §4140; $75/mo child-support-received disregard; exempt income types not yet excluded (see limitation) |
| §4140 bypass | `has_benefit("tx_snap")`, `has_benefit("tx_wic")`, `has_insurance_types(("chp",))` | CHIP Perinatal not captured (gap) |
| Medicaid exclusion | `member.insurance.medicaid` | Emergency Medicaid excluded from match |

## Test Scenarios

These scenarios document the logic implemented in `calculator.py` (the source of truth) and
are the basis for the unit tests in `tx/fpp/tests/test_fpp.py`. The income limit is
`2.5 × FPL(household_size)`; examples below use an FPL of $15,000 → limit **$37,500**.

**Age / insurance — per member (`member_eligible`)**

| Scenario | Expected |
|----------|----------|
| Age 64 (upper boundary) | eligible |
| Age 65 | ineligible |
| Age unknown (`None`) | ineligible |
| Young child (no minimum age) | eligible |
| Uninsured | eligible |
| Full Medicaid | ineligible |
| Emergency Medicaid | eligible (underinsured, §4100) |
| Employer / private / CHIP coverage | eligible (§4200) |

**Income — countable vs 250% FPL (`household_eligible` / `_countable_income`)**

| Scenario | Countable income | Expected |
|----------|------------------|----------|
| Unearned $20k | $20,000 | eligible |
| Unearned exactly at limit | $37,500 | eligible |
| Unearned $37,501 | $37,501 | ineligible |
| Adult $30k earned + minor $15k earned | $30,000 (minor exempt) | eligible |
| Two adults $30k + $15k (age 18 = adult) | $45,000 | ineligible |
| Unknown-age member's earnings | not counted (can't confirm 18+) | — |
| Unearned $40k − $5k child support paid | $35,000 | eligible |
| Unearned $28k + $10k child support received ($75/mo disregard) | $37,100 | eligible |
| Child support received ≤ $900/yr | $0 (fully disregarded) | — |
| Deductions exceed income | floored at $0 | — |
| All components combined | adult earned + unearned + (received − disregard) − paid | — |

**§4140 adjunctive bypass — waives the income test**

| Scenario | Expected |
|----------|----------|
| Enrolled in SNAP (`tx_snap`) | eligible regardless of income |
| Enrolled in WIC (`tx_wic`) | eligible regardless of income |
| CHIP coverage (per-member insurance) | eligible regardless of income |
| High income, no bypass | ineligible |
| Bare `snap` / `wic` (legacy unprefixed name) | no bypass |
| `tx_chip` as a current benefit | no bypass (PE program, never a benefit tile) |
| Bypass, but the only member is full-Medicaid | ineligible (bypass waives income only) |

**Benefit value**

| Scenario | Expected |
|----------|----------|
| One eligible member | $266.84 |
| Two eligible members | $533.68 (sum) |
| Ineligible member (Medicaid / over-age) in household | excluded from value |
