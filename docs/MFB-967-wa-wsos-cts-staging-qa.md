# MFB-967 — WA WSOS CTS staging QA results

**Ticket:** [MFB-967: WA Washington State Opportunity Scholarship (CTS)](https://linear.app/myfriendben/issue/MFB-967/wa-washington-state-opportunity-scholarship-cts)  
**Program:** `wa_wsos_cts`  
**Staging API:** `cobenefits-api-staging`  
**Staging screener:** https://benefits-calculator-staging.herokuapp.com  
**Spec:** `programs/programs/wa/wsos_cts/spec.md`  
**QA run date:** 2026-05-08 (America/Los_Angeles)

---

## 1. Program config on staging

| Check | Result |
|--------|--------|
| `import_all_program_configs` | **PASS** — `wa_wsos_cts_initial_config.json` imported successfully |
| Staging program ID | **1748** |
| `active` (from import log) | **True** |
| White label | `wa` / category `wa_education` |

**Command (executed):**

```bash
heroku run "python manage.py import_all_program_configs" -a cobenefits-api-staging
```

**Import excerpt (CTS):**

- Created: `wa_wsos_cts` (ID **1748**)
- `active: True`, `has_calculator: True`, `value_format: None`
- Warning: `wa_wsos_cts_warning` created  
- Documents: existing FAFSA/WASFA + new `wa_wsos_cts_essay_question`

**Admin verification:** Confirm in Django admin on staging that Program **1748** shows **Active** (import log already reports `active: True`).

**Note:** The same Heroku run also imported `wa_wsos_bas` (program **1747**) and skipped `wa_seattle_fresh_bucks` (already recorded).

---

## 2. Structured validations (staging DB)

**Command:**

```bash
heroku run "python manage.py import_validations validations/management/commands/import_validations/data/wa_wsos_cts.json" -a cobenefits-api-staging
heroku run "python manage.py validate --program wa_wsos_cts" -a cobenefits-api-staging
```

**Result:** **Passed: 3 — Failed: 0 — Skipped: 0**

| # | Notes (from validation JSON) | Eligibility | Value |
|---|------------------------------|-------------|-------|
| 1 | Scenario 1 — eligible student, $2,500/mo | Eligible | $0 |
| 2 | Scenario 2 — not a student | Not eligible | $0 |
| 3 | Scenario 4 (spec) — 3p boundary ($12,208/mo head wages) | Eligible | $0 |

**Admin validation links (staging):**

- https://benefits-calculator-staging.herokuapp.com/wa/37fdc9c8-5a6e-4305-96a7-922881396329/results/benefits/1748/?admin=true  
- https://benefits-calculator-staging.herokuapp.com/wa/901f8506-fe47-4ca3-852c-50b3a169218e/results/benefits/1748/?admin=true  
- https://benefits-calculator-staging.herokuapp.com/wa/1ee05031-a19f-48da-af6b-dfeb0fa53a80/results/benefits/1748/?admin=true  

---

## 3. Spec.md scenarios vs staging coverage

`spec.md` defines **six** scenarios. The repo validation file `validations/management/commands/import_validations/data/wa_wsos_cts.json` currently contains **three** cases (aligned with scenarios **1**, **2**, and the **3-person boundary** case labeled like spec scenario 4).

| Spec scenario | Description | Staging validation | Staging status |
|---------------|-------------|-------------------|----------------|
| 1 | Eligible — student below 125% MFI | Yes | **PASS** (validate + FE URL) |
| 2 | Ineligible — not a student | Yes | **PASS** |
| 3 | Ineligible — income above 125% MFI ($8k/mo) | No JSON case | **Not run on staging** — add case + `import_validations` |
| 4 | Edge — 3p at boundary | Yes (monthly $12,208 in JSON) | **PASS** |
| 5 | Eligible — RJI-like (Whatcom, 2p) | No JSON case | **Not run on staging** — add case + import |
| 6 | Ineligible — 4p above cap | No JSON case | **Not run on staging** — add case + import |

**Recommendation:** Extend `wa_wsos_cts.json` with scenarios 3, 5, and 6; re-import validations on staging and prod; re-run `validate --program wa_wsos_cts`.

**Automated Playwright:** Not executed from this workspace. Use team skill with Linear MCP + Playwright MCP, for example:

`/playwright-qa-execution MFB-967 staging`

Target environment string should match your skill (often `staging`). That run typically writes results under the repo’s ignored `qa/` folder (see team-claude-config).

---

## 4. Manual UI check (staging)

**Profile:** Validation **scenario 1** (eligible student, King, $2,500/mo).  
**URL opened:** [Program detail — scenario 1 screen](https://benefits-calculator-staging.herokuapp.com/wa/37fdc9c8-5a6e-4305-96a7-922881396329/results/benefits/1748/?admin=true)

| Check | Result |
|--------|--------|
| Program appears | **Yes** — Education category |
| Program name | **PASS** — full CTS title, no raw `_label` |
| Warning banner | **PASS** — deadline / cycle text from config warning (English) |
| Estimated value | **PASS** — shows **$0** (eligibility-only program); admin line `$0 => $0` |
| Apply CTA | **PASS** — “How to Apply” goes to WSOS CTS page |
| Documents | **PASS** — FAFSA, WASFA, CTS short-answer guide links present |
| Spanish (`ESPAÑOL`) | **Partial** — category/footer translated; program **name**, **warning**, **long description**, and **“How to Apply”** remained **English**; one doc line mixed (“Short essay answers” in English). Flag for translation / content if full ES parity is required |

---

## 5. Summary for Linear comment (copy/paste)

- **Import:** `import_all_program_configs` on `cobenefits-api-staging` — **wa_wsos_cts** created as program **ID 1748**, **active: True** (per command output).  
- **Validations:** `import_validations` + `validate --program wa_wsos_cts` — **3 passed, 0 failed**.  
- **Spec coverage gap:** Only **3** of **6** `spec.md` scenarios are in `wa_wsos_cts.json`; scenarios **3, 5, 6** should be added and re-imported for full staging parity.  
- **Playwright:** Run `/playwright-qa-execution MFB-967 staging` in Claude Code for full scenario automation artifact.  
- **Manual:** Scenario 1 program detail reviewed — content/links OK; **Spanish** shows partial translation (program copy still largely English).  

---

## 6. Related PRs

- Implementation merged to `main` (staging deploy): WSOS CTS calculator + config + validations artifact.  
- This document: **draft PR** `docs/mfb-967-staging-qa-results` — adds `docs/MFB-967-wa-wsos-cts-staging-qa.md` (QA record only; no application logic changes).
