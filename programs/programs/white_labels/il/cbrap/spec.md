# Court-Based Rental Assistance Program (CBRAP) (IL) — Program Spec

- **Program key**: `il_cbrap` — `programs/programs/white_labels/il/cbrap`, class `IlCbrap`
- **Base federal program**: none — Illinois state program (IHDA)
- **White label**: IL
- **Engine**: MFB custom — no PolicyEngine variable models this program
- **Program status**: paused — not accepting new applications
- **Added to MFB**: 2026-09-01
- **Spec last updated**: 2026-08-31
- **Sources verified as of**: 2026-08-28

## Covered Eligibility Criteria

All criteria are conjunctive: every one must hold.

1. **The household's total gross income is at or below 80% of the Area Median Income for its county, adjusted for household size.**
   - Evaluation scope: `household`
   - Captured via: accessor `Screen.calc_gross_income("yearly", ["all"])`; `county` (Screen, CharField) and `household_size` (Screen, IntegerField) select the limit; the limit itself comes from HUD's Standard Section 8 Income Limits via `hud_client.get_screen_il_ami(screen, "80%", year)` (`integrations/clients/hud_income_limits`)
   - Implementation note:
     - The comparison is **inclusive** (`<=`).
     - The limit set is HUD's **Standard Section 8** income limits, **not MTSP**. IHDA's income-limit
       link resolves to `huduser.gov/portal/datasets/il.html` (that href is in the snapshot's
       `raw.html`, not in the extracted text).
     - The **vintage is a per-round parameter, not the current year**: IHDA used FY2025 limits for the
       FY2026 round.
     - `Screen.county` is nullable and the HUD client has two distinct failure families. See
       Implementation → *Error paths*.
   - Source: Illinois Housing Help CBRAP page, eligibility list — "Your household income is at or below 80% of the area median income, adjusted for household size." followed by "(See the income limits for your county here.)", whose href in the snapshot's `raw.html` is `https://www.huduser.gov/portal/datasets/il.html` — [snapshot `2026-08-26--illinoishousinghelp-cbrap`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-cbrap/content.md), accessed 2026-08-26
   - Source: CBRAP FAQ, tenant eligibility — "The household’s total gross income does not exceed 80% of the Area Median Income for location." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26
   - Source: FY26 CBRAP Tenant Guide p3, Program Eligibility → Income — "total household income cannot exceed the maximum for your household size in your county." — [snapshot `2026-08-26--fy26-cbrap-tenant-guide`](../../../sources/il/il_cbrap/2026-08-26--fy26-cbrap-tenant-guide/content.md), accessed 2026-08-26
   - Source: FY26 CBRAP Tenant Guide p3, Program Eligibility → Income, on the limit vintage — "2025 limits will be used." — [snapshot `2026-08-26--fy26-cbrap-tenant-guide`](../../../sources/il/il_cbrap/2026-08-26--fy26-cbrap-tenant-guide/content.md), accessed 2026-08-26
   - Source: HUD FY2025 Standard Section 8 Income Limits, Illinois rows — Cook County (Chicago-Joliet-Naperville, IL HUD Metro FMR Area) `l80_1` 67150 and `l80_4` 95900; Adams County `l80_1` 52150 — [snapshot `2026-08-28--hud-section8-income-limits-fy2025`](../../../sources/il/il_cbrap/2026-08-28--hud-section8-income-limits-fy2025/content.md), accessed 2026-08-28
   - Source (corroborating, independent HUD publication in a different format): FY2025 Adjusted HOME Income Limits, Illinois — "Chicago-Joliet-Naperville, IL HUD Metro FMR Area" LOW INCOME row "67150      76750      86350      95900" and "Adams County, IL" LOW INCOME row "52150      59600      67050      74500" — [snapshot `2026-08-28--hud-home-income-limits-il-fy2025`](../../../sources/il/il_cbrap/2026-08-28--hud-home-income-limits-il-fy2025/content.md), accessed 2026-08-28
   - Code note (not a source claim): that `get_screen_il_ami` reads the Standard Section 8 limits rather than MTSP is established by the client itself — `integrations/clients/hud_income_limits/client.py`, whose docstring describes the method as returning the "Standard Section 8 Income Limit" and which maps `"80%"` to the API's `low` category. The snapshot is evidence of the figures, not of what the code does.

