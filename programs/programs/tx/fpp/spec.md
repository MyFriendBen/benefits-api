# Texas Family Planning Program (FPP) — Hybrid PolicyEngine Calculator Spec

- **Program:** Family Planning Program (FPP)
- **State:** TX (`tx`)
- **name_abbreviated:** `tx_fpp`
- **Tickets:** MFB-1088 (custom migration), MFB-1316 (hybrid re-migration to PolicyEngine income)
- **Calculator:** `programs/programs/tx/pe/member.py` (`TxFpp`), registered in `tx_pe_calculators`

## Background

FPP is a state-funded HHSC program offering free or low-cost reproductive and preventive
health care to Texans through age 64.

It has moved twice. It began as a PolicyEngine calculator (`tx_fpp_benefit`). MFB-1088 migrated
it to a **fully custom** calculator so the §4140 adjunctive income bypass — which depends on MFB
enrollment flags PolicyEngine cannot see — could be enforced directly, and so the §4100 insurance
rule could be relaxed from the prior strict "no insurance" filter to a Medicaid-only exclusion.
That custom calculator re-implemented the income test as a flat `gross_income ≤ 2.5 × FPL`, which
**drifted** from PolicyEngine's countable-income formula as PE refined it (income sources list,
child-earnings exemption, child-support and dependent-care deductions).

This spec describes the current **hybrid** shape: PolicyEngine owns the income determination
again, while MFB keeps the two overlays PE cannot model. PE's periodic income fixes now flow in
automatically instead of being hand-maintained.

## Design

- PolicyEngine computes and MFB reads back two eligibility sub-variables (not the bundled
  `tx_fpp_benefit`, which is $0 unless income-eligible and so would zero out the §4140 bypass):
  - `tx_fpp_age_eligible` (person) — §4130 age, 64 or younger, upper bound only.
  - `tx_fpp_income_eligible` (spm_unit) — countable income (1 TAC 382.109) ≤ 250% FPG.
- MFB layers on:
  - **§4140 adjunctive bypass** — SNAP/WIC/CHIP enrollment makes the household income-eligible
    regardless of PE's income test.
  - **§4100 insurance rule** — only *full* Medicaid disqualifies; Emergency Medicaid and other
    coverage remain eligible.
- Income inputs fed to PE: `AgeDependency`, `TxStateCodeDependency`, and `irs_gross_income`.

## Eligibility Criteria

1. **Age 64 or younger** (§4130)
   - Delegated to PolicyEngine's `tx_fpp_age_eligible` (upper bound only, no minimum age).
     A member with no recorded age comes back not age-eligible.

2. **Household income at or below 250% FPG** (§4130), **OR adjunctive income eligibility** (§4140)
   - Income test delegated to PolicyEngine's `tx_fpp_income_eligible` (countable income per
     1 TAC 382.109 ≤ 250% FPG). MFB no longer computes this.
   - **§4140 bypass** — enrollment in any of the following makes the household income-eligible
     regardless of the income test:
     - SNAP — `screen.has_benefit("tx_snap")` (CurrentBenefit join table, TX-scoped name)
     - WIC — `screen.has_benefit("tx_wic")`
     - CHIP (applicant or their child) — `screen.has_insurance_types(("chp",))` (per-member
       insurance; `tx_chip` is a PE eligibility program, never a current-benefit tile, so
       `has_benefit("tx_chip")` is always False)
     - ⚠️ *data gap:* CHIP Perinatal, the 4th §4140 program, is not collected by the screener.

3. **Not enrolled in (full) Medicaid** (§4100)
   - `member.insurance.has_insurance_types(("medicaid",))` disqualifies. Notably:
     - **Emergency Medicaid** recipients are underinsured and remain eligible (separate
       `emergency_medicaid` flag — intentionally not matched).
     - **Employer / private / CHIP** coverage does **not** disqualify. Per §4200, insured clients
       still qualify with a confidentiality concern OR an annual deductible > 5% of income; the
       screener cannot capture those, so insured (non-Medicaid) clients are included and the §4200
       caveat is surfaced in the program description copy (MFB-1014).

4. **Texas residency** (§4130) — handled automatically by the TX white label; not re-checked.

5. **Citizenship / immigration status — not required** (§4130)
   - `legal_status_required` includes all six values (no restriction). FPP is available regardless
     of immigration status (§4130, Form 1065, TMPPM Vol. 2 §1.1).

## Benefit Value

- **$266.84 / year per eligible member** (annual). Source: TX HHS Women's Health Programs Report
  FY2024 — $78,705,897 ÷ 294,954 clients = $266.84 average annual benefit per participant. Mirrors
  PolicyEngine's `gov.states.tx.fpp.annual_benefit`. Kept as an MFB constant rather than read from
  PE's `tx_fpp_benefit`, because that variable is $0 for §4140 bypass cases (not income-eligible).
- The household total is the sum across eligible members and is truncated for display (e.g., two
  eligible members → `trunc(266.84 × 2) = 533`).

## Screener Field Mapping Summary

| Criterion | Source | Notes |
|-----------|--------|-------|
| Age ≤ 64 | PE `tx_fpp_age_eligible` | per-member; None-age → not eligible |
| Income ≤ 250% FPG | PE `tx_fpp_income_eligible` | PE owns the countable-income formula |
| §4140 bypass | `has_benefit("tx_snap")`, `has_benefit("tx_wic")`, `has_insurance_types(("chp",))` | CHIP Perinatal not captured (gap) |
| Medicaid exclusion | `member.insurance.medicaid` | Emergency Medicaid excluded from match |

## Test Scenarios

Unit tests: `programs/programs/tx/pe/tests/test_fpp.py` (PE determination mocked).
Validation set: `validations/management/commands/import_validations/data/tx_fpp.json` (live PE).
One case each, matching the unit tests `test_s0` … `test_s10`:

0. Eligible 25-year-old, low income, no insurance → eligible, 266.
1. Eligible 64-year-old at the maximum-age boundary, no insurance, low income → eligible, 266.
2. Medicaid-only rule: employer-insured adult AND uninsured 18-year-old both eligible → 533.
3. Ineligible 65-year-old (above maximum age) despite low income and no insurance.
4. Emergency Medicaid recipient remains eligible (underinsured, §4100) → 266.
5. Eligible 30-year-old with employer insurance (other coverage does not disqualify) → 266.
6. Ineligible household whose only reproductive-age member has full Medicaid.
7. Ineligible 35-year-old above 250% FPG, no insurance, no adjunctive benefit.
8. §4140 adjunctive bypass: income above 250% FPG but enrolled in SNAP → eligible, 266.
9. Eligible couple (ages 55 and 30), no insurance → 533.
10. Eligible self-employed parent (age 32) under threshold; Medicaid children excluded → 266.

Unit tests additionally cover the WIC and CHIP adjunctive bypasses and assert that the §4140
bypass does not override the age or Medicaid gates.
