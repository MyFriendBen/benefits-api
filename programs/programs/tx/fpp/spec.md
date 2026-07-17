# Texas Family Planning Program (FPP) — Custom Calculator Spec

- **Program:** Family Planning Program (FPP)
- **State:** TX (`tx`)
- **name_abbreviated:** `tx_fpp`
- **Tickets:** MFB-1088 (custom migration), MFB-1325 (income mirror of PolicyEngine)
- **Calculator:** `programs/programs/tx/fpp/calculator.py` (`TxFpp`)

## Background

FPP is a state-funded HHSC program offering free or low-cost reproductive and preventive
health care to Texans through age 64. It was previously screened via a PolicyEngine
calculator (`tx_fpp_benefit`). MFB-1088 migrates it to a **custom calculator** so the
§4140 adjunctive income bypass — which depends on MFB enrollment flags PolicyEngine cannot
see — can be enforced directly, and so the §4100 insurance rule can be relaxed from the
prior strict "no insurance" filter to a Medicaid-only exclusion.

## Eligibility Criteria

1. **Age 64 or younger** (§4130)
   - Screener fields: `birth_year` + `birth_month` (→ `member.age`)
   - No minimum age. HHSC states only "64 or younger"; this matches PolicyEngine's
     `tx_fpp_age_eligible` (upper bound only). Members with no recorded age are not counted.

2. **Countable income at or below 250% FPL** (§4130), **OR adjunctive income eligibility** (§4140)
   - Income limit = `2.5 × FPL(household_size)` for the program's FPL year (2026)
     (`self.program.year.get_limit(household_size)`).
   - **Countable income is not a flat gross total** — it mirrors PolicyEngine's
     `gov.states.tx.fpp` countable-income model at the version we serve (policyengine-us
     **1.768.1**), computed in `_countable_income()`. PolicyEngine is treated as the source of
     truth here (not independently verified against 1 TAC §382.109 / the FPP Policy Manual).
     It is `adult_earned + unearned + countable_child_support − child_support_paid`, floored at 0:
     - **adult_earned** — earned income (`wages`, `selfEmployment`) summed only for members
       age ≥ 18. Under-18 earnings are **exempt** (`child_age_threshold = 18`).
     - **unearned** — all unearned income *except* child support received.
     - **countable_child_support** — `max(0, child_support_received − disregard)`. The disregard
       is **$75/month** ($900/yr) per the Texas FPP Policy Manual (Definition of Income, Rev 24-2),
       mirroring PolicyEngine's `gov.states.tx.fpp.income.child_support_disregard` (unchanged
       since 2016-07-01). Received child support ("Child Support (Received)" income) at or under
       $900/yr counts as $0.
     - **child_support_paid** — the `childSupport` expense, **deducted**.
     - *Not applied:* the dependent-care deduction PolicyEngine added in 1.771.2 (frontier),
       which is absent from the 1.768.1 model we serve. Re-sync if PE changes this logic.
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
       description copy (added in MFB-1014).

4. **Texas residency** (§4130) — handled automatically by the TX white label; not re-checked.

5. **Citizenship / immigration status — not required** (§4130)
   - `legal_status_required` includes all six values (no restriction). Per §4130, Form 1065,
     and TMPPM Vol. 2 §1.1, FPP is available regardless of immigration status. (Team decision
     on MFB-1088 #3: relax the prior restrictive filter.)

## Benefit Value

- **$266.84 / year per eligible member** (annual). Source: TX HHS Women's Health Programs
  Report FY2024 — total expenditures $78,705,897 ÷ 294,954 clients served = $266.84 average
  annual benefit per participant. Mirrors PolicyEngine's `gov.states.tx.fpp.annual_benefit`.
- The household total is the sum across eligible members (e.g., two eligible members →
  `trunc(266.84 × 2) = 533`).

## Screener Field Mapping Summary

| Criterion | Fields | Notes |
|-----------|--------|-------|
| Age ≤ 64 | `birth_year`, `birth_month` | per-member; None-safe |
| Countable income ≤ 250% FPL | per-member `calc_gross_income(["earned"])` (adults only), screen `["unearned"]` / `["childSupport"]`, `calc_expenses(["childSupport"])`, `household_size`, `program.year` | mirrors PE `tx_fpp` countable income (1.768.1); child-support-received disregard $75/mo |
| §4140 bypass | `has_benefit("tx_snap")`, `has_benefit("tx_wic")`, `has_insurance_types(("chp",))` | CHIP Perinatal not captured (gap) |
| Medicaid exclusion | `member.insurance.medicaid` | Emergency Medicaid excluded from match |

## Validation Scenarios

See `validations/management/commands/import_validations/data/tx_fpp.json`. Coverage includes:
the eligible standard case, the age-64 upper boundary, age-65/70 ineligible, the Medicaid-only
insurance rule (employer-insured now eligible; full-Medicaid excluded; Emergency Medicaid
eligible), the 250% FPL income ceiling, the §4140 adjunctive bypass (income over 250% FPL but
on SNAP → eligible), and a multi-eligible-member household (value 533).

The **countable-income** behaviors (under-18 earnings exempt, child support paid deducted,
child support received $75/mo disregard) are covered by unit tests in
`tx/fpp/tests/test_fpp.py::TestTxFppCountableIncome`; the validation JSON does not yet include
cases for them and should be extended to cover them.