2. **The household rents its home in Illinois.**
   - Evaluation scope: `household`
   - Captured via: accessor `Screen.has_expense(["rent"])` (backed by `type` (Expense, CharField)); the Illinois condition is satisfied by the IL white label and `county` (Screen, CharField)
   - Source: Illinois Housing Help CBRAP page, eligibility list — "You rent/ let your home in Illinois." — [snapshot `2026-08-26--illinoishousinghelp-cbrap`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-cbrap/content.md), accessed 2026-08-26
   - Source: CBRAP FAQ, tenant eligibility — "The household lives in Illinois and rents their home as their primary residence." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26

3. **There is no citizenship or immigration status requirement — assistance is available to eligible renters regardless of immigration status.**
   - Evaluation scope: `config`
   - Captured via: config `legal_status_required` — **all six user-selectable statuses listed explicitly**: `citizen`, `non_citizen`, `refugee`, `gc_5plus`, `gc_5less`, `otherWithWorkPermission`
   - Implementation note:
     - **An empty `legal_status_required` does not mean "unrestricted" — it means the program is shown
       to nobody.** The results layer filters with
       `program.legal_status_required.some((status) => checkedFilterNames.includes(status))`
       (`benefits-calculator/src/Components/Results/Filter/filterPrograms.ts`), and `[].some(...)` is
       `false`.
     - An unrestricted program must therefore enumerate all six statuses, as `tx_hse` does.
     - The importer only *warns* on an unrecognised status and drops it silently, so the six strings
       must match `LegalStatus.status` exactly.
   - Source: Illinois Housing Help CBRAP page, eligibility list — "Proof of citizenship is not required." — [snapshot `2026-08-26--illinoishousinghelp-cbrap`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-cbrap/content.md), accessed 2026-08-26
   - Source: CBRAP FAQ — "No, CBRAP assistance is available to all eligible renters in Illinois regardless of immigration status." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26
   - Source: CBRAP FAQ, on identifiers — "No, a Social Security Number (SSN) or Individual Taxpayer Identification Number (ITIN) is not required for tenants." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26

   *(The SSN/ITIN sentence is not a separate criterion — it is the same rule stated as a documentation consequence.)*

## Missing Eligibility Criteria (Data Gaps)

1. ⚠️ **Data Gap** — **The household must be engaged in an active court eviction proceeding that includes non-payment of rent.**
   - Why unobservable: no screener field identifies an eviction case. `needs_housing_help` (Screen, BooleanField) records a housing *need*, not a court-case status; `housing_situation` (Screen, CharField) exists on the model but the frontend never writes it, so it holds no values.
   - Handling: `assumed-met` (code comment). **The program description must state that CBRAP is for households already in eviction court** — without this gate the program shows to renters who cannot apply, so the description carries the whole burden of narrowing.
   - Source: FY26 CBRAP Tenant Guide p3, Program Eligibility → Eviction — "Tenants and housing providers/landlords must be engaged in active court eviction" / "proceedings that must include non-payment of rent." (one sentence, split by a PDF line break) — [snapshot `2026-08-26--fy26-cbrap-tenant-guide`](../../../sources/il/il_cbrap/2026-08-26--fy26-cbrap-tenant-guide/content.md), accessed 2026-08-26
   - Source: CBRAP FAQ, landlord eligibility — "They have a pending eviction due to nonpayment. A court-summons document will be required." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26

2. ⚠️ **Data Gap** — **The rental unit must be the household's primary residence at the time of applying.**
   - Why unobservable: the screener records one household with one rent expense and does not distinguish a primary residence from any other rented unit.
   - Handling: `assumed-met` (code comment). Widens results for households whose screened rent is for a non-primary unit.
   - Source: CBRAP FAQ, tenant eligibility — "The household lives in Illinois and rents their home as their primary residence." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26

3. ⚠️ **Data Gap** — **The household must not have been approved for CBRAP assistance, including tenant direct assistance, in the previous 18 months.**
   - Why unobservable: `CurrentBenefit` records benefits a household currently receives and has no date column, so there is no 18-month receipt history; CBRAP is also not among the programs the current-benefits step asks about.
   - Handling: `assumed-met` (code comment). Widens results for repeat applicants inside the 18-month window.
   - Source: CBRAP FAQ, tenant eligibility — "Tenant household must not have been approved for CBRAP assistance, including tenant direct assistance, in the previous 18 months." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26

