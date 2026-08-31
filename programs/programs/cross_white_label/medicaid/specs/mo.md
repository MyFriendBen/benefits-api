# Implement Medicaid (MO) Program

## Program Details

- **Program**: Medicaid
- **Program key**: `mo_medicaid`
- **Policy year**: 2026
- **Calculator type**: PE (eligibility varies)
- **State**: MO
- **White Label**: mo
- **Research Date**: 2026-07-20

**Screenable pathways**: infants and children, pregnant women, parent/caretaker relatives (MHF), Adult Expansion, MHABD (aged/blind/disabled), and MO HealthNet for Disabled Children (MHDC).

**Documented but not directly screenable** — surfaced in the program description, not gated on: postpartum continuation (criterion 3), Transitional MO HealthNet (NOT RUNNABLE, criterion 9), automatic newborn continuation (criterion 10), Former Foster Care Youth (NOT RUNNABLE, criterion 11), §1619(b) continuation (NOT RUNNABLE, criterion 15), and the four-month spousal-support extension (NOT RUNNABLE, criterion 16).

**Legal status / immigration**: handled through `legal_status_required`, the platform-wide household-visibility gate — not per-member logic inside `MoHealthNet`. See "Legal Status & Immigration" below.

**Build pattern**: `MoHealthNet(Medicaid)`, following the existing Medicaid PE-calculator pattern (`KsKanCare(Medicaid)` precedent, MFB-1054).

**Explicitly out of scope**: Premium CHIP 73/74/75 (MFB-1262 — not CHIP 4M, which this calculator continues to cover under criterion 2b), Ticket to Work Health Assurance (MFB-1287/MFB-1223), institutional/vendor/HCBS/long-term-care Medicaid, BCCT, Show-Me Healthy Babies, UWHS, and Emergency MO HealthNet Care for Ineligible Aliens (EMCIA).

**PE alignment**: PE remains authoritative for modelable Medicaid eligibility/category decisions; MFB does not add state-specific overrides solely to correct PE differences.

## Eligibility Criteria

1. **Missouri residency required**
   - Screener fields: `zipcode`, `county`
   - Source: MO DSS FSD Manual Section 1805.005.00 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-005-00/ — "42 CFR subsection 435.403 requires individuals to reside in the state where they are applying for benefits."
   - **Screener-level precondition, not a calculator-level test**: `benefits-calculator`'s `Zipcode.tsx` step Zod-validates the ZIP against `counties_by_zipcode` before the screener advances, so no non-Missouri household ever reaches `MoHealthNet`.

2a. **MO HealthNet for Kids (MHK) — Infants (under age 1): base 196% FPL, effective 201% FPL after the 5% MAGI disregard**
   - Operative table row (Appendix A, effective 07-01-26–03-31-27): "196% of Poverty# MPW & MHK under 1" — HH1 $2,674, HH2 **$3,625**, HH3 $4,577, HH4 $5,528 ("#" = 5% disregard already applied).
   - Screener fields: `household_size`, `birth_year`/`birth_month`, `relationship`, `income (all types)`
   - Source: MO DSS MAGI Income Limits Appendix A, "196%# MPW & MHK under 1" row — https://dssmanuals.mo.gov/wp-content/uploads/2019/03/MAGIappendix-a.pdf; MO DSS "MAGI MO HealthNet Program Descriptions" (04/2026), MHK/CHIP row — https://dssmanuals.mo.gov/wp-content/uploads/2020/03/MAGI-Appendix-I.pdf

2b. **Children ages 1–18, effective 153% FPL — non-CHIP MHK and CHIP 4M share one 153% ceiling**
   - Non-CHIP MHK (§1830.010.05) covers ages 1–18 up to 148% base. CHIP 4M (§1840.010.05) covers the remainder up to 153% base: ages 1–5 from 148–153%; ages 6–18 from 110–153% (so CHIP 4M also covers ages 6–18 between 110–148%, not just the gap above 148%). CHIP 4M is legally a Title XXI "Non-Premium Group" (§1840.010.00), not non-CHIP MHK — but PE models it `is_medicaid_eligible: true`, and MFB-1262's `mo_chip_spec.md` scopes it out of premium CHIP. `mo_medicaid` follows PE's routing (one flat 153% test for the whole 1–18 band) as an **implementation convention**, not a claim that CHIP 4M is Medicaid policy. **Value**: $4,576 (Children) — see Benefit Value's CHIP 4M methodology note.
   - Operative table row (Appendix A, effective 07-01-26–03-31-27): "153%* of Poverty CHIP 4M" — HH1 $2,035, HH2 **$2,760**, HH3 $3,484, HH4 $4,208 ("*" = income ranges CHIP 4M ages 1–5: 148%–153%; ages 6–18: 110%–153%).
   - Screener fields: `household_size`, `birth_year`/`birth_month`, `relationship`, `income (all types)`
   - Source: MO DSS FSD manual, Section 1830.010.05 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1830-000-00/1830-010-00/1830-010-05/; CHIP 4M — Section 1840.010.05 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1840-000-00/1840-010-00/1840-010-05/; MFB-1262 `mo_chip_spec.md`; PE source — `policyengine_us/parameters/gov/hhs/medicaid/eligibility/categories/{young_child,older_child}/income_limit.yaml`.

3. **MO HealthNet for Pregnant Women (MPW) — base 196% FPL, effective 201% FPL, including 12 months postpartum**
   - Same operative table row as criterion 2a: "196% of Poverty# MPW & MHK under 1" — HH2 **$3,625** (unborn child counted toward household size, per below).
   - Income test applies only during pregnancy; household size includes the unborn child. Self-attestation (`pregnant: true/false`) is sufficient.
   - ⚠️ **Data gap (postpartum continuation)**: no "was pregnant within the last 12 months" field. No inclusive assumption (would risk false positives) — surface in the program description; don't gate; no new field proposed.
   - Screener fields: `household_size`, `pregnant`, `income (all types)`
   - Source: MO DSS "MAGI MO HealthNet Program Descriptions" (04/2026), MPW row — https://dssmanuals.mo.gov/wp-content/uploads/2020/03/MAGI-Appendix-I.pdf; continuous eligibility — Section 1850.020.00 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1850-000-00/1850-020-00/.

4. **MO HealthNet for Families (MHF) — Parent/Caretaker Relatives**
   - Three conditions, all required:
     1. **Relationship/responsibility**: a blood/adoption/marriage relative of a dependent child (parent, grandparent, sibling, step-relation, aunt/uncle, cousin, niece/nephew, or their spouse) with whom the child lives and who is primarily responsible for their care (§1810.020.20.10). A non-relative caregiver doesn't qualify (the child is still independently evaluated under 2b).
        - ⚠️ **Data gap — kinship**: MFB cannot independently verify Missouri's blood/adoption/marriage requirement for every relationship represented by `relatedOther`. Do not add a separate MFB kinship gate; use PE's returned MHF result. Scenario 20 covers `relatedOther`.
        - ⚠️ **Data gap — foster-care kinship**: `fosterChild`/`fosterParent` doesn't confirm an *additional* blood/adoption/marriage tie. No dedicated scenario.
        - **Foster-care handling**: pass the foster-care relationship fact to PE; do not use it as a separate MFB eligibility gate.
     2. **Income**: MHF uses a flat, non-FPL-indexed 1996 AFDC-equivalent monthly standard:

        | HH size | Limit | HH size | Limit |
        |---|---|---|---|
        | 1 | $141 | 5 | $400 |
        | 2 | $241 | 6 | $445 |
        | 3 | $301 | 7 | $490 |
        | 4 | $353 | 8 | $532 |

        Operative table row (Appendix A): "MHF/MPW MHF" — HH1 $141, HH2 $241, HH3 $301, HH4 $353 (figures above continue this row through HH8). Missouri's table continues past HH8, but the screener caps household entry at 8 (`MAX_HOUSEHOLD_SIZE`, `HouseholdMemberBasicInfoPage.tsx`), so HH9+ is structurally unreachable — not a gap.
     3. **Student extension for a qualifying child aged 18–19** (high-school student expected to graduate) — determines whether the parent stays on MHF or moves to AEG.
        - ⚠️ **Data gap**: no school-enrollment field. MFB adds no gate in either direction — it reads PE's own `is_parent_for_medicaid` result unmodified, with no special-cased routing to AEG at 18. Surface in the program description.
   - Screener fields: `household_size`, `relationship`, `income (all types)`, `birth_year`/`birth_month`
   - Source: relationship — §1810.020.20.10 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1810-000-00/1810-020-00/1810-020-20/1810-020-20-10/; income standard — MO DSS "MAGI MO HealthNet Program Descriptions" (04/2026), MHF row; dollar figures — MAGI Income Limits Appendix A, "MHF/MPW MHF" row; student extension — §1810.020.20.20 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1810-000-00/1810-020-00/1810-020-20/1810-020-20-20/.

