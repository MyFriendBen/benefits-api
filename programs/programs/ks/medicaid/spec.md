# Implement KanCare (Medicaid) (KS) Program

## Program Details

- **Program**: KanCare (Medicaid)
- **State**: KS
- **White Label**: ks
- **Calculator Type**: PE Custom (existing) — `KsKanCare(Medicaid)`, a subclass of the federal PE `medicaid` calculator (pattern: CO/NC/MA/WA)
- **Research Date**: 2026-06-23

## Eligibility Criteria

A person qualifies by meeting the **general requirements** and **one categorical pathway**. Kansas has **not** expanded Medicaid, so non-disabled, non-pregnant, childless adults under 65 have no pathway at any income. Dollar figures are monthly, from KFMAM Appendix F-8 ("Kansas Medical Assistance Standards," Rev 04-26; MAGI standards updated 4/1/26; PDF confirmed directly).

### General requirements (all pathways)

1. **Kansas residency**
   - Screener fields: `zipcode`, `county`
   - Source: K.A.R. 129-6-55 ("Residence, citizenship, and alienage"); 42 CFR 435.403

2. **U.S. citizen or qualified non-citizen**
   - Configured at the program level via `legal_status_required` — **not** a data gap. Set to `["citizen", "refugee", "gc_5plus", "otherWithWorkPermission"]`. Kansas has not adopted the ICHIA/CHIPRA §214 option, so LPRs within the 5-year bar (`gc_5less`) are excluded. `otherWithWorkPermission` is kept as an over-inclusive catch-all covering COFA migrants (work-authorized, no green card, no waiting period) and some humanitarian parolees, per MFB's over-include-and-explain principle.
   - Source: KFMAM §2040–2048 "Citizenship and Alien Status" (§2043 = no-wait eligible non-citizens incl. COFA migrants §2043.12; §2044 = LPRs/parolees eligible after the 5-yr bar; §2040 = non-qualified → emergency only; §2040 NOTE = undocumented parent + citizen child → child still covered); K.A.R. 129-6-55; 8 U.S.C. §1613; KFF State Health Facts, "Medicaid/CHIP Coverage of Lawfully-Residing Immigrant Children and Pregnant Women" (Jan 2026) — Kansas = No/No, https://www.kff.org/affordable-care-act/state-indicator/medicaid-chip-coverage-of-lawfully-residing-immigrant-children-and-pregnant-women/

### Categorical pathways (qualify under any one)

3. **Infant under age 1** — household MAGI ≤ **171% FPL** (F-8: HH1 $2,275; HH3 $3,894)
   - Screener fields: `birth_year`/`birth_month`, income streams, `household_size`
   - Source: KFMAM Appendix F-8 §A.1 ("171%* PW & Infants under age 1"); K.A.R. 129-6-72; 42 CFR 435.118 (171% includes the 5-pt MAGI disregard; PE `infant` = 1.71)

4. **Child age 1–5** — household MAGI ≤ **154% FPL effective** (F-8 statutory 149%, HH1 $1,982, + 5-pt income disregard)
   - Screener fields: `birth_year`/`birth_month`, income streams, `household_size`
   - Source: KFMAM Appendix F-8 §A.1 ("149% Children age 1-5"); K.A.R. 129-6-72; 42 CFR 435.118 (PE `young_child` = 1.54)

5. **Child age 6–18** — household MAGI ≤ **138% FPL effective**. F-8 covers ages 6–18 under Medicaid to **113%** (HH1 $1,503) plus Medicaid-funded **M-CHIP to 133%** (HH1 $1,769); with the 5-pt disregard PE's `medicaid` ceiling = 138% (`older_child` = 1.38). Coverage from ~134–255% FPL is separate CHIP (MFB-1055), not this calculator.
   - Screener fields: `birth_year`/`birth_month`, income streams, `household_size`
   - Source: KFMAM Appendix F-8 §A.1 ("113% / 113-133% Children age 6-18"); K.A.R. 129-6-72; 42 CFR 435.118

6. **Pregnant** — household MAGI ≤ **171% FPL**; the unborn child is counted in household size
   - Screener fields: `pregnant`, income streams, `household_size`
   - Source: KFMAM Appendix F-8 §A.1 (171% column); K.A.R. 129-6-71; 42 CFR 435.116

7. **Parent / caretaker relative** of a dependent child in the household — household MAGI ≤ **38% FPL** (F-8: HH1 $506, HH3 $866). Requires a dependent child present; a childless adult cannot qualify here.
   - Screener fields: `relationship` (child member present), income streams, `household_size`
   - Source: KFMAM Appendix F-8 §A.1 ("38%* Caretakers and Children"); K.A.R. 129-6-70; 42 CFR 435.110