4. ⚠️ **Data Gap** — **Where the housing provider lives in the same multi-unit building, the household must rent its own unit and must not be members of the housing provider's household.**
   - Why unobservable: the screener records no landlord identity, nothing about the household's relationship to its landlord, and nothing about whether the landlord occupies the building.
   - Scope: the rule applies only to the owner-occupied multi-unit case the source addresses ("I own and live in a multi-unit building which is also tenant occupied"), not to every CBRAP household.
   - Handling: `assumed-met` (code comment). Widens results only for that case — a household renting from, and belonging to, its housing provider's household.
   - Source: CBRAP FAQ, owner-occupied multi-unit buildings — "Tenants may be eligible for CBRAP assistance provided they rent their own unit and are not members of the housing provider’s household." — [snapshot `2026-08-26--illinoishousinghelp-faqs`](../../../sources/il/il_cbrap/2026-08-26--illinoishousinghelp-faqs/content.md), accessed 2026-08-26

## Priority Criteria

None.

## Related Programs

- **CBRAP Tenant Direct** — pays the tenant directly rather than the landlord.
  - Own eligibility: otherwise CBRAP-eligible, **and either** the housing provider is not
    participating in CBRAP **or** the household plans to move out of the unit.
  - Award basis: HUD Fair Market Rent for a comparable unit, not actual past-due rent. Not reviewable
    until at least 14 days after submission.
  - MFB treatment: **not a separate eligibility path.** Its awards come from the same State CBRAP pool
    and fall inside the FY2026 projection the Benefit Value is derived from.
  - Program description tie-back: none needed — reached through the same application.
  - Source: FY26 CBRAP Tenant Guide p37, Tenant Direct — "If your housing provider/landlord is not participating in CBRAP" … "This assistance will be equal to up to two months rent based on the HUD Fair Market Rent for a similar" … "A tenant direct application will be eligible for review at least 14 days after submission" — [snapshot `2026-08-26--fy26-cbrap-tenant-guide`](../../../sources/il/il_cbrap/2026-08-26--fy26-cbrap-tenant-guide/content.md), accessed 2026-08-26

- **CBRAP Cook County Right to Cure** — funds a tenant's exercise of the local Right to Cure / Pay
  and Stay right in Cook County and the City of Chicago.
  - Own eligibility: household lives in Cook County; its housing provider is not participating in
    CBRAP; it works with a legal aid agency; payment is made before a judge enters an eviction order.
    Mount Prospect residents are excluded.
  - Award covers past-due rent and $700 in court costs but **not** future rent.
  - MFB treatment: **not a separate eligibility path.**
  - Program description tie-back: none needed.
  - Source: FY26 CBRAP Tenant Guide p36–37, Cook County Right to Cure — "If your housing provider/landlord is not participating in CBRAP and you live in Cook County" … "To use CBRAP assistance for a Right to Cure payment, tenants must work with a legal aid agency." … "past due rent and $700 in court costs, it does not include future rent." — [snapshot `2026-08-26--fy26-cbrap-tenant-guide`](../../../sources/il/il_cbrap/2026-08-26--fy26-cbrap-tenant-guide/content.md), accessed 2026-08-26

## Benefit Value

**Actual program award.** CBRAP is need-based, not a flat payment. The FY2026 round caps total
assistance at **$10,000**, covering past-due rent, up to two months of future rent, and up to **$700**
in court costs. It is a **grant, not a loan**.

**Why a household-specific value cannot be computed.** The award depends on rent arrears, court costs,
and remaining round funds. The screener collects none of them, so no per-household figure can be
derived — and the $10,000 cap would overstate the award for nearly every household.

**Agency projection.** IHDA projects disbursing $50,000,000 to 6,500 approved households in FY2026.

**MFB calculation.** $50,000,000 ÷ 6,500 = $7,692.31, rounded to the nearest dollar.

- **Value: $7,692 one-time per eligible household.**
- `value_format`: `lump_sum` — a single one-time grant, not annualized. A repeat award is barred within
  18 months, so it is never paid twice in a year.
- Variation axes: flat.
- **Not an entitlement.** $7,692 is an MFB modelled estimate for display; no household is promised that
  amount. The projection is a plan, so the number of households actually served may differ.

