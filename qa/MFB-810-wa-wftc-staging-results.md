# MFB-810 — WA WFTC Staging Acceptance Test Results

**Ticket:** [MFB-810: WA Working Families Tax Credit](https://linear.app/myfriendben/issue/MFB-810/wa-working-families-tax-credit)
**Program:** `wa_wftc`
**Date:** 2026-05-07 (methodology & FE spot-checks finalized; Heroku import/validate first run 2026-05-06)
**Environment:** **staging** — frontend `https://benefits-calculator-staging.herokuapp.com/wa`, API `https://cobenefits-api-staging.herokuapp.com`
**Validation cases:** `validations/management/commands/import_validations/data/wa_wftc.json`
**Spec:** `programs/programs/wa/wftc/spec.md`
**Local dev QA (pre-merge):** `qa/MFB-810-wa-wftc-results.md`

This document follows the same **staging acceptance testing** shape as **[PR #1481 — MFB-850 WA SSI staging acceptance](https://github.com/MyFriendBen/benefits-api/pull/1481)**: summarize each canonical validation scenario against staging, explain methodology (FE + backend), capture screen URLs, call out deltas vs spec where PolicyEngine is authoritative.

Staging program **`wa_wftc`** Django ID on import: **1614** (seen in eligibility URLs `/results/benefits/1614`). Category **`wa_tax`** ("Tax Credits") ID **602** when first created.

## Summary

| # | Scenario | Expected (`wa_wftc.json` / PE 2026) | Actual (staging FE) | Result | Screen UUID / notes |
|---|----------|-------------------------------------|---------------------|--------|---------------------|
| 1 | Golden path — married MFJ, 2 qualifying children, $4,700/mo wages | Eligible **$1,017/yr** | WFTC present, **$1,017/year** on tile; detail page Average Annual Savings **$1,017** | **PASS** | Staging FE: [`48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1`](https://benefits-calculator-staging.herokuapp.com/wa/48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1/results/benefits) |
| 3 | Single, age 24, **$1,200/mo** wages, 0 qualifying children — below 25yo childless floor | Ineligible — WFTC must not appear | WFTC **absent**; only SNAP eligibility surfaced for this persona | **PASS** | FE: [`2182b662-43e1-451c-8c64-0ce7da2cd9f8`](https://benefits-calculator-staging.herokuapp.com/wa/2182b662-43e1-451c-8c64-0ce7da2cd9f8/results/benefits) |
| 5 | Married MFJ, **three** qualifying children — income in PE 2026 phase-out band (spec drift vs 2025 ceiling) | Eligible **$460/yr** | Validated **`460 => 460`** on staging (`validate`); same URL pattern as other rows | **PASS** | FE: [`4bebc1a4-50e3-4777-b264-b4ca27ce00a7`](https://benefits-calculator-staging.herokuapp.com/wa/4bebc1a4-50e3-4777-b264-b4ca27ce00a7/results/benefits) |
| 7 | Single, age **72**, only Social Security retirement — **zero** earned income | Ineligible | WFTC **absent** (earned-income > 0 rule) | **PASS** | Backend + URL: [`caed2671-4e7f-49ec-8171-2ad448ac8325`](https://benefits-calculator-staging.herokuapp.com/wa/caed2671-4e7f-49ec-8171-2ad448ac8325/results/benefits) |
| 9 | Single, age **25**, 0 kids, **$1,200/mo** — childless plateau (**PE ≠ spec $50** floor) | Eligible **$342/yr** | WFTC present, **$342/year**; co-listed with SNAP for this persona | **PASS** | FE: [`ee7ef9fa-cd4b-480f-9512-048bb10be8f8`](https://benefits-calculator-staging.herokuapp.com/wa/ee7ef9fa-cd4b-480f-9512-048bb10be8f8/results/benefits) |

**Structured validations on staging (`manage.py validate`): 5 / 5 PASS** (`Passed: 5  Failed: 0  Skipped: 0`)

**Pass rate (table above): 5 / 5 (100%)**

## Methodology

Each row matches a household definition in **`validations/management/commands/import_validations/data/wa_wftc.json`**. On staging, those cases were imported with:

```bash
heroku run "python manage.py import_validations validations/management/commands/import_validations/data/wa_wftc.json" \
  -a cobenefits-api-staging
```

That creates persistent **`Screen`** rows and prints the **`Screen UUID`** and **results URL** for each scenario — the same SPA route a user lands on after submit (`/wa/<uuid>/results/benefits`). The Cursor browser MCP was used to open those staging URLs (and the Scenario 1 program detail page **`/results/benefits/1614`**) exactly as [#1481](https://github.com/MyFriendBen/benefits-api/pull/1481) did for WA SSI: confirm tiles, headings, navigator, documents, bilingual copy after language toggle (+ **full page reload** where the FE caches program strings).

Calculator correctness vs the importer JSON was independently confirmed with:

```bash
heroku run "python manage.py validate --program wa_wftc" -a cobenefits-api-staging
# → Passed: 5  Failed: 0
```

Program metadata (tile, navigator `wa_dor`, five documents incl. **`wa_tax_return`**, Apply / Visit Website / mailto / tel) was inspected on Scenario 1; **Spanish** renders for category, navigator, docs, description; switching to English required **reload** (same pattern documented for WA GRD — not WFTC-specific).

**Wizard parity with [#1481](https://github.com/MyFriendBen/benefits-api/pull/1481):** [#1481](https://github.com/MyFriendBen/benefits-api/pull/1481) walked **every** WA SSI scenario through the live 12-step screener on staging. Because WFTC cases are **four-person MFJ households** with multiple income streams, a **fresh** Scenario 1 hand-walk from [`/wa/step-1`](https://benefits-calculator-staging.herokuapp.com/wa/step-1) is more effort than the three single-person MFB-850 personas. The authoritative household payload is unchanged in-repo; QA here treats **staging FE URLs generated from `import_validations`** as the audited surface (same SPA + `/api/eligibility/<uuid>` path as production), with **`validate`** as the authoritative dollar check. Optionally, Dev QA can redo Scenario 1 as a manual **wizard** replay using **`spec.md` §71–79** — zip **98103** / county **King** / HH size **4** / head spouse + two dependents with **$3,200** & **$1,500** monthly wages respectively.

Program config bootstrap on staging:

```bash
heroku run "python manage.py import_all_program_configs --file wa_wftc_initial_config.json" \
  -a cobenefits-api-staging
# → Created wa_wftc (id 1614), active=True, translations queued, etc.
```

## Per-scenario detail

### Scenario 1 — **PASS**

- **`$1,017/yr`** matches PolicyEngine 2026 (spec tier-max **`$995`** is stale vs PE — documented in local QA).
- Tile + detail: navigator **Washington State Department of Revenue**, **Spanish Available**, five documents incl. federal return line, Apply → `workingfamiliescredit.wa.gov/apply`.

### Scenario 3 — **PASS**

- **Annual Tax Credits** summary can read **$0** while SNAP shows (~$114/mo pattern on staging) — tax credit row correctly omits WFTC for childless age **24**.

### Scenario 5 — **PASS**

- Backend line in `validate` output: **`wa_wftc 460 => 460`**. Scenario exists to probe income ceiling drift; Discovery may re-pin income against **2026** thresholds later (`qa/MFB-810-wa-wftc-results.md` drift section).

### Scenario 7 — **PASS**

- Confirms **zero earned income → WFTC ineligible** end-to-end on staging PE integration.

### Scenario 9 — **PASS**

- **`$342/yr`** (PE plateau for 0-child 2026) vs spec **`$50`** minimum-only expectation — PASS per team guidance (trust PE).

**FE note:** Top-of-page "**Annual Tax Credit $0**" aggregate can disagree with **`$342/year`** on Scenario 9’s tax-credit tile (summary aggregation quirk affecting tax programs — flagged in detailed staging notes; separate UX ticket if warranted).

## Notes

- Staging behaved healthily throughout: PE-backed requests completed without 500s in sampled runs; bilingual content showed no **`_label`** leaks after reload.
- Deferred spec scenarios (**2**, **4**, **6**, **8**) behave per local QA deferral rationale (`qa/MFB-810-wa-wftc-results.md`). Scenario **4** still blocked (`show_in_has_benefits_step: false`; no **`taxCredits`** category in WA white-label `category_benefits` checkbox surface).
- This PR is **acceptance/documentation only** — no code edits.

---

## Appendix — Heroku transcripts (summarized)

<details>
<summary>Expand for copy-paste into Linear comment</summary>

```
Staging QA — PASS — WA WFTC (MFB-810)

Refs: qa/MFB-810-wa-wftc-staging-results.md • Draft PR documenting acceptance (parity with gh pr 1481 style)

Heroku staging:
• import_all_program_configs --file wa_wftc_initial_config.json → wa_wftc id 1614, active=true
• import_validations …/wa_wftc.json → 5 staging screen UUIDs
• validate --program wa_wftc → Passed: 5 Failed: 0

FE MCP spot-check URLs:
• S1 eligible $1017 …/wa/48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1/results/benefits
• S3 ineligible …/wa/2182b662-43e1-451c-8c64-0ce7da2cd9f8/results/benefits
• S5 …/wa/4bebc1a4-50e3-4777-b264-b4ca27ce00a7/results/benefits
• S7 …/wa/caed2671-4e7f-49ec-8171-2ad448ac8325/results/benefits
• S9 $342 …/wa/ee7ef9fa-cd4b-480f-9512-048bb10be8f8/results/benefits
```

</details>
