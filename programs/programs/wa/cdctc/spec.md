# Washington Child and Dependent Care Tax Credit — Discovery spec

## Program details

- **Program**: Washington Child and Dependent Care Tax Credit (CDCTC)
- **White label**: `wa`
- **`name_abbreviated`**: `wa_cdctc`
- **Linear**: [MFB-923](https://linear.app/myfriendben/issue/MFB-923/wa-child-and-dependent-care-tax-credit)
- **Discovery date**: 2026-05-14
- **Tax year (config seed)**: 2025 — **QA**: align every threshold and citation to Washington’s enacted parameters for returns / applications referencing that year.

## Program note

Washington’s CDCTC is a **state** refundable credit. It borrows conceptual structure from the **federal** credit (26 U.S.C. § 21 and related IRS guidance) — work-related expenses, qualifying individuals, earned-income requirements, identification of care providers — but **state statutes, percentages, ceilings, residency, and claiming mechanics are authoritative**.

Administration parallels other Washington refundable credits (compare the [Working Families Tax Credit](https://dor.wa.gov/taxes-rates/tax-incentives/credits/working-families-tax-credit)): Washington does **not** use an individual income-tax return channel for households the way many states do. **QA**: replace any placeholder application URL once the Washington Department of Revenue publishes the official CDCTC application path.

**Discovery scope**: Configuration and research artifacts only (`wa_cdctc_initial_config.json`, this `spec.md`, `wa_cdctc.json` validations draft). Calculator, PolicyEngine variable names, benefit-value surfaces, and `has_calculator`/current-benefits wiring are **out of scope** until engineering selects the computation path.

## Eligibility criteria (draft — reconcile with statutes & DOR)

Use this list as an implementation checklist after statutory review. Strike or amend items once RCW/WAC cites are nailed down.

1. **Washington eligibility / residency (state-specific)**  
   Confirm physical presence or domicile requirements, clawbacks for part-year residents, and how they differ from federal rules.  

2. **Qualifying dependents**  
   Typical federal-style tests: qualifying child rules, dependents physically or mentally incapable of self-care while the taxpayer works — **exact Washington alignment is TBD** in citation and age limits.

3. **Work-related expense test**  
   Expenses paid for care of a qualifying individual so that the taxpayer (and spouse if applicable) could work or look for work — match Washington definitions of “employment-related” care.

4. **Earned income floor**  
   Federal CDCTC looks to earned income; Washington may impose similar or amended floors. Evaluate using filer (+ spouse MFJ where applicable), not unrelated household adults.

5. **Care provider qualification**  
   Provider identification rules (including non-relative vs relative limitations and TIN/EIN reporting) — align with statute and IRS provider rules only where Washington explicitly tracks federal law.

6. **Expense ceiling**  
   Federal law caps **eligible** expenses per qualifying individual ($3,000 / $6,000 in common federal formulations — **inflate and verify WA**).

7. **Credit rate and refundable portion**  
   Washington may specify a fraction of allowable expenses vs a flat schedule; document phase-in/phase-out and interaction with AGI concepts Washington uses.

8. **Income limitations**  
   Identify Washington’s MAGI/FAGI analogue and phase-outs; thresholds may differ materially from § 21.

9. **Filing / unit assumptions**  
   MFJ vs MFS, separated-spouse treatment, qualifying person claimed by someone else — screener today infers spouses as joint filing in many WA tax-adjacent programs; capture known gaps explicitly.

10. **Interaction with federal credit**  
    Clarify whether Washington credit is layered on allowable federal eligibility, capped by federal credit claimed, or fully independent once expenses qualify.

## Data gaps (typical AI mistakes — verify explicitly)

| Risk | Mitigation |
|------|-------------|
| Copying § 21 numbers (expense caps, rates, MAGI thresholds) verbatim | Demand Washington statutory / DOR numbers for **each tax year**. |
| Using Texas or federal-only copy in `learn_more` / descriptions | Separate **education** vs **benefit estimation** messaging; IRS links are illustrative, not substitutes for WA law. |
| Treating childcare subsidy programs (Working Connections Child Care, etc.) as interchangeable with CDCTC | Keep program boundaries crisp in copy and calculators. |
| Assuming calendar-year household snapshot equals tax-year residency, custody, or “lived with you” tests | Prefer December 31 of tax year for age/status where applicable — same caution as WA EITC spec. |

## Benefit value — Discovery stance

Until PolicyEngine exposes a definitive `wa_*` variable:

- Omit dollar estimates from the product **or** mark `low_confidence` / gated copy once a calculator exists — **currently** `has_calculator: false` in import JSON.
- When implemented, methodology should cite **Washington** tables (not Pub 503 alone).

## Priority criteria

None identified for capped enrollment; confirm no waitlist analogous to subsidy programs.

## Implementation coverage — Discovery stance

Pre-calculator release:

- ⚠️ All criteria are narrative pending statutory capture and QA sign-off.

## Research sources — fill during QA hardening

- **QA**: Replace with Washington session law / RCW cites for enacted CDCTC; add DOR rulings & application instructions when published.
- **Cross-reference**: [IRS Publication 503 (federal childcare credit framing)](https://www.irs.gov/publications/p503) — for conceptual alignment only where Washington tracks federal constructs.
- [26 U.S.C. § 21 — federal Child and Dependent Care Credit](https://www.law.cornell.edu/uscode/text/26/21) — contrast, not substitution.

## Research output files

- [`programs/management/commands/import_program_config_data/data/wa_cdctc_initial_config.json`](../../../../programs/management/commands/import_program_config_data/data/wa_cdctc_initial_config.json)
- [`programs/programs/wa/cdctc/spec.md`](spec.md)
- [`validations/management/commands/import_validations/data/wa_cdctc.json`](../../../../validations/management/commands/import_validations/data/wa_cdctc.json)

## Acceptance criteria (Discovery)

- [ ] Statutory citations and income/expense ceilings match Washington Department of Revenue or enacted law — not federal defaults alone  
- [ ] Application URL and timelines match live DOR guidance  
- [ ] Description draws clear boundary vs federal Pub 503 and vs non-tax childcare benefits  
- [ ] Calculator + PE mapping agreed; `has_calculator` flipped with validation cases updated  
- [ ] `legal_status_required` aligns with Legislature’s exclusions (if narrower than WA EITC)

## Workflow note (QA / Discovery ownership)

Discovery is consolidated under **one QA owner** end-to-end: Program Research seeds artifacts; QA reviews, edits, and merges corrections without a separate QA hand-off stage.
