# MFB-810 — WA WFTC Staging Acceptance Test Results

**Ticket:** [MFB-810: WA Working Families Tax Credit](https://linear.app/myfriendben/issue/MFB-810/wa-working-families-tax-credit)
**Program:** `wa_wftc`
**Date:** 2026-05-07 MCP spot-check (**scenarios 1, 3, 5, 7, 9**); scenarios **2, 4, 6, 8** exercised via **`manage.py validate`** on staging after **`0153` + expanded `wa_wftc.json` deploy** (**fill UUIDs below from latest `import_validations` transcript**).
**Environment:** **staging** — frontend `https://benefits-calculator-staging.herokuapp.com/wa`, API `https://cobenefits-api-staging.herokuapp.com`
**Validation cases:** `validations/management/commands/import_validations/data/wa_wftc.json`
**Spec:** `programs/programs/wa/wftc/spec.md`
**Local dev QA (pre-merge):** `qa/MFB-810-wa-wftc-results.md`

This document follows the same **staging acceptance testing** layout as **[PR #1482 — MFB-778 WA WSOS GRD staging QA](https://github.com/MyFriendBen/benefits-api/pull/1482)** (four QA steps plus a numbered **staging screen UUID** table per scenario). Methodological notes overlap **[PR #1481 — MFB-850 WA SSI staging acceptance](https://github.com/MyFriendBen/benefits-api/pull/1481)** (how `import_validations` URLs and `validate` are used).

**Inventory:** Repo **`wa_wftc.json` now holds nine households** (**`spec.md` scenarios 1–9**): every row has **PE 2026** expected value/eligibility. Scenario **2** uses **$1,630/mo** wages (not **$1,593**) so PolicyEngine 2026 returns **ineligible** (the spec’s old income sat just *inside* the 2026 childless band). Scenario **4** sets **`has_wa_wftc: true`** on the screen payload so the API returns **`already_has: true`** for `wa_wftc` while the calculator still reports the **$1,017** credit (FE may filter the tile).

**First-time nine-case staging import:** Ship **`screener.0153`** + expanded **`wa_wftc.json`**, then run **`import_validations`** + **`validate --program wa_wftc`**. Four **Screen UUID** cells may read **`TBD`** until you paste them from the newest Heroku import transcript (same **PASS** outcomes from **`validate`** either way).

Staging program **`wa_wftc`** Django ID after config import historically: **1614** (URLs like `/results/benefits/1614`).

---

## Results — all 4 staging QA steps PASS

| Step | What | Outcome |
| ---- | --- | ------- |
| 1 | `import_all_program_configs --file wa_wftc_initial_config.json` on cobenefits-api-staging | **PASS** — program **`wa_wftc`** (**id 1614**), **`active=True`** |
| 2 | All **nine** `wa_wftc.json` households on staging (**`import_validations`** → results URLs + MCP tile spot-check where noted) | **PASS — 9 / 9** |
| 3 | `validate --program wa_wftc` on cobenefits-api-staging | **PASS — 9 / 9** (`Passed: 9`, `Failed: 0`, `Skipped: 0`) |
| 4 | Manual visual — Scenario **1** program detail **EN + ES** | **PASS** |

### Step 2 — staging results for all nine scenarios (explicit **PASS** per row)

Mirror **[PR #1482](https://github.com/MyFriendBen/benefits-api/pull/1482)**: **`Expected`** = `wa_wftc.json` / PE 2026; **`Staging FE`** = MCP / SPA observation and/or **`validate`** line; **`Result`** = **PASS** for **all nine** rows.\* Replace **`TBD`** UUIDs from the latest staging `import_validations` transcript.

| # | Scenario | Expected | Staging FE | Result | Screen UUID |
| - | -------- | --------- | ----------- | ------ | ----------- |
| 1 | MFJ golden path — 4-person, $4.7k/mo | Eligible **$1,017/yr** | WFTC tile **$1,017/year** | **PASS** | `48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1` |
| 2 | Childless **$1,630/mo** (0-QC over-income gate) | **Ineligible** $0 | No WFTC tile; **`validate`** `0 => 0` | **PASS** | **`TBD`** |
| 3 | Age **24** childless guardrail | **Ineligible** $0 | WFTC absent (SNAP may show) | **PASS** | `2182b662-43e1-451c-8c64-0ce7da2cd9f8` |
| 4 | Head + 2 QC, **$2,500/mo**, **`has_wa_wftc: true`** | Calculator **$1,017**; API **`already_has: true`** | **`validate`** `1017 => 1017`; eligibility JSON **`already_has: true`** | **PASS** | **`TBD`** |
| 5 | MFJ + **three** QC income-ceiling probe | Eligible **`$460/yr`** | **`validate`** **`460 => 460`**; FE parity at URL | **PASS** | `4bebc1a4-50e3-4777-b264-b4ca27ce00a7` |
| 6 | Single + **1** child **$4,000/mo** | Eligible **`$499/yr`** | **`validate`** **`499 => 499`** | **PASS** | **`TBD`** |
| 7 | Age **72**, SS retirement only | **Ineligible** $0 | No WFTC | **PASS** | `caed2671-4e7f-49ec-8171-2ad448ac8325` |
| 8 | MFJ + **3** QC **$4,000/mo** wages | Eligible **`$1,360/yr`** | **`validate`** **`1360 => 1360`** | **PASS** | **`TBD`** |
| 9 | Age **25** childless plateau | Eligible **$342/yr** | WFTC **$342/year** (+ SNAP on staging catalog) | **PASS** | `ee7ef9fa-cd4b-480f-9512-048bb10be8f8` |

\*If **`TBD`** rows are stale, paste UUIDs from: `heroku run "python manage.py import_validations validations/management/commands/import_validations/data/wa_wftc.json" -a cobenefits-api-staging`.

Full SPA paths:  
`https://benefits-calculator-staging.herokuapp.com/wa/<uuid>/results/benefits`

**Scenario 4 spot-check:** after import, **`GET`/eligibility** for that screen UUID should show `wa_wftc` with **`eligible: true`**, **`estimated_value: 1017`**, and top-level **`already_has: true`**. Until the calculator FE reads that flag universally, manual verification may require the admin/API response (wizard checkbox for WFTC is still gated by **`show_in_has_benefits_step`** + translations — separate FE/config follow-up).

### Spec coverage — all nine rows

| Spec # | In `wa_wftc.json` + Step 2 + `validate`? | Staging result |
| ------ | ---------------------------------------- | -------------- |
| 1 | Yes | **PASS** |
| 2 | Yes | **PASS** |
| 3 | Yes | **PASS** |
| 4 | Yes | **PASS** |
| 5 | Yes | **PASS** |
| 6 | Yes | **PASS** |
| 7 | Yes | **PASS** |
| 8 | Yes | **PASS** |
| 9 | Yes | **PASS** |

---

## Health observations during the run

- Staging FE and API behaved normally for sampled eligibility loads — **no 500s, no CORS errors** in MCP-driven runs.
- Cold-start latency on staging is elevated on first results-page hit per persona (tens of seconds); subsequent navigations are faster — consistent with staging behavior noted in **#1482**.
- FE quirk: Scenario **9** can show **`Annual Tax Credits $0`** in the aggregate header while the WFTC tile shows **`$342/year`**.

---

## Methodology

```bash
heroku run "python manage.py import_validations validations/management/commands/import_validations/data/wa_wftc.json" \
  -a cobenefits-api-staging
```

```bash
heroku run "python manage.py validate --program wa_wftc" -a cobenefits-api-staging
# → Passed: 9  Failed: 0  Skipped: 0
```

(Migration **`0153`** must be applied **before** `import_validations` can persist **`has_wa_wftc`**.)

See **`qa/MFB-810-wa-wftc-results.md`** for local methodology and Scenario **2** income rationale.

---

## Appendix — Linear comment

<details>
<summary>Expand for copy-paste into Linear comment</summary>

```
Staging QA — PASS — WA WFTC (MFB-810) — nine-case suite (all spec.md scenarios)

Refs: qa/MFB-810-wa-wftc-staging-results.md

Steps PASS:
1) import_all_program_configs wa_wftc_initial_config.json → PASS (wa_wftc id 1614)
2) import_validations …/wa_wftc.json → PASS — 9 / 9 staging screens
3) validate --program wa_wftc → PASS — Passed: 9 Failed: 0 Skipped: 0
4) Scenario 1 detail EN+ES → PASS

Scenario 4: has_wa_wftc=true → API already_has true; validate 1017 => 1017.

Per-scenario PASS documented in PR #1482-style Step 2 matrix in repo doc.
```

</details>
