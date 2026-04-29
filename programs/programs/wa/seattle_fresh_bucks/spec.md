# Implement Seattle Fresh Bucks (WA) Program

## Program Details

- **Program**: Seattle Fresh Bucks
- **State**: WA
- **White Label**: wa
- **Research Date**: 2026-04-29

Seattle Fresh Bucks is a city-administered healthy-food assistance program funded by Seattle's Sweetened Beverage Tax Fund and the General Fund, and operated by the Seattle Office of Sustainability & Environment. Enrolled households receive a monthly benefit (loaded onto a Fresh Bucks card / Healthy Benefits+ app) that can be redeemed for fruits and vegetables at participating Seattle farmers markets, independent grocers, and supermarkets.

> **Note on enrollment model**: Fresh Bucks is currently a **waitlist** program with budget-limited enrollment. Eligible applicants are added to the waitlist and selected via a randomized lottery (with priority weighting — see Criterion #6 below). Eligibility for the screener's purposes means the household *qualifies to apply* and would be considered in the next lottery round, not that benefits are guaranteed in any given month.

## Eligibility Criteria

> **How to read this list**: Criteria #1–#3 are the **hard eligibility gates** that the screener can evaluate against current fields. Criteria #4–#9 are documented **data gaps** — either application-stage requirements the screener does not need to verify, or selection-process priority weights that affect lottery odds rather than eligibility.

### Hard eligibility gates (all must be met)

1. **Household income at or below 80% of King County Area Median Income (AMI), banded by household size**
   - Screener fields: `household_size`, income via `calc_gross_income`
   - Note: Fresh Bucks publishes a per-household-size income table on the official application page. The figures below are **HUD FY2025 80% AMI limits for the Seattle-Bellevue HMFA** — they match the Seattle Housing Authority's "April 2025" 80% AMI table byte-for-byte. As of this research date, the Fresh Bucks application page is still republishing the FY2025 figures; HUD's FY2026 income limits typically release in mid-April and the page will need to be re-checked once that update propagates. **The implementation calculator should not hard-code this table** — see "Implementation Notes for the Follow-Up PR" below for the `hud_client.get_screen_il_ami(...)` recommendation.

     | Household size | Annual income | Monthly income |
     | --- | --- | --- |
     | 1 | $84,850 | $7,070 |
     | 2 | $96,950 | $8,079 |
     | 3 | $109,050 | $9,087 |
     | 4 | $121,150 | $10,095 |
     | 5 | $130,850 | $10,904 |
     | 6 | $140,550 | $11,712 |
     | 7 | $150,250 | $12,520 |
     | 8 | $159,950 | $13,329 |
     | 9 | $169,650 | $14,137 |
     | 10+ | $179,350 | $14,945 |

   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) — "Program Eligibility" section + AMI table. The seattle.gov page describes the threshold as "≤ 80% of the Area Median Income (AMI)", which matches HUD's published 80% AMI limits for the Seattle-Bellevue HMFA.