5. **MO HealthNet Adult Expansion (AEG), ages 19–64 — base 133% FPL, effective 138% FPL**
   - Operative table row (Appendix A): "133% of Poverty# AEG" — HH1 **$1,836**, HH2 $2,489, HH3 $3,142, HH4 **$3,795**.
   - All required: age 19–64; income ≤138% FPL effective; not pregnant; not entitled to/enrolled in Medicare Part A/B; not receiving SSI; ineligible for all mandatory categories (MPW/3, MHK/2b, MHF/4, MHABD non-spend-down/6, MO foster care to 26/11 — these take precedence); and, if an uninsured child under 19 lives in the household, that child must be found MHN-eligible.
     - **MEC condition — negative branch NOT RUNNABLE**: existing scenarios satisfy it but don't vary it, and it can't be isolated with current inputs (MHK's 153% ceiling exceeds AEG's 138%, so any income failing the child also fails the parent). The rule (§1865.020.00) is real regardless.
   - Medicare and SSI each independently exclude AEG (Scenario 10).
   - **Routing rule for self-reported disability/blindness/SSDI** (§1865.040.10): triggers a **concurrent MAGI (AEG) and non-MAGI (MHABD) determination**, not automatic AEG exclusion or MHABD establishment. If adjusted MHABD income (criterion 6) clears the non-spend-down standard, MHABD is **mandatory** and displaces AEG with no choice. If it doesn't clear (spend-down only, non-mandatory), Missouri's rule defaults to AEG absent an election — MFB doesn't implement this election/default mechanism (the screener can't capture it) and instead sends the facts to PE and reads its `medicaid_category` result.
   - **Committed launch result**: Scenarios 19, 21, and 31 use PE's Adult Expansion result; see the MFB-1261 accepted-divergences decision.
   - **SSI vs. SSDI**: SSI independently excludes AEG; MHABD eligibility is then evaluated under criterion 6. SSDI does not independently exclude AEG; like a disability/blindness report, it triggers the concurrent AEG/MHABD determination. `sSDisability` is the per-member SSDI signal — there is no dedicated `has_ssdi` field.
   - Screener fields: `household_size`, `birth_year`/`birth_month`, `income (all types)`, `pregnant`, `disabled`, `long_term_disability`, `visually_impaired`, insurance type (`medicare`), income type (`sSI`, `sSDisability`)
   - Source: §1865.020.00 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1865-000-00/1865-020-00/; concurrent-determination and choice mechanism — §1865.040.10 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1865-000-00/1865-040-00/1865-040-10/; PE source — `policyengine_us/variables/gov/hhs/medicaid/eligibility/categories/adult/is_adult_for_medicaid_{fc,nfc}.py`, `.../ssi_recipient/is_209b_ssi_recipient_for_medicaid.py`.

6. **MO HealthNet for Aged, Blind, and Disabled (MHABD)** ⚠️ *partial data gap (spend-down)*
   - Non-spend-down countable monthly income must not exceed (effective 04-01-26): Aged/disabled $1,131 individual / $1,533 couple. Blind $1,330 individual / $1,804 couple.
   - Operative table rows (Appendix J, "Spend Down (includes disabled child) - MHNS, MHSD, MHDC"): "1 person – aged or disabled $1,131 04-01-26"; "2 people – aged or disabled 1,533 04-01-26"; "1 person – blind 1,330 04-01-26"; "2 people – blind 1,804 04-01-26."
   - ⚠️ **Data gap — spend-down**: Missouri allows an otherwise eligible MHABD applicant above the non-spend-down income limit to qualify when the monthly spend-down obligation (incurred medical expenses ≥ excess income) is met. MFB cannot determine whether spend-down is met from current screener inputs. **Committed handling**: do not independently grant eligibility through spend-down; use PE's returned Medicaid result and surface the spend-down possibility in the program description. This handling also applies to MHDC (criterion 12).
   - ⚠️ **Data gap — SGA**: bars MHABD when earnings exceed $1,690/mo (non-blind) or $2,830/mo (blind), net of IRWE, per an MRT determination the screener can't replicate — not screenable; not surfaced or independently scenario-tested. Operative table rows (Appendix J): "SGA (Substantial Gainful Activity) – aged or disabled 1,690 01-01-26"; "SGA – blind 2,830 01-01-26."
   - Missouri is a **209(b) state**: SSI receipt doesn't automatically confer eligibility. SSI is entered as unearned income (§0805.015.30) then **deducted** before the final adjusted-income comparison (§0805.015.35).
   - Blind (100% FPL) and aged/disabled (85% FPL) are distinct standards; use `visually_impaired` / `long_term_disability` respectively. This mandatory-vs-non-mandatory question doesn't arise for MHDC (criterion 12) — no competing AEG pathway for under-18s.
   - **Formal disability determination required, not just self-report** ⚠️ *data gap*: the screener's flags are self-report only. Any of the three flags is a sufficient MHABD-routing signal (inclusive assumption); not gated on the formal requirement; not surfaced. (Same handling for MHDC, criterion 12.)
   - Screener fields: `household_size`, `birth_year`/`birth_month`, `disabled`, `long_term_disability`, `visually_impaired`, `income (all types)`
   - Source: §0805.015.45 — https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/0805-015-45-income-maximum/; dollar figures — "Eligibility Standards for Non-MAGI Programs" (07/2026) — https://dssmanuals.mo.gov/wp-content/uploads/2022/07/mhabd-appendix-j.pdf; SSI as unearned income — §0805.015.30; SSI deduction — §0805.015.35; SGA/MRT — §0840.010.35; IRWE — §1060.005.12; formal disability requirement — mydss.mo.gov/eligibility-requirements-mo-healthnet-coverage; 209(b) — SSA POMS SI 01715.020; PE source — `policyengine_us/parameters/gov/hhs/medicaid/eligibility/categories/senior_or_disabled/income/limit/{individual,couple}.yaml`, `.../medicaid_category.py`.

7. **MHABD Resource/Asset Limit: $6,220.50 individual, $12,441.00 couple (effective 07-01-26)** ⚠️ *data gap — inclusive assumption*
   - Operative table row (Appendix J, "Spend Down..." resource-maximum column): "1 person – aged or disabled ... $6,220.50 07-01-26"; "2 people – aged or disabled ... 12,441.00 07-01-26" (same figures repeat for the blind rows).
   - `household_assets` can't separate countable from excluded resources (home, one vehicle, household goods, etc.). Never hard-gate MHABD on assets. Not surfaced.
   - **Committed handling**: do not use aggregate `household_assets` to enforce the MHABD resource limit because MFB cannot distinguish countable from excluded resources.
   - Source: "Eligibility Standards for Non-MAGI Programs" (07/2026) — https://dssmanuals.mo.gov/wp-content/uploads/2022/07/mhabd-appendix-j.pdf.

