# MFB-966 — WA WSOS BaS staging manual QA

**Ticket:** [MFB-966: WA Washington State Opportunity Scholarship — BaS](https://linear.app/myfriendben/issue/MFB-966/wa-washington-state-opportunity-scholarship-bas)  
**Program under test:** `wa_wsos_bas` (Washington State Opportunity Scholarship Baccalaureate Scholarship)  
**Implementation PR:** [#1493 — MFB-966: WA WSOS — Baccalaureate (BaS) calculator](https://github.com/MyFriendBen/benefits-api/pull/1493) (merged to `main`)  
**Date:** 2026-05-08  
**Environment:** **Staging** — frontend `https://benefits-calculator-staging.herokuapp.com/wa`  
**Spec:** `programs/programs/wa/wsos_bas/spec.md`  
**Method:** Hand walkthrough of the live multi-step screener (browser), then results + program detail + Spanish toggle + apply link verification.

---

## Executive summary

| Item | Status |
|------|--------|
| **BaS appears for Scenario 1 (eligible profile)** | **FAIL** — no “Baccalaureate” / BaS program on the results page; in-page search for `Baccalaureate` had no matches. |
| **GRD appears instead** | **OBSERVED** — *Washington State Opportunity Scholarship Graduate Scholarship (GRD)* appeared under Education with **~$2,083/mo** summary and **$25,000** estimated savings on the card. |
| **Root cause hypothesis** | Staging API DB likely missing imported/active `wa_wsos_bas` program row and/or frontend not yet receiving BaS in the program payload after deploy. **Action:** confirm Heroku deploy from `main`, then `import_program_config` (or `import_all_program_configs`) on **`cobenefits-api-staging`**, re-test. |
| **Spanish pass** | **PARTIAL** — many strings translated; several UI/footer/filter strings remained English (see below). |
| **Apply link (for program shown)** | **PASS for GRD** — primary apply control opened Caspio **GRD** flow in a new tab (not BaS `#apply` URL). |

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
| **Program detail (GRD, id `1581`)** | https://benefits-calculator-staging.herokuapp.com/wa/fe1b54e5-f320-47de-960e-891a994793a9/results/benefits/1581 |

Session id in path: `fe1b54e5-f320-47de-960e-891a994793a9`

---

## Results page checklist

| Check | Result | Notes |
|-------|--------|------|
| **BaS in results** | **FAIL** | Expected eligible **$22,500** lump sum per spec/calculator; program card **not** present. |
| **Program name** (no raw `_label` keys) | **PASS** (GRD only) | Title rendered as human-readable English/Spanish for **GRD**. |
| **Description / copy** | **PASS** (GRD only) | GRD-appropriate framing; BaS long description **not** exercisable. |
| **Estimated value** | **GRD only** | Summary tile **~$2,083/mo**; card **$25,000** — consistent with GRD lump-sum amortization in UI (**not** BaS $22,500). |
| **Apply-now** | **PASS** (GRD) | **“Solicite en línea”** (Spanish) opened new tab: `https://waopportunityscholarship.caspio.com/dp/d6868000fc394872a8ef46beace8` — **GRD Eligibility Check** (Caspio). Config for BaS expects `https://waopportunityscholarship.org/applicants/baccalaureate/#apply` — **not verified** (BaS absent). |
| **Documents / navigators** | **PASS** (GRD detail) | On detail page in Spanish: FAFSA, WASFA, recommendation guide, essay guide, etc. **BaS** lists no recommendation form in config — **not verified** on staging. |

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

## Recommended follow-up (staging)

1. Confirm **benefits-api** staging dynos are on latest **`main`** including merge of [#1493](https://github.com/MyFriendBen/benefits-api/pull/1493).  
2. On **`cobenefits-api-staging`**, run (dry-run first if desired):

   `python manage.py import_program_config programs/management/commands/import_program_config_data/data/wa_wsos_bas_initial_config.json`

   or batch:

   `python manage.py import_all_program_configs`

3. If validation cases changed, re-import:

   `python manage.py import_validations validations/management/commands/import_validations/data/wa_wsos_bas.json`

4. Re-run **this same Scenario 1** path; **expect** a **BaS** card (and possibly **GRD** alongside, depending on eligibility rules and config).

---

## Related artifacts

| Artifact | Path / link |
|----------|-------------|
| Calculator + tests | `programs/programs/wa/wsos_bas/` |
| Initial config | `programs/management/commands/import_program_config_data/data/wa_wsos_bas_initial_config.json` |
| Validations JSON | `validations/management/commands/import_validations/data/wa_wsos_bas.json` |
| Sister program QA example | `qa/MFB-778-wa-wsos-grd-results.md` |
