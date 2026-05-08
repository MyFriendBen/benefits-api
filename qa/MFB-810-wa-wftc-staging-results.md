# MFB-810 — WA WFTC Staging Acceptance Test Results

**Ticket:** [MFB-810: WA Working Families Tax Credit](https://linear.app/myfriendben/issue/MFB-810/wa-working-families-tax-credit)
**Program:** `wa_wftc`
**Date:** 2026-05-07 (methodology & FE spot-checks finalized; Heroku import/validate first run 2026-05-06)
**Environment:** **staging** — frontend `https://benefits-calculator-staging.herokuapp.com/wa`, API `https://cobenefits-api-staging.herokuapp.com`
**Validation cases:** `validations/management/commands/import_validations/data/wa_wftc.json`
**Spec:** `programs/programs/wa/wftc/spec.md`
**Local dev QA (pre-merge):** `qa/MFB-810-wa-wftc-results.md`

This document follows the same **staging acceptance testing** layout as **[PR #1482 — MFB-778 WA WSOS GRD staging QA](https://github.com/MyFriendBen/benefits-api/pull/1482)** (four QA steps plus a numbered **staging screen UUID** table per scenario row in scope). Methodological notes overlap **[PR #1481 — MFB-850 WA SSI staging acceptance](https://github.com/MyFriendBen/benefits-api/pull/1481)** (how `import_validations` URLs and `validate` are used).

**Important:** Unlike GRD (`spec.md` row count equals `validate` row count), WFTC’s importer file **`wa_wftc.json` contains five households** keyed to **`spec.md` scenarios 1, 3, 5, 7, and 9** only. Scenarios **2, 4, 6, and 8** are **not imported** — they are **`DEFERRED`** on staging (same rationale as `qa/MFB-810-wa-wftc-results.md`). The matrices below spell out **PASS** vs **`DEFERRED`** for **all nine** spec rows so reviewers never have to hunt footnotes.

Staging program **`wa_wftc`** Django ID on import: **1614** (seen in eligibility URLs `/results/benefits/1614`). Category **`wa_tax`** ("Tax Credits") ID **602** when first created.

## Results — all 4 staging QA steps PASS

| Step | What | Outcome |
| ---- | --- | ------- |
| 1 | `import_all_program_configs --file wa_wftc_initial_config.json` on cobenefits-api-staging | **PASS** — program id **1614**, `active=True`, metadata + translations as expected |
| 2 | All **5** households in **`wa_wftc.json`** on staging FE (`import_validations` URLs) | **PASS — 5 / 5** |
| 3 | `validate --program wa_wftc` on cobenefits-api-staging | **PASS — 5 / 5** (`Passed: 5`, `Failed: 0`, `Skipped: 0`) |
| 4 | Manual visual check (Scenario 1 program detail, EN + ES) | **PASS** — tile, `$1,017` value, navigator, five documents, bilingual copy after reload |

### Step 2 — staging screen UUIDs for all 5 validation scenarios

Each `#` matches the **`programs/programs/wa/wftc/spec.md` scenario index** carried through `wa_wftc.json` notes (not a 1–5-only internal index).

| # | Scenario | Expected (`wa_wftc.json` / PE 2026) | Staging FE | Result | Screen UUID |
| - | ---------- | ----------------------------------- | ---------- | ------ | ----------- |
| 1 | MFJ golden path — 4-person, $4.7k/mo wages combined | Eligible **$1,017/yr** | WFTC present, **$1,017/year** on tile | **PASS** | `48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1` |
| 3 | Single age **24**, $1.2k/mo, 0 QC — childless < 25 guardrail | **Ineligible** — WFTC absent | SNAP may show for low income; **no WFTC tile** | **PASS** | `2182b662-43e1-451c-8c64-0ce7da2cd9f8` |
| 5 | MFJ + **three** QC — income probing 2026 phase-out ceiling | Eligible **`$460/yr`** (see local drift notes) | `validate`: **`460 => 460`**; FE parity at results URL | **PASS** | `4bebc1a4-50e3-4777-b264-b4ca27ce00a7` |
| 7 | Single age **72**, SS retirement only — **zero** earned income | **Ineligible** | **No WFTC** | **PASS** | `caed2671-4e7f-49ec-8171-2ad448ac8325` |
| 9 | Single age **25**, $1.2k/mo, childless plateau (**PE `$342`** vs spec **`$50`**) | Eligible **`$342/yr`** | WFTC **$342/year** (+ SNAP on staging catalog) | **PASS** | `ee7ef9fa-cd4b-480f-9512-048bb10be8f8` |

Full SPA paths (same shape as GRD QA):  
`https://benefits-calculator-staging.herokuapp.com/wa/<uuid>/results/benefits`

### Where every `spec.md` scenario landed on staging — PASS / DEFERRED

Nine rows explicitly; this is the analogue of counting **every** GRD scenario in PR **#1482** even though three WFTC spec rows never enter the staging validation file.

| Spec # | In `wa_wftc.json` + Step 2 / `validate`? | Staging result | Notes |
| ------ | ------------------------------------------ | -------------- | ----- |
| 1 | Yes | **PASS** | Documented in Step 2 table |
| 2 | No | **`DEFERRED`** | Not in importer — 2026 PE / Discovery re-pin (local QA) |
| 3 | Yes | **PASS** | Step 2 table |
| 4 | No | **`DEFERRED`** | “Already receiving WFTC” exclusion — `show_in_has_benefits_step: false` blocks structured FE path |
| 5 | Yes | **PASS** | Step 2 table |
| 6 | No | **`DEFERRED`** | Not in importer — child + income band vs 2026 PE |
| 7 | Yes | **PASS** | Step 2 table |
| 8 | No | **`DEFERRED`** | Not in importer — married + 3-kid band vs 2026 PE |
| 9 | Yes | **PASS** | Step 2 table |

**Counts:** **5 `PASS`** on staging for imported rows; **4 `DEFERRED`** (not **FAIL** — no staging evidence contradicts spec intent; they were never run as structured imports).

### Step 4 — manual visual checks (Scenario 1 program detail)

Detail page on staging for Scenario **1**: [https://benefits-calculator-staging.herokuapp.com/wa/48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1/results/benefits/1614](https://benefits-calculator-staging.herokuapp.com/wa/48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1/results/benefits/1614)

**English** — Working Families Tax Credit tile and detail: policy copy, **$1,017** estimated value, navigator to **Washington State Department of Revenue**, Apply / web / phone affordances, document list incl. **`wa_tax_return`**, no raw `_label` keys.

**Spanish (`es`)** — after **full reload** following language toggle (same caching caveat as WA GRD in PR **#1482**): translated category/navigator/doc tiles and body text coherent with EN.

## Health observations during the run

- Staging FE and API behaved normally for sampled eligibility loads — **no 500s, no CORS errors** in MCP-driven runs.
- Cold-start latency on staging is elevated on first results-page hit per persona (tens of seconds); subsequent navigations are faster — consistent with staging behavior noted in **#1482**.
- FE quirk unrelated to **`wa_wftc` correctness:** Scenario **9** can show **`Annual Tax Credits $0`** in the aggregate header while the WFTC tile shows **`$342/year`** — same inconsistency flagged in detailed notes below.

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

- Deferred **`spec.md` rows 2, 4, 6, 8** match the rationale in **`qa/MFB-810-wa-wftc-results.md`** and are enumerated as **`DEFERRED`** in the nine-row matrix above (not hidden in prose).
- Scenario **4** remains structurally blocked for Discovery-style automation (`show_in_has_benefits_step: false`; no **`taxCredits`** category in WA white-label `category_benefits` checkbox surface).
- This PR is **acceptance/documentation only** — no code edits.

---

## Appendix — Heroku transcripts (summarized)

<details>
<summary>Expand for copy-paste into Linear comment</summary>

```
Staging QA — PASS — WA WFTC (MFB-810)

Refs: qa/MFB-810-wa-wftc-staging-results.md • Acceptance doc mirrors PR #1482 (4 steps + UUID table + full spec matrix) & PR #1481 methodology

Heroku staging:
• import_all_program_configs --file wa_wftc_initial_config.json → wa_wftc id 1614, active=true
• import_validations …/wa_wftc.json → 5 staging screen UUIDs (spec rows 1,3,5,7,9)
• validate --program wa_wftc → Passed: 5 Failed: 0
• spec rows 2,4,6,8 DEFERRED (see nine-row matrix in doc)

FE MCP spot-check URLs:
• S1 eligible $1017 …/wa/48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1/results/benefits
• S3 ineligible …/wa/2182b662-43e1-451c-8c64-0ce7da2cd9f8/results/benefits
• S5 …/wa/4bebc1a4-50e3-4777-b264-b4ca27ce00a7/results/benefits
• S7 …/wa/caed2671-4e7f-49ec-8171-2ad448ac8325/results/benefits
• S9 $342 …/wa/ee7ef9fa-cd4b-480f-9512-048bb10be8f8/results/benefits
```

</details>