8. **Aged 65+, blind, or disabled (ABD / SSI-related)** — countable income ≤ the **SSI federal benefit rate** ($994/mo individual, $1,491/mo couple). Screened on income + categorical status; the asset test is **not** screened (see note).
   - Screener fields: `birth_year`/`birth_month` (65+), `disabled` / `long_term_disability` / `visually_impaired`, income streams
   - ⚠️ **Asset test not screened (inclusive handling).** KanCare's ABD pathway has a $2,000 ind / $3,000 couple resource limit and PE does gate on it (a senior with $5,000 in `ssi_countable_resources` returns ineligible). MFB does **not** feed `household_assets` into PE's asset/SSI-resource check for this pathway; the limit is surfaced in the `description` instead. With no asset input, PE returns the income-eligible senior/ABD person eligible.
   - ⚠️ **Disability determination — inclusivity assumption + build mapping.** PE's ABD/disability eligibility keys off `is_ssi_disabled` (an SSA determination), computed as `meets_ssi_disability_criteria & ~ssi_engaged_in_sga` — not the generic `is_disabled`. The screener captures `disabled`/`long_term_disability` and SSDI receipt but can't make a formal SSA determination, so self-reported disability/SSDI signals are treated as meeting the criterion (mapped to `meets_ssi_disability_criteria` — see Implementation Notes) and the agency makes the official determination at application. Without this mapping, a disabled, under-65, not-yet-on-SSI applicant is wrongly excluded (non-expansion KS has no adult-expansion fallback).
   - For a low-income senior/ABD applicant, PE's binding pathway is the SSI-recipient route (FBR-based: countable income = income − $20 general exclusion, eligible up to ~$1,014/mo), not the lower 75%-FPL optional-senior pathway. PE's threshold slightly exceeds the KS $994 standard, so there is no under-inclusion gap at the $978–$994 income band.
   - Source: KFMAM Appendix F-8 §A.2 ("Presumptive Medicaid Disability: SI-Related… must not exceed the applicable SSI federal benefit rate") + §E Resource Standards ("SSI Medical $2,000 / $3,000"); K.A.R. 129-6-85 ("aged, blind, or disabled… based on social security administration criteria" — confirmed verbatim), 129-6-103, 129-6-106–110

9. **SSI recipient** — receiving SSI confers automatic Medicaid eligibility
   - Screener fields: income type `sSI`, or `current_benefits` (`screen.has_benefit("ssi")`). Do not use `receives_ssi` — that field exists only on the supplemental Energy Calculator, not the general screener.
   - Source: KanCare Eligibility ("Persons currently receiving SSI payments"); K.A.R. 129-6-85; 42 CFR 435.120 (KS is an SSI-criteria state, not 209(b); PE `ssi_recipient/is_covered` KS = true)

### Explicitly not eligible

10. **Childless, non-disabled, non-pregnant adults under 65** — no pathway at any income (Kansas declined ACA adult expansion, 42 CFR 435.119). This includes the 19–20 "young adult" category (`is_young_adult_for_medicaid`), which KS also sets to −∞.
    - Source: PE `adult/income_limit` and `young_adult/income_limit` KS = −∞; KanCare covered-groups list

### Data gaps (screener cannot verify)

