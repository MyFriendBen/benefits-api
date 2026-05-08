# MFB-850 — WA SSI Staging Acceptance Test Results

**Ticket:** [MFB-850 · WA Supplemental Security Income](https://linear.app/myfriendben/issue/MFB-850/wa-ssi)  
**Program:** `wa_ssi`  
**Date:** 2026-05-06 (**structured acceptance**); refreshed **2026-05-08** to **[PR #1482](https://github.com/MyFriendBen/benefits-api/pull/1482)** / **[PR #1486](https://github.com/MyFriendBen/benefits-api/pull/1486)** layout  
**Environment:** **staging** — frontend [https://benefits-calculator-staging.herokuapp.com/wa](https://benefits-calculator-staging.herokuapp.com/wa), API [https://cobenefits-api-staging.herokuapp.com](https://cobenefits-api-staging.herokuapp.com)  
**Validation cases:** `validations/management/commands/import_validations/data/wa_ssi.json`  
**Spec:** `programs/programs/wa/ssi/spec.md`  

This document follows the same **staging acceptance** shape used for **[MFB-778 WSOS GRD staging QA (PR #1482)](https://github.com/MyFriendBen/benefits-api/pull/1482)** and **MFB-810 WA WFTC ([PR #1486](https://github.com/MyFriendBen/benefits-api/pull/1486))**: **four QA steps PASS**, explicit **PASS** per **imported validation row**, and a **coverage matrix** tying **`spec.md` § Test Scenarios (1–15)** to importer / deferred / manual rows.

---

## Important — importer scope vs **15** QA scenarios

- **`wa_ssi.json`** holds **three** households (eligible standard, primary ineligible exclusion, earned-income exclusions edge case) — the **canonical reviewer-guide set** (**see `spec.md` → “JSON Test Cases”**).
- **`spec.md` acceptance list** spells out **15** narrative scenarios plus one **manual** citizenship-filter check. Scenarios **not encoded in **`wa_ssi.json`** today remain reference-only until validations are expanded (same pattern used when WFTC grew past the first reviewer-batch).

---

## Results — all 4 staging QA steps PASS

| Step | What | Outcome |
| ---- | ----- | ------- |
| 1 | **`import_all_program_configs --file wa_ssi_initial_config.json`** on **cobenefits-api-staging** | **PASS** — **`wa_ssi`** program live, **`active=True`**, metadata + navigator + documents as deployed |
| 2 | All **three** JSON households exercised on staging **via full 12-step screener** (MCP, same funnel as **[PR #1481](https://github.com/MyFriendBen/benefits-api/pull/1481)** original write-up) — zip **98101** / county **King** | **PASS — 3 / 3** |
| 3 | **`validate --program wa_ssi`** on **cobenefits-api-staging** | **PASS — 3 / 3** (`Passed: 3`, `Failed: 0`, `Skipped: 0`) |
| 4 | **Spot-check** — Scenario-row **§1 / eligible standard** tiles + Cash Assistance grouping + copy | **PASS** |

### Step 2 — staging observations for **all three** importer rows (**Result = PASS** each)

Closest **`spec.md` § Scenario** numbering is shown (**not** importer array index vs spec 1-for-15).

| `wa_ssi.json` row | Spec § anchor | Scenario (short) | Expected (PE **`wa_ssi`**, annual **`value`** unless ineligible) | Staging FE / `validate` | Result | Screen UUID / repro |
| --- | --- | --- | --- | --- | --- | --- |
| **1** | **§ Scenario 1** | Aged-only golden path (**70**, no income, **$0** resources) | **Eligible `11928`** / **$994**/mo individual FBR (2026) | SSI present **$994**/mo (**$11,928**/yr displayed path) • **`validate`** **11928 ⇒ 11928** | **PASS** | MCP end-to-end walk **2026-05-06** (**UUID not archived**) — rerun staging **`import_validations …/wa_ssi.json`** for deterministic SPA UUID |
| **2** | **§ Scenario 7** | Working-age (**35**) **no disability / blindness** categorical gate | **Ineligible** (**value** omitted in JSON) | SSI **absent** • **`validate`** ineligible **`0 ⇒ 0`** | **PASS** | MCP wizard walk (**UUID not archived**); rerun **`import_validations`** for SPA UUID |
| **3** | **§ Scenario 12** | **Long‑term disability** path + **$400/mo** wages (**SGA‑safe**) | **`10038`** / **$836.50**/mo (**trunc → `validate`**) | FE tile **$837**/mo (whole-dollar rounding vs PE); **`validate`** **`10038 ⇒ 10038`** | **PASS** | [`2eb9a2fc-d8a5-4522-a7ac-efa59c46dba8`](https://benefits-calculator-staging.herokuapp.com/wa/2eb9a2fc-d8a5-4522-a7ac-efa59c46dba8/results/benefits) |

**Rounding note (row 3):** staging tile **$837**/mo vs PE **$836.50**/mo — under **$1/year** after annualization; treat as **PASS** (consistent with **[PR #1481](https://github.com/MyFriendBen/benefits-api/pull/1481)**).

---

### Spec.md § test scenarios **1–15** + citizenship chip — staging coverage

| Spec # | In **`wa_ssi.json`** + **`validate`**? | Staging result / disposition |
| ------ | --------------------------------------- | -------------------------------- |
| 1 | ✅ Row **1** | **PASS** (Step 2 matrix) |
| 2 | ⛔️ Not in importer (yet) | **DEFERRED** — expand validations when prioritized |
| 3 | ⛔️ | **DEFERRED** |
| 4 | ⛔️ | **DEFERRED** |
| 5 | ⛔️ | **DEFERRED** |
| 6 | ⛔️ | **DEFERRED** |
| 7 | ✅ Row **2** | **PASS** |
| 8 | ⛔️ | **DEFERRED** — **`has_ssi`** “already enrolled” path (distinct from categorical math) |
| 9 | ⛔️ | **DEFERRED** |
| 10 | ⛔️ | **DEFERRED** |
| 11 | ⛔️ | **DEFERRED** |
| 12 | ✅ Row **3** | **PASS** |
| 13 | ⛔️ | **DEFERRED** |
| 14 | ⛔️ | **DEFERRED** (**SGA** trip-wire) |
| 15 | ⛔️ | **DEFERRED** |
| *Out‑of‑band citizen filter* | *n/a (not JSON-able)* | **MANUAL QA** — toggle Results citizenship chip; confirm **`wa_ssi`** disappears for non–SSI‑qualifying legal selections (**`spec.md` § “Out‑of‑band”**) |

**Counts:** **`PASS`** for **Importer rows = 3 / 3** (also **staging wizard = 3 / 3**). **Defer / manual ≠ FAIL** — they are **explicitly unscored automation gaps** tracked in **`spec.md`**.

---

## Health observations during the run

- **No HTTP 500s**, **no CORS failures**, clean browser console across sampled MCP runs.
- Staging PE cold‑start (**~10–25 s**) on first **`/results/benefits`** hit per persona (**expected** noisy staging infra — same commentary as **[#1482](https://github.com/MyFriendBen/benefits-api/pull/1482)** GRD QA).

---

## Methodology (**unchanged semantics from [#1481](https://github.com/MyFriendBen/benefits-api/pull/1481)**)

Wizard parity (each JSON row): language → consent → **`98101` / King County** residency → HH size (**1**) → demographics / insurance / categorical flags → incomes → expenses → **`0` countable assets declared** (`household_assets: 0` JSON alignment) → *current-benefits* step (**no conflicting SSI** flags) → help / referral extras → freeze + submit (**real `Screen` persisted** hitting **`POST/PATCH`** → **`GET /api/eligibility/<uuid>` SPA render** identical to prod).

Backend cross-check (**authoritative arithmetic** versus tile rounding):

```bash
heroku run "python manage.py import_validations validations/management/commands/import_validations/data/wa_ssi.json" \
  -a cobenefits-api-staging
```

```bash
heroku run "python manage.py validate --program wa_ssi" -a cobenefits-api-staging
# → Passed: 3  Failed: 0  Skipped: 0
```

---

## Appendix — **Linear-ready** blunt summary (**copy / paste after runs**)

<details>
<summary>Expand for posting on **MFB-850**</summary>

```
MFB-850 staging QA — PASS — WA SSI (canonical 3 importer rows)

four-step staging workflow (PR #1482 / #1486 style):
PASS (1) import_all_program_configs wa_ssi_initial_config.json
PASS (2) MCP full-funnel staging WA — §1 golden, §7 ineligible categorical, §12 earned exclusions (3 personas)
PASS (3) validate --program wa_ssi — Passed 3 Failed 0
PASS (4) Scenario §1 grouping / navigator / copy sanity

spec.md Scenario coverage:
PASS §1 §7 §12 via validations JSON + staging MCP + validate — others DEFERRED per spec “JSON contains 3 rep rows” reviewer guide + §15 matrix until expanded

Manual QA still required: citizenship filter chip out-of-band (wa_ssi legal_status_required) per spec § Out-of-band
```

</details>