7a. **Non-Correctional Public-Institution Residency** ⚠️ *data gap — inclusive assumption*
   - A resident of a non-correctional, government-operated public institution is ineligible unless a patient in a medical institution (13 CSR 40-2.080(2)) — distinct from ordinary correctional incarceration, which is NOT an exclusion (CMS: inmate status suspends rather than terminates coverage, effective 2026-01-01, CIB 122325). No screener field; never gate; not surfaced.
   - Source: 13 CSR 40-2.080(2) — https://www.sos.mo.gov/cmsimages/adrules/csr/current/13csr/13c40-2.pdf.

### MAGI Household Composition & Income Methodology

Missouri determines a **separate MAGI household for each applicant** based on tax-filing status and dependency, not the physical household.

- Tax filer: filer + tax dependents. Non-filer **adult**: self + spouse (if living together) + children under 19. Non-filer **child**: self + parents + dependent siblings/stepsiblings under 19 (§1805.030.10.15) — a different unit than the adult rule, so a parent and child can have different-sized households in the same home. Applicable tax-dependent exceptions (§1805.030.10.20 — e.g. claimed by someone other than a spouse/parent, or by a noncustodial parent) use the non-filer rules instead.
- ⚠️ **Data gap — tax-filing relationships**: MFB does not collect formal tax-filing/dependency relationships. Apply the age-appropriate non-filer composition when inferable from entered members; otherwise use the inclusive non-filer assumption. A non-dependent adult relative (e.g. a grandparent not claimed as a dependent) is treated as a separate unit.
- **MHABD income consideration**: single adult — own income only. Married couple living together — combined income at the couple standard, **except** when one spouse already receives SNC/SAB/SP, in which case the applicant is evaluated individually (§0805.015.05). ⚠️ **Data gap**: no SNC/SAB/SP field — default to the couple-combined rule (narrows rather than broadens who counts, so defaulting away from it avoids false positives); the individual-determination branch is NOT RUNNABLE.
- **Unborn child**: counts only in the pregnant woman's own MAGI household.
- **Income counting**: MAGI income excludes SSI (criterion 6). Apply the exclusion where the income-type field permits; don't deny an otherwise-eligible applicant over other MAGI adjustments the screener can't capture.
- Source: §1805.030.10 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-030-00/1805-030-10/; 42 USC 1396a(e)(14); MHABD spousal income — §0805.015.05 — https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/0805-015-05/.

**Household construction**: use applicant-specific units; do not combine non-spouses or non-dependent relatives solely because they live in the same physical household. Scenarios 7 and 8 verify this requirement.

### Additional Pathways

9. **Transitional MO HealthNet (TMH), up to 12 months** — ⚠️ *NOT RUNNABLE, documentation only*
   - A family that received MHF in 3 of the last 6 months and loses it due to the parent/caretaker's increased earned income continues coverage up to 12 months if a dependent child under 19 remains in the home (subject to original-household-only, no medical-support sanction, and a 196% FPL ceiling for months 7–12).
   - No field for prior MHF receipt, conversion timing, original-household membership, sanction status, or compliance — too many unmeasurable defining facts to approve via inclusive assumption. Document the target rule; don't run; surface general TMH availability.
   - Source: MAGI Program Descriptions TMH row; §1820.015.00, §1820.020.00, §1820.040.00 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1820-000-00/.

10. **Automatic Newborn Coverage** ⚠️ *data gap — narrow continuation, not a universal infant exemption*
    - A child born to a woman eligible for and receiving Title XIX **on the date of birth** is deemed eligible for MO HealthNet for Newborns through age 1 with no new income determination (§1860.010.20) — a **continuation**, not a blanket exemption from the ordinary under-1 test (2a). A mother not on active Title XIX at birth means the child is evaluated under 2a's ordinary test instead.
    - Screener can't confirm maternal Medicaid status at birth. **Committed handling**: don't override 2a's income test; surface as an uncheckable note.
    - Source: §1860.010.20 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1860-000-00/1860-010-00/1860-010-20/; MAGI Program Descriptions, "MO HealthNet for Newborns" row.

11. **Former Foster Care Youth (FFCY), under age 26**
    - Individuals under 26 who aged out of foster care (in-state or, subject to a 2023 cohort split, out-of-state/tribal) are eligible with no income test and citizenship/SSN waived entirely (§1805.050.00). Would value at $6,379/yr (Adults) for ages 19–25 if runnable.
    - ⚠️ **Data gap — no inclusive assumption, description only**: no field identifies who aged out of foster care; assuming every 18–25-year-old qualifies would create substantial false positives. A future per-member expansion belongs to **MFB-1254**, not this ticket.
    - **Cohort split** (out-of-state/tribal only): turned 18 on/after 2023-01-01 — mandatory federal FFCC category (SUPPORT Act §1002), no duration requirement. Turned 18 on/before 2022-12-31 — covered via Missouri's Section 1115 demonstration (approved 2026-03-13), requiring 6 months of prior out-of-state/tribal foster care. No calculator impact either way.
    - Source: §1805.050.00 — https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-050-00/; 1115 demonstration extension approval — https://www.medicaid.gov/medicaid/section-1115-demonstrations/downloads/mo-ffcy-demo-cms-extnsn-aprvl-03132026.pdf; MO SPA 23-0007 — https://www.medicaid.gov/medicaid/spa/downloads/MO-23-0007.pdf.

