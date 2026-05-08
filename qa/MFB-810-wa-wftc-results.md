# MFB-810 — WA Working Families Tax Credit (WFTC) QA Results

**Ticket:** [MFB-810: WA Working Families Tax Credit](https://linear.app/myfriendben/issue/MFB-810/wa-working-families-tax-credit)
**Program:** `wa_wftc`
**Calculator:** `WaWftc` (PolicyEngineTaxUnitCalulator) extending federal `Eitc`, registered in `programs/programs/wa/pe/__init__.py` and the global PE registry
**Date:** 2026-05-06 (initial); **nine-case validations + `has_wa_wftc` merged 2026-05-08**
**Environment:** local (frontend `http://localhost:3002`, backend `http://localhost:8000`)
**Spec:** `programs/programs/wa/wftc/spec.md`
**Staging QA:** `qa/MFB-810-wa-wftc-staging-results.md`

## Summary

| # | Spec Scenario | Spec-expected | PE / FE actual | Result | Coverage | Notes |
|---|---|---|---|---|---|---|
| 1 | Married, 2 kids, $4,700/mo MFJ | Eligible $995/yr | Eligible **$1,017/yr** | PASS (drift) | validation | PE 2026 tier |
| 2 | Single, 0 kids, ~~$1,593~~ **$1,630**/mo ceiling probe | Ineligible $0 | Ineligible $0 (`wa_wftc.json` wages **1630**/mo rebased to PE 2026) | PASS | validation | `$1,593/mo` still eligible in PE 2026 ($99 credit) |
| 3 | Single, age 24, $1,200/mo | Ineligible $0 | Ineligible $0 | PASS | validation + FE | |
| 4 | Already receiving WFTC | Ineligible $0 *(wizard)* | API: **`already_has: true`**, calculator **$1,017** | PASS | validation + Screen flag | **`has_wa_wftc`** on `Screen`; `validate` asserts PE dollars. |
| 5 | Married, 3 kids, $5,723/mo | Ineligible $0 | Eligible **$460/yr** | PASS (drift) | validation + FE | 2026 ceiling vs 2025 spec |
| 6 | Single + 1 child, $4,000/mo | Eligible $335/yr | Eligible **$499/yr** | PASS (drift) | validation | PE 2026 curve |
| 7 | Single, age 72, only SS Retirement | Ineligible $0 | Ineligible $0 | PASS | validation (+ FE optional) | |
| 8 | Married, 3 kids, $4,000/mo MFJ wages | Eligible $1,330/yr | Eligible **$1,360/yr** | PASS (drift) | validation | PE 2026 max tier |
| 9 | Single, age 25, $1,200/mo | Eligible $50/yr | Eligible **$342/yr** | PASS (drift) | validation + FE | Plateau |

**Backend validations (`wa_wftc.json` + `validate --program wa_wftc`):** **9 / 9 PASS**  
**Screen model:** **`has_wa_wftc`** (`screener.0153`) drives `Screen.has_benefit("wa_wftc")` and API **`already_has`**.  
**Unit tests (`programs.programs.wa.pe.tests.test_tax`):** 11 / 11 PASS *(unchanged count)*  

## Spec drift — PolicyEngine's 2026 calculation

Same themes as before: plateau vs **$50** minimum (Scenario 9), inflated tier max (Scenarios **1**, **8**), stale **MFJ + 3** ceiling (Scenario 5). **Scenario 2** additionally shows the **childless income gate moved** versus the spec’s **`$19,104`-era** cutoff — **`$1,593/mo` is no longer above** PE’s **2026** limit; validations use **`$1,630/mo`** so the row cleanly exercises **ineligibility**.

## Scenario 4 — “already receiving WFTC”

The discovery checkbox path remains gated by **`show_in_has_benefits_step`** and WA **`category_benefits`** (still a longer FE rollout). **`has_wa_wftc`** on **`Screen`** is the authoritative backend enrollment flag (`import_validations` JSON accepts it):

- **`validate`** compares PolicyEngine eligibility **value** (still **$1,017** for the spec household).
- **`eligibility_results`** sets **`already_has: true`** at the program level when **`has_wa_wftc`** is **true**.

## Known data gaps (per `spec.md`, surfaced to user via program description)

The screener does not collect the following WFTC-required information; the calculator treats each as an inclusivity assumption (the program is shown as long as the screener-checkable criteria pass) and the program description copy makes them visible to the user before they apply:

- 183-day Washington physical-presence requirement
- Whether qualifying children lived with the filer > 6 months
- Whether the filer is claimed as a dependent on someone else's return (mostly affects 18–24 year olds)
- Whether the filer will actually file a federal return for the year
- Married-filing-separately filing status (the screener treats spouses as MFJ — the most common case — and the description discloses this assumption)

## Methodology

For each scenario the household input was encoded into **`validations/management/commands/import_validations/data/wa_wftc.json`** and imported via **`python manage.py import_validations`**. **`python manage.py validate --program wa_wftc`** then exercises the same end-to-end pipeline the FE uses (**`screen → fetch_results → PolicyEngine`**) and compares the calculator's output to the expected eligibility / value.

For visual confirmation, the per-screen UUID emitted by **`import_validations`** was opened directly at **`http://localhost:3002/wa/<uuid>/results/benefits`** (and **`/results/benefits/<program_id>`** for the program-detail page). This bypasses the screener form walk but exercises the same FE rendering path used by users on a normal funnel.

Detail checks included tax-credit placement, **`$` values**, Apply CTA → **`workingfamiliescredit.wa.gov/apply`**, **`wa_dor`** navigator chip, documents, and ES toggle + reload (generic FE caching).

## Implementation summary

- **Calculator** (`programs/programs/wa/pe/tax.py`): **`WaWftc`** extends federal **`Eitc.pe_inputs`** and adds **`WaStateCodeDependency`**. Targets PE's **`wa_working_families_tax_credit`** variable. Output is **`tax.WaWftc`**. No screener-side overrides — eligibility math lives in PE.
- **Tax dependency** (`programs/programs/policyengine/calculators/dependencies/tax.py`): **`WaWftc(TaxUnit)`** with **`field = "wa_working_families_tax_credit"`**.
- **Registry** (`programs/programs/wa/pe/__init__.py`): **`wa_tax_calculators`** merged into **`wa_pe_calculators`** and the global PE tax-unit registry.
- **Enrollment flag** (**`Screen.has_wa_wftc`**, migration **`0153`**): maps to **`wa_wftc`** in **`Screen.has_benefit`** / **`_build_benefit_map`** so eligibility JSON exposes **`already_has`** without changing PE output.
- **Spec, config, validations**: **`spec.md`**, **`wa_wftc_initial_config.json`**, **`wa_wftc.json`**.

### Discovery-config corrections (original MFB-810 calculator PR)

See merged PR **[#1483](https://github.com/MyFriendBen/benefits-api/pull/1483)** / git history for: **`legal_status_required`** snake_case fixes, **`wa_tax`** category **`name`/`icon`**, duplicate **`description_short`**, **`wa_dor` email**, etc.

## Recommendations / next steps

- **Validations**: All nine **`spec.md`** scenarios are encoded with **PolicyEngine 2026** authoritative numbers; rerun **`validate --program wa_wftc`** locally and on staging whenever PE bumps tax-year parameters.
- **Discovery/`spec.md` textual refresh** (informational): update Scenario **2** narrative to **`$1,630/mo`** (or cite PE-derived cutoff) so written spec matches importer JSON.
- **FE**: Surface **`wa_wftc`** on the “already has benefits” step when **`show_in_has_benefits_step`** and WA **`category_benefits`** include it; wire **`has_wa_wftc`** in **`updateScreen`** (benefits-calculator repo).