- The assistance is a **grant, not a loan** — "provided in the form of a grant, which does not need to be repaid" (FY26 CBRAP Tenant Guide) — [snapshot `2026-08-26--fy26-cbrap-tenant-guide`](../../../sources/il/il_cbrap/2026-08-26--fy26-cbrap-tenant-guide/content.md), accessed 2026-08-26
- Source: IHDA Report of Activities p20, State CBRAP — "FY 2026 Projection: Under State CBRAP, IHDA projects disbursing $50 million to 6,500 approved households." — [snapshot `2026-08-28--ihda-report-of-activities-fy2025`](../../../sources/il/il_cbrap/2026-08-28--ihda-report-of-activities-fy2025/content.md), accessed 2026-08-28
- Source: FY26 CBRAP Tenant Guide p4, What Assistance Includes and Excludes, on the current cap — "There is an overall cap of $10,000 per household for this round." — [snapshot `2026-08-26--fy26-cbrap-tenant-guide`](../../../sources/il/il_cbrap/2026-08-26--fy26-cbrap-tenant-guide/content.md), accessed 2026-08-26
- Source: IHDA 2025 Annual Comprehensive Housing Plan Progress Report p35, FY2026 round terms — "Under State FY 2026, total CBRAP assistance will be up to $10,000 which can be applied to" "past due rent, up to two months future rent, and up to $700 in court costs." — [snapshot `2026-08-26--ihda-achp-progress-report-cy2025`](../../../sources/il/il_cbrap/2026-08-26--ihda-achp-progress-report-cy2025/content.md), accessed 2026-08-26

## Implementation

Binding build requirements for `programs/programs/white_labels/il/cbrap`, class `IlCbrap`. These are not sourced
policy rules; they are how the sourced rules map onto MFB.

- **Income limit**: call `hud_client.get_screen_il_ami(screen, "80%", program.year.period)`. Pass the
  **vintage**, not the current year — IHDA used FY2025 limits for the FY2026 round, which is why the
  config carries `year: "2025"`. A call made with the current year is a defect even when it returns a number.
- **Income**: aggregate the whole household annually via `Screen.calc_gross_income("yearly", ["all"])` —
  every member, every income type, converted to yearly before comparison.
- **Comparison**: inclusive. `income <= limit` is eligible.
- **Tenure**: require `Screen.has_expense(["rent"])`.
- **Do not gate on `needs_housing_help`.** `IlRenterAssistance` gates on it, but that is a narrowing
  proxy, not the CBRAP rule — reusing it would deny income-eligible renters who did not tick a
  housing-need box. The real eviction requirement is a data gap, handled `assumed-met`.
- **Data gaps**: all four unobservable rules — active eviction proceeding, primary residence, the
  18-month repeat-award bar, and the landlord-household relationship — are `assumed-met`, each with a
  code comment naming it. The program description carries the narrowing instead.
- **The calculator owns the value; the config must not.** `IlCbrap.value()` returns **7692**.
  Config `estimated_value` maps to `estimated_value_override`, which makes the frontend render the
  literal string *instead of* the calculated value and drops the program from category totals — so it
  is deliberately left empty (`""`). Do not populate it to "display" the estimate.
- **Release dependency: deactivate `il_rent_asst` in the same release that activates `il_cbrap`.**
  `IlRenterAssistance` (`programs/urgent_needs/il/il_rent_asst.py`, registered `il_rent_asst`) is an
  active representation of CBRAP — same program, same apply URL, this program's rule plus a
  `needs_housing_help` gate. Set **`active=False`** on its `UrgentNeed` row.
  - Ship it with `il_cbrap`: earlier and Illinois renters lose CBRAP entirely; later and some receive
    two CBRAP results with different eligibility logic.
  - `show_on_current_benefits=False` does **not** work — the results path filters on `active` only
    (`screener/views.py:711-713`).
  - Nothing happens automatically: `import_program_config` never touches `UrgentNeed` rows.
- **Legal status stays config-owned.** The calculator never reads immigration status; criterion 3
  lives entirely in `legal_status_required`.
- **Error paths: two distinct exception families, and neither may become a policy result.**
  - `HudIncomeClientError` — raised when the county is not found, when the limits API fails, and when
    the response is missing the expected category or household-size field.
  - `AttributeError` / `TypeError` — raised by the *nullable-field* paths, which do **not** use that
    class: `county=None` fails on `county_name.strip()`; `household_size=None` fails on `None < 1`.
    So `except HudIncomeClientError: skip` still crashes on a null `county`.
  - **Declare `county` and `household_size` as dependencies**, with a `HudIncomeClientError` catch on
    top for the county-not-found and API-failure cases.
  - **A missing dependency or HUD failure must never be surfaced to the user as `Ineligible`.**
  - (The client also raises when `household_size` is outside 1–8, but the frontend caps household entry
    at 8, so that path is unreachable from the screener.)
- **Guard `program.year` before dereferencing it.** The importer only *warns* when a `year` row is
  missing, leaving `program.year` null, and `program.year.period` on a null FK raises `AttributeError`
  on the calculator's first line. Raise a named `ValueError` instead, as `il_rent_asst.py` does.

