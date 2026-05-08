# MFB-810 — WA WFTC Staging Acceptance Test Results

**Ticket:** [MFB-810: WA Working Families Tax Credit](https://linear.app/myfriendben/issue/MFB-810/wa-working-families-tax-credit)
**Program:** `wa_wftc`
**Date:** 2026-05-07 (prior 5-case MCP spot-check); **nine-case suite + migration `0153` pending staging deploy**
**Environment:** **staging** — frontend `https://benefits-calculator-staging.herokuapp.com/wa`, API `https://cobenefits-api-staging.herokuapp.com`
**Validation cases:** `validations/management/commands/import_validations/data/wa_wftc.json`
**Spec:** `programs/programs/wa/wftc/spec.md`
**Local dev QA (pre-merge):** `qa/MFB-810-wa-wftc-results.md`

This document follows the same **staging acceptance testing** layout as **[PR #1482 — MFB-778 WA WSOS GRD staging QA](https://github.com/MyFriendBen/benefits-api/pull/1482)** (four QA steps plus a numbered **staging screen UUID** table per scenario). Methodological notes overlap **[PR #1481 — MFB-850 WA SSI staging acceptance](https://github.com/MyFriendBen/benefits-api/pull/1481)** (how `import_validations` URLs and `validate` are used).

**Inventory:** Repo **`wa_wftc.json` now holds nine households** (**`spec.md` scenarios 1–9**): every row has **PE 2026** expected value/eligibility. Scenario **2** uses **$1,630/mo** wages (not **$1,593**) so PolicyEngine 2026 returns **ineligible** (the spec’s old income sat just *inside* the 2026 childless band). Scenario **4** sets **`has_wa_wftc: true`** on the screen payload so the API returns **`already_has: true`** for `wa_wftc` while the calculator still reports the **$1,017** credit (FE may filter the tile).

**Deploy before re-running staging QA:** apply **`screener.0153_screen_has_wa_wftc`** (adds `Screen.has_wa_wftc`) and ship the expanded **`wa_wftc.json`**, then **`import_validations`** + **`validate --program wa_wftc`** on **cobenefits-api-staging**. UUIDs below for scenarios **2, 4, 6, and 8** are **placeholders** until that import completes.

Staging program **`wa_wftc`** Django ID after config import historically: **1614** (URLs like `/results/benefits/1614`).

---

## Results — all 4 staging QA steps (**target after nine-case redeploy**)

| Step | What | Outcome |
| ---- | --- | ------- |
| 1 | `import_all_program_configs --file wa_wftc_initial_config.json` on cobenefits-api-staging | **PASS** (existing) — program **1614**, `active=True` |
| 2 | All **nine** households in **`wa_wftc.json`** on staging FE (`import_validations` URLs) | **PASS — 9 / 9** *(pending fresh import)* |
| 3 | `validate --program wa_wftc` on cobenefits-api-staging | **PASS — 9 / 9** *(pending redeploy)* |
| 4 | Manual visual check (Scenario 1 program detail, EN + ES) | **PASS** *(prior run; spot-check after redeploy)* |

### Step 2 — staging screen UUIDs (all nine `spec.md` scenarios)

**Fill in the last column** from the Heroku `import_validations` transcript after the next staging import. Rows **1, 3, 5, 7, 9** retain UUIDs from the **2026-05-06/07** five-case run for regression until replaced.

| # | Scenario | Expected (`wa_wftc.json` / PE 2026) | Staging FE / `validate` | Result | Screen UUID |
| - | --- | --- | --- | --- | --- |
| 1 | MFJ golden path — 4-person, $4.7k/mo | **$1,017** eligible | | **PASS** *(prior)* | `48b8bcc6-4167-49b7-bb9f-cfa75e01d0e1` |
| 2 | Childless single **$1,630/mo** — above PE 2026 0-QC cutoff | **$0** ineligible | | pending import | **`TBD`** |
| 3 | Age **24** childless guardrail | **$0** ineligible | | **PASS** *(prior)* | `2182b662-43e1-451c-8c64-0ce7da2cd9f8` |
| 4 | Head + **2 QC**, **$2,500/mo** + **`has_wa_wftc: true`** | Calculator **$1,017**; API **`already_has: true`** | | pending import | **`TBD`** |
| 5 | MFJ + **three** QC income probe | **`$460`** eligible | | **PASS** *(prior)* | `4bebc1a4-50e3-4777-b264-b4ca27ce00a7` |
| 6 | Single + **1** child **$4,000/mo** | **`$499`** eligible | | pending import | **`TBD`** |
| 7 | Age **72**, SS retirement only | **$0** ineligible | | **PASS** *(prior)* | `caed2671-4e7f-49ec-8171-2ad448ac8325` |
| 8 | MFJ **+3** QC **$4,000/mo** combined wages | **`$1,360`** eligible | | pending import | **`TBD`** |
| 9 | Age **25** childless **`$342`** plateau | **`$342`** eligible | | **PASS** *(prior)* | `ee7ef9fa-cd4b-480f-9512-048bb10be8f8` |

Full SPA paths:  
`https://benefits-calculator-staging.herokuapp.com/wa/<uuid>/results/benefits`

**Scenario 4 spot-check:** after import, **`GET`/eligibility** for that screen UUID should show `wa_wftc` with **`eligible: true`**, **`estimated_value: 1017`**, and top-level **`already_has: true`**. Until the calculator FE reads that flag universally, manual verification may require the admin/API response (wizard checkbox for WFTC is still gated by **`show_in_has_benefits_step`** + translations — separate FE/config follow-up).

### Spec coverage summary (staging)

| Spec # | In importer + `validate`? | Expected staging result |
| ------ | ------------------------- | ------------------------ |
| 1–9 | **Yes — all nine** | **PASS** per row expectations after redeploy/import |

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
# Target after redeploy: Passed: 9  Failed: 0
```

(Migration **`0153`** must be applied **before** `import_validations` can persist **`has_wa_wftc`**.)

See **`qa/MFB-810-wa-wftc-results.md`** for local methodology and Scenario **2** income rationale.

---

## Appendix — Linear comment (**update counts after staging import**)

<details>
<summary>Expand for copy-paste into Linear comment</summary>

```
Staging QA — WA WFTC (MFB-810) — nine-case suite

Refs: qa/MFB-810-wa-wftc-staging-results.md

Deploy: screener migration 0153 (has_wa_wftc) + expanded validations/…/wa_wftc.json

Heroku staging (after merge):
• import_validations …/wa_wftc.json → 9 Screen UUIDs
• validate --program wa_wftc → target Passed: 9 Failed: 0

Scenario 4: household has has_wa_wftc=true; API already_has should be true; PE value still $1,017.

Prior MCP UUIDs still valid for S1,S3,S5,S7,S9 until superseded by new import output.
```

</details>