12. **MO HealthNet for Disabled Children (MHDC), under age 18**
    - A disabled child under 18 may receive spend-down, non-spend-down, or vendor coverage under the same standards as disabled adults (criteria 6–7), with parental income deemed only when the child lives with a parent — stepparent/sibling income is explicitly NOT counted.
    - **Deeming order**: Missouri applies sibling allocation → $20 personal exclusion → $65 earned-income exclusion and half the remainder → parental living allowance → equal division among multiple disabled children (§0805.020.15). Scenarios 9 and 25 intentionally assert the committed PE deemed-income outputs.
    - ⚠️ **Data gap — non-applying-sibling allocation**: whether another minor child is not applying for MA and not receiving specified cash assistance is not observable. Assume the prerequisite is met for other minor children; not surfaced.
    - **Multiple disabled children**: divide deemed income equally (Scenario 25).
    - ⚠️ **Data gap — SSI-receiving parent / spend-down**: Missouri does not deem income from a parent receiving SSI. The screener cannot determine the policy-correct top-level result when spend-down becomes relevant because the necessary medical-expense facts are not collected. No deterministic scenario or MFB-side eligibility correction is applied.
    - `cashAssistance` is too generic to identify one of Missouri's specifically named no-deeming programs — don't use it to bypass deeming.
    - ⚠️ **Data gap — existing non-spend-down Medicaid**: MFB cannot distinguish a parent's spend-down vs. non-spend-down `medicaid` status. Default: deeming applies. Not surfaced.
    - ⚠️ **Data gap — other unobservable deeming adjustments**: spend-down medical expenses and Missouri Family Trust Fund payments aren't separately captured by the screener; no additional calculator logic.
    - Screener fields: `birth_year`/`birth_month`, `long_term_disability`, `relationship`, `income (all types)` (parent's income, when living with a parent)
    - Source: §0805.020.00 — https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-020-00/; deeming detail — §0805.020.15 — https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-020-00/0805-020-15/.

### Cross-Cutting Applicant-Level Eligibility Conditions

Criteria 13–14 are genuine but unscreenable conditions layered on top of whichever pathway applies, not alternate routes.

13. **Social Security Number** ⚠️ *data gap — inclusive assumption*: required with several exceptions (§1805.015.00); not screenable — never gate on this; assume satisfied. Source: https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-015-00/

14. **Medical support cooperation (parent/caretaker cases)** ⚠️ *data gap — inclusive assumption*: cooperation in establishing paternity/support (§1805.040.10, good-cause exception), applies to criteria 4/9; non-cooperation ends only the parent/caretaker's own eligibility. Not screenable — never gate; assume satisfied or excused. Source: https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-040-00/1805-040-10/

15. **Section 1619(b) continuation** (disabled workers who lose SSI cash due to earnings) — ⚠️ *NOT RUNNABLE*: requires SSA-approved status, resources under the 1619(b) max, and prior-month MO HealthNet receipt (§0850.005.00). This population reports as **not currently receiving SSI**, so without this rule they'd be wrongly pushed toward ordinary AEG/MHABD routing, and no reliable proxy exists to infer status. Document the target rule; surface briefly; don't gate or assume. Source: https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0850-000-00/0850-005-00/

**Cash-linked automatic MHABD eligibility — out of scope**: SP/SAB/SNC/Blind Pension recipients are automatically Medicaid-eligible (MHABD manual §1.0); SP is a closed 1973 program. Not recreated by this calculator regardless of which are open.

**"Individuals Deemed To Be Receiving SSI" — out of scope**: MO SPA 23-0007's federal deemed/protected-SSI categories (Pickle Amendment, etc.), distinct from §1619(b). Depends on benefit-history facts the screener has no field for; not built.

16. **Four-Month Extended Medicaid** (loss of MHF due to increased spousal-support collections) — ⚠️ *NOT RUNNABLE*: 42 CFR 435.115, distinct from TMH (which requires the loss be from **earned income** specifically). No field for prior receipt, collection amounts, or denial reason — can't distinguish this trigger from an ordinary over-income denial. Document the target rule; surface alongside TMH.

**Child-welfare automatic Medicaid — out of scope, not built**: IV-E/adoption-guardianship-subsidy or Children's Division custody children are automatically eligible (Child Welfare Manual §4 Ch.9.6) — subsidy families already have this in their Agreement; foster-custody Medicaid is handled by the caseworker (FACES), not a family screener.

### Legal Status & Immigration

**Committed treatment**: handled through `legal_status_required` — the same config-level, household-visibility mechanism every MFB calculator uses (e.g. `TxEmergencyMedicaid`). No calculator-level enforcement or dedicated scenario.

- **Committed launch-period value (through 2026-09-30)**: `legal_status_required: ["citizen", "gc_5plus", "refugee", "otherWithWorkPermission"]` — matches Missouri's ordinary rule and the identical precedent shipped for `ks_medicaid`. `non_citizen` and `gc_5less` are deliberately excluded: `non_citizen` doesn't correspond to a Missouri-qualifying status outside EMCIA (out of scope); `gc_5less` is subject to Missouri's standard 5-year bar (Missouri hasn't adopted the ICHIA/CHIPRA §214 option, per KFF).
- **October 1, 2026 follow-up — not part of this launch**: Missouri's non-citizen Medicaid eligibility rules change effective October 1, 2026. Re-review the MFB `legal_status_required` mapping before that date and update the configuration through a separate post-launch ticket. The launch-period configuration above remains authoritative through September 30, 2026.
- **Missouri's military exceptions** (active-duty, veterans, their families) exempt from the 5-year bar (§§1805.020.10, .10.05, .10.10) are not separately modeled by the household-level `legal_status_required` gate — the standard MFB treatment.
- **Emergency-only coverage for immigration-ineligible applicants is out of scope** — see EMCIA in Program Details' "Explicitly out of scope."
- Source: CMS SHO #26-001; mydss.mo.gov/hr1-non-citizenship-medicaid-faqs; KFF — Medicaid/CHIP Coverage of Lawfully-Residing Immigrant Children and Pregnant Women; §§1805.020.10, 1805.020.10.10.05, 1805.020.10.10.10.

## Priority Criteria

None identified. MO HealthNet is an entitlement program — eligibility runs solely through the categorical pathways above (criteria 1–16), with no waitlist, funding cap, or priority-ranking mechanism.

## Benefit Value

This section reports an **estimated annual valuation** — average per-enrollee program spend from KFF State Health Facts — not a statutory cash payment.

Medicaid is valued per MFB convention as KFF's published average spending per full-benefit enrollee (same methodology as `ks_medicaid`) — **not** PolicyEngine's `medicaid_cost`. Values are from KFF State Health Facts (Missouri, calendar year 2023 preliminary data). KFF's groups are mutually exclusive by age, disability eligibility, and expansion status:

| KFF category | Annual value | Definition | Applies to |
|---|---|---|---|
| Children | $4,576 | Age ≤18, not disability-eligible | Non-disabled children (2b), infants (2a), newborn auto-coverage (10), FFCY (11) ≤18, and any otherwise-Adults-pathway person who is themselves ≤18 |
| Adults | $6,379 | Ages 19–64, not disability-eligible, not expansion | Pregnant women (3), parent/caretaker (4), TMH (9), FFCY (11) ages 19–25, spousal-support extension (16) — only when the person is themselves 19–64 |
| ACA Expansion Adults | $7,445 | Ages 19–64, newly eligible via expansion | Adult Expansion (5) |
| Seniors | $21,857 | Age 65+ regardless of disability | MHABD aged pathway (6), and any disabled person who is themselves 65+ |
| People with Disabilities | $30,410 | Under 65, disability-eligible | MHABD blind/disabled (6), MHDC (12) — only when under 65 |

**Value-priority rule**: assign a member's KFF value by their own facts, regardless of which pathway found them eligible: (1) age 65+ → **Seniors**, even if disability-eligible; (2) under 65, disability-basis pathway → **People with Disabilities**; (3) otherwise age ≤18 → **Children**, even via a nominally "Adults" pathway (MPW, MHF, TMH, spousal-support extension); (4) otherwise 19–64 → **ACA Expansion Adults** if via AEG, else **Adults**. See Scenarios 22–24.

**Per-member values**: report each eligible member's category/value separately; do not sum values into a household total.

**CHIP 4M valuation — $4,576/year.** Missouri legally classifies CHIP 4M as CHIP, but its age/income band corresponds to Missouri's Medicaid-expansion CHIP ("M-CHIP") population, not separate CHIP — confirmed against NASHP's Missouri CHIP fact sheet (M-CHIP ends at 150% FPL both age bands, matching CHIP 4M's range) and CMS T-MSIS coding (M-CHIP reports as Medicaid enrollment, `ENROLLMENT-TYPE=1` — the same data KFF's Medicaid valuation is built from). KFF does not publish a CHIP-4M-specific value; this is MFB's committed informed estimate, applying the KFF Children Medicaid figure. No separate scenario value needed.
- Source: NASHP Missouri CHIP fact sheet; CMS T-MSIS coding guidance; §§1840.010.05/1840.010.00.