## Acceptance Criteria

Each item names how it is verified — by scenario, by the stub contract, or at gate-config.

- [ ] **AC1 — Eligible households are valued at $7,692 by `IlCbrap.value()`.** An Illinois renter
      household whose annual gross household income is at or below the HUD FY2025 Standard Section 8
      80% limit for its county and household size is **Eligible** at **$7,692**.
      → Scenarios 1, 2, 5. Config `estimated_value` stays `""` → gate-config.
- [ ] **AC2 — The income boundary is inclusive and exact.** One dollar above the limit is
      **Ineligible**; exactly at the limit is **Eligible**. → Scenarios 2, 3, 7.
- [ ] **AC3 — Income is whole-household and all-type**, summed across every member and every income
      type and converted to yearly before comparison. → Scenarios 2, 3.
- [ ] **AC4 — The limit varies by both `county` and `household_size`**; neither is hardcoded.
      → Scenarios 5/6 (county), 5 and 7 against 2 (household size).
- [ ] **AC5 — Renters only.** No rent expense is **Ineligible** regardless of income. → Scenario 4.
- [ ] **AC6 — `needs_housing_help` does not affect the result.** → Scenario 1, which pins it false.
- [ ] **AC7 — The HUD call uses the FY2025 vintage**, not the current year. → All scenarios, via the
      stub contract: a call with `year=2026` fails rather than returning a number.
- [ ] **AC8 — Failures never render as policy.** HUD and dependency failures surface as a skipped or
      errored program, never as `Ineligible`. → Implementation → *Error paths*; no scenario.
- [ ] **AC9 — `legal_status_required` lists all six user-selectable statuses**, so the program is
      visible to every citizenship selection. → gate-config.

## Test Scenarios

**Coverage map**

| Rule / variation axis | Scenarios |
|---|---|
| Income comparison inclusive (`<=`) (criterion 1) | 2 (exactly at limit), 3 ($1 over → fail), 7 ($1 over at a different limit) |
| Income aggregated across household members (criterion 1, `household` scope) | 2, 3 (income split between two members) |
| Income counts all types, not just earned (criterion 1, `["all"]`) | 3 (wages + unemployment) |
| Income frequency conversion to yearly (criterion 1) | 2, 3 (monthly stream against an annual limit) |
| Limit selected by `household_size` (criterion 1) | 5, 7 (1-person limit) vs 2 (4-person limit) |
| Limit selected by `county` (criterion 1) | 5 (Cook) vs 6 (Adams) — same income, same size, opposite outcomes |
| Rent expense present (criterion 2) | 1 (present), 4 (homeowner → fail) |
| `needs_housing_help` does not gate the program (Acceptance Criterion 6) | 1 (pinned false) |
| HUD call made with the FY2025 vintage (Acceptance Criterion 7) | all — enforced by the binding stub contract in the Fixture note |
| Income counted for members outside the head's tax unit (criterion 1, `household` scope) | 3 (`relatedOther`) |
| Benefit value (flat, $7,692 one-time) | 1, 2, 5 |

**Known scenario gaps** — coverage boundaries with committed handling, not open issues.

- **The four data gaps** are unscreenable, so no scenario asserts them in either direction. A household
  in eviction court and one not in eviction court screen identically.
- **Criterion 3 (legal status)** is config-owned: `legal_status_required` is a `Program` attribute the
  results layer applies, never something a calculator reads. Verified at gate-config.
- **AC1's config half** — `estimated_value` stays `""` — is likewise config-owned and not falsifiable
  by a calculator scenario. Verified at gate-config.
- **The "in Illinois" half of criterion 2** is white-label-scoped: every screen reaching an IL
  calculator is already an Illinois screen.
- **Error paths** — the HUD client's failure families and the null `program.year` path — are
  implementation decisions, specified in Implementation → *Error paths* and *Guard `program.year`*.

**Fixture note**: the AMI limit is fetched at runtime by
`hud_client.get_screen_il_ami(screen, "80%", program.year.period)`. Scenarios below use the **FY2025
Standard Section 8 low-income (80%) limits as published by HUD**, which is the vintage the FY2026
round used — Cook County **$67,150** for one person and **$95,900** for four; Adams County
**$52,150** for one person — [snapshot `2026-08-28--hud-section8-income-limits-fy2025`](../../../sources/il/il_cbrap/2026-08-28--hud-section8-income-limits-fy2025/content.md), accessed 2026-08-28. **Stub contract (binding).** Key the HUD stub by `(county, household_size, year)` and **raise on any
unseeded tuple** — an unseeded county, an unseeded household size, or `year=2026` must fail the test
rather than return a number. Do not use a flat stub that ignores its arguments; it would make
Scenarios 5, 6 and 7 vacuous.

