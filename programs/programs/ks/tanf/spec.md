# Implement TANF (KS) Program

## Program Details

- **Program**: TANF
- **State**: KS
- **White Label**: ks
- **Research Date**: 2026-06-03

## Eligibility Criteria

1. **Household must include a dependent child under age 18 (or age 18 and working toward a high school diploma or equivalent, up to age 19)**
   - A child temporarily absent from the home for 180 consecutive days or fewer still qualifies if the intent is to return.
   - Screener fields:
     - `household_members.birth_year` + `household_members.birth_month` (use these to calculate precise age; `age` field is deprecated)
     - `household_members.relationship` (use values `child`, `grandChild`, `fosterChild`, `sibling` to identify qualifying children — `sibling` covers households where the HOH is an adult sibling acting as caretaker for a minor sibling)
   - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 2; K.A.R. 30-4-34; KEESM 2110

2. **Pregnant woman with no other dependent children may qualify**
   - Screener fields:
     - `household_members.pregnant` (confirmed real field per MFB screener reference — Section 5: Special Circumstances)
   - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 2; KEESM 2110

3. **Gross household income must be less than 30% of the Federal Poverty Level (FPL)**
   - Income disregards apply: $90 per employed person is subtracted first, then 60% of the remainder is excluded from countable income (countable earned income = (earnings − $90) × 40%, minimum $0). Earnings of children are fully excluded.
   - Whose income counts (mandatory filing unit): per K.S.A. 39-709(a)(1)(A)(i)–(ii) and (b)(1), the mandatory filing unit is the responsible adult, their spouse **or cohabiting partner**, and their minor children/stepchildren; a cohabiting partner's income and resources are counted. Other relatives may be included only at the household's discretion. PE counts the income of every assistance-unit member (all household members except SSI recipients), and MFB places every household member — including a `domesticPartner` — into a single PE `spm_unit` (`policy_engine.py`), so cohabiting-partner income is counted correctly, consistent with the statute.
   - ⚠️ *data gap (understates)* — Because MFB pools **all** co-residents into one assistance unit, there is no mechanism to exercise the KEESM-permitted discretion to *exclude* a non-mandatory relative (e.g., an adult sibling or grandparent who is not the responsible adult) whose income the household could leave out. When such a relative has income, MFB/PE count it, which can **understate** eligibility or benefit value. Shared MFB architecture limitation, not KS-specific; handled by directing borderline households to apply and confirm with DCF.
   - Note: PE runs two income checks — both must pass:
     1. **Gross income < 30% FPL** (`ks_tanf_gross_income_eligible`) — the initial eligibility gate per the TANF State Plan
     2. **Countable income < payment standard** (`ks_tanf_income_eligible`) — after applying the $90 + 60% earned income disregard; per K.A.R. 30-4-110 and KEESM 7110
   - In practice these rarely conflict: when gross income is below 30% FPL, countable income after disregards will almost always be below the payment standard too. The second check is belt-and-suspenders.
   - Screener fields:
     - `household_size`
     - `calc_gross_income("monthly", ["all"])` — for the 30% FPL gross income check, paired with `household_size`
     - `income_streams` per member — for the earned income disregard and SSI exclusion (children's earnings excluded before calculating countable income)
   - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 2; Appendix 1, p. 28 (income disregard); [KEESM 7200 — Income](https://content.dcf.ks.gov/ees/keesm/current/keesm7200.htm); [KEESM 7110](https://content.dcf.ks.gov/ees/keesm/current/keesm7110.htm); K.A.R. 30-4-110; K.S.A. 39-709

4. **Countable household assets must be below $3,000** ⚠️ *partial data gap*
   - Exempt resources (statute/KEESM policy — see the caveat below on what PE actually enforces): per K.S.A. 39-709(a)(1)(A)(iv), **one motor vehicle is exempt regardless of its value or use**; equity in a boat, RV, or ATV, and in any additional vehicle, is countable, except an additional vehicle used primarily to earn income may be exempted at the agency's discretion. Also exempt: the home the family resides in, household furnishings/equipment/personal effects/tools in use, educational accounts for minors (529 plans), individual development accounts (IDAs), and earnings of children.
   - ⚠️ **PE does not model any of the above resource exemptions.** PE's `ks_tanf_resources_eligible` tests `spm_unit_cash_assets` (cash, checking/savings, stocks, bonds, mutual funds) against the $3,000 limit and counts **no vehicles or other non-liquid property at all**. MFB sends liquid `household_assets` → `spm_unit_cash_assets`, so in practice the calculator already exempts every vehicle. The vehicle/exempt-resource detail above is documented for policy accuracy, not because the calculator applies it.
   - Note: PE's `ks_tanf_resources_eligible` uses **$3,000**, citing KEESM 5110 as the operational source (confirmed in PE parameter file). The DCF public-facing TANF page also states $3,000. The TANF State Plan Appendix 1 states "$2,750" — this appears to be a different or outdated reference. For the calculator, use **$3,000** consistent with PE and KEESM 5110. The $2,000/$3,000 age-based tier in the original draft was a SNAP rule incorrectly applied here — TANF has no age-based asset exception.
   - ⚠️ *partial data gap* — `household_assets` captures liquid assets only (cash, checking/savings, stocks, bonds, mutual funds). Non-liquid countable resources — primarily non-work vehicles (vehicles not used for employment, education, or training) and life insurance cash surrender value — are not captured. For the calculator, assume no countable non-liquid assets (inclusivity assumption). In practice this affects very few TANF applicants; households with countable non-liquid assets above the threshold would need to disclose these at application.
   - ~~💡 Screener improvement (withdrawn): ask about non-work vehicles and add their value to the resource test.~~ **Do not implement.** It contradicts both PE (which counts cash assets only — no vehicles) and the statute (K.S.A. 39-709(a)(1)(A)(iv) exempts one vehicle regardless of value). Summing a vehicle's value into the test would make MFB stricter than PE and the law, risking false ineligibility. The correct behavior — count liquid assets only — is already what the calculator does.
   - Screener fields:
     - `household_assets` (liquid assets only — non-liquid countable resources not captured; see data gap above)
   - Source: [KEESM 5110 — Resource Limitation](https://content.dcf.ks.gov/ees/keesm/current/keesm5000.htm); [KS DCF TANF page](https://www.dcf.ks.gov/services/ees/pages/cash/tanf.aspx); K.A.R. 30-4-40

5. **Applicant must reside in the state of Kansas**
   - Screener fields:
     - `zipcode`
     - `county`
   - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 15 (Special Provisions B.1); KEESM 2100; K.S.A. 39-709

6. **The applicant/caretaker must be an adult (age 18+) to act in their own behalf** ⚠️ *data gap for minor exceptions*
   - Confirmed: KEESM 2111 defines "adult" as anyone 18 or older for application purposes. KEESM 2112 states that minors are presumed legally incapable of acting in their own behalf and generally cannot apply for assistance for themselves.
   - **Narrow minor exceptions exist** (KEESM 2112): a minor may act in their own behalf only if: (a) emancipated by a court, (b) age 16 or 17 and married, (c) no available caretaker in specified circumstances, (d) placed in DCF independent living, (e) in a transitional living program (e.g., MINK), or (f) in Job Corps or an approved adult-supervised living arrangement (requires EES Program Administrator approval). The TANF State Plan's reference to "minor caregivers" likely refers to this narrow exception pathway, not a general minor-parent rule.
   - ⚠️ *data gap* — The screener captures `birth_year`/`birth_month` so a minor HOH is detectable, but the screener cannot determine which narrow exception applies (emancipation, marriage, independent living, Job Corps, etc.). For the calculator, apply the **inclusivity assumption**: if the HOH is under 18 and the exception field is not checked, still show the program as potentially eligible.
   - 💡 **Screener improvement:** Add a single optional checkbox to the Special Circumstances section (step 5), shown **only when the detected HOH age is under 18**: *"I am authorized to apply for benefits independently (e.g., emancipated by a court, married, or in an independent living arrangement)."* Checking this confirms the minor exception pathway without requiring detail. Optional — if left blank, the inclusivity assumption applies. Most users never see it. Also benefits any other program with a minor applicant pathway.
   - **PE gap — deferred, not implemented MFB-side.** PE's `ks_tanf_eligible` does not implement this check (verified against the PE source: it ANDs only `is_demographic_tanf_eligible` (child age/pregnancy), immigration, non-empty assistance unit, income, and resources — no applicant-age or act-on-own-behalf test). MFB will **not** add an MFB-side eligibility override for it: `ks_tanf` is a pure PolicyEngine calculator, and per team policy calculators are kept either pure-PE *or* pure-custom — no hybrid PE-passthrough-plus-override. Enforcing the minor-capacity gate is therefore deferred to PolicyEngine (raise in the PE delta report). Until PE implements it, the inclusivity assumption above stands and a minor-applicant household is shown as potentially eligible; final capacity is confirmed by DCF at application.
   - Screener fields: `household_members.birth_year` + `household_members.birth_month`, `household_members.relationship`
   - Source: [KEESM 2111–2112 — Act in Own Behalf](https://content.dcf.ks.gov/ees/keesm/current/keesm2100.htm); [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 4

7. **U.S. citizenship or qualified alien immigration status required** ⚠️ *data gap*
   - Note: Applicants must be U.S. citizens or qualified aliens (lawful permanent residents with 5+ years, refugees, asylees, etc.). Refugees and asylees are exempt from the 5-year bar. KEESM Appendix A-1 details the specific immigration statuses that qualify. The MFB screener does not and should not collect citizenship or immigration status — asking this question would be sensitive, counter to MFB's mission of inclusive low-friction screening, and could deter the most vulnerable users from completing the screener. The `legal_status_required` config field is set to all 6 base values — the program is shown to all immigration status groups and eligibility is confirmed at the application level. No screener improvement is recommended.
   - Screener fields: none (handled via `legal_status_required` in config)
   - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 15 (Special Provisions B.2); [KEESM Appendix A-1](https://content.dcf.ks.gov/EES/KEESM/Appendix/A-1KEESNon-CitizenshipDocumentsandEligibility.pdf); 8 U.S.C. § 1612; K.S.A. 39-709
   - Impact: HIGH

8. **Caretaker relative must have a qualifying degree of relationship to the dependent child** ⚠️ *partial data gap*
   - KEESM 2220 defines qualifying caretaker relationships as: any blood relative within the 5th degree of kinship (parent, grandparent, sibling, uncle/aunt, nephew/niece, great-grandparent, great uncle/aunt, first cousin, first cousin once removed), relatives by marriage within the same degree, legally adoptive relatives, and court-appointed guardians/conservators/legal custodians.
   - The screener's `relationship` field covers the most common cases: `parent`, `stepParent`, `fosterParent`, `grandParent`, `sibling`, `grandChild`, `fosterChild`. However, `aunt`, `uncle`, and `guardian` (court-appointed) are qualifying caretaker types that have no dedicated value and fall under `other`, preventing the calculator from verifying them.
   - For the calculator, assume a qualifying relationship if the household contains a child-relationship member and an adult caretaker. If the adult's relationship is `other`, apply the inclusivity assumption — they may be an aunt, uncle, or guardian.
   - 💡 **Screener improvement:** Add `niece`, `nephew`, and `ward` to the `relationship` enum. These values describe the *child's* relationship to the HOH caretaker — `niece`/`nephew` confirms the HOH is an aunt/uncle (explicitly qualifying under KEESM 2220), and `ward` confirms the HOH is a court-appointed guardian/conservator/legal custodian. Adding these closes the data gap for the most common extended-family caretaker types: when the calculator sees `niece`, `nephew`, or `ward`, it can confirm eligibility rather than rely on an assumption. More distant qualifying relationships (cousins, great-uncle/aunt, relatives by marriage) remain under `other` with the inclusivity assumption — those cases are rare enough that this is acceptable. Also benefits Head Start and other programs with caretaker-relationship requirements.
   - Screener fields: `household_members.relationship` (covers parent, grandparent, sibling, foster — partially closed for aunt/uncle/guardian with the suggested improvement; `other` + inclusivity assumption for remaining T-6 categories)
   - Source: [KEESM 2220 — Living With a Caretaker](https://content.dcf.ks.gov/ees/keesm/current/keesm2220.htm); [KEESM Appendix T-6](https://content.dcf.ks.gov/EES/KEESM/Appendix/T-6RelationshipChart05-17.pdf); K.A.R. 30-4-34
   - Impact: MEDIUM

9. **24-month lifetime limit on TANF cash assistance receipt (with hardship extensions)** ⚠️ *data gap*
   - Note: Kansas imposes a 24-month lifetime limit on TANF cash assistance — shorter than the federal 60-month limit. The clock is tracked per adult, not per household. Hardship extensions of up to 12 additional months are available (domestic violence, disability, caring for disabled family member, PPS involvement with open social service plan), for a maximum of 36 months total.
   - Diversion payment variant: Households that received a diversion payment (a one-time lump sum in lieu of ongoing assistance) face a lifetime maximum of **18 months** of assistance rather than 24.
   - Out-of-state time limit: If a case was closed in another state after reaching that state's TANF time limit, the household is ineligible for Kansas TANF cash assistance — unless they meet one of the first four hardship criteria (caretaker of disabled family member, disability precluding employment, domestic violence/sexual assault, or open PPS social service plan).
   - The screener captures `has_tanf` (currently receiving TANF) but not prior receipt history. For the calculator, assume the household has not exhausted their time limit — this applies to both the standard 24-month limit and the 18-month diversion payment variant; the calculator cannot distinguish between them and treats both with the same inclusivity assumption. Surface the 24-month limit in the program description.
   - 💡 **Screener improvement:** When a user selects `has_tanf` (currently receiving TANF) or a new "previously received TANF" option in Current Household Benefits, show a conditional optional follow-up checkbox: *"I have received TANF cash assistance for 24 months or more in my lifetime."* If checked, the calculator surfaces a time-limit warning and directs the user to contact DCF about hardship extension eligibility. If unchecked or skipped, the inclusivity assumption applies. This pattern only appears for users already engaging with TANF in the benefits section — no burden on everyone else. Also benefits all other state TANF implementations.
   - Screener fields: none (partial: `has_tanf` captures current TANF receipt only)
   - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 15–16; [KEESM Appendix E-4](https://content.dcf.ks.gov/EES/KEESM/Appendix/E-4_24_mo_limited_questions_07_19.pdf); K.S.A. 39-709(b)(3)
   - Impact: HIGH

10. **Must not be a fleeing felon or in violation of probation/parole** ⚠️ *data gap*
    - Note: Federal law prohibits TANF assistance to individuals fleeing prosecution for a felony or violating probation/parole conditions. The screener does not collect criminal justice information. For the calculator, assume this disqualification does not apply (inclusivity assumption). No screener improvement is recommended — collecting criminal justice status is sensitive, invasive, and counter to MFB's mission of inclusive screening.
    - Screener fields: none
    - Source: 42 U.S.C. § 608(a)(9); [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), Appendix 1, p. 27; KEESM 2130
    - Impact: LOW

11. **Drug felony conviction restrictions (Kansas-specific)** ⚠️ *data gap*
    - Note: Kansas has modified the federal drug felon ban. First drug felony conviction (on or after July 1, 2013): 5-year ineligibility. Second offense: lifetime ineligibility. Drug testing is also required on reasonable suspicion. The screener does not collect criminal history. For the calculator, assume this disqualification does not apply (inclusivity assumption). No screener improvement is recommended — collecting criminal conviction history is sensitive and inappropriate for a public-facing screening tool.
    - Screener fields: none
    - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), Appendix 1, p. 27; K.S.A. 39-709(f)(3); 21 U.S.C. § 862a
    - Impact: LOW

12. **SSI recipients are excluded from the TANF assistance unit** ⚠️ *partial data gap*
    - Note: SSI recipients are excluded from the TANF assistance unit — their income and needs are not counted in the case. Other household members may still qualify.
    - The screener's per-member income entry already handles this: when a household has more than one member, each person's income is entered separately. If an SSI recipient enters `income_streams[].type: "sSI"`, the calculator can identify that specific member and exclude them from the TANF filing unit. This is the primary approach.
    - The household-level `has_ssi` flag serves as a backup. The only remaining gap is if someone checks `has_ssi` but skips the income entry — a minor edge case. No screener improvement is needed; the existing per-member income flow handles this.
    - Screener fields:
      - `income_streams[].type: "sSI"` per member (primary — identifies the specific SSI recipient; note capitalization)
      - `has_ssi` (household level — backup flag)
    - Source: [KEESM 2210 — Child in Family](https://content.dcf.ks.gov/ees/keesm/current/keesm2210.htm) ("a child must be included in the assistance plan unless excluded as an SSI recipient"); KEESM 2110; [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), p. 2
    - Impact: MEDIUM

13. **Striker disqualification** ⚠️ *data gap*
    - Note: Individuals participating in a labor strike are ineligible for TANF per federal law. The screener does not collect strike participation information. For the calculator, assume this disqualification does not apply (inclusivity assumption). No screener improvement is recommended — asking about labor strike participation is sensitive and would be adversarial to users exercising their labor rights.
    - Screener fields: none
    - Source: KEESM 2130; 42 U.S.C. § 608(a)(5)
    - Impact: LOW

14. **Fraud disqualification** ⚠️ *data gap*
    - Note: Adults found to have committed TANF fraud — through an administrative disqualification hearing, a court ruling, or a signed waiver/consent agreement — are ineligible for TANF for their lifetime. All adult household members in the case are also rendered ineligible. The screener does not and should not collect this information; asking about fraud history is sensitive and not appropriate for a public-facing screening tool. For the calculator, assume this disqualification does not apply (inclusivity assumption). No screener field improvement is recommended.
    - Screener fields: none
    - Source: [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), Appendix 1, p. 27; KEESM 2130
    - Impact: LOW

---

## Implementation Notes

### Calculator type: pure PolicyEngine (no hybrid)

`ks_tanf` is implemented as a **pure PolicyEngine passthrough** (`KsTanf` in `programs/programs/ks/pe/spm.py`): it wires the household's circumstances into PE via `pe_inputs` and returns PE's eligibility and benefit value unchanged. Per team policy, calculators are kept either **pure-PE** or **pure-custom** — MFB does **not** add MFB-side eligibility overrides on top of a PE calculator (no hybrid). Any KS TANF rule that PolicyEngine does not model is therefore handled by an inclusivity assumption and/or raised in the PE delta report for PE to implement — it is not coded on the MFB side.

### Deferred, PE-dependent limitations

These rules are verified against the PE `ks_tanf` source and are **not** enforced today. They are intentionally left to PolicyEngine (see "pure PolicyEngine" above); until PE implements them, the inclusivity assumptions in the referenced criteria apply.

- **Minor application capacity (KEESM 2111–2112) — Criterion 6.** A minor who cannot act on their own behalf is ineligible unless a narrow exception applies or a legally permitted adult applies for them. PE's `ks_tanf_eligible` has no applicant-age/capacity test, so a minor-applicant household is shown potentially eligible. Deferred to PE; raise in the PE delta report. This is why Scenario 7 expects **Eligible** (matching PE + the inclusivity assumption), not Not eligible.
- **Incapacitated-person care deduction scope (KEESM 7211).** PE's `ks_tanf_countable_earned_income` deducts incapacitated-person care expenses but, per its own code comment, does **not** enforce KEESM 7211's requirement that the cared-for dependent be a member of the assistance unit. Minor over-inclusivity in PE's favor of the applicant; note for the PE delta report.

### SSI Unit Composition

The codebase confirms (models.py line 388): `has_ssi_or_ssi_income = self.has_ssi or self.calc_gross_income("yearly", ["sSI"]) > 0`. Use this same pattern for the `ks_tanf` SSI unit exclusion check — if a household member has income_streams of type `sSI`, they should be excluded from the assistance unit.

### Additional Useful Per-Member Fields

The following per-member fields exist in `HouseholdMember` and may be useful in the calculator:
- `unemployed` — can partially support the two-parent deprivation determination (one parent unemployed) and work requirement context
- `worked_in_last_18_mos` — additional work history signal
- `disabled`, `long_term_disability` — support the work requirement exemption for caretakers of disabled household members

---

## Priority Criteria

None. Kansas TANF (Successful Families Program) is an entitlement — every household that meets the eligibility criteria receives benefits up to the applicable payment standard. There are no priority tiers, waitlists, or preference criteria that would cause one eligible household to be served before another.

---

## Benefit Value

**Type:** Variable monthly cash benefit delivered via Kansas Benefits EBT card.

### Methodology

**Benefit = Payment Standard − Countable Income** (minimum $0)

#### Step 1 — Countable Income

Apply income disregards to gross income:
- Earned income disregard: subtract $90 per employed person first, then exclude 60% of the remainder
  - Formula: countable earned income = (earnings − $90) × 40% per employed person (minimum $0)
  - Example: $500/month earned → countable = ($500 − $90) × 40% = $164/month
- Children's earnings: fully excluded
- Unearned income (e.g., Social Security, child support): counted in full with no disregard

#### Step 2 — Payment Standard

The payment standard depends on three factors:

1. **Family size**
2. **County tier** — determined by the county's shelter group assignment per [KEESM Appendix T-2](https://content.dcf.ks.gov/EES/KEESM/Appendix/T-2_county_group_assignments_04_18_fromxls.pdf). Inferred mapping: Groups I/II = Rural, Group III = High Cost Rural, Group IV = High Population, Group V = High Cost + High Population. Confirm this mapping against [KEESM Appendix F-4](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-4_TAFtable07_11.pdf) before implementation.
3. **Living situation** — Non-Shared (family lives independently) vs. Shared (family lives with others not in the TANF household)

**Non-Shared Payment Standards (Monthly Maximum)**

| Family Size | Rural | High Cost Rural | High Population | High Cost + High Population |
|---|---|---|---|---|
| 1 | $224 | $229 | $241 | $267 |
| 2 | $309 | $314 | $326 | $352 |
| 3 | $386 | $391 | $403 | $429 |
| 4 | $454 | $459 | $471 | $497 |
| 5 | $515 | $520 | $532 | $558 |
| 6 | $576 | $581 | $593 | $619 |
| 7 | $637 | $642 | $654 | $680 |
| 8 | $698 | $703 | $715 | $741 |

For non-shared living, each additional person beyond 8 adds $61/month (confirmed consistent across county tiers). Refer to [KEESM Appendix F-4](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-4_TAFtable07_11.pdf) for larger households.

**Shared Payment Standards (Monthly Maximum)**

| Family Size | Rural | High Cost Rural | High Population | High Cost + High Population |
|---|---|---|---|---|
| 1 | $168 | $170 | $175 | $186 |
| 2 | $263 | $265 | $271 | $284 |
| 3 | $349 | $352 | $359 | $375 |
| 4 | $421 | $425 | $432 | $449 |
| 5 | $487 | $490 | $499 | $517 |
| 6 | $557 | $561 | $571 | $592 |
| 7 | $618 | $622 | $632 | $653 |
| 8 | $679 | $683 | $693 | $714 |

Note: For shared living, the per-person increment for family sizes 5+ is not a flat $61 — it varies slightly by county tier (approx. $60–$68). Use the full table above or refer to [KEESM Appendix F-5](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-5_TABLEII-TAFSharedLiving.htm) for family sizes beyond 8.

#### Step 3 — Benefit

Benefit = Payment Standard − Countable Income. If countable income ≥ payment standard, benefit = $0.

> **Storage convention:** All benefit values in this spec are expressed as monthly figures for readability. The validation JSON (`ks_tanf.json`) stores `expected_results.value` as annual amounts (monthly × 12). Example: $403/month → 4836 in the JSON.

### Data Gaps

⚠️ **Living situation** (shared vs. non-shared) is not captured in the screener. The screener has a `housing_situation` field (renting, owning, homeless, shelter, etc.) but it does not map cleanly to TANF's shared/non-shared distinction. For the calculator, use the **non-shared** standard — the higher, more inclusive value. Surface this assumption in the program description so users in shared living arrangements know their actual benefit may be lower.

💡 **Screener improvement:** Add "Do you share your home with adults who are not part of your TANF household?" (Yes/No) under Housing/Special Circumstances. Closes the shared vs. non-shared living gap and allows the calculator to apply the correct payment standard. Kansas-specific — the shared/non-shared distinction is unique to KS TANF payment tiers.

**County tier** is derivable from the screener's `county` field via the T-2 lookup. PE's `ks_tanf` calculator likely already has this mapping — verify before implementation.

### Estimated Value

- Family of 3, no income, High Population county (e.g. Wyandotte, Sedgwick, Shawnee): **$403/month**
- Family of 3, no income, High Cost + High Population county (e.g. Johnson, Douglas): **$429/month**
- Family of 3, no income, Rural county: **$386/month**
- A typical family of 3 with modest earned income (~$400/month): benefit ≈ **$300–$370/month** after income disregard

Source: [KS DCF Cash Assistance Payment Standards](https://www.dcf.ks.gov/services/ees/Pages/Cash/CashAssistance.aspx); [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf), Appendix 1, pp. 28–29; [KEESM Appendix F-4 — TANF Non-Shared Living Standards](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-4_TAFtable07_11.pdf); [KEESM Appendix F-5 — TANF Shared Living Standards](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-5_TABLEII-TAFSharedLiving.htm)

## Test Scenarios

*All scenarios use 2026 FPL values (matching the config's `year` field). Scenarios 1, 10, and 15 are reflected in the validation JSON (`ks_tanf.json`). All other scenarios are for QA coverage and traceability. Scenarios marked ⚠️ PE depend on MFB-level logic not yet in PE and should be confirmed via the PE delta report.*

Payment standard assumptions: non-shared living (inclusivity assumption). County tiers per KEESM Appendix T-2. Income disregard: countable = (earnings − $90) × 40% (minimum $0), applied per employed person.

---

### Scenario 1: Single parent, 2 children, no income (Golden Path) ✓ in validation JSON

**What we're checking**: A single parent with two young children and no income qualifies under Criterion 1 (child presence) and Criterion 3 (income below 30% FPL). High Population county tier.
**Expected**: Eligible — $403/month (payment standard family 3, High Pop, non-shared: $403 − $0 countable = $403).
**Steps**:
* Location: ZIP `67202`, county `Sedgwick`
* Household size: `3`, assets: $500
* Person 1: Birth month/year `March 1996` (age 30), `headOfHousehold`, no income, insurance: none
* Person 2: Birth month/year `January 2020` (age 6), `child`, no income, insurance: none
* Person 3: Birth month/year `December 2022` (age 3), `child`, no income, insurance: none

**Why this matters**: Primary regression test. Confirms basic eligibility, residency gate, child presence check, and High Population payment standard lookup all work correctly together.

---

### Scenario 2: Minor parent (age 17) with infant — minor exception pathway ⚠️ PE

**What we're checking**: HOH under 18 with a qualifying infant. Criterion 6 requires caretakers to be 18+, but narrow exceptions exist. PE does not implement this check — with the MFB inclusivity assumption the household is still shown as potentially eligible.
**Expected**: Eligible — $326/month *(PE dependent — confirm via delta report before go-live)*.
**Steps**:
* Location: ZIP `66604`, county `Shawnee`
* Household size: `2`, assets: $200
* Person 1: Birth month/year `March 2009` (age 17), `headOfHousehold`, no income, insurance: none
* Person 2: Birth month/year `March 2026` (age 0), `child`, no income, insurance: none

**Why this matters**: Validates the minor exception pathway and the inclusivity assumption for Criterion 6. Confirms the program is shown as potentially eligible when the HOH is under 18 and no exception flag is set.

---

### Scenario 3: Income just below 30% FPL boundary, family 3

**What we're checking**: Household with gross income just under the 30% FPL ceiling. Validates that the earned income disregard formula is applied correctly and eligibility is granted at the boundary.
**Expected**: Eligible — $175/month (countable = ($660 − $90) × 40% = $228; payment standard $403 − $228 = $175).
**Steps**:
* Location: ZIP `66502`, county `Riley`
* Household size: `3`, assets: $200
* Person 1: Birth month/year `April 1992` (age 34), `headOfHousehold`, wages: $660/month, insurance: none
* Person 2: Birth month/year `March 2018` (age 8), `child`, no income, insurance: none
* Person 3: Birth month/year `June 2021` (age 4), `child`, no income, insurance: none
* Gross $660 < ~$683 (30% FPL for family 3) ✓

**Why this matters**: Income boundary test (just-eligible side). Confirms the 30% FPL gate and disregard formula work at the upper end of the eligible range.

---

### Scenario 4: Income just above 30% FPL boundary, family 2

**What we're checking**: Household with gross income just over the 30% FPL ceiling is correctly rejected. Validates the income gate is enforced.
**Expected**: Not eligible (no value).
**Steps**:
* Location: ZIP `66502`, county `Riley`
* Household size: `2`, assets: $200
* Person 1: Birth month/year `April 1992` (age 34), `headOfHousehold`, wages: $545/month, insurance: none
* Person 2: Birth month/year `March 2018` (age 8), `child`, no income, insurance: none
* Gross $545 > ~$541 (30% FPL for family 2) ✗

**Why this matters**: Income boundary test (just-ineligible side). Pairs with Scenario 3 to confirm the 30% FPL ceiling is correctly applied and the screener rejects households over the threshold.

---

### Scenario 5: Liquid assets exceed $3,000

**What we're checking**: Household with liquid assets just over the $3,000 resource limit is rejected regardless of income (Criterion 4).
**Expected**: Not eligible (no value).
**Steps**:
* Location: ZIP `67202`, county `Sedgwick`
* Household size: `3`, assets: $3,001
* Person 1: Birth month/year `April 1990` (age 36), `headOfHousehold`, no income, insurance: none
* Person 2: Birth month/year `March 2015` (age 11), `child`, no income, insurance: none
* Person 3: Birth month/year `June 2019` (age 6), `child`, no income, insurance: none

**Why this matters**: Asset limit boundary test. Confirms the $3,000 resource limit is enforced and that assets alone can disqualify an otherwise-eligible household. Note: `household_assets` captures liquid assets only (see Criterion 4 data gap).

---

### Scenario 6: Non-parent caretaker exactly age 18 ⚠️ PE

**What we're checking**: Caretaker who just turned 18 — boundary condition for the age-18+ requirement (Criterion 6). PE does not currently implement this check.
**Expected**: Eligible — $326/month *(PE dependent)*.
**Steps**:
* Location: ZIP `67202`, county `Sedgwick`
* Household size: `2`, assets: $200
* Person 1: Birth month/year `June 2008` (age 18), `headOfHousehold`, no income, insurance: none
* Person 2: Birth month/year `March 2022` (age 4), `child`, no income, insurance: none

**Why this matters**: Boundary test for the caretaker age requirement. Confirms that a caretaker who has just reached 18 is not incorrectly excluded. Pairs with Scenario 7 to test both sides of the age-18 gate.

---

### Scenario 7: Non-parent caretaker age 17, caring for minor sibling ⚠️ PE

**What we're checking**: HOH age 17 caring for a 15-year-old sibling. Under the caretaker age-18+ rule (Criterion 6) the household would be ineligible unless a minor exception applies, but PE's `ks_tanf_eligible` has no applicant-capacity check and MFB does not add an MFB-side gate (pure-PE calculator — see Implementation Notes). Under the inclusivity assumption the household is therefore shown as potentially eligible; DCF confirms capacity at application.
**Expected**: Eligible — $326/month (Shawnee = High Population tier, family 2, non-shared: $326 − $0 countable = $326). *Minor-capacity gate is a deferred PE limitation (Criterion 6); revisit if PE implements it.*
**Steps**:
* Location: ZIP `66604`, county `Shawnee`
* Household size: `2`, assets: $200
* Person 1: Birth month/year `March 2009` (age 17), `headOfHousehold`, no income, insurance: none
* Person 2: Birth month/year `March 2011` (age 15), `sisterOrBrother`, no income, insurance: none

**Why this matters**: Confirms the minor-caretaker inclusivity assumption (Criterion 6) — a minor HOH is shown potentially eligible rather than screened out, since the capacity gate is a deferred PE limitation, not an MFB-side check. Also validates that `sisterOrBrother` is recognized as a qualifying child relationship (Criterion 1). Pairs with Scenario 2 (minor parent) to cover the minor-HOH pathway across relationship types — both now expect Eligible.

---

### Scenario 8: Two-parent household, 3 children, combined $500 earned income

**What we're checking**: Earned income disregard applied to a larger household. Validates that countable income is correctly calculated and subtracted from a higher payment standard.
**Expected**: Eligible — $404/month (countable applied per employed person: HOH ($300 − $90) × 40% = $84, spouse ($200 − $90) × 40% = $44, total $128; payment standard family 5, High Pop $532 − $128 = $404).
**Steps**:
* Location: ZIP `66502`, county `Riley`
* Household size: `5`, assets: $400
* Person 1: Birth month/year `April 1991` (age 35), `headOfHousehold`, wages: $300/month, insurance: none
* Person 2: Birth month/year `June 1993` (age 32), `spouse`, wages: $200/month, insurance: none
* Person 3: Birth month/year `March 2015` (age 11), `child`, no income, insurance: none
* Person 4: Birth month/year `June 2018` (age 7), `child`, no income, insurance: none
* Person 5: Birth month/year `September 2021` (age 4), `child`, no income, insurance: none

> **PE behavior confirmed (2026-07-23, live PE):** PE applies the $90 work expense **per employed person**, then 40% of each person's remainder — HOH ($300 − $90) × 40% = $84, spouse ($200 − $90) × 40% = $44, total $128 countable → benefit $404. Verified via live-PE API QA (screen `6642e382`).

**Why this matters**: Tests the income disregard on a two-parent, multi-child household. Also confirms the payment standard scales correctly to family size 5.

---

### Scenario 9: Grandparent kinship caretaker, 2 grandchildren

**What we're checking**: Extended-family caretaker pathway. Validates that `grandChild` relationship values are recognized as qualifying children and that a non-parent caretaker household passes eligibility (Criterion 8).
**Expected**: Eligible — $403/month (payment standard family 3, High Pop, non-shared: $403 − $0 = $403).
**Steps**:
* Location: ZIP `66604`, county `Shawnee`
* Household size: `3`, assets: $1,200
* Person 1: Birth month/year `March 1964` (age 62), `headOfHousehold`, no income, insurance: none
* Person 2: Birth month/year `January 2016` (age 10), `grandChild`, no income, insurance: none
* Person 3: Birth month/year `September 2019` (age 6), `grandChild`, no income, insurance: none

**Why this matters**: Validates the `grandChild` relationship value for extended-family caretaker cases. Confirms that a grandmother raising grandchildren passes both child presence (Criterion 1) and caretaker relationship (Criterion 8) checks.

---

### Scenario 10: Adult-only household — no qualifying child (Primary Exclusion) ✓ in validation JSON

**What we're checking**: The most common TANF ineligibility reason — no dependent child present (Criterion 1 fails). Income level is irrelevant; the household is rejected at the first criterion.
**Expected**: Not eligible (no value).
**Steps**:
* Location: ZIP `67202`, county `Sedgwick`
* Household size: `1`, assets: $1,000
* Person 1: Birth month/year `March 1991` (age 35), `headOfHousehold`, wages: $1,200/month, insurance: none

**Why this matters**: Primary exclusion test. Validates that the child presence gate is enforced before any income or asset checks run. The most important ineligibility path for TANF.

---

### Scenario 11: Pregnant woman with no other children

**What we're checking**: Alternative eligibility pathway under Criterion 2. A pregnant adult with no children qualifies; confirms pregnancy confers eligibility independently of child presence.
**Expected**: Eligible — $197/month (countable = ($200 − $90) × 40% = $44; payment standard family 1, High Pop $241 − $44 = $197).
**Steps**:
* Location: ZIP `66604`, county `Shawnee`
* Household size: `1`, assets: $200
* Person 1: Birth month/year `May 1994` (age 32), `headOfHousehold`, pregnant: yes, wages: $200/month, insurance: none

**Why this matters**: Validates the pregnancy pathway as an independent eligibility route (Criterion 2). Also confirms the earned-income disregard is applied to the HOH's wages even without a qualifying child present — countable = ($200 − $90) × 40% = $44.

---

### Scenario 12: Rural county tier (Allen County, Group I)

**What we're checking**: T-2 county tier lookup for the lowest payment tier. Validates that the Rural payment standard is applied when `county` maps to Group I in the T-2 lookup.
**Expected**: Eligible — $342/month (countable = ($200 − $90) × 40% = $44; payment standard family 3, Rural $386 − $44 = $342).
**Steps**:
* Location: ZIP `66749`, county `Allen`
* Household size: `3`, assets: $200
* Person 1: Birth month/year `April 1990` (age 36), `headOfHousehold`, wages: $200/month, insurance: none
* Person 2: Birth month/year `March 2018` (age 8), `child`, no income, insurance: none
* Person 3: Birth month/year `June 2021` (age 4), `child`, no income, insurance: none

**Why this matters**: Tests the lowest county tier in the T-2 lookup. Confirms the Rural payment standard ($386 for family 3) is used instead of High Population ($403). County tier is one of the two most complex KS-specific calculation pieces.

---

### Scenario 13: High Cost + High Population county tier (Johnson County, Group V)

**What we're checking**: T-2 county tier lookup for the highest payment tier. Validates that the HC+HP payment standard is applied when `county` maps to Group V.
**Expected**: Eligible — $429/month (payment standard family 3, HC+HP, non-shared: $429 − $0 = $429).
**Steps**:
* Location: ZIP `66062`, county `Johnson`
* Household size: `3`, assets: $200
* Person 1: Birth month/year `April 1990` (age 36), `headOfHousehold`, no income, insurance: none
* Person 2: Birth month/year `March 2018` (age 8), `child`, no income, insurance: none
* Person 3: Birth month/year `June 2021` (age 4), `child`, no income, insurance: none

**Why this matters**: Tests the highest county tier in the T-2 lookup. Confirms the HC+HP premium ($429 vs $386 Rural for family 3) is correctly applied. Pairs with Scenario 12 to validate the full tier range.

---

### Scenario 14: SSI unit exclusion — HOH receives SSI, child qualifies

**What we're checking**: SSI recipients are excluded from the TANF assistance unit (Criterion 12). The HOH's $900 SSI income is not counted; only the child remains in the unit, giving a family-of-1 payment standard.
**Expected**: Eligible — $241/month (HOH excluded from unit; family 1, High Pop, non-shared: $241 − $0 countable = $241).
**Steps**:
* Location: ZIP `67202`, county `Sedgwick`
* Household size: `2`, assets: $500
* Person 1: Birth month/year `April 1980` (age 46), `headOfHousehold`, SSI (`income_streams[].type: "sSI"`): $900/month — excluded from TANF unit, insurance: none
* Person 2: Birth month/year `March 2022` (age 4), `child`, no income, insurance: none

**Why this matters**: Validates the SSI unit exclusion logic. Confirms the calculator correctly identifies the SSI recipient via `income_streams[].type: "sSI"`, removes them from the filing unit, and applies the family-1 payment standard to the remaining child.

---

### Scenario 15: Income disregard + county tier — single parent, earned income, Johnson County ✓ in validation JSON

**What we're checking**: The $90 + 60% earned income disregard formula and the T-2 HC+HP county tier lookup together. Uses a mid-range income to produce a non-zero countable amount and tests the highest-tier payment standard.
**Expected**: Eligible — $268/month (gross $300 < ~$541 (30% FPL for family 2) ✓; countable = ($300 − $90) × 40% = $84; payment standard family 2, HC+HP $352 − $84 = $268).
**Steps**:
* Location: ZIP `66062`, county `Johnson`
* Household size: `2`, assets: $300
* Person 1: Birth month/year `June 1998` (age 28), `headOfHousehold`, wages: $300/month, insurance: none
* Person 2: Birth month/year `March 2024` (age 2), `child`, no income, insurance: none

**Why this matters**: Edge case combining the two most complex KS-specific calculation pieces — the earned income disregard and the county tier lookup — in a single scenario. Validates that both work correctly together and that the HC+HP tier is correctly applied to a family-2 case with earned income.

---

## Implementation Coverage

- ✅ Fully evaluable: 4 (criteria 1, 2, 3, 5)
- ✅/⚠️ Partially evaluable: 4 (criteria 4, 6, 8, 12)
- ⚠️ Data gaps: 6 (criteria 7, 9, 10, 11, 13, 14)

4 criteria are fully evaluable: dependent child presence, pregnancy, income vs. 30% FPL, and Kansas residency. 4 criteria are partially evaluable — assets (liquid assets captured, non-liquid countable resources not), caretaker age (detectable but minor exceptions unverifiable), caretaker relationship (common cases covered, extended family partial), and SSI exclusion (household level). The 6 data gaps include 2 high-impact factors (immigration status and 24-month time limit) and 4 sensitive disqualifications (fleeing felon, drug felony, striker, fraud) that are intentionally not surfaced in the screener. All gaps are handled via inclusivity assumptions; users should be directed to apply to confirm final eligibility. Note: The deprivation requirement has been removed — confirmed inapplicable to Kansas TANF (not in PE's ks_tanf implementation, K.A.R. 30-4-50, KEESM 2220, or the TANF State Plan).

## Screener Improvement Opportunities

The following changes to the MFB screener would close data gaps identified in this spec. Each is flagged inline under its relevant criterion above. None are required for the initial implementation.

| # | Suggested change | Closes | Also benefits |
|---|---|---|---|
| 1 | When user selects `has_tanf` or "previously received TANF" in Current Household Benefits, show conditional optional follow-up: "I have received TANF for 24 months or more in my lifetime" | Criterion 9 — 24-month time limit history not screenable; surfaces time-limit warning for at-risk households without burdening other users | All state TANF implementations |
| 2 | Add "Do you share your home with adults not in your TANF household?" (Yes/No) | Benefit calculation — shared vs. non-shared living standard | Kansas-specific |
| 3 | Add optional checkbox to Special Circumstances (shown only when HOH age < 18): "I am authorized to apply independently (e.g., emancipated, married, or in an independent living arrangement)" | Criterion 6 — minor exception pathway unverifiable | Any program with a minor applicant pathway |
| 4 | Add `niece`, `nephew`, and `ward` to the `relationship` enum | Criterion 8 — partially closes gap: `niece`/`nephew` confirms HOH is aunt/uncle (qualifying KEESM 2220 caretaker); `ward` confirms court-appointed guardian. Cousins and more distant relatives remain under `other` + inclusivity assumption. | Head Start, other programs with caretaker-relationship rules |
| 5 | When household enters assets below $3,000, show follow-up: "Does your household own any vehicles not used primarily for work, school, or job training?" with optional estimated value field. Sum with `household_assets` for resource test; if combined value exceeds $3,000, surface a note to verify with DCF rather than excluding outright. | Criterion 4 — `household_assets` captures liquid assets only; non-work vehicles are the most common countable non-liquid resource for TANF applicants | SNAP and other programs with asset/resource limits |

---

## Research Sources

### Program Overview & Eligibility

- [KS DCF – Successful Families Program (TANF)](https://www.dcf.ks.gov/services/ees/pages/cash/tanf.aspx) — eligibility overview, work requirements, work exemptions, 24-month time limit
- [KS TANF State Plan FFY 2024–2026](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20FFY%202024%20-%202026.pdf) — authoritative policy: 30% FPL income limit, asset limit, income disregard formula, work hour requirements, immigration rules, time limit, hardship extensions
- [KS DCF – Cash Assistance Overview](https://www.dcf.ks.gov/services/ees/Pages/Cash/CashAssistance.aspx) — full payment standard table by family size and living situation (families 1–8)
- [K.A.R. 30-4-50 — Assistance Eligibility (TANF)](https://www.law.cornell.edu/regulations/kansas/K-A-R-30-4-50) — public regulation confirming: 24-month time limit, hardship extension conditions (up to 36 months), diversion payment 18-month variant, fleeing felon disqualification, drug testing requirements
- [K.A.R. 30-4-34 — Public Assistance Program](https://www.law.cornell.edu/regulations/kansas/K-A-R-30-4-34) — defines TANF as a covered program type under Kansas public assistance
- [K.S.A. 39-709 — Temporary Assistance for Needy Families](https://ksrevisor.gov/statutes/chapters/ch39/039_007_0009.html) — primary Kansas TANF statute

### KEESM Policy Manual

- [KEESM Home](https://content.dcf.ks.gov/EES/KEESM/Keesm.htm) — Kansas Economic and Employment Services Manual (living policy document; updated Feb, May, Jul, Oct)
- [KEESM Summary of Changes & SCLs](https://content.dcf.ks.gov/EES/KEESM/state_comCurrent.html) — current and historical policy change summaries; used to verify minor parent eligibility and confirm deprivation requirement is not in current policy
- [KEESM Appendix Index](https://content.dcf.ks.gov/EES/KEESM/Appendix/Appendix.html) — full index of all KEESM appendix documents

### Eligibility — General Requirements

- [KEESM 2100–2112 — General Eligibility / Act in Own Behalf](https://content.dcf.ks.gov/ees/keesm/current/keesm2100.htm) — confirms adult (18+) definition, minor applicant rules and narrow exceptions
- [KEESM 2210 — Child in Family (TANF-specific)](https://content.dcf.ks.gov/ees/keesm/current/keesm2210.htm) — definitive TANF child eligibility requirements: child must be present, under 18 (or 18-19 pursuing diploma), school enrollment for ages 7-17. **Confirms no deprivation requirement in Kansas TANF.** Also confirms SSI exclusion (SSI recipient children excluded from assistance plan) and unborn child pathway.

### Eligibility — Household Composition & Relationships

- [KEESM 2220 — Living With a Caretaker](https://content.dcf.ks.gov/ees/keesm/current/keesm2220.htm) — definitive list of qualifying caretaker relationships (blood relatives within 5th degree, relatives by marriage, adoptive relatives, court-appointed guardians/conservators/legal custodians)
- [KEESM Appendix T-6 — Relationship Chart (TANF Only)](https://content.dcf.ks.gov/EES/KEESM/Appendix/T-6RelationshipChart05-17.pdf) — illustrated relationship chart ⚠️ *dated May 2017 — verify still current; KEESM 2220 is the authoritative text*

### Eligibility — Immigration & Citizenship

- [KEESM Appendix A-1 — Non-Citizenship Documents and Eligibility](https://content.dcf.ks.gov/EES/KEESM/Appendix/A-1KEESNon-CitizenshipDocumentsandEligibility.pdf) — qualifying immigration statuses, required documents, 5-year bar details

### Eligibility — Time Limits & Hardship

- [KEESM Appendix E-4 — TANF 24-Month Limit Screening Questions](https://content.dcf.ks.gov/EES/KEESM/Appendix/E-4_24_mo_limited_questions_07_19.pdf) — time limit rules, hardship extension criteria
- [KEESM Appendix P-18 — Hardship Instructions](https://content.dcf.ks.gov/EES/KEESM/Appendix/P-18.docx) — detailed hardship extension procedures

### Eligibility — Income

- [KEESM 7110 — Countable Income / Payment Standard Test](https://content.dcf.ks.gov/ees/keesm/current/keesm7110.htm) — countable income (after disregards) must be below the payment standard; PE's second income check (`ks_tanf_income_eligible`, K.A.R. 30-4-110)
- [KEESM 7200 — Income](https://content.dcf.ks.gov/ees/keesm/current/keesm7200.htm) — income types, disregards, and calculation methodology

### Eligibility — Work Requirements

- [KEESM Appendix E-26 — Consolidated Work Requirements](https://content.dcf.ks.gov/EES/KEESM/Appendix/E-26%20-%20Consolidated%20Work%20Requirements%20(English).pdf) — work activity hours, exemptions, sanctions
- [KEESM Appendix E-1 — TANF Coding Chart for Work Programs](https://content.dcf.ks.gov/EES/KEESM/Appendix/E-1_TANFCodingChartforWP10-20.pdf) — activity type definitions used in PE implementation

### Benefit Calculation — Payment Standards & County Tiers

- [KEESM Appendix F-4 — TANF Non-Shared Living Payment Standards](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-4_TAFtable07_11.pdf) — official non-shared payment standard table
- [KEESM Appendix F-5 — TANF Shared Living Payment Standards](https://content.dcf.ks.gov/EES/KEESM/Appendix/F-5_TABLEII-TAFSharedLiving.htm) — official shared payment standard table
- [KEESM Appendix T-2 — County Group Assignments Chart](https://content.dcf.ks.gov/EES/KEESM/Appendix/T-2_county_group_assignments_04_18_fromxls.pdf) — maps all 105 Kansas counties to shelter groups (I–V), used to determine county payment tier ⚠️ *dated April 2018 — verify county groupings are still current*

### Application & Reporting

- [KEES Self-Service Portal — Apply for Benefits](https://cssp.kees.ks.gov/apspssp/sspNonMed.portal) — online application for TANF, SNAP, child care, and other DCF programs
- [DCF Self-Service Portal FAQ](https://content.dcf.ks.gov/SSP/FAQs.pdf) — confirms application time ("30 minutes or more"), cash assistance processing time (45 days), required documents, and Kansas Benefits Card delivery process
- [KS DCF – TANF Drug Testing](https://www.dcf.ks.gov/services/ees/Pages/Drug-Testing.aspx) — suspicion-based drug testing policy and penalties

### Program Data & Reporting

- [TANF State Plan Completion Letter](https://www.dcf.ks.gov/services/ees/Documents/Reports/TANF%20State%20Plan%20completion%20letter.pdf) — federal approval of the FFY 2024–2026 state plan
- [FY 2024 TANF Annual Report (ACF-204)](https://www.dcf.ks.gov/services/ees/Documents/Reports/FY2024ACF-204Report.pdf) — most recent annual federal TANF report for Kansas