2. **Applicant must reside within Seattle city limits**
   - Screener fields: `zipcode`, `county`
   - Note: The program enforces this via an exact-address lookup tool (see Criterion #5 — data gap). For screener purposes, a Seattle ZIP + King County is treated as a *likely-eligible* signal; some Seattle ZIPs (e.g. 98122, 98178, 98146) span the city boundary, so a percentage of "Seattle ZIP" households are technically outside the city limits and would be denied at application stage.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) — "Seattle households that meet the income requirements and live within city limits qualify for Fresh Bucks."

3. **Household must not already be enrolled in Fresh Bucks (one benefit per household)**
   - Screener fields: *(no direct field — see Criterion #7 data gap below)*
   - Note: The program enforces a strict one-benefit-per-household cap. Because the screener has no `has_seattle_fresh_bucks` (or equivalent) field on `Screen` and no `has_benefit("seattle_fresh_bucks")` mapping, the screener cannot filter out current enrollees. Recommendation for the implementation PR: add a `has_seattle_fresh_bucks` boolean field to `Screen` (or a more general `has_freshbucks`) and wire it into `Screen._build_benefit_map()` so the calculator can call `screen.has_benefit("seattle_fresh_bucks")` consistently with the SSI / SNAP duplicate-enrollment pattern. Until then, this criterion is **not enforced** by the screener and is surfaced to the user in the program description / application instructions.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) FAQ — "Benefits are limited to one per household. If someone in your household is already enrolled, additional applications will not be accepted."
   - Impact: Medium

### Data gaps and application-stage requirements

4. **Date of birth (application requirement, not an eligibility test)** ⚠️ *data gap*
   - Screener fields: `household_member.age`, `household_member.birth_year_month` (approximations only)
   - Note: The application form requires a full date of birth, but the program publishes no minimum or maximum age for eligibility. The screener's age / birth_year_month fields are sufficient to render the program in results; the exact DOB is collected only at application submission.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) — "What You Need to Submit Your Application: Your date of birth."
   - Impact: Low

5. **Exact street address verification within Seattle city limits** ⚠️ *data gap*
   - Screener fields: `zipcode`, `county` (approximation only)
   - Note: The program uses an address-based [Seattle City Council district lookup tool](https://www.seattle.gov/council/meet-the-council/find-your-district-and-councilmembers) to confirm city-limit residency. The screener collects ZIP + county but not a street address. Several King County ZIPs straddle the Seattle border (e.g. 98146, 98166, 98178) — applicants in those ZIPs may be screened in here but denied at the application stage if their address falls outside city limits. Treat the screener's residency check (Criterion #2) as a *likely-eligible* signal, not a definitive pre-filter.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) — "Use this tool to see if you live within the city limits."
   - Impact: Medium

6. **Lottery priority — "Lowest household income"** ⚠️ *data gap (priority weight, not eligibility)*
   - Screener fields: `household_size`, `calc_gross_income` (relative ranking not computable from a single-applicant context)
   - Note: This is a lottery-weighting factor — households in the lowest income tier receive an additional entry in the random selection process. The program does not publish the threshold for "lowest income category" (it is a relative ranking against the current waitlist), so the screener cannot evaluate this. It does not affect eligibility, only odds of being selected once enrolled on the waitlist.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) "How Enrollment Works".
   - Impact: Low

7. **Lottery priority — "Non-English language preference"** ⚠️ *data gap (priority weight, not eligibility)*
   - Screener fields: `request_language_code` (rough proxy only — captures *interface* language, not "primarily spoken at home")
   - Note: Households where a language other than English is primarily spoken receive an additional lottery entry. The screener's `request_language_code` indicates the language the user *chose for the screener interface*, which is a noisy proxy for "primarily spoken at home." Surfacing this as a priority signal would over- or under-count depending on the user's circumstances. As with #6, this is a lottery weight, not an eligibility gate.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) "How Enrollment Works".
   - Impact: Low

8. **Lottery priority — "Waitlist duration"** ⚠️ *data gap (priority weight, not eligibility)*
   - Note: Households that remain on the waitlist after the first enrollment period receive an additional entry in subsequent selection processes. This is a program-internal administrative criterion based on time on the waitlist; it cannot be evaluated at the screening stage and depends entirely on future program operations.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) "How Enrollment Works".
   - Impact: Low

9. **No citizenship or immigration-status requirement is stated by the program**
   - Note: Neither the seattle.gov program page nor the Fresh Bucks application FAQ lists a citizenship, SSN, or qualified-noncitizen requirement. The application asks only for household size, income, address, and DOB. We therefore set the program's `legal_status_required` to all 6 base values (`citizen`, `non_citizen`, `gc_5plus`, `gc_5less`, `refugee`, `otherWithWorkPermission`) per the canonical reviewer guide's "no restriction → include all 6" rule, so the post-results citizenship chip does not erroneously filter the program out for any user.
   - Source: [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) — application requirements section.

## Implementation Coverage

