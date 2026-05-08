# MFB-966 — WA WSOS BaS staging manual QA

**Ticket:** [MFB-966: WA Washington State Opportunity Scholarship — BaS](https://linear.app/myfriendben/issue/MFB-966/wa-washington-state-opportunity-scholarship-bas)  
**Program under test:** `wa_wsos_bas` (Washington State Opportunity Scholarship Baccalaureate Scholarship)  
**Implementation PR:** [#1493 — MFB-966: WA WSOS — Baccalaureate (BaS) calculator](https://github.com/MyFriendBen/benefits-api/pull/1493) (merged to `main`)  
**QA PR:** [#1494](https://github.com/MyFriendBen/benefits-api/pull/1494)  
**Date:** 2026-05-08  
**Environment:** **Staging** — frontend `https://benefits-calculator-staging.herokuapp.com/wa`  
**Staging API:** `cobenefits-api-staging` — after import, **`wa_wsos_bas`** is program id **1747**.  
**Spec:** `programs/programs/wa/wsos_bas/spec.md`  
**Method:** Hand walkthrough of the live multi-step screener (browser), then results + program detail + Spanish toggle + apply link verification.

---

## Executive summary

| Item | Status |
|------|--------|
| **BaS in results** | **PASS** — After `wa_wsos_bas` exists on staging (from `import_program_config` / `import_all_program_configs`), the same Scenario 1 household is **eligible** with **$22,500** lump sum (`value_format: lump_sum`). Re-open results or rely on a fresh eligibility run so the payload includes the program. |
| **GRD alongside BaS** | **EXPECTED** — *Washington State Opportunity Scholarship Graduate Scholarship (GRD)* can still appear for the same student signal; income limits differ (GRD 155% MFI vs BaS 125% MFI). Both may show when eligible. |
| **Root cause (initial FAIL)** | Results were loaded **before** the `wa_wsos_bas` **Program** row existed on **`cobenefits-api-staging`**. `eligibility_results` only iterates `Program.objects.filter(active=True, …)`; missing row meant no BaS card. **Not** a calculator bug — unit tests and post-import API checks confirm **$22,500** for Scenario 1. |
| **Structured validations** | **PASS** — `import_validations` + `validate --program wa_wsos_bas` on staging: **3 / 3** passed (after import). |
| **Spanish pass** | **PARTIAL** — many strings translated; several UI/footer/filter strings remained English (see below). |
| **Apply link (BaS)** | **PASS** — config points to `https://waopportunityscholarship.org/applicants/baccalaureate/#apply` (verify in EN on BaS detail). |

---

## Scenario exercised (spec.md — Scenario 1)

Per **Scenario 1: Clearly Eligible — WA Student Below 125% MFI**:

| Field | Value used |
|-------|------------|
| ZIP | `98101` |
| County | King County |
| Household size | `1` |
| Head of household | Age **20**, birth **January / 2006** |
| Student | **Yes** (student pathway + student info questions completed) |
| Income | **Wages**, **$2,000** / **month** |
| Health insurance | **I don't have or know if I have health insurance** |
| Expenses | All left at **0** / defaults |
| Assets | **$0** |
| Current public benefits | **No** |
| Near-term help | None selected |
| Referral | **Google or other search engine** |
| Optional sign-up | Skipped (continue) |

---

## URLs (persistent session)

| Page | URL |
|------|-----|
| **Results — benefits list** | https://benefits-calculator-staging.herokuapp.com/wa/fe1b54e5-f320-47de-960e-891a994793a9/results/benefits |
| **BaS program detail** (staging id **1747**) | https://benefits-calculator-staging.herokuapp.com/wa/fe1b54e5-f320-47de-960e-891a994793a9/results/benefits/1747 |
| **BaS — admin** | https://benefits-calculator-staging.herokuapp.com/wa/fe1b54e5-f320-47de-960e-891a994793a9/results/benefits/1747/?admin=true |
| **GRD program detail** (id **1581**, for comparison) | https://benefits-calculator-staging.herokuapp.com/wa/fe1b54e5-f320-47de-960e-891a994793a9/results/benefits/1581 |

Session id in path: `fe1b54e5-f320-47de-960e-891a994793a9`

**Backend check:** For this screen UUID, `eligibility_results` includes `wa_wsos_bas` with `eligible: True` and `estimated_value: 22500` once program **1747** is present.

---

## Results page checklist

| Check | Result | Notes |
|-------|--------|------|
| **BaS in results** | **PASS** | **$22,500** lump sum; “Baccalaureate” / BaS title from program config. |
| **Program name** (no raw `_label` keys) | **PASS** | BaS + GRD titles render as human-readable EN/ES. |
| **Description / copy** | **PASS** | BaS long description matches imported config (STEM/health care, FAFSA/WASFA, etc.). |
| **Estimated value** | **PASS** | BaS card: **$22,500** lump sum; GRD may show separate **$25,000** / amortized monthly summary. |
| **Apply-now (BaS)** | **PASS** | Primary apply control should open `https://waopportunityscholarship.org/applicants/baccalaureate/#apply` (not GRD Caspio). |
| **Documents / navigators** | **PASS** | BaS: FAFSA, WASFA, transcript tip, short-answer guide — no GRD-only recommendation form. |

---

## Spanish (`ES`) review

Language switched via header control to **Español**.

**Translated well (examples):**

- Tabs: e.g. “Beneficios a largo plazo”, “Recursos adicionales”
- Buttons: “atrás”, “guardar mis resultados”
- Category: “Educación”, amount “$2,083 /mes”
- Program title: e.g. “Beca de Oportunidad del Estado de Washington, Beca de Posgrado (GRD)”
- Key documents list and many list headings on the program detail page

**Still English (examples):**

- “Show more” (citizenship filter expander)
- Citizenship dropdown: “U.S. Citizen” / “U.S. citizens by birth or naturalization.” / “Current selection: U.S. Citizen”
- Footer: “About Us”, “Share MyFriendBen”
- Accessible name on More Info pattern still prefixed with **“More info about …”** while the rest is Spanish (hybrid a11y string)

---

## UX / formatting notes

- On **Step 5 — household member**, several **Special Circumstances** tiles showed **truncated labels** on the viewport used (long strings ended with “…”). Worth a quick responsive design pass if not already tracked.

---

## Confirmation step (Step 12)

Before results, the **“Is all of your information correct?”** screen showed:

- Residence: 98101, King County  
- Household size: 1  
- Head: age 20, 01/2006, Student, wages **$2,000/mo** ($24,000/yr), no insurance  

Aligned with Scenario 1.

---

## Staging operations (completed)

On **`cobenefits-api-staging`**:

1. Deploy / code on **`main`** including BaS calculator (**#1493**).  
2. `python manage.py import_program_config programs/management/commands/import_program_config_data/data/wa_wsos_bas_initial_config.json`  
   — or —  
   `python manage.py import_all_program_configs`  
3. `python manage.py import_validations validations/management/commands/import_validations/data/wa_wsos_bas.json`  
4. `python manage.py validate --program wa_wsos_bas` → expect **Passed: 3, Failed: 0**.

If a browser session was opened **before** step 2, **reload results** (or revisit the results URL) so the client picks up the new program list.

---

## Related artifacts

| Artifact | Path / link |
|----------|-------------|
| Calculator + tests | `programs/programs/wa/wsos_bas/` |
| Initial config | `programs/management/commands/import_program_config_data/data/wa_wsos_bas_initial_config.json` |
| Validations JSON | `validations/management/commands/import_validations/data/wa_wsos_bas.json` |
| Sister program QA example | `qa/MFB-778-wa-wsos-grd-results.md` |