11. **Medically needy / spend-down** ⚠️ *data gap* — someone over the income limit with high medical bills can still qualify by "spending down." Screener fields: none (doesn't collect monthly incurred medical expenses). Handling: surfaced in the `description` ("if your income is above the limit but you have high medical bills, you may still qualify through a 'spend-down'"); a spend-down expense field would be complex and invasive to screen.
    - Source: F-8's own current standard for this pathway is SSI-FBR-aligned ($994/$1,491); PE's parameter is a stale 2018 load ($475) — tracked as PE #8361, bypassed here since the screener never feeds this input

12. **Foster care (current + former foster youth to age 26)** ⚠️ *data gap* — both are mandatory federal categories where income is irrelevant, but in non-expansion KS they currently fall through as "childless adults." Screener fields: none. Handling: proposed screener field `foster_care` (Step 5, "In foster care now or in the past" — one yes/no; the engine derives current-foster-child and former-foster-youth-to-26 from it, using existing `birth_year`) plus near-term `description` surfacing.

13. **Adoption-assistance children** ⚠️ *data gap* — a mandatory federal IV-E category named on the KanCare eligibility page alongside foster children; most also qualify via the income-based child pathways (criteria 3–5), so the false-negative risk is smaller. Screener fields: none. Handling: fold into the proposed `foster_care` field (widen wording to "In foster care, formerly in foster care, or receiving adoption support") plus `description` surfacing.

14. **12-month postpartum extension** ⚠️ *data gap* — the screener's `pregnant` field only captures *currently* pregnant; a recently-postpartum applicant can fall through. Screener fields: `pregnant` only. Handling: `description` surfacing ("there are other ways to qualify too — apply if you're unsure"); a dedicated field would add intake friction for a narrow window.

15. **Early Detection Works (breast/cervical cancer), TB-inpatient** ⚠️ *data gap* — diagnosis-specific, tiny populations. Screener fields: none. Handling: covered by a generic catch-all line in the `description` rather than named individually (naming them would alarm/clutter for almost no one).

**Out of scope, not data gaps:** Working Healthy disabled buy-in (MFB-1066) and HCBS/long-term care (MFB-1072) are separate tickets.

## Priority Criteria

None. KanCare Medicaid has no priority/waitlist tiers — eligibility is categorical and entitlement-based.

## Benefit Value

**Shape:** Insurance coverage (non-cash). Value = monthly dollar amount per Medicaid category (`medicaid_categories` table, ×12 for the annual figure the calculator returns), following the MFB insurance method (program spend ÷ beneficiaries, by eligibility group) and matching the WA Apple Health precedent. **Eligibility is determined by PolicyEngine; the value table is MFB-set and independent of PE's `medicaid_cost`.**

KS values are derived from FY2023 KS per-enrollee Medicaid & CHIP spending by group (KHI / Kansas Action for Children, confirmed verbatim via kac.org): *"annual Medicaid and CHIP spending averaged $3,644 per pregnant woman, child, or family member, compared to $32,459 per enrollee with a disability and $20,511 per enrollee age 65 and older."* Annual ÷ 12:

| Category | KS monthly value | KS annual value |
|---|---|---|
| INFANT / YOUNG_CHILD / OLDER_CHILD / PREGNANT / PARENT / ADULT / YOUNG_ADULT | $304 | $3,648 |
| AGED | $1,709 | $20,508 |
| DISABLED / SSI_RECIPIENT | $2,705 | $32,460 |
| NONE | $0 | $0 |

KS publishes a single combined MAGI per-enrollee figure ($3,644), so $304/mo applies uniformly across MAGI categories (unlike WA's finer child/adult split). This is an estimate; exact per-household value is returned by the calculator. `value_format: estimated_annual`.

**Edge case:** a person who is both 65+ and disabled gets the **DISABLED** value ($32,460), since MFB's calc checks `is_disabled` before `is_senior` — see Scenario 19.

AGED vs. DISABLED is decided from the screener's own `is_senior`/`is_disabled` flags, not from PE's `medicaid_category` enum. Confirmed via the live PE run: for every ABD-pathway scenario (7, 8, 9, 16, 17, 19), PE's `medicaid_category` returns `SSI_RECIPIENT` uniformly and does not distinguish AGED from DISABLED. The value tier comes from MFB's own age/disability logic, not PE's category enum.

Source: KHI / Kansas Action for Children, FY2023 KS Medicaid & CHIP per-enrollee spending — https://www.khi.org/articles/2024-kansas-medicaid-a-primer/ ; https://www.kac.org/budget_summary_medicaid

## Implementation Notes

The KS subclass requires four `pe_inputs`/registry changes. These are committed implementation steps.

1. **Add a disability→SSI-criterion dependency.** On production PE, `is_ssi_disabled = meets_ssi_disability_criteria & ~ssi_engaged_in_sga`, where `meets_ssi_disability_criteria` is a pure input (defaults False); `is_disabled` does not feed it. Add a dependency mapping the screener's `disabled`/`long_term_disability`/SSDI signals → **`meets_ssi_disability_criteria`** (not by overriding `is_ssi_disabled` directly, so the SGA test still applies — see Scenario 15). Also map `visually_impaired` → PE's **`is_blind`** input (also a pure input, defaults False) — K.A.R. 129-6-85 covers *blind* as a qualifying status distinct from disabled, and `is_blind=True` exempts from SGA entirely (`ssi_engaged_in_sga = (earned_income > $1,690/mo) & ~is_blind`; 20 CFR 416.971). See Scenario 16.
2. **Do not send assets for the ABD pathway.** Drop `SsiCountableResourcesDependency` (→ `ssi_countable_resources`, from `household_assets`) from the KS `pe_inputs`. The $2,000/$3,000 limit is surfaced in the `description` instead. SSI-recipient and medically-needy pathways still reference resources, but neither is the deciding pathway here.
3. **Add `ks_medicaid` to `STATE_MEDICAID_OPTIONS`** in `benefits-api/programs/programs/helpers.py` (currently `("co_medicaid", "nc_medicaid", "il_medicaid")`). The `medicaid_eligible()` helper gates ~15 programs on calculated Medicaid eligibility — without KS, this program won't exclude Medicaid-eligible Kansans from the KS ACA Premium Tax Credit (MFB-1052) or feed KS Medicaid sub-pathways.
4. **Register the `ks` `white_label` enum** in the test-case schema — shared KS-launch infrastructure across all KS tickets, not specific to this one.

**`show_in_has_benefits_step` = false:** Medicaid conferral runs off the calculated `medicaid_eligible()` helper, and "already enrolled" is detected via the Step 8 insurance question — not the Has-Benefits step.

**MFB-layer branches (not PolicyEngine):**
- **Already-enrolled suppression** (Scenario 12). PE Medicaid eligibility takes no insurance/enrollment input. MFB suppresses an already-enrolled household at the display layer via the Step 8 insurance answer / `current_benefits`.
- **No separate unborn enrollee** (Scenario 13). PE models pregnancy via `is_pregnant` on the mother with no separate-unborn entity. MFB enforces "no separate unborn enrollee" in household construction.
- **Immigration / citizenship.** MFB does not send `immigration_status` to PE; eligibility by status is enforced by the config's `legal_status_required` (criterion 2).

## Implementation Coverage

- ✅ Evaluable by the screener/PE: 8 (residency, infant, young child, older child, pregnant, parent/caretaker, ABD, SSI recipient)
- ✅ Handled outside the eligibility calc: 1 (citizenship/immigration → `legal_status_required`)
- ⚠️ True data gaps: 5 (medically needy/spend-down, foster care, adoption-assistance, postpartum extension, Early Detection Works/TB) — each has a concrete disposition (inclusivity assumption, proposed screener field, or description surfacing); none silent

## Acceptance Criteria

All 23 scenarios run through PolicyEngine (confirmed live 2026-07-06, `policyengine-us` 1.755.5): **37/37 person-level assertions matched expectation.**

- [ ] Scenario 1 (Pregnant, low income): **eligible**, $3,648/yr
- [ ] Scenario 2 (Pregnant, near 171% boundary): **eligible**, $3,648/yr
- [ ] Scenario 3 (Parent + 2 children, very low income, on SNAP): **all eligible**, $3,648/yr each
- [ ] Scenario 4 (Parent just over 38%): children **eligible** ($3,648/yr each), parent **ineligible**
- [ ] Scenario 5 (Single childless adult): **ineligible** (non-expansion)
- [ ] Scenario 6 (Childless adult age 64): **ineligible** (not yet 65)
- [ ] Scenario 7 (Senior 65+, assets above limit): **eligible**, $20,508/yr (asset test not screened)
- [ ] Scenario 8 (Disabled adult on SSDI): **eligible**, $32,460/yr (depends on Implementation Note 1)
- [ ] Scenario 9 (SSI recipient): **eligible**, $32,460/yr
- [ ] Scenario 10 (Infant, parents over limit): infant **eligible** ($3,648/yr), parents **ineligible**
- [ ] Scenario 11 (School-age child, parent over limit): child **eligible** ($3,648/yr), parent **ineligible**
- [ ] Scenario 12 (Already enrolled): PE-eligible but **suppressed** at display layer (MFB dedup)
- [ ] Scenario 13 (Future birth date / unborn as separate person): mother **eligible**, $3,648/yr (PREGNANT); no separate unborn enrollee (MFB household-construction rule)
- [ ] Scenario 14 (Young adult age 20, childless): **ineligible** (`young_adult` category, KS −∞)
- [ ] Scenario 15 (Disabled, earnings above SGA): **ineligible** (SGA gate)
- [ ] Scenario 16 (Legally blind, under 65): **eligible**, $32,460/yr (depends on Implementation Note 1 blind mapping)
- [ ] Scenario 17 (Long-term disability only, no SSDI): **eligible**, $32,460/yr (depends on Implementation Note 1)
- [ ] Scenario 18 (Aged, income above SSI FBR): **ineligible** (ABD income ceiling)
- [ ] Scenario 19 (Aged AND disabled): **eligible**, $32,460/yr (DISABLED value takes priority over AGED)
- [ ] Scenario 20 (Pregnant above 171% FPL): **ineligible**
- [ ] Scenario 21 (Parent + young child, income above child limits): both **ineligible**
- [ ] Scenario 22 (Parent + infant, income above infant's own 171% ceiling): both **ineligible**
- [ ] Scenario 23 (Parent + older child, income above older-child's own 138% ceiling): both **ineligible**

## Test Scenarios

Expected values use the Benefit Value table above (annual figures). ZIP/county pairs: 66603/66604/66044/66502 = Shawnee/Shawnee/Douglas/Riley; 67202 = Sedgwick; 66102 = Wyandotte.

Scenarios 7, 8, 16, and 17 are eligible because of the KS calculator's committed input handling (Implementation Notes 1–2: omitting `household_assets` from the ABD asset check, and mapping disability/SSDI/long-term-disability/blindness signals to `meets_ssi_disability_criteria`/`is_blind`). With the federal `pe_inputs` inherited unchanged, all four would return ineligible. This is intentional KS input handling, not a PolicyEngine defect.

### Scenario 1: Pregnant woman, low income
**What we're checking**: Golden-path pregnancy eligibility (criterion 6), well under the 171% FPL threshold.
**Expected**: Eligible · $3,648/yr (PREGNANT)

**Steps**:
- **Location**: ZIP `66603`, county `Shawnee`
- **Household**: 1 person (MAGI size 2 — unborn counted)
- **Person 1**: Head of Household, born `March 1991` (age 35), female, US citizen, pregnant: yes, employment income `$1,200`/mo, insurance: none

**Why this matters**: The primary regression test for the pregnancy pathway. 171% FPL HH2 = $3,084/mo; $1,200 is well under.

---

### Scenario 2: Pregnant woman near the 171% boundary
**What we're checking**: Pregnancy eligibility just under the FPL ceiling (criterion 6 boundary).
**Expected**: Eligible · $3,648/yr (PREGNANT)

**Steps**:
- **Location**: ZIP `66502`, county `Riley`
- **Household**: 1 person (MAGI size 2)
- **Person 1**: Head of Household, born `September 1996` (age 29), female, US citizen, pregnant: yes, employment income `$2,900`/mo, insurance: none

**Why this matters**: $2,900 is just under the $3,084/mo (171% FPL HH2) ceiling — tests the upper boundary from the eligible side.

---

### Scenario 3: Parent + 2 children, very low income, on SNAP
**What we're checking**: All three household members qualify under separate pathways simultaneously (parent/caretaker + two child age bands), and SNAP receipt doesn't exclude Medicaid.
**Expected**: All eligible · $3,648/yr each (PARENT, OLDER_CHILD, YOUNG_CHILD)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 3 people
- **Person 1**: Head of Household, born `September 1991` (age 34), female, US citizen, not pregnant/disabled, employment income `$620`/mo, insurance: none, current benefits: SNAP
- **Person 2**: Child, born `March 2018` (age 8), no income
- **Person 3**: Child, born `November 2020` (age 5), no income

**Why this matters**: $620 is under the 38% FPL HH3 limit ($866) for the parent; both kids are well under their respective limits. Confirms SNAP receipt has no bearing on PE Medicaid eligibility.

---

### Scenario 4: Parent just over 38% — children eligible, parent not
**What we're checking**: Per-member independence — a parent over the caretaker income limit doesn't disqualify their children from the child MAGI pathways.
**Expected**: Children eligible ($3,648/yr each); parent ineligible ($0)

**Steps**:
- **Location**: ZIP `66502`, county `Riley`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1991` (age 35), female, US citizen, not pregnant/disabled, employment income `$900`/mo, insurance: none
- **Person 2**: Child, born `January 2018` (age 8), no income
- **Person 3**: Child, born `September 2020` (age 5), no income

**Why this matters**: $900 exceeds the 38% FPL HH3 limit ($866) for the parent, but both kids are far under their own limits — tests that eligibility is evaluated per person, not per household.

---

### Scenario 5: Single childless adult, low income — ineligible
**What we're checking**: Non-expansion Kansas has no pathway for childless, non-disabled, non-pregnant adults under 65 at any income (criterion 10).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `February 1981` (age 45), male, US citizen, not pregnant/disabled, no dependent children, employment income `$350`/mo, insurance: none

**Why this matters**: Confirms PE `adult/income_limit` = −∞ for KS regardless of how low income is.

---

### Scenario 6: Childless adult age 64 — ineligible
**What we're checking**: A person just under 65 has no ABD pathway (requires 65+ or disability) and no adult-expansion pathway either (criterion 10).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `December 1961` (age 64), male, US citizen, not disabled, employment income `$250`/mo, insurance: none

**Why this matters**: Distinguishes "not yet 65" from the ABD age trigger — pairs with Scenario 7 (age 66, eligible). The birth month is intentionally late in the year (December) so the applicant is unambiguously age 64 on any run date; a birth month equal to the current month would resolve to age 65 under the platform's month-only age arithmetic and wrongly qualify under the AGED pathway.

---

### Scenario 7: Senior 65+, low income, assets above the $2,000 limit
**What we're checking**: The ABD asset test is intentionally not screened (Implementation Note 2) — a senior with assets over KanCare's limit should still be eligible.
**Expected**: Eligible · $20,508/yr (AGED)

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick`
- **Household**: 1 person
- **Person 1**: Head of Household, born `April 1960` (age 66), male, US citizen, not disabled, Social Security income `$900`/mo, `household_assets`: `$5,000`, insurance: none

**Why this matters**: Income qualifies ($900 < $994 SSI FBR); the $5,000 is over KanCare's $2,000 ABD asset limit, but MFB doesn't asset-gate — confirms the inclusive-handling decision (PE returns ineligible if `ssi_countable_resources` is sent; MFB's calc omits that input).

---

### Scenario 8: Disabled adult on SSDI, low income
**What we're checking**: The ABD disability pathway via the disability/SSDI → `meets_ssi_disability_criteria` mapping (Implementation Note 1).
**Expected**: Eligible · $32,460/yr (DISABLED)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `May 1976` (age 50), male, US citizen, disabled: yes, receives SSDI, SSDI income `$800`/mo, insurance: none

**Why this matters**: This outcome depends on Implementation Note 1 — without the disability→`meets_ssi_disability_criteria` mapping, PE returns this person ineligible. Contrast with Scenario 15 (same profile, earnings above SGA → ineligible).

---

### Scenario 9: SSI recipient
**What we're checking**: SSI receipt confers automatic Medicaid eligibility (criterion 9).
**Expected**: Eligible · $32,460/yr (DISABLED/SSI_RECIPIENT)

**Steps**:
- **Location**: ZIP `66102`, county `Wyandotte`
- **Household**: 1 person
- **Person 1**: Head of Household, born `June 1985` (age 40), female, US citizen, disabled: yes, SSI income `$943`/mo, `household_assets`: `$1,000`, insurance: none

**Why this matters**: Confirms the SSI-recipient auto-eligibility pathway independent of the ABD income/asset tests.

---

### Scenario 10: Infant under 1 — child eligible, parents not
**What we're checking**: Per-member independence in a 3-person household — an infant qualifies under the higher infant threshold while both parents exceed the parent/caretaker limit.
**Expected**: Infant eligible ($3,648/yr, INFANT); parents ineligible ($0)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 3 people
- **Person 1**: Head of Household, born `March 1994` (age 32), female, US citizen, not pregnant, employment income `$1,800`/mo, insurance: none
- **Person 2**: Spouse, born `May 1993` (age 33), male, employment income `$800`/mo, insurance: none
- **Person 3**: Child, born `May 2026` (age 0, newborn), no income

**Why this matters**: The combined parental income ($2,600/mo) is well under the infant's own 171% HH3 threshold ($3,894), so the infant qualifies regardless of the parents' income; the parents themselves exceed the 38% HH3 caretaker limit ($866).

---

### Scenario 11: School-age child eligible, parent not
**What we're checking**: A 2-person household where the child qualifies under the older-child threshold while the parent (with employer insurance) exceeds the caretaker limit.
**Expected**: Child eligible ($3,648/yr, OLDER_CHILD); parent ineligible ($0)

**Steps**:
- **Location**: ZIP `66044`, county `Douglas`
- **Household**: 2 people
- **Person 1**: Head of Household, born `March 1985` (age 41), female, US citizen, not pregnant/disabled, employment income `$1,600`/mo, insurance: employer
- **Person 2**: Child, born `September 2014` (age 11), no income, insurance: none

**Why this matters**: Older-child 138% HH2 (≈$2,490) is above the child's own income; parent exceeds 38% HH2 ($685) and separately has employer insurance.

---

### Scenario 12: Already enrolled in KanCare — suppressed at display layer
**What we're checking**: PE has no insurance/enrollment input, so "already enrolled" must be handled MFB-side (Implementation Notes, MFB-layer branches).
**Expected**: PE returns eligible (PREGNANT, $3,648/yr if shown) — but MFB suppresses the result because the household is already enrolled

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `September 1991` (age 34), female, US citizen, pregnant: yes, employment income `$400`/mo, insurance: Medicaid, current benefits: Medicaid/KanCare

**Why this matters**: Confirms the dedup rule lives in MFB's display layer (Step 8 insurance / `current_benefits`), not in PE — implement the suppression, don't try to make PE itself return ineligible.

---

### Scenario 13: Future birth date (unborn as separate person) — ineligible as a distinct enrollee
**What we're checking**: PE models pregnancy via `is_pregnant` on the mother with no separate unborn entity — "no separate unborn enrollee" must be an MFB household-construction rule.
**Expected**: Mother eligible · $3,648/yr (PREGNANT); the unborn is **not** a separate PE person / enrollee

**Steps**:
- **Location**: ZIP `66603`, county `Shawnee`
- **Household**: 2 people
- **Person 1**: Head of Household, born `March 1996` (age 30), female, US citizen, pregnant: yes, employment income `$400`/mo, insurance: none
- **Person 2**: Child, born `December 2026` (future / unborn)

**Why this matters**: Run the mother through PE (she's eligible); enforce the no-separate-unborn-person rule in MFB household construction, not PE.

---

### Scenario 14: Young adult age 20, childless, low income — ineligible
**What we're checking**: The distinct 19–20 `young_adult` category, which KS also sets to −∞ (criterion 10) — confirms this branch returns ineligible, not just adults 21+.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `May 2006` (age 20), male, US citizen, not disabled/pregnant, no children, employment income `$300`/mo, insurance: none

**Why this matters**: Covers the 19–20 young-adult category so it isn't mistaken for an omission alongside the general adult-expansion exclusion.

---

### Scenario 15: Disabled adult, earnings above SGA — ineligible edge case
**What we're checking**: The disability mapping (Implementation Note 1) doesn't make every disabled applicant eligible — the SGA earnings test still applies.
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `May 1976` (age 50), male, US citizen, disabled: yes, employment income `$2,000`/mo (earned, above the $1,690/mo SGA threshold), insurance: none

**Why this matters**: PE's `is_ssi_disabled = meets_ssi_disability_criteria & ~ssi_engaged_in_sga` — earnings above SGA flip `ssi_engaged_in_sga` true → `is_ssi_disabled` false → no ABD pathway, and the person is over every MAGI limit. Contrast with Scenario 8 (unearned SSDI income, no SGA test).

---

### Scenario 16: Legally blind, under 65, income under FBR
**What we're checking**: The ABD blind pathway via the `visually_impaired` → `is_blind` mapping (Implementation Note 1).
**Expected**: Eligible · $32,460/yr (DISABLED)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `August 1975` (age 50), female, US citizen, visually impaired: yes, disabled: no, employment income `$500`/mo, insurance: none

**Why this matters**: K.A.R. 129-6-85 treats blindness as a qualifying status distinct from disability. Without the `visually_impaired` → `is_blind` mapping, this person returns ineligible despite qualifying under KS law. SGA doesn't apply to blind individuals for the disability-route computation, but this is moot in practice: the $994 FBR income ceiling binds before the $1,690 SGA threshold would, so no blind person earning above SGA would pass the income test regardless.

---

### Scenario 17: Long-term disability only (no `disabled` flag, no SSDI)
**What we're checking**: The disability mapping must cover `long_term_disability` independently of the `disabled` flag and SSDI receipt (Implementation Note 1).
**Expected**: Eligible · $32,460/yr (DISABLED)

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person
- **Person 1**: Head of Household, born `March 1970` (age 56), male, US citizen, long-term disability: yes, disabled: no, no SSDI income, employment income `$600`/mo, insurance: none

**Why this matters**: A partial implementation that only maps the `disabled` flag and SSDI receipt — but not `long_term_disability` — would incorrectly return this person ineligible.

---

### Scenario 18: Aged, income above the SSI FBR — ineligible
**What we're checking**: The ABD income ceiling from the over-income side (complements Scenarios 7 and 8, which test under-income).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick`
- **Household**: 1 person
- **Person 1**: Head of Household, born `January 1958` (age 68), male, US citizen, not disabled, Social Security income `$1,100`/mo, insurance: none

**Why this matters**: Countable income = $1,100 − $20 general unearned-income exclusion = $1,080 > $994 SSI FBR → fails the ABD income test, with no MAGI pathway available (non-expansion, no dependents, not pregnant).

---

### Scenario 19: Aged and disabled — DISABLED value, not AGED
**What we're checking**: A person qualifying under both the AGED and DISABLED pathways gets the DISABLED value — MFB's value logic checks `is_disabled` before `is_senior`.
**Expected**: Eligible · $32,460/yr (DISABLED, not the $20,508 AGED value)

**Steps**:
- **Location**: ZIP `67202`, county `Sedgwick`
- **Household**: 1 person
- **Person 1**: Head of Household, born `April 1958` (age 68), male, US citizen, disabled: yes, Social Security retirement `$500`/mo + SSDI `$300`/mo (total `$800`/mo), insurance: none

**Why this matters**: Countable income = $800 − $20 = $780 < $994 SSI FBR. Confirms the value-priority rule documented in the Benefit Value section's edge case — a $12,000/yr difference depending on which pathway MFB's value logic picks.

---

### Scenario 20: Pregnant woman above 171% FPL — ineligible
**What we're checking**: The upper-income bound of the pregnant pathway (complements Scenarios 1 and 2).
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 1 person (MAGI size 2)
- **Person 1**: Head of Household, born `March 1998` (age 28), female, US citizen, pregnant: yes, employment income `$3,500`/mo, insurance: none

**Why this matters**: 171% FPL HH2 = $3,084/mo; $3,500 exceeds it and no other pathway applies (not disabled, no children, non-expansion KS).

---

### Scenario 21: Parent + young child, income above child limits — both ineligible
**What we're checking**: All four child/parent MAGI pathways correctly gate on income from the ineligible side in one household.
**Expected**: Both not eligible

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 2 people
- **Person 1**: Head of Household, born `September 1990` (age 34), female, US citizen, not pregnant/disabled, employment income `$3,500`/mo, insurance: none
- **Person 2**: Child, born `January 2022` (age 4), no income

**Why this matters**: Young child (1–5) 154% HH2 = $2,777/mo and parent 38% HH2 = $685/mo are both far below $3,500 — income also exceeds the 171% HH2 ($3,084) and 138% HH2 ($2,490) thresholds, so an infant or older child in this household would likewise be ineligible.

---

### Scenario 22: Parent + infant, income above the infant's own 171% ceiling — both ineligible
**What we're checking**: The infant pathway's own ceiling (`infant` = 1.71, a distinct PE parameter from `pregnant`) gated from the ineligible side — not yet exercised by any other scenario.
**Expected**: Both not eligible

**Steps**:
- **Location**: ZIP `66604`, county `Shawnee`
- **Household**: 2 people
- **Person 1**: Head of Household, born `January 1991` (age 35), female, US citizen, not pregnant/disabled, employment income `$3,500`/mo, insurance: none
- **Person 2**: Child, born `April 2026` (age 0, infant), no income

**Why this matters**: Infant 171% HH2 = $3,084/mo and parent 38% HH2 = $685/mo are both far below $3,500. Scenario 21 proves the same income fails the young-child (1.54) and parent (0.38) parameters; this scenario proves it independently against the `infant` (1.71) parameter specifically, since a typo'd infant ratio wouldn't be caught by any other scenario.

---

### Scenario 23: Parent + older child, income above the older child's own 138% ceiling — both ineligible
**What we're checking**: The older-child pathway's own ceiling (`older_child` = 1.38, a distinct PE parameter) gated from the ineligible side — not yet exercised by any other scenario.
**Expected**: Both not eligible

**Steps**:
- **Location**: ZIP `66044`, county `Douglas`
- **Household**: 2 people
- **Person 1**: Head of Household, born `March 1985` (age 41), female, US citizen, not pregnant/disabled, employment income `$2,600`/mo, insurance: none
- **Person 2**: Child, born `September 2014` (age 11), no income

**Why this matters**: Older-child 138% HH2 (≈$2,490) and parent 38% HH2 ($685) are both below $2,600. Scenario 11 proves the older-child pathway works on the eligible side; this scenario proves the `older_child` (1.38) parameter specifically fails correctly above its own ceiling, distinct from the young-child (1.54) and infant (1.71) parameters tested elsewhere.

---

Every scenario field (age, `is_pregnant`, income streams, `is_disabled`/`meets_ssi_disability_criteria`, `is_blind`/`visually_impaired`, `ssi`, `ssi_countable_resources`, state) maps to a real PE input. Confirmed via the live PE run, not assumed: SNAP receipt (Scenario 3) and employer insurance (Scenario 11) do not affect PE Medicaid eligibility. Scenarios 1–11 and 14–23 are the PE-computed eligibility-threshold set; Scenarios 12–13 are MFB display/household-construction rules (see Implementation Notes).

## Research Sources

### Kansas program sources
- KanCare Eligibility — https://www.kancare.ks.gov/apply-now/eligibility
- KFMAM Appendix F-8, "Kansas Medical Assistance Standards" (Rev 04-26) — via https://www.kancare.ks.gov/data-policy/policy/eligibility/manuals; PDF confirmed directly 2026-07-05, every cited dollar figure matches verbatim
- KFMAM manual — https://khap.kdhe.ks.gov/kfmam/main.asp
- K.A.R. Agency 129, Article 6 — https://rules.ks.gov/ (§129-6-70/71/72/85/103/106–110); full operative text for §129-6-55 and §129-6-85 confirmed via https://www.law.cornell.edu/regulations/kansas

### Federal regulation & statute
- 42 CFR 435.110 (parents/caretakers), 435.116 (pregnant women), 435.118 (infants/children under 19), 435.119 (age 19–64 expansion group, declined by KS), 435.120 (SSI recipients), 435.403 (state residence) — https://www.law.cornell.edu/cfr/text/42/
- 8 U.S.C. §1613 (5-year bar)
- 2026 HHS/ASPE Federal Poverty Guidelines — https://www.aspe.hhs.gov/sites/default/files/documents/b1bfa16b20ae9b89d525bc35de7c1643/detailed-guidelines-2026.pdf

### Benefit value source
- KHI / Kansas Action for Children, FY2023 KS Medicaid & CHIP per-enrollee spending — https://www.khi.org/articles/2024-kansas-medicaid-a-primer/ ; https://www.kac.org/budget_summary_medicaid

### PolicyEngine verification
- `policyengine-us` 1.755.5 — live run 2026-07-06, all 23 scenarios / 37 person-level assertions matched (Scenarios 22–23 added this pass to close infant/older-child upper-bound coverage). Formulas confirmed directly from source: `is_ssi_disabled`, `is_ssi_aged_blind_disabled`, `ssi_engaged_in_sga`, `is_blind`, `meets_ssi_disability_criteria`; parameters confirmed: KS category ratios (`gov/hhs/medicaid/eligibility/categories/*/income_limit.yaml`), SSI FBR (`gov/ssa/ssi/amount/*.yaml`), SGA threshold (`gov/ssa/sga/non_blind.yaml`)