`value_format: estimated_annual`. Source: [KFF State Health Facts — "Medicaid Spending per Full-Benefit Enrollee by Enrollment Group," Missouri, CY2023 preliminary](https://www.kff.org/medicaid/state-indicator/medicaid-spending-per-full-benefit-enrollee/).

**Methodology**: uses the **Full-Benefit** table ($21,857 Seniors / $30,410 Disabilities), not Full-or-Partial-Benefit ($18,373 / $28,345), because this calculator represents full-scope MO HealthNet coverage — the other three category values are identical across both tables.

## Acceptance Criteria

**Scenario coverage**: Scenarios 1–34 are executable and numbered sequentially. Documented data gaps and non-runnable pathways do not receive scenario numbers. Legal status is handled through `legal_status_required`, not calculator logic.

**Implementation is complete when:**

- [ ] 33 of the 34 scenarios pass with the exact eligibility, category, and annual value stated. `eligible: true` alone is insufficient where a value is specified. Scenario 8 is the accepted exception: it depends on applicant-specific MAGI household construction, which the platform does not yet build, and so cannot pass on any white label — tracked in MFB-1745 and annotated at the scenario itself.
- [ ] Income boundaries confirm an inclusive (`≤`) comparator across the tested household sizes and pathways: AEG HH1 $1,836/$1,837 (2/5) and HH4 $3,795/$3,797 (32/33); MHK HH2 $2,760/$2,761 (4/17); MHF HH2 $241/$242 (12/26); and infant/MPW HH2 $3,625/$3,626 (27/28, 29/30). MHABD is tested at the exact adjusted-income ceiling only (11) because the over-limit branch may depend on unobservable spend-down.
- [ ] Scenarios 27 and 29 confirm the infant/MPW 201% standard is load-bearing by using income above the 1–18 children's 153% ceiling.
- [ ] MHDC deeming scenarios 9 and 25 assert the exact PE deemed-income value and non-spend-down classification, not only top-level eligibility/value.
- [ ] Categorical routing returns the committed category/value: Scenario 12 returns MHF rather than Adult Expansion; Scenarios 19, 21, and 31 return the committed PE Adult Expansion result documented in criteria 5–6 and the MFB-1261 accepted-divergences decision.
- [ ] Value-priority scenarios 22–24 use the member's age/disability category for the KFF value rather than the pathway name alone.
- [ ] Scenario 20 reads PE's `is_parent_for_medicaid` result as-is for `relatedOther`, consistent with criterion 4's kinship data-gap handling.
- [ ] Scenario 34 switches from MHDC deeming to adult MHABD and uses the applicant's own income once the MHDC deeming period has ended.
- [ ] Non-runnable pathways remain documentation/data-gap treatments only and are not implemented as calculator gates.
- [ ] Household construction uses applicant-specific units; non-spouses and non-dependent relatives sharing a physical household are not combined into one unit — see MAGI Household Composition & Income Methodology. **Not met today**, for the reason recorded against Scenario 8 above; this is the criterion that scenario tests.

## Test Scenarios

### Scenario 1: Single Mother with Two Young Children
**Expected**: Mother eligible — Adult Expansion, $7,445/year. Both children eligible — Children, $4,576/year each.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 3 people
- **Person 1**: `headOfHousehold`, born March 1996 (age 30), not pregnant/disabled, employment income $1,800/mo, no other income, no insurance
- **Person 2**: `child`, born January 2020 (age 6), not long_term_disability, no income
- **Person 3**: `child`, born September 2022 (age 3), not long_term_disability, no income

**Why this matters**: The most common Missouri Medicaid shape — validates MAGI eligibility for both children and the parent in one household.

---

### Scenario 2: Single Adult Age 19 - Barely Eligible for Adult Expansion
**Expected**: Eligible — Adult Expansion, $7,445/year

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 1 person
- **Person 1**: born March 2007 (age 19), `headOfHousehold`, not pregnant/disabled, employment income $1,836/mo, no other income, not enrolled in Medicare, not receiving SSI

**Why this matters**: Tests the exact $1,836/month HH1 AEG ceiling — eligible at the boundary (inclusive `≤`). See Scenario 5 for one dollar over.

---

### Scenario 3: Pregnant Woman with Spouse - Both Members Resolved
**Expected**: Pregnant woman eligible — Adults, $6,379/year (201% effective FPL, HH3 with unborn counted, $4,577 ceiling). Spouse ineligible — his own AEG test uses HH2 (no unborn credit), and $3,050 combined income exceeds the $2,489 HH2 ceiling.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1996 (age 30), `headOfHousehold`, pregnant: yes, employment income $1,500/mo
- **Person 2**: born June 1995 (age 31), `spouse`, employment income $1,550/mo

**Why this matters**: Tests the pregnant-to-Adults KFF mapping and the MAGI rule that an unborn child counts only toward the pregnant woman's own household.

---

### Scenario 4: Parent and Child at Age 1 at the Exact $2,760 HH2 Children's Ceiling
**Expected**: Child eligible — Children, $4,576/year (exact $2,760 HH2 ceiling, `≤`). Parent ineligible (over the $2,489 HH2 AEG ceiling and the MHF flat standard).

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1996 (age 30), `headOfHousehold`, not pregnant/disabled, employment income $2,760/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born March 2025 (age 1), `child`, not long_term_disability, no income

**Why this matters**: The children's ceiling (153% effective) exceeds AEG's (138%), so this pins the real income band where the child qualifies and the parent doesn't, at the exact boundary. See Scenario 17 for one dollar over.

---

### Scenario 5: Single Adult - Income Just Above 138% FPL Effective
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 1 person
- **Person 1**: born March 1996 (age 30), `headOfHousehold`, not pregnant/disabled, employment income $1,837/mo, no other income, no current benefits

**Why this matters**: Paired with Scenario 2 — one dollar over the $1,836 HH1 AEG ceiling flips the applicant to ineligible.

---

### Scenario 6: Disability Claim With Only Spend-Down-Level MHABD — Defaults to Adult Expansion
**Expected**: Eligible — Adult Expansion, $7,445/year (not MHABD). Income ($1,700/mo via `pension`, deliberately not `sSI`/`sSDisability`) triggers a concurrent MHABD determination (criterion 5) via the self-reported `disabled` flag, but adjusted MHABD income ($1,700 − $20 = $1,680) exceeds the $1,131 non-spend-down standard — MHABD is only reachable via spend-down (non-mandatory), so Missouri's own choice/default mechanism (not independently implemented by MFB) defaults to AEG, and this scenario's result is PE's actual output. Gross income is under the $1,836 HH1 AEG ceiling.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1986 (age 40), `headOfHousehold`, not pregnant, `disabled`: yes (`long_term_disability`/`visually_impaired`: no), income type `pension` $1,700/mo, no employment income, not enrolled in Medicare, not receiving SSI

**Why this matters**: Tests the non-mandatory MHABD branch under the AEG ceiling; contrast Scenario 19's mandatory-MHABD case.

---

### Scenario 7: Mixed Household - Corrected MAGI Household Composition
**Expected**: Child eligible — Children, $4,576/year (under $2,760 HH2 ceiling). Grandparent eligible — Seniors, $21,857/year (own $750/mo income, evaluated independently under MHABD's unconditional individual-income rule). Parent ineligible (over the $2,489 HH2 AEG ceiling).

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 3 people
- **Person 1**: born March 1991 (age 35), `headOfHousehold`, not pregnant/disabled, employment income $2,600/mo, employer-sponsored insurance, not receiving Medicare or SSI
- **Person 2**: born January 2018 (age 8), `child`, no income
- **Person 3**: born February 1958 (age 68), `grandParent`, income type `sSRetirement` $750/mo

**Why this matters**: Confirms a non-dependent grandparent is evaluated in her own MHABD unit rather than the parent's MAGI unit.

---

### Scenario 8: Four-Member Household - Pregnant Mother, Working Father, Toddler, Disabled Sibling
**Expected**: Mother eligible — Adults (pregnant), $6,379/year. Disabled sibling eligible — People with Disabilities, $30,410/year (his $500/mo SSI is entered as unearned income then fully deducted per §0805.015.35, leaving $0 adjusted income; evaluated in his own MHABD unit). Father ineligible. Toddler ineligible — his MAGI household is parent+spouse+toddler (HH3), and their combined $4,000/mo income exceeds the $3,484 HH3 ceiling, even though neither parent's income alone would.

**Steps**:
- **Location**: ZIP `65201`, County `Boone`
- **Household**: 4 people
- **Person 1**: born March 1994 (age 32), `headOfHousehold`, pregnant: yes, employment income $2,000/mo, not receiving Medicare or SSI
- **Person 2**: born June 1993 (age 33), `spouse`, employment income $2,000/mo, not receiving Medicare or SSI
- **Person 3**: born January 2024 (age 2), `child`, no income
- **Person 4**: born September 1996 (age 29), `sisterOrBrother`, `long_term_disability`: yes, income type `sSI` $500/mo — evaluated on MHABD using only his own income

**Why this matters**: Load-bearing test for Missouri's non-filer child MAGI rule (household = child + both parents + dependent siblings) — combining both parents' income is what correctly denies the toddler; either parent's income alone would wrongly pass him.

**Known platform gap — the toddler currently comes back eligible.** MFB builds one
`main_tax_unit` per screen holding every member `is_in_tax_unit()` accepts
(`programs/framework/pe_dependencies/payload.py`), so it never constructs the applicant-specific
MAGI households 42 CFR 435.603 defines. The 29-year-old sibling satisfies the qualifying-child
path and joins that unit, which tests the toddler at the HH4 ceiling ($4,208/mo) instead of HH3
and lets $4,000 through. Confirmed on production; the other three members match this scenario
exactly. Scenario 7's grandparent passes only because MHABD is evaluated on individual income,
which masks the same gap. As written this scenario cannot pass on any white label — tracked in
MFB-1744.

---

### Scenario 9: MHDC Deeming — Stepparent Exclusion

**Expected**: Disabled child eligible — People with Disabilities/MHDC, $30,410/year, with exact deemed income of **$1,103.00**.

Deemed parental income uses **only** the biological parent's $4,300/month earned income (Person 2) — the stepparent's $3,000/month (Person 1) is entirely excluded (criterion 12). No other minor child is in the home, so no non-applying-sibling allocation applies. Calculation: $4,300 − $65 = $4,235, ÷ 2 = $2,117.50; combine with unearned income (none) and subtract the $20 exclusion: $2,117.50 − $20 = $2,097.50, floored to $2,097; subtract the one-parent living allowance ($994) = **$1,103.00** — under the $1,131 standard. Parent and stepparent are both independently ineligible for MHF/AEG (combined $7,300/mo, HH3).

**Steps**:
- **Location**: ZIP `65201`, County `Boone`
- **Household**: 3 people
- **Person 1**: born June 1988 (age 38), `headOfHousehold` — the stepparent, employment income $3,000/mo, not pregnant/disabled, not enrolled in Medicare or receiving SSI
- **Person 2**: born April 1990 (age 36), `spouse` — the biological parent of Person 3, employment income $4,300/mo, no unearned income
- **Person 3**: born March 2015 (age 11), `stepChild` (tie to the head), `long_term_disability`: yes, no income

  *(`relationship` describes a member's tie **to the head of household**, not a pairwise descriptor — same convention as the `fosterChild`/`fosterParent` handling, criterion 4.)*

**Why this matters**: Confirms stepparent income is excluded from MHDC deeming; contrast Scenario 25's equal-division test.

---

### Scenario 10: Adult Expansion Denied Due to Medicare Enrollment
**Expected**: Not eligible, despite otherwise-qualifying income.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1975 (age 51), `headOfHousehold`, employment income $1,000/mo, health insurance: Medicare

**Why this matters**: Confirms the Medicare-enrollment exclusion (criterion 5) is applied rather than approving AEG on income alone.

---

### Scenario 11: MHABD Disregard Application — Gross Income Would Fail, Adjusted Income Passes at the Exact Boundary
**Expected**: Eligible — Seniors, $21,857/year, non-spend-down, adjusted income landing exactly on the $1,131 standard. Per §0805.015.00's sequence: gross earned income $2,367/mo; standard earned-income deduction (§0805.015.25, $65 plus half) — $2,367 − $65 = $2,302, ÷ 2 = $1,151; no unearned income; subtract the $20 personal exemption (§0805.015.35) — $1,151 − $20 = **$1,131** — exactly at the standard, eligible (`≤`).
Uses an aged (66) rather than disabled applicant, to isolate the disregard math from criterion 6's separate SGA/IRWE data gap (SGA applies only to the disability-determination pathway).

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born April 1960 (age 66), `headOfHousehold`, not long_term_disability, employed, employment income $2,367/mo, no unearned income

**Why this matters**: A calculator comparing gross income directly against $1,131 would wrongly deny this person — the disregards are what make the difference. Pinned at the exact boundary to confirm the comparator is inclusive.

---

### Scenario 12: Positive MHF Parent/Caretaker Eligibility — MHF Takes Precedence Over Adult Expansion, at the Exact HH2 Ceiling
**Expected**: Parent eligible — **Adults, $6,379/year** (via MHF — NOT the $7,445 Adult Expansion value). Child eligible — Children, $4,576/year.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1990 (age 36), `headOfHousehold`, biological parent living with and primarily responsible for Person 2, not pregnant/disabled, employment income $241/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2015 (age 11), `child`, no income

**Why this matters**: At exactly the $241/mo flat MHF standard, this parent also comfortably clears AEG's much higher ceiling — a calculator that doesn't apply categorical precedence (MHF is mandatory and must be evaluated first) could wrongly default to AEG's $7,445 instead of MHF's $6,379. See Scenario 26 for one dollar over.

---

### Scenario 13: SSI Receipt Excludes Adult Expansion but Routes to MHABD
**Expected**: Not eligible for Adult Expansion — SSI is an explicit exclusion (criterion 5). **Eligible via MHABD** — People with Disabilities, $30,410/year: SSI receipt is itself a sufficient disability-routing signal. His $500/mo SSI is deducted (§0805.015.35) before the MHABD test, leaving only $200/mo employment income — well under $1,131.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born June 1985 (age 41), `headOfHousehold`, not long_term_disability, not pregnant, employment income $200/mo, income type `sSI` $500/mo, not enrolled in Medicare

**Why this matters**: Confirms SSI alone (with no separately-reported disability flag) still correctly routes to MHABD rather than a wrongful full denial.

---

### Scenario 14: Married-Couple MHABD — Combined Income Test
**Expected**: Both spouses eligible — Seniors, $21,857/year each. Combined couple income ($1,300/mo) minus one $20 personal exemption per couple (§0805.015.35: "Only one $20.00 exemption is allowed even if the income of a couple is being considered") = $1,280 — under the $1,533 couple standard, confirming the couple standard governs each spouse's own determination.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 2 people
- **Person 1**: born March 1959 (age 67), `headOfHousehold`, married, living with spouse, not long_term_disability, income type `sSRetirement` $600/mo
- **Person 2**: born June 1960 (age 66), `spouse`, married, living with Person 1, income type `sSRetirement` $700/mo

**Why this matters**: Combined income would fail the $1,131 individual standard if either spouse were wrongly evaluated alone, but passes the $1,533 couple standard that actually governs (§0805.015.05's default, since no SNC/SAB/SP field exists — see MAGI Household Composition).

---

### Scenario 15: MHABD Categorical Failure — Under 65, No Disability Signal
**Expected**: Not eligible for MHABD (fails the categorical gate, criterion 6) or Adult Expansion (over the AEG ceiling).

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1980 (age 46), `headOfHousehold`, not long_term_disability, not visually_impaired, not pregnant, employment income $3,000/mo, not enrolled in Medicare, not receiving SSI

**Why this matters**: Confirms MHABD is never evaluated for someone who doesn't meet its categorical gate, regardless of income.

---

### Scenario 16: MHDC Categorical Failure — Child Has No Disability Signal
**Expected**: Child not eligible — fails MHDC's categorical disability requirement (criterion 12) and ordinary children's Medicaid (over the $2,760 HH2 ceiling). Parent not eligible (over the $2,489 HH2 AEG ceiling).

**Steps**:
- **Location**: ZIP `65201`, County `Boone`
- **Household**: 2 people
- **Person 1**: born April 1985 (age 41), `headOfHousehold`, employment income $3,000/mo, not long_term_disability, not enrolled in Medicare, not receiving SSI
- **Person 2**: born March 2015 (age 11), `child`, not long_term_disability, not visually_impaired, no income

**Why this matters**: Isolates MHDC's categorical gate — household income is set high enough that the child is unambiguously ineligible everywhere, not just for the higher-value category.

---

### Scenario 17: Parent + Child at Age 18 One Dollar Over the $2,760 HH2 Children's Ceiling
**Expected**: Child not eligible — $2,761/mo exceeds the $2,760 HH2 ceiling by one dollar. Parent not eligible either.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1996 (age 30), `headOfHousehold`, not pregnant/disabled, employment income $2,761/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2008 (age 18), `child`, not long_term_disability, no income

**Why this matters**: Paired with Scenario 4 — confirms the boundary is a true edge in a normal two-person household.

---

### Scenario 18: Disability Claim via SSDI — Non-Mandatory MHABD, Defaults to Adult Expansion
**Expected**: Eligible — Adult Expansion, $7,445/year (not MHABD). $500/mo employment plus a $1,200/mo `sSDisability` income stream triggers a concurrent MHABD determination (same as a bare disability claim). Adjusted MHABD income: earned $500 − $65 = $435, ÷2 = $217.50; unearned $1,200 − $20 = $1,180; total = $1,397.50 — over $1,131, so only non-mandatory spend-down applies, defaulting to AEG.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1986 (age 40), `headOfHousehold`, not pregnant, income type `sSDisability` $1,200/mo, employment income $500/mo, not enrolled in Medicare, not receiving SSI

**Why this matters**: Confirms SSDI triggers the same concurrent MHABD evaluation as another disability signal; contrast Scenario 31.

---

### Scenario 19: Disability Claim — Mandatory MHABD Not Applied
**Expected**: Adult Expansion, $7,445/year (committed PE result — see criterion 5). Adjusted MHABD income: ($1,600 − $65) ÷ 2 − $20 = $747.50, floored to $747 — under the $1,131 standard.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1986 (age 40), `headOfHousehold`, not pregnant, `disabled`: yes (`long_term_disability`: no, `visually_impaired`: no), employment income $1,600/mo, no unearned income, not enrolled in Medicare, not receiving SSI/SSDI

**Why this matters**: Regression case for the committed PE result when Missouri's mandatory-MHABD priority would otherwise apply.

---

### Scenario 20: MHF Kinship — PE's Kinship-Blind Result Applies Regardless of Relationship Enum
**Expected**: Adult eligible via MHF, $6,379/year (not Adult Expansion). Child eligible via children's Medicaid, $4,576/year.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1985 (age 41), `headOfHousehold`, employment income $150/mo, not pregnant/disabled, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2018 (age 8), `relatedOther` (the head's nephew), no income

**Why this matters**: `relatedOther` is a real qualifying relative under Missouri's rule with no exact-match enum value, and MFB's own dependency logic treats it as dependent-eligible — confirms MHF eligibility per criterion 4's kinship data-gap handling.

---

### Scenario 21: Blind Applicant — Mandatory MHABD Not Applied
**Expected**: Adult Expansion, $7,445/year (committed PE result — see criterion 5). Unearned income of $1,350/mo (`pension`) produces adjusted income of exactly **$1,330** after the $20 exemption — precisely the blind non-spend-down standard.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1980 (age 46), `headOfHousehold`, not pregnant, income type `pension` $1,350/mo, no earned income, not enrolled in Medicare, not receiving SSI, `visually_impaired`: yes, `long_term_disability`: no

**Why this matters**: Exercises the same committed PE result at the blind MHABD boundary.

---

### Scenario 22: Pregnant Minor — MPW Eligibility Values at Children, Not Adults
**Expected**: Eligible via MPW (criterion 3) — valued at **Children, $4,576/year**, not Adults. MPW has no age floor, and KFF's Children/Adults split is age-based alone for a non-disability-eligible, non-expansion enrollee.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 1 person
- **Person 1**: born June 2009 (age 17), `headOfHousehold`, pregnant: yes, no other income

**Why this matters**: Confirms KFF value selection follows the member's age, not the eligibility pathway.

---

### Scenario 23: MHF Minor Parent — Values at Children, Not Adults
**Expected**: Parent eligible via MHF (criterion 4) — valued at **Children, $4,576/year** (MHF also has no age floor). Child independently eligible via criterion 2a (infant), $4,576/year.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born June 2009 (age 17), `headOfHousehold`, biological parent living with and primarily responsible for Person 2, not pregnant/disabled, employment income $100/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2026 (age 0), `child`, no income

**Why this matters**: MHF equivalent of Scenario 22.

---

### Scenario 24: Disabled Senior — MHABD Values at Seniors, Not People with Disabilities
**Expected**: Eligible via MHABD — valued at **Seniors, $21,857/year**, not People with Disabilities. KFF's Seniors definition is age 65+ regardless of disability.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1956 (age 70), `headOfHousehold`, `long_term_disability`: yes, income type `pension` $1,000/mo, no earned income, not enrolled in Medicare, not receiving SSI

**Why this matters**: Adjusted income ($1,000 − $20 = $980) clears $1,131 regardless of which standard applies, so eligibility isn't in question — this is the first scenario combining "aged" and "disabled" on one person, exercising the age-over-disability priority rather than merely stating it.

---

### Scenario 25: MHDC — Multiple Disabled Children, Equal Division of Deemed Income

**Expected**: Both disabled children independently eligible — People with Disabilities/MHDC, $30,410/year each — **and the calculator must assert each child's own deemed-income figure**. Parent independently ineligible for MHF or Adult Expansion — $5,273/mo exceeds both the $301/mo HH3 MHF standard and the $3,142/mo HH3 AEG effective ceiling (MAGI Income Limits Appendix A, "133% of Poverty# AEG" row, HH3).

No non-applying-sibling allocation applies (only the two disabled-child applicants). Calculation: $5,273 − $65 = $5,208, ÷ 2 = $2,604; − $20 = $2,584; − $994 one-parent living allowance = $1,590 undivided; divided equally per Missouri's rule: $1,590 ÷ 2 = **$795.00 per child**. Both remain under $1,131 (eligible, non-spend-down).

**Steps**:
- **Location**: ZIP `65201`, County `Boone`
- **Household**: 3 people
- **Person 1**: born March 1986 (age 40), `headOfHousehold` — the parent, no other children in the home, employment income $5,273/mo, no unearned income, not pregnant/disabled, not enrolled in Medicare or receiving SSI
- **Person 2**: born March 2015 (age 11), `child`, `long_term_disability`: yes, no income
- **Person 3**: born January 2018 (age 8), `child`, `long_term_disability`: yes, no income

**Why this matters**: Proves the equal-division rule is independently load-bearing, distinct from Scenario 9's stepparent-exclusion test.

---

### Scenario 26: Parent One Dollar Over the $241 HH2 MHF Ceiling — Falls Through to Adult Expansion, Not Denied
**Expected**: Parent not eligible for MHF ($242/mo, one dollar over) — but still **eligible: true via Adult Expansion, $7,445/year**, since $242/mo is nowhere near the $2,489/mo HH2 AEG ceiling. Child independently eligible via children's Medicaid, $4,576/year.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1990 (age 36), `headOfHousehold`, biological parent living with and primarily responsible for Person 2, not pregnant/disabled, employment income $242/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2015 (age 11), `child`, no income

**Why this matters**: Paired with Scenario 12 — confirms failing MHF re-evaluates under AEG rather than denying the parent outright.

---

### Scenario 27: Infant Under Age 1 — the 201% Standard Is Load-Bearing, Not the 1–18 153% Ceiling
**Expected**: Infant eligible — Children, $4,576/year — at the exact $3,625/mo HH2 ceiling for criterion 2a's 201% effective standard. This income is *above* the $2,760 HH2 ceiling that governs ages 1–18 — a calculator wrongly applying the 1–18 standard would incorrectly deny this child. Parent independently ineligible.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1996 (age 30), `headOfHousehold`, not pregnant/disabled, employment income $3,625/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2026 (age 0, under 1), `child`, no income

**Why this matters**: Isolates the infant-specific 201% standard from the lower 1–18 ceiling.

---

### Scenario 28: Infant Under Age 1 — One Dollar Over the 201% Ceiling
**Expected**: Infant not eligible — $3,626/mo is one dollar over the infant-specific ceiling. Parent remains ineligible.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born March 1996 (age 30), `headOfHousehold`, not pregnant/disabled, employment income $3,626/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2026 (age 0, under 1), `child`, no income

**Why this matters**: Paired with Scenario 27 — confirms the infant-specific boundary is a true edge.

---

### Scenario 29: Pregnant Woman — the MPW 201% Ceiling Itself
**Expected**: Eligible via MPW — Adults, $6,379/year — at the exact $3,625/mo ceiling for her own MAGI household size 2 (herself + unborn child).

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 1 person (MAGI size 2, counting the unborn child)
- **Person 1**: born March 1994 (age 32), `headOfHousehold`, pregnant: yes, employment income $3,625/mo, not long_term_disability, not enrolled in Medicare, not receiving SSI

**Why this matters**: Pins the MPW comparator at its exact ceiling. See Scenario 30 for one dollar over.

---

### Scenario 30: Pregnant Woman — One Dollar Over the MPW Ceiling
**Expected**: Not eligible. $3,626/mo is one dollar over. No AEG fallback — pregnancy is an explicit AEG exclusion (criterion 5), not a lower-priority pathway.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 1 person (MAGI size 2, counting the unborn child)
- **Person 1**: born March 1994 (age 32), `headOfHousehold`, pregnant: yes, employment income $3,626/mo, not long_term_disability, not enrolled in Medicare, not receiving SSI

**Why this matters**: Paired with Scenario 29 — confirms the MPW boundary is a true edge.

---

### Scenario 31: Disability Claim via SSDI — Mandatory MHABD Not Applied
**Expected**: Adult Expansion, $7,445/year (committed PE result — see criterion 5). A $600/mo `sSDisability` stream plus $500/mo employment triggers the same concurrent determination as Scenario 18. Adjusted MHABD income: earned $500 − $65 = $435, ÷2 = $217.50; unearned $600 − $20 = $580; total = **$797.50** — under $1,131.

**Steps**:
- **Location**: ZIP `65101`, County `Cole`
- **Household**: 1 person
- **Person 1**: born March 1986 (age 40), `headOfHousehold`, not pregnant, income type `sSDisability` $600/mo, employment income $500/mo, not enrolled in Medicare, not receiving SSI

**Why this matters**: The SSDI-specific analogue of Scenario 19 — confirms the accepted divergence holds via SSDI, not just a bare `disabled` flag, distinguishing it from Scenario 18's non-mandatory (agreeing) case.

---

### Scenario 32: Adult Expansion — the Exact $3,795/Month HH4 Ceiling
**Expected**: Parent eligible — Adult Expansion, $7,445/year — at the exact $3,795/mo HH4 ceiling (MAGI Income Limits Appendix A, "133% of Poverty# AEG," HH4). Children independently eligible via children's Medicaid, $4,576/year each.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 4 people
- **Person 1**: born March 1990 (age 36), `headOfHousehold`, single parent, not pregnant/disabled, employment income $3,795/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2015 (age 11), `child`, no income
- **Person 3**: born January 2017 (age 9), `child`, no income
- **Person 4**: born January 2019 (age 7), `child`, no income

**Why this matters**: Confirms the AEG ceiling scales correctly to HH4, not just HH1 (Scenarios 2/5). See Scenario 33 for the over-ceiling case.

---

### Scenario 33: Adult Expansion — Two Dollars Over the HH4 Ceiling
**Expected**: Parent not eligible for Adult Expansion — $3,797/mo is over the $3,795/mo HH4 ceiling and the flat MHF HH4 standard, with no other routing signal. Children remain independently eligible via children's Medicaid, $4,576/year each.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 4 people
- **Person 1**: born March 1990 (age 36), `headOfHousehold`, single parent, not pregnant/disabled, employment income $3,797/mo, not enrolled in Medicare, not receiving SSI
- **Person 2**: born January 2015 (age 11), `child`, no income
- **Person 3**: born January 2017 (age 9), `child`, no income
- **Person 4**: born January 2019 (age 7), `child`, no income

**Why this matters**: Uses $3,797 rather than $3,796 because the target PE behavior has a known precision edge at $3,796 (PR #9297); $3,797 is the stable over-limit regression point. Missouri's actual ceiling remains $3,795.

---

### Scenario 34: Disabled 18-Year-Old — MHDC's Under-18 Cutoff Ends, Adult MHABD Applies With No Parental Deeming

**Expected**: Person 2 eligible — People with Disabilities, $30,410/year, via adult MHABD. Parental deeming ended after the month they turned 18, so eligibility is based on their own $0 income.

**Steps**:
- **Location**: ZIP `63101`, County `St. Louis City`
- **Household**: 2 people
- **Person 1**: born June 1978 (age 48), `headOfHousehold`, employment income $10,000/mo, not pregnant/disabled, not enrolled in Medicare, not receiving SSI
- **Person 2**: born March 2008 (age 18), `child` (tie to the head), `long_term_disability`: yes, no income

**Parent's own result**: Person 1 is independently ineligible for any pathway — $10,000/mo is far over the AEG HH2 ceiling and the flat MHF standard, with no disability/blindness/SSDI signal of his own.

**Why this matters**: Confirms the transition from MHDC parental deeming to adult MHABD individual-income treatment after age 18.

---

## Source Documentation

- [MO DSS "MAGI MO HealthNet Program Descriptions" (04/2026)](https://dssmanuals.mo.gov/wp-content/uploads/2020/03/MAGI-Appendix-I.pdf)
- [MO DSS MAGI Income Limits Appendix A, Section 18.2.1](https://dssmanuals.mo.gov/wp-content/uploads/2019/03/MAGIappendix-a.pdf)
- [MO DSS FSD manual, Section 1830.010.05 — Children's 148% FPL rule](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1830-000-00/1830-010-00/1830-010-05/)
- [MO DSS FSD manual, Section 1865.020.00 — Adult Expansion Eligibility Requirements](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1865-000-00/1865-020-00/)
- [MO DSS FSD manual, Section 1810.020.20.10 — Parent/Caretaker Relative Definition](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1810-000-00/1810-020-00/1810-020-20/1810-020-20-10/)
- [MO DSS FSD manual, Section 1805.030.10 — MAGI Household Composition](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-030-00/1805-030-10/)
- [MO DSS FSD manual, Section 1805.050.00 — Former Foster Care Youth](https://dssmanuals.mo.gov/family-mo-healthnet-magi/1805-000-00/1805-050-00/)
- [MHABD manual, Section 0805.020.00 — MHDC](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-020-00/); [Section 0805.020.05 — Definition of Living With a Parent](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-020-00/0805-020-05-definition-of-living-with-a-parent/); [Section 0805.020.15 — Deeming Parental Income](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-020-00/0805-020-15/)
- [MHABD manual, Section 0805.015.45 — Income Maximum](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/0805-015-45-income-maximum/); [Section 0805.015.30 — Unearned Income](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/0805-015-30/); [Section 0805.015.35 — Income Exemptions/Deductions](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/0805-015-35/); [Section 0805.015.00 — Financial Need](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/); [Section 0805.015.25 — Standard Deductions From Gross Earned Income](https://dssmanuals.mo.gov/mo-healthnet-for-the-aged-blind-and-disabled/0805-000-00/0805-015-00/0805-015-25/)
- [MO DSS "Eligibility Standards for Non-MAGI Programs" (07/2026)](https://dssmanuals.mo.gov/wp-content/uploads/2022/07/mhabd-appendix-j.pdf)
- [Missouri Revised Statutes, Section 208.146](https://revisor.mo.gov/main/OneSection.aspx?section=208.146); [Missouri Senate, HB 2372 bill tracker](https://www.senate.mo.gov/BillTracking/Bills/BillInformation?billid=12902414&year=2026)
- [CMS Informational Bulletin CIB 122325 — Inmates and Medicaid Eligibility](https://www.medicaid.gov/federal-policy-guidance/downloads/cib122325.pdf)
- [CMS SHO #26-001 — Alien Medicaid Eligibility, Section 71109](https://www.medicaid.gov/federal-policy-guidance/downloads/sho26001.pdf)
- [KFF — Medicaid/CHIP Coverage of Lawfully-Residing Immigrant Children and Pregnant Women](https://www.kff.org/affordable-care-act/state-indicator/medicaid-chip-coverage-of-lawfully-residing-immigrant-children-and-pregnant-women/)
- [SSA POMS SI 01715.020 — 209(b) States](https://secure.ssa.gov/poms.nsf/lnx/0501715020)
- [KFF State Health Facts — "Medicaid Spending per Full-Benefit Enrollee by Enrollment Group," Missouri, CY2023 preliminary](https://www.kff.org/medicaid/state-indicator/medicaid-spending-per-full-benefit-enrollee/)
- [Apply for MO HealthNet Coverage](https://mydss.mo.gov/healthcare/apply)
