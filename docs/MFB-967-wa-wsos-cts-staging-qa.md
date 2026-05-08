# MFB-967 — WA WSOS CTS staging QA results

**Ticket:** [MFB-967: WA Washington State Opportunity Scholarship (CTS)](https://linear.app/myfriendben/issue/MFB-967/wa-washington-state-opportunity-scholarship-cts)  
**Program:** `wa_wsos_cts` (staging program id **1748**)  
**Staging API:** `cobenefits-api-staging`  
**Staging screener:** https://benefits-calculator-staging.herokuapp.com  
**Spec:** `programs/programs/wa/wsos_cts/spec.md`  
**Repo validation data:** `validations/management/commands/import_validations/data/wa_wsos_cts.json` (six scenarios, spec order)  
**QA run date:** 2026-05-08 (America/Los_Angeles)

---

## PR description (copy/paste)

### What's in this PR

- **`docs/MFB-967-wa-wsos-cts-staging-qa.md`** — this staging QA record (MFB-778–style summary below).
- **`validations/management/commands/import_validations/data/wa_wsos_cts.json`** — structured import cases for **all six** `spec.md` scenarios (use once per clean environment).
- **`validations/management/commands/import_validations/data/wa_wsos_cts_import_scenarios_3_5_6.json`** — **incremental** import for staging if scenarios **1, 2, and 4** were already imported earlier; keeps a single set of six validation rows without re-importing the first batch.

### Results — all 4 staging QA steps PASS

| Step | What | Outcome |
|------|------|---------|
| 1 | `import_all_program_configs` with `wa_wsos_cts_initial_config.json` on `cobenefits-api-staging` | **PASS** — program id **1748**, `active=True` |
| 2 | All **6** `spec.md` scenarios on staging FE (via admin result URLs below) | **PASS** — **6 / 6** |
| 3 | `validate --program wa_wsos_cts` on `cobenefits-api-staging` | **PASS** — **6 / 6** (Passed: 6, Failed: 0, Skipped: 0) |
| 4 | Manual visual check (Scenario 1, EN + ES) | **PASS** with **caveat** — copy, links, documents, **$0** value OK; **Spanish** still partial (much program copy English) |

### Step 2 — staging screen UUIDs for all 6 scenarios

| # | Scenario | Expected | Staging FE | Result | Screen UUID |
|---|----------|----------|------------|--------|-------------|
| 1 | WA student, 1 person, **$2,500/mo** (King) | Eligible (**$0** estimated value) | WSOS CTS under Education, **$0** | PASS | `37fdc9c8-5a6e-4305-96a7-922881396329` |
| 2 | 1 person, **not** a student | Ineligible (CTS absent) | CTS absent | PASS | `901f8506-fe47-4ca3-852c-50b3a169218e` |
| 3 | 1 person student, **$8,000/mo** (> 125% MFI size 1) | Ineligible | CTS absent | PASS | `253324b1-68a5-4fbb-aed2-c9cd636984d9` |
| 4 | 3 person student head, **$12,208/mo** (125% MFI size 3) | Eligible | WSOS CTS under Education, **$0** | PASS | `1ee05031-a19f-48da-af6b-dfeb0fa53a80` |
| 5 | **Whatcom**, 2 person (RJI-like), combined income under 125% MFI | Eligible | WSOS CTS under Education, **$0** | PASS | `d2a88186-dd5e-4565-b1a4-75acefc0731e` |
| 6 | 4 person student head, **$15,000/mo** (> 125% MFI size 4) | Ineligible | CTS absent | PASS | `c33355dd-9855-4fb8-adcb-0929cb86557d` |

**Admin URLs (program 1748):** `https://benefits-calculator-staging.herokuapp.com/wa/<SCREEN_UUID>/results/benefits/1748/?admin=true`

---

## Import commands (staging)

**Full six cases (new database / first-time import):**

```bash
heroku run "python manage.py import_validations validations/management/commands/import_validations/data/wa_wsos_cts.json" -a cobenefits-api-staging
```

**Incremental three cases** (only if scenarios 1, 2, and 4 were already imported from an older three-case file — otherwise skip this and use the full file once):

```bash
heroku run "curl -sfL 'https://raw.githubusercontent.com/cdadams1888/benefits-api/docs/mfb-967-staging-qa-results/validations/management/commands/import_validations/data/wa_wsos_cts_import_scenarios_3_5_6.json' -o /tmp/w.json && python manage.py import_validations /tmp/w.json" -a cobenefits-api-staging
```

After this branch is merged to `MyFriendBen/benefits-api`, point the URL at `main` (or a release tag) instead of the fork branch.

**Validate:**

```bash
heroku run "python manage.py validate --program wa_wsos_cts" -a cobenefits-api-staging
```

---

## Notes

- **Playwright** `/playwright-qa-execution MFB-967 staging` was not run from this workspace; team automation may still emit artifacts under the ignored `qa/` tree.
- **Spanish:** Scenario 1 manual review — category/footer translated; program name, warning, long description, and primary CTA copy were still largely English; flag if full ES parity is required.

---

## Related PRs

- WSOS CTS implementation merged to `main` (deployed to staging).
- QA / validation expansion: branch `docs/mfb-967-staging-qa-results`.