- ✅ Evaluable eligibility criteria: 2 of 3 (income test #1, residency approximation #2)
- ⚠️  Partially evaluable: 1 (residency — ZIP/county only; exact-address verification at application stage)
- ❌ Not evaluable in current screener: 1 (duplicate enrollment #3 — needs a new `has_seattle_fresh_bucks` field on `Screen`)
- ⚠️  Application-stage / lottery-weight criteria: 5 (DOB, address, lowest-income priority, language priority, waitlist duration)

The income test (Criterion #1) is fully computable from `household_size` and the screener's gross-income calculation, and is the dominant eligibility gate. The geographic test (Criterion #2) is computable to within ZIP-level precision and will correctly screen *out* most non-Seattle WA residents while letting Seattle ZIPs through. The duplicate-enrollment criterion (#3) is the only meaningful gap that should be addressed before the program is shown to users; the implementation PR should add a `has_seattle_fresh_bucks` field on `Screen` and a `_build_benefit_map` entry so existing enrollees are not redundantly recommended.

## Benefit Value

| Field | Value |
| --- | --- |
| Monthly benefit (per household) | **$60** |
| Annualized benefit (per household) | **$720** |

- Source: [seattle.gov — Fresh Bucks](https://www.seattle.gov/environment/food-policy-and-programs/fresh-bucks): "Eligible and enrolled customers receive **$60 each month**" and "**$720 average annual savings**".
- The benefit is a flat per-household amount and **does not vary by household size**.
- ⚠️ **Source discrepancy to verify**: The FAQ on [seattlefreshbucks.org/apply/](https://www.seattlefreshbucks.org/apply/) currently states "$40/month in Fresh Bucks benefits", which conflicts with the seattle.gov page's "$60 each month" and "$720 average annual savings". The seattle.gov figure is treated as authoritative for this spec because (a) it is a city-government source and (b) it is internally consistent (60 × 12 = 720). The implementation PR should re-verify this with the Fresh Bucks program team and update the value if the FAQ is the current rate.

## Acceptance Criteria

- [ ] Scenario 1 (Single adult, Seattle ZIP, low income): Eligible — `value` `720`
- [ ] Scenario 2 (Family of 4, Seattle ZIP, mid income within band): Eligible — `value` `720`
- [ ] Scenario 3 (Single adult, Seattle ZIP, income above 1-person AMI threshold): Ineligible
- [ ] Scenario 4 (Single adult, low income, ZIP outside Seattle city — e.g. Bellevue): Ineligible
- [ ] Scenario 5 (Income exactly at 1-person threshold $7,070/mo): Eligible — `value` `720`
- [ ] Scenario 6 (Income $1 over 1-person threshold — $7,071/mo): Ineligible

## Test Scenarios

> **Note on `value` units**: All `value` numbers below and in `wa_seattle_fresh_bucks.json` are **annual** dollars (per the screener's `estimated_value` convention — see `screener/management/commands/export_screener_data.py` and the `* 12` pattern in calculator implementations). Fresh Bucks pays a flat $60/mo per household → annualized to `720`.

### Scenario 1: Single Adult, Seattle ZIP, Low Income — Eligible (golden path)

**What we're checking**: Cleanest happy path — a single Seattle adult well under the 1-person AMI ceiling.

**Expected**: Eligible (`value` = `720`)

**Steps**:
- **Location**: ZIP `98101` (downtown Seattle), County `King`
- **Household**: 1 person
- **Person 1**: Age 32, Head of Household, U.S. Citizen, no disability, wages: `$3,000/month`
- **Insurance**: None
- **Household assets**: `$0` (Fresh Bucks has no asset test)

**Why this matters**: Income ($3,000/mo) is well below the 1-person AMI threshold ($7,070/mo); ZIP is unambiguously inside Seattle city limits; no other gates apply. Confirms baseline eligibility logic and the flat $720/yr benefit value.

---

### Scenario 2: Family of 4, Seattle ZIP, Mid Income — Eligible

**What we're checking**: Per-household-size threshold and that the benefit is flat regardless of family size.

**Expected**: Eligible (`value` = `720`)

**Steps**:
- **Location**: ZIP `98144` (Central District / Mt Baker), County `King`
- **Household**: 4 people
- **Person 1 (Head)**: Age 38, U.S. Citizen, wages: `$5,000/month`
- **Person 2 (Spouse)**: Age 36, U.S. Citizen, wages: `$3,000/month`
- **Person 3 (Child)**: Age 9, U.S. Citizen, no income
- **Person 4 (Child)**: Age 6, U.S. Citizen, no income
- **Insurance**: Employer for adults; Medicaid for children
- **Household assets**: `$0`

**Why this matters**: $8,000/mo combined income is well below the 4-person AMI threshold ($10,095/mo). Confirms the per-household-size band is read correctly and that the $720/yr benefit does not scale with family size.

---

### Scenario 3: Single Adult, Seattle ZIP, Income Above 1-Person AMI — Ineligible

**What we're checking**: Income disqualification at the 1-person threshold.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98101`, County `King`
- **Household**: 1 person
- **Person 1**: Age 32, Head of Household, U.S. Citizen, wages: `$8,000/month`
- **Insurance**: Employer
- **Household assets**: `$0`

**Why this matters**: $8,000/mo > $7,070/mo (1-person 80% AMI). Confirms the income gate fires correctly when the per-band cap is exceeded.

---

### Scenario 4: Low Income, Outside Seattle (Bellevue) — Ineligible

**What we're checking**: Geographic disqualification — applicant is in WA and below the income cap, but the ZIP is unambiguously outside Seattle city limits.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98004` (Bellevue), County `King`
- **Household**: 1 person
- **Person 1**: Age 32, Head of Household, U.S. Citizen, wages: `$2,500/month`
- **Insurance**: Employer
- **Household assets**: `$0`

**Why this matters**: King County resident with very low income, but in Bellevue (98004) — clearly outside Seattle city limits. Confirms the ZIP-based residency pre-filter excludes non-Seattle King County addresses.

---

### Scenario 5: Single Adult, Income Exactly at 1-Person Threshold — Eligible (boundary)

**What we're checking**: Boundary behavior — the threshold is "at or below", so an income that exactly matches the cap should be eligible.

**Expected**: Eligible (`value` = `720`)

**Steps**:
- **Location**: ZIP `98109` (South Lake Union / Queen Anne), County `King`
- **Household**: 1 person
- **Person 1**: Age 32, Head of Household, U.S. Citizen, wages: `$7,070/month` (exactly the 1-person monthly AMI cap)
- **Insurance**: Employer
- **Household assets**: `$0`

**Why this matters**: Documents that the calculator uses `<=` (not `<`) when comparing to the AMI threshold — matching the program's published "equal to or less than" wording.

---

### Scenario 6: Single Adult, Income $1 Over 1-Person Threshold — Ineligible (boundary)

**What we're checking**: The other side of the boundary — income that's just one dollar above the cap should be ineligible. This is the explicit complement to Scenario 5 and isolates the comparison-operator decision.

**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `98109`, County `King`
- **Household**: 1 person
- **Person 1**: Age 32, Head of Household, U.S. Citizen, wages: `$7,071/month`
- **Insurance**: Employer
- **Household assets**: `$0`

**Why this matters**: Confirms the off-by-one boundary on the income test fires correctly. Together with Scenario 5, this pins down the exact AMI-cap comparison semantics.

---

### Out-of-band: Currently enrolled household

The "one benefit per household" rule (Criterion #3) cannot be tested today because the screener has no `has_seattle_fresh_bucks` field. When the implementation PR adds that field (recommended), add a 7th scenario: same household as Scenario 1 but with `has_seattle_fresh_bucks = true` → expected `eligible: false`.

## JSON Test Cases

File: `validations/management/commands/import_validations/data/wa_seattle_fresh_bucks.json`

The validations file contains 3 representative scenarios per the canonical "Checking Program Researcher Output" reviewer guide (eligible standard, ineligible primary exclusion, edge case). The full 6 scenarios listed above remain in this spec.md as the dev's reference for implementation and future expansion.

| Scenario | Eligible? | `value` | Math |
| --- | --- | --- | --- |
| 1 — Single adult, $3,000/mo, ZIP 98101 | true | `720` | flat $60/mo × 12 |
| 2 — Family of 4, $8,000/mo, ZIP 98144 | true | `720` | flat $60/mo × 12 (does not scale by household size) |
| 3 — Single adult, $8,000/mo, ZIP 98101 | false | omitted | $8,000 > $7,070 (1-person 80% AMI cap) |
| 4 — Single adult, $2,500/mo, ZIP 98004 (Bellevue) | false | omitted | outside Seattle city limits |
| 5 — Single adult, $7,070/mo (exactly at cap), ZIP 98109 | true | `720` | $7,070 ≤ $7,070 → eligible |
| 6 — Single adult, $7,071/mo (one over), ZIP 98109 | false | omitted | $7,071 > $7,070 |

Per the canonical guide, `value` is omitted (not set to `0`) for ineligible scenarios. The 3 cases that land in `wa_seattle_fresh_bucks.json` are #1, #3, and #5 — golden path, primary exclusion (income), and the inclusive boundary edge case.

## Generated Program Configuration

File: `programs/management/commands/import_program_config_data/data/wa_seattle_fresh_bucks_initial_config.json`

Key fields:

- `name_abbreviated`: `wa_seattle_fresh_bucks`
- `program_category`: `wa_food` (Food and Nutrition) — same category used by `wa_snap`
- `legal_status_required`: `["citizen", "non_citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission"]` — all 6 base values, because the program does not enforce any citizenship/immigration restriction
- `value_type`: `benefit`
- `estimated_application_time`: `"15 - 20 minutes"` (per seattle.gov)
- `estimated_delivery_time`: `"varies (waitlist)"` — reflects the lottery-based enrollment model
- `apply_button_link`: `https://www.seattlefreshbucks.org/apply/`
- `learn_more_link`: `https://www.seattle.gov/environment/food-policy-and-programs/fresh-bucks`
- `show_in_has_benefits_step`: `true` — set so the duplicate-enrollment filter (Criterion #3) can take effect once the implementation PR adds the corresponding `Screen.has_seattle_fresh_bucks` field, `Screen._build_benefit_map()` entry, and frontend `category_benefits` tile (see "Has-benefits-step wiring" under *Implementation Notes for the Follow-Up PR* below). Fresh Bucks is the first city-specific program flipped on for this step — every other entry in `programs/migrations/0142_audit_show_in_has_benefits_step.py` is a federal or major statewide program — so the implementation PR should land all four pieces together to avoid a half-rendered state.

## Research Sources

- [seattlefreshbucks.org — Apply / Eligibility](https://www.seattlefreshbucks.org/apply/) — primary application page; AMI table; FAQ; lottery selection criteria.
- [seattlefreshbucks.org — Home](https://www.seattlefreshbucks.org/) — program overview and benefit-amount confirmation.
- [seattle.gov — Fresh Bucks (Office of Sustainability & Environment)](https://www.seattle.gov/environment/food-policy-and-programs/fresh-bucks) — official city-government program page; benefit value ($60/mo, $720/yr); residency rule (≤ 80% AMI, Seattle city limits).
- [Seattle City Council district lookup tool](https://www.seattle.gov/council/meet-the-council/find-your-district-and-councilmembers) — referenced by the program for verifying Seattle city-limit residency at the application stage.

## Implementation Notes for the Follow-Up PR

This program is **not** modeled by PolicyEngine and has no federal equivalent. The implementation should be a custom `ProgramCalculator` subclass in `programs/programs/wa/seattle_fresh_bucks/calculator.py`, registered in `wa_calculators` (not `wa_pe_calculators`) in `programs/programs/wa/__init__.py`.

### AMI source — use `hud_client`, do not hard-code the table

The 80% AMI table in Criterion #1 above is included for **review and test-scenario reference only**. The implementation calculator must **not** hard-code those numbers. Instead, use the project's existing HUD income-limits client:

```python
from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
```

and read the Section 8 80% AMI for the screen's county directly:

```python
income_limit_yearly = hud_client.get_screen_il_ami(self.screen, "80%", self.program.year.period)
```

This is the same pattern used by the existing IL housing programs (e.g. `programs/programs/urgent_needs/il/il_rent_asst.py`) and by the MA `homebridge` / `cpp` / `middle_income_rental` calculators. Benefits over a hard-coded table:

- Pulls the **HUD-published 80% AMI for King County (Seattle-Bellevue HMFA)** directly from HUD — no manual annual updates.
- Automatically picks up HUD's FY2026 limits the moment HUD publishes them, then FY2027, etc.
- Keeps the screener's AMI math consistent with every other AMI-based program in the codebase.
- Eliminates the FY2025-vs-FY2026 ambiguity called out in Criterion #1 above.

The dev should set `program.year` on the `Program` row (the `import_program_config` flow already supports a `year` field on the config; if Fresh Bucks doesn't currently set one, add the desired HUD year there so `self.program.year.period` resolves) — or pass a fixed string like `"2025"` if a specific HUD vintage is required.

### Has-benefits-step wiring (required by `show_in_has_benefits_step: true` in the import config)

The discovery PR sets `show_in_has_benefits_step: true` so the program appears as a selectable tile in the screener's "I already receive these benefits" step (the same step that surfaces SNAP, TANF, SSI, etc.). For that to render and the duplicate-enrollment short-circuit (Criterion #3) to actually fire, the implementation PR must land all four pieces together — otherwise the backend will report the program as has-benefits-step-eligible while the frontend has no tile and the calculator can't read the user's selection:

1. **Screen field** (`screener/models.py`): add `has_seattle_fresh_bucks = models.BooleanField(default=False, blank=True, null=True)` on `Screen`. Generate a migration (`python manage.py makemigrations screener`) and apply it.
2. **Benefit map** (`screener/models.py`): in `Screen._build_benefit_map()`, add `"seattle_fresh_bucks": self.has_seattle_fresh_bucks` so `screen.has_benefit("seattle_fresh_bucks")` resolves consistently with the SSI / SNAP duplicate-enrollment pattern. Verify `screener/serializers.py` already exposes the new field (add it if not).
3. **White label config** (`configuration/white_labels/wa.py`): add a `seattle_fresh_bucks` entry under the appropriate `category_benefits` category (likely the existing food category that already lists `wa_snap`) so the `wa` white label renders the tile.
4. **Frontend** (separate frontend repo): mirror the new field in `Types/FormData.ts`, `Types/ApiFormData.ts`, `Assets/updateScreen.ts`, `Assets/updateFormData.tsx`, and `Components/Wrapper/Wrapper.tsx` per the canonical Step 5–7 + frontend section of the program-implementation guide.

The calculator skeleton below already calls `self.screen.has_benefit("seattle_fresh_bucks")` at the top of `household_eligible`, so once steps 1–2 land the duplicate-enrollment filter is active end-to-end. Until then the call is a safe no-op (`has_benefit` returns `False` for unknown keys), so partial deployment of this PR is non-breaking.

> **Note**: every other program in `programs/migrations/0142_audit_show_in_has_benefits_step.py` is a federal or major statewide program (SNAP, TANF, WIC, SSI, SSDI, LIHEAP/LEAP, CCAP, Section 8, OAP). Seattle Fresh Bucks is the first **city-specific** program to be flipped on for this step. Confirm with the team that this is the desired UX before merging the implementation PR — alternatively, the impl PR could leave step 4 (frontend tile) hidden behind a flag while the backend remains wired up.

### Suggested skeleton

```python
# programs/programs/wa/seattle_fresh_bucks/calculator.py
from typing import ClassVar

from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.programs.calc import Eligibility, ProgramCalculator


class WaSeattleFreshBucks(ProgramCalculator):
    """
    Seattle Fresh Bucks — flat $60/month per household for income-eligible Seattle
    residents. See programs/programs/wa/seattle_fresh_bucks/spec.md.
    """

    monthly_benefit = 60
    ami_percent = "80%"

    seattle_zips: ClassVar[set[str]] = {
        "98101", "98102", "98103", "98104", "98105", "98106", "98107", "98108",
        "98109", "98112", "98115", "98116", "98117", "98118", "98119", "98121",
        "98122", "98125", "98126", "98133", "98134", "98136", "98144", "98146",
        "98154", "98164", "98174", "98177", "98178", "98195", "98199",
        # plus a handful of Seattle-only secondary ZIPs as needed
    }

    dependencies: ClassVar[list[str]] = [
        "household_size",
        "income_amount",
        "income_frequency",
        "zipcode",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        if self.screen.zipcode not in self.seattle_zips:
            e.eligible = False
            return

        if self.screen.has_benefit("seattle_fresh_bucks"):
            e.eligible = False
            return

        try:
            income_limit_yearly = hud_client.get_screen_il_ami(
                self.screen, self.ami_percent, self.program.year.period
            )
        except HudIncomeClientError:
            # Conservative: if HUD lookup fails we cannot affirm eligibility.
            e.eligible = False
            return

        gross_yearly = self.screen.calc_gross_income("yearly", ["all"])
        e.condition(gross_yearly <= income_limit_yearly)

    def household_value(self) -> int:
        return self.monthly_benefit * 12
```

The hard-coded `ami_monthly_by_size` table from earlier drafts of this spec has been removed intentionally — relying on `hud_client` is the canonical pattern.