**Series provenance.** HUD publishes the figures as columns `l80_1`..`l80_8`; the client maps `"80%"`
to the API's `low.il80_p{household_size}` series in `il/data/{fips}`. The FY2025 Adjusted HOME Income
Limits LOW INCOME rows independently corroborate the three fixture values — [snapshot `2026-08-28--hud-home-income-limits-il-fy2025`](../../../sources/il/il_cbrap/2026-08-28--hud-home-income-limits-il-fy2025/content.md), accessed 2026-08-28.

**County strings.** Use the bare values MFB stores — `"Cook"`, `"Adams"`
(`configuration/white_labels/il.py`) — **not** `"Cook County"`. The HUD client appends the `" County"`
suffix itself.

### Scenario 1: Renter well under the income limit — Eligible, $7,692
**What we're checking**: the ordinary eligible case — an Illinois renter household whose income sits comfortably below 80% AMI.
**Expected**: Eligible — $7,692
**Steps**:
* Location: ZIP `60601`, county `Cook`
* Household size: 4 — HUD 80% AMI limit $95,900
* Person 1: `birth_year` 1986, `birth_month` 3, head of household, wages $3,500/monthly
* Person 2: `birth_year` 1988, `birth_month` 6, spouse, wages $1,000/monthly
* Person 3: `birth_year` 2016, `birth_month` 1, child, no income
* Person 4: `birth_year` 2019, `birth_month` 4, child, no income
* Expense: rent $1,500/monthly
* `needs_housing_help`: **not selected (false)**
**Why this matters**: the positive control ($54,000 against a $95,900 limit), and the guard against
this program's highest-risk mutation. `IlRenterAssistance` returns
`needs_housing_help and has_rent and below_income_limit`; an implementer who copies it inherits a gate
CBRAP does not have. With `needs_housing_help` pinned false, that copy flips this scenario to
Ineligible and fails. **Do not let a fixture default this field to true.**

---

### Scenario 2: Household income exactly at the limit, split across two members and two frequencies — Eligible, $7,692
**What we're checking**: the income boundary is inclusive, the total is aggregated across members, and a monthly stream is converted before comparison.
**Expected**: Eligible — $7,692 (household income $60,000 + $35,900 = $95,900, exactly the limit)
**Steps**:
* Location: ZIP `60601`, county `Cook`
* Household size: 4 — HUD 80% AMI limit $95,900
* Person 1: `birth_year` 1986, `birth_month` 3, head of household, wages $5,000/monthly (= $60,000/yearly)
* Person 2: `birth_year` 1988, `birth_month` 6, spouse, wages $35,900/yearly
* Person 3: `birth_year` 2016, `birth_month` 1, child, no income
* Person 4: `birth_year` 2019, `birth_month` 4, child, no income
* Expense: rent $1,500/monthly
**Why this matters**: kills three mutations at once.
- `<` vs `<=` — the FY26 Tenant Guide's "must be below 80%" phrasing makes strict inequality the
  plausible wrong implementation.
- Head-only — counting just Person 1 gives $60,000 and still passes here, but fails Scenario 3.
- Frequency — a dropped or wrong ×12 moves Person 1's contribution off $60,000 and breaks the
  exact boundary.

---

