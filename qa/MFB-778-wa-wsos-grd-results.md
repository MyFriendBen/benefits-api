# MFB-778 — WA WSOS GRD QA Results

**Ticket:** [MFB-778: WA Washington State Opportunity Scholarship (GRD)](https://linear.app/myfriendben/issue/MFB-778/wa-washington-state-opportunity-scholarship-grd)
**Program:** `wa_wsos_grd`
**Date:** 2026-05-06
**Environment:** local (frontend `http://localhost:3002`, backend `http://localhost:8000`)
**Spec:** `programs/programs/wa/wsos_grd/spec.md`

## Summary

| # | Scenario | Expected | Actual (FE) | Result | Screen UUID |
|---|----------|----------|-------------|--------|-------------|
| 1 | WA student, 1-person, $4k/mo (well below 125% MFI) | Eligible $25,000 | Eligible $25,000 | PASS | `16e38a75-7022-44b0-ae91-2446ae7be33a` (manual UI walk) |
| 2 | 1-person, not a student, $4k/mo | Ineligible | 0 programs found | PASS | `cf1379a7-744a-4415-a9a2-a7b368333171` |
| 3 | 1-person student, $10k/mo (above 155% MFI for size 1) | Ineligible | 0 programs found | PASS | `8c32da02-91f1-4892-a748-1155bb573f36` |
| 4 | 3-person student head, $12,208/mo (at 125% MFI for size 3) | Eligible $25,000 | Eligible $25,000 | PASS | `395e24d7-7823-4cb6-9158-b99447ba20b2` |
| 5 | 1-person student, $8,500/mo (in 126-155% MFI band, size 1) | Eligible $25,000 | Eligible $25,000 | PASS | `ee3e5f3e-666c-46ce-9137-4636c03e7b8e` |
| 6 | 3-person student head, $13k/mo (in 126-155% MFI band, size 3) | Eligible $25,000 | Eligible $25,000 | PASS | `075312eb-228c-4f1d-9188-f24ef595cf55` |
| 7 | 3-person student head, $16k/mo (above 155% MFI for size 3) | Ineligible | 0 programs found | PASS | `0793bac5-39da-4828-a589-b7deb167e7c0` |

**Pass rate: 7 / 7 (100%)**

## Methodology

For each spec scenario, the household input was first encoded into the validation file
`validations/management/commands/import_validations/data/wa_wsos_grd.json` so that
`python manage.py validate --program wa_wsos_grd` exercises the calculator end-to-end against
the same code path the FE uses to render results.

- **Scenario 1**: completed via a full hand-walked flow through the Cursor browser MCP
  (zip → county → household size → member basics → student info → income → expenses →
  assets → benefits → near-term → referral → confirmation → submit) to confirm the new
  program shows up in the FE results page after a real screener submission.
- **Scenarios 2-7**: each scenario was imported via `import_validations`, generating a
  persistent screen UUID. The FE results page was opened directly at
  `http://localhost:3002/wa/<uuid>/results/benefits` to verify the rendered output
  (program present with `$25,000` for eligible cases, `0 Programs Found` for ineligible).

The full hand-walked Scenario 1 confirmed the funnel correctly persists `student=true` and
the wages income, and that the submitted screen produces the expected results page in the
FE. Scenarios 2-7 reuse the same FE rendering path with directly-injected screens that vary
only the dimensions under test.

## Per-scenario detail

### Scenario 1: Clearly Eligible — WA student below 125% MFI — **PASS**

- Steps walked end-to-end through the FE: zip `98101` → King County → household_size `1` → head
  born 1990-01 (age 36) → marked Student (half-time enrolled = Yes; job-training, work-study,
  20+hrs other employment = No) → No insurance → $4,000/mo wages → $0 expenses → $0 assets →
  No public benefits → no near-term help → referral = Flyer → submit.
- Results page: program appears under **Education** with **Application Time: 30 minutes**
  and **Estimated Savings: $25,000**.
- The "Estimated Monthly Savings" tile shows `$2,083` ($25,000 / 12), which is how the FE
  amortizes a `lump_sum` value for the monthly summary tile. The underlying `$25,000` value
  is correctly displayed on the program card itself.

### Scenario 2: Ineligible — not a student — **PASS**
Results page shows **0 Programs Found** (per-member student gate fails → household ineligible).

### Scenario 3: Ineligible — 1-person student, $10k/mo above 155% MFI — **PASS**
$10,000/mo × 12 = $120,000/yr > $112,500 (size-1 155% MFI cap). Results page shows
**0 Programs Found**.

### Scenario 4: Eligible — 3-person at the 125% MFI boundary — **PASS**
$12,208/mo × 12 = $146,496/yr <= $181,500 (size-3 155% MFI cap). Program appears with
**Estimated Savings: $25,000**.

### Scenario 5: Eligible — 1-person student in 126-155% MFI band — **PASS**
$8,500/mo × 12 = $102,000/yr is above the size-1 125% threshold ($90,500) but at or below
the 155% cap ($112,500). Program appears with **Estimated Savings: $25,000**. Per spec, the
hardship caveat is surfaced in the program description so the user knows that final eligibility
in this band is conditional on demonstrating financial hardship.

### Scenario 6: Eligible — 3-person, head is student, in 126-155% MFI band — **PASS**
$13,000/mo × 12 = $156,000/yr lands inside the size-3 expanded eligibility band — above the
size-3 125% threshold ($146,500) and below the 155% cap ($181,500). Program appears with
**Estimated Savings: $25,000**. Per spec, the hardship caveat is surfaced in the program
description for applicants in this band.

> Note: this scenario originally walked at $10,000/mo (which also resolved to "eligible
> $25,000" because $120k/yr is below the 3-person 155% cap). The income was raised to
> $13,000/mo across the spec, validations, and unit tests during pre-merge code review so
> that scenario 6 actually exercises the 126–155% expanded band rather than duplicating
> Scenario 1's "well below 125%" coverage.

### Scenario 7: Ineligible — 3-person at $16k/mo above 155% MFI for size 3 — **PASS**
$16,000/mo × 12 = $192,000/yr > $181,500 (size-3 155% MFI cap). Results page shows
**0 Programs Found** (no hardship path applies above 155% MFI).

## Backing automated checks

In addition to the FE-driven scenarios above, the following automated checks all pass:

- **Unit tests** (`python manage.py test programs.programs.wa.wsos_grd`): **10 / 10 pass**
  - Cover all 7 spec scenarios at the calculator level, plus boundary checks against the
    published 6-row MFI table and the linear extension for sizes > 6.
- **Validations** (`python manage.py validate --program wa_wsos_grd`): **all pass**
  - Runs every validation case in `wa_wsos_grd.json` against the same calculator path the FE
    uses; this command is what is rerun on staging and prod after each promotion.
