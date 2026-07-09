# Texas Family Planning Program (FPP) — Custom Calculator Spec

- **Program:** Family Planning Program (FPP)
- **State:** TX (`tx`)
- **name_abbreviated:** `tx_fpp`
- **Ticket:** MFB-1088
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

2. **Household income at or below 250% FPL** (§4130), **OR adjunctive income eligibility** (§4140)
   - Screener fields: `calc_gross_income("yearly", ["all"])`, `household_size`, `program.year`
   - Income limit = `2.5 × FPL(household_size)` for the program's FPL year (2026).
   - **§4140 bypass** — enrollment in any of the following makes the household income-eligible
     regardless of the 250% FPL test:
     - SNAP — `screen.has_benefit("snap")`
     - WIC — `screen.has_benefit("wic")`
     - CHIP (applicant or their child) — `screen.has_benefit("chp")`
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
| Income ≤ 250% FPL | `calc_gross_income`, `household_size`, `program.year` | gross income, all types |
| §4140 bypass | `has_benefit("snap")`, `has_benefit("wic")`, `has_benefit("chp")` | CHIP Perinatal not captured (gap) |
| Medicaid exclusion | `member.insurance.medicaid` | Emergency Medicaid excluded from match |

## Validation Scenarios

See `validations/management/commands/import_validations/data/tx_fpp.json`. Coverage includes:
the eligible standard case, the age-64 upper boundary, age-65/70 ineligible, the Medicaid-only
insurance rule (employer-insured now eligible; full-Medicaid excluded; Emergency Medicaid
eligible), the 250% FPL income ceiling, the §4140 adjunctive bypass (income over 250% FPL but
on SNAP → eligible), and a multi-eligible-member household (value 533).