### Scenario 3: Household income one dollar over the limit, from two income types — Ineligible
**What we're checking**: the income test excludes above the limit, counts unearned income, and counts every member.
**Expected**: Ineligible (criterion 1 fails — household income $60,000 + $35,901 = $95,901, one dollar over the $95,900 limit)
**Steps**:
* Location: ZIP `60601`, county `Cook`
* Household size: 4 — HUD 80% AMI limit $95,900
* Person 1: `birth_year` 1986, `birth_month` 3, head of household, wages $5,000/monthly (= $60,000/yearly)
* Person 2: `birth_year` 1988, `birth_month` 6, **`relatedOther`** (an adult relative, not the head's spouse and not in the head's tax unit), unemployment $35,901/yearly
* Person 2 disability flags: `disabled`, `visually_impaired`, `long_term_disability` — **all false (pin these; see below)**
* Person 3: `birth_year` 2016, `birth_month` 1, child, no income
* Person 4: `birth_year` 2019, `birth_month` 4, child, no income
* Expense: rent $1,500/monthly
**Why this matters**: with Scenario 2, pins the boundary to the exact dollar. It also kills three
scoping mutations, each of which would leave Person 1 alone at $60,000 → wrongly Eligible: head-only;
earned-income-only (ignoring unemployment); and **tax-unit scoping** to `is_in_tax_unit` (head +
spouse), which would survive Scenario 2 where every dollar sits on the head and the spouse.
**The disability flags must be pinned false**: `is_dependent()` treats `has_disability()` as an
alternative to the age test, so a disability flag would make Person 2 a qualifying child ($35,901 is
below half the household's $95,901), put them back inside the tax unit, and defeat this scenario.

---

### Scenario 4: Homeowner with no rent expense — Ineligible
**What we're checking**: CBRAP is for renters; a low-income homeowner is not eligible.
**Expected**: Ineligible (criterion 2 fails — no rent expense, so the household does not rent its home)
**Steps**:
* Location: ZIP `60601`, county `Cook`
* Household size: 4 — HUD 80% AMI limit $95,900
* Person 1: `birth_year` 1986, `birth_month` 3, head of household, wages $3,500/monthly
* Person 2: `birth_year` 1988, `birth_month` 6, spouse, wages $1,000/monthly
* Person 3: `birth_year` 2016, `birth_month` 1, child, no income
* Person 4: `birth_year` 2019, `birth_month` 4, child, no income
* Expense: mortgage $1,500/monthly (no rent expense)
**Why this matters**: kills a mutation that drops `has_expense(["rent"])` and shows CBRAP to every income-eligible household regardless of tenure. Income here is identical to Scenario 1, so tenure is the only thing that changed.

---

### Scenario 5: Single-person Cook County renter under the one-person limit — Eligible, $7,692
**What we're checking**: the one-person limit is selected by household size, and it is high enough in Cook County for this income to pass.
**Expected**: Eligible — $7,692 ($55,000 against the $67,150 one-person Cook limit)
**Steps**:
* Location: ZIP `60601`, county `Cook`
* Household size: 1 — HUD 80% AMI limit $67,150
* Person 1: `birth_year` 1986, `birth_month` 3, head of household, wages $55,000/yearly
* Expense: rent $1,100/monthly
**Why this matters**: the positive half of the county pair. Scenario 6 holds income and household size fixed and changes only the county; together they make the county lookup outcome-determinative.

---

### Scenario 6: Same household in Adams County, over the lower one-person limit — Ineligible
**What we're checking**: the AMI limit is selected by county, not fixed statewide.
**Expected**: Ineligible (criterion 1 fails — $55,000 exceeds the $52,150 one-person Adams limit)
**Steps**:
* Location: ZIP `62301`, county `Adams`
* Household size: 1 — HUD 80% AMI limit $52,150
* Person 1: `birth_year` 1986, `birth_month` 3, head of household, wages $55,000/yearly
* Expense: rent $1,100/monthly
**Why this matters**: kills the mutation that hardcodes one statewide limit while still honouring household size — the exact mutation that survived the previous scenario set, which only ever used Cook County. Identical to Scenario 5 in every input but county, and the outcome flips.

---

### Scenario 7: Single-person Cook County household one dollar over the one-person limit — Ineligible
**What we're checking**: the one-person boundary is exact, and the four-person limit is not applied to a one-person household.
**Expected**: Ineligible (criterion 1 fails — $67,151 exceeds the $67,150 one-person limit)
**Steps**:
* Location: ZIP `60601`, county `Cook`
* Household size: 1 — HUD 80% AMI limit $67,150
* Person 1: `birth_year` 1986, `birth_month` 3, head of household, wages $67,151/yearly
* Expense: rent $1,100/monthly
**Why this matters**: pins the one-person boundary to the dollar and kills the mutation that ignores `household_size` — under the 4-person $95,900 limit this income would wrongly pass.

---

## Research Sources

Pin-cite page numbers are **PDF page index**, which may differ from the printed footer.

**Fidelity**: fourteen snapshots are `raw` (bytes exactly as the server returned them). The two HUD
snapshots are `rendered` — `huduser.gov` answers default tooling User-Agents with an empty HTTP 202,
so both were fetched with a browser User-Agent and captured `--from-file`. Both fidelities are citable
for verbatim quotes; raw bytes are retained and hash-verified. The three AMI figures the scenario suite
rests on appear independently in both HUD snapshots.

The last four rows are **navigator sources**, captured 2026-08-31 to support the config's
`navigators` block. They establish no eligibility rule and are cited by no criterion; they exist so
that every navigator name, phone number, email and description traces to evidence like the rest of
the package.

| Snapshot | Tier | Fidelity | Title | URL | Retrieved |
|---|---|---|---|---|---|
| `2026-08-26--ihda-cbrap` | 2 | raw | IHDA — Illinois Court-Based Rental Assistance Program (CBRAP) | https://www.ihda.org/about-ihda/cbrap/ | 2026-08-26 |
| `2026-08-26--illinoishousinghelp-cbrap` | 2 | raw | Illinois Housing Help — CBRAP | https://www.illinoishousinghelp.org/cbrap | 2026-08-26 |
| `2026-08-26--illinoishousinghelp-faqs` | 2 | raw | Illinois Housing Help — FAQs | https://www.illinoishousinghelp.org/faqs | 2026-08-26 |
| `2026-08-26--fy26-cbrap-tenant-guide` | 2 | raw | FY26 CBRAP Tenant Guide (IHDA) | https://cdn.prod.website-files.com/617033bdd8cf10d9f75baef2/68f90a3187c4eb55220970f6_FY26%20CBRAP%20TENANT%20Guide%20FINAL.pdf | 2026-08-26 |
| `2026-08-26--ihda-achp-progress-report-cy2025` | 2 | raw | Illinois 2025 Annual Comprehensive Housing Plan Progress Report (IHDA) | https://www.ihda.org/wp-content/uploads/2026/04/CY-2025-ACHP-Progress-Report.pdf | 2026-08-26 |
| `2026-08-26--illinoishousinghelp-resources` | 2 | raw | Illinois Housing Help — Rental Resource Toolkit | https://www.illinoishousinghelp.org/resources | 2026-08-26 |
| `2026-08-26--ilrpp-cbrapcore-portal` | 2 | raw | CBRAPCore — IHDA application portal | https://ilrpp.ihda.org/ | 2026-08-26 |
| `2026-08-26--ncsha-il-cbrap-award-2025` | 3 | raw | Illinois Court-Based Rental Assistance Program — NCSHA 2025 award entry (IHDA-authored) | https://www.ncsha.org/wp-content/uploads/Illinois-Special-Needs-Housing-Combating-Homelessness-2025.pdf | 2026-08-26 |
| `2026-08-28--ihda-report-of-activities-fy2025` | 2 | raw | IHDA Report of Activities for FY 2025 and Projected Activities for FY 2026 | https://www.ilga.gov/Documents/Reports/ReportsSubmitted/6616RSGAEmail14712RSGAAttachFY%202025_IHDA_Report%20of%20Activities.pdf | 2026-08-28 |
| `2026-08-28--hud-section8-income-limits-fy2025` | 2 | rendered | HUD FY2025 Standard Section 8 Income Limits (national dataset) | https://www.huduser.gov/portal/datasets/il/il25/Section8-FY25.xlsx | 2026-08-28 |
| `2026-08-28--hud-home-income-limits-il-fy2025` | 2 | rendered | HUD FY2025 Adjusted HOME Income Limits — Illinois | https://www.huduser.gov/portal/datasets/home-datasets/files/HOME_IncomeLmts_State_IL_2025.pdf | 2026-08-28 |
| `2026-08-31--eviction-help-illinois` | 3 | raw | Eviction Help Illinois (navigator source) | https://evictionhelpillinois.org/ | 2026-08-31 |
| `2026-08-31--eviction-help-illinois-about` | 3 | raw | About Eviction Help Illinois — first-party hotline number and statewide scope (navigator source) | https://evictionhelpillinois.org/about-eviction-help-illinois/ | 2026-08-31 |
| `2026-08-31--carpls-eviction-help-illinois` | 3 | raw | CARPLS — Eviction Help Illinois Hotline (navigator source, corroborates the number) | https://carpls.org/services/eviction-help-illinois/ | 2026-08-31 |
| `2026-08-31--nhs-chicago-renter-support` | 3 | raw | NHS Chicago — Renter Support (navigator source) | https://nhschicago.org/renter-support/ | 2026-08-31 |
| `2026-08-31--nhs-chicago-emergency-assistance-stale` | 3 | raw | NHS Chicago — Emergency Assistance Grants (**conflict evidence only; cited for no rule** — carries superseded CBRAP2-era terms, see companion C7) | https://nhschicago.org/emergency-assistance-grants/ | 2026-08-31 |
