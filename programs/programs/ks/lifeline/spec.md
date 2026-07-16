# Implement Lifeline Phone and Internet Discount (KS) Program — Light Spec

**Tier**: Fed (value varies) · **Engine**: PE · **State**: KS · **White Label**: ks
**Research Date**: 2026-06-30 · **Revised to light spec**: 2026-07-12 · **PE-verified**: 2026-07-12

---

## Program Details

- **Program**: Lifeline Phone and Internet Discount
- **PE variable**: `lifeline` (federal, KS state branch)
- **Config category**: `ks_housing`

## Value Delta (what actually varies for KS)

- **Federal baseline**: $9.25/month, per 47 CFR § 54.403(a)(1): *"Federal Lifeline support in the amount of $9.25 per month will be made available to an eligible telecommunications carrier providing Lifeline service to a qualifying low-income consumer."* PE's `gov.fcc.lifeline.amount.standard` parameter = 9.25, matches.
- **KS-specific Δ**: Kansas Lifeline state supplement of **$7.77/month**, and it applies to **phone service only** — this is not a PE quirk, it's the actual program rule. Verbatim, from the Kansas Citizens' Utility Ratepayer Board (CURB) Lifeline/ACP fact sheet (Kansas state source, current as of the 2025-09-08 KCC news release which reconfirms the same $7.77/$17.02 figures):
  > *"The Kansas portion of the discount may only be applied to phone service. The federal discount may be used for internet or phone service. Total federal and state discounts of up to $17.02 per month are available."*
  — Source: https://curb.kansas.gov/documents/Lifeline_Program_Affordable_Connectivity_Program_2024_02262025.pdf ; confirmed current at https://www.kcc.ks.gov/public-affairs-and-consumer-protection/kansas-lifeline-program and https://www.kcc.ks.gov/news-9-8-25
  - PE's KS branch matches this exactly: `ks_lifeline_supplement` ($7.77/month, `policyengine_us/parameters/gov/states/ks/kcc/lifeline/supplement.yaml`) is only released in `lifeline.py` up to the household's `phone_cost` (`min_(phone_cost, ks_supplement * MONTHS_IN_YEAR)`) — `broadband_cost` does not count toward it. **PE's implementation is correct, not a bug.**
- **Confirmed value matrix MFB should display** (live PE API results, KS, SNAP-eligible single adult, `broadband_cost=500`):

  | Household reports a phone/telephone cost? | PE `lifeline` result | MFB display |
  |---|---|---|
  | Yes (any nonzero `phone_cost`) | **$17.02/month** ($204.24/year) | Combined federal + KS |
  | No (broadband/internet-only) | **$9.25/month** ($111.00/year) | Federal only |

- ⚠️ **BLOCKING — confirmed implementation gap, MFB-side, not PE-side**: MFB's shared `Lifeline` PE calculator (`programs/programs/federal/pe/spm.py:79-85`) sends `broadband_cost` (hardcoded `500`) but has **no dependency supplying `phone_cost` at all**. Ran this exact input set (no `phone_cost` key sent) live against PE: result was **$111.00/year** — confirmed, not estimated. Every KS household gets shortchanged $93.24/year today, regardless of whether they'd otherwise qualify for the phone-based supplement, until `KsLifeline` adds a `phone_cost` PE input dependency (reusing the existing telephone-expense screener data already used by `PhoneExpenseDependency`, `programs/programs/policyengine/calculators/dependencies/spm.py:98`, which reads `self.screen.calc_expenses("yearly", ["telephone"])` for a different PE field today). **Resolved decision** (not a fork): map that same telephone-expense screener data directly to the new `phone_cost` field — this isn't a UX choice, it's just matching PE's variable semantics to data MFB already collects. Documented as a required implementation step on [MFB-1057](https://linear.app/myfriendben/issue/MFB-1057/ks-lifeline-phone-and-internet-discount); see the PE delta report comment for full detail. Not a Discovery blocker; is an Implementation blocker.
## Test Scenarios (value-isolating only — not re-testing federal eligibility)

### Scenario 1: Eligible KS household with a phone cost — combined value
**What we're checking**: A household that clearly passes PE's federal eligibility test (SNAP) and reports a telephone expense gets the **combined** $17.02/month, not the federal-only $9.25/month.
**Expected (post phone_cost fix)**: Eligible, **$17.02/month** ($204.24/year)
⚠️ **Known-broken until implementation fix lands**: live-verified today (no `phone_cost` sent) → PE returns **$111.00/year**. Do not treat a $111/year result as a scenario failure pre-fix; treat it as confirmation the `phone_cost` dependency is still outstanding.

**Steps**:
- **Location**: ZIP `67202`, Sedgwick County, KS
- **Household**: 1 person, Head of Household, age 40, US Citizen, employment income $1,200/month ($14,400/year)
- **Current Benefits**: SNAP
- **Expenses**: Telephone expense reported (any nonzero monthly amount, e.g. $50/month)

**PE verification** (`api.policyengine.org`, `household.state_name=KS`, `employment_income=14400`, `snap=1`, `broadband_cost=500`, `phone_cost=600`): `is_lifeline_eligible=true`, `ks_lifeline_supplement=93.24`, `lifeline=204.24` ✅ matches expected.

**Why this matters**: This is the scenario that actually exercises the Tier's "value varies" concern — if the KS state branch or the `phone_cost` input isn't wired correctly, this silently returns $111/year instead of $204.24/year, and nothing about federal eligibility logic would catch it.

---

### Scenario 2: Eligible KS household, broadband-only (no phone cost) — federal-only value
**What we're checking**: Confirms the source-documented rule that the KS supplement is phone-service-only — a household with only broadband/internet cost and no telephone expense should get federal-only, both today and after the `phone_cost` fix ships.
**Expected**: Eligible, **$9.25/month** ($111.00/year) — same result before and after the fix, since `phone_cost` is genuinely $0 for this household (not a bug in either state).

**Steps**:
- **Location**: ZIP `67202`, Sedgwick County, KS
- **Household**: 1 person, Head of Household, age 40, US Citizen, employment income $1,200/month ($14,400/year)
- **Current Benefits**: SNAP
- **Expenses**: No telephone expense reported (broadband/internet only)

**PE verification**: `employment_income=14400`, `snap=1`, `broadband_cost=500`, `phone_cost=0` → `is_lifeline_eligible=true`, `ks_lifeline_supplement=93.24` (computed but capped by `phone_cost=0`... `min_(0, 93.24)=0`), `lifeline=111.00` ✅ matches expected.

**Why this matters**: Proves the $9.25-vs-$17.02 split is a real, source-documented distinction (not just a PE modeling artifact) and gives a scenario whose expected value doesn't depend on the pending implementation fix — useful as a control case.

---

### Scenario 3: Clearly ineligible KS household — not shown
**What we're checking**: A KS household well above the federal income threshold with no qualifying program participation is correctly excluded — confirms the KS state branch doesn't accidentally short-circuit federal eligibility (full FPL/categorical boundary testing itself is PE's responsibility and out of scope here).
**Expected**: Ineligible.

**Steps**:
- **Location**: ZIP `67202`, Sedgwick County, KS
- **Household**: 1 person, Head of Household, age 40, US Citizen, employment income $3,333/month ($40,000/year)
- **Current Benefits**: None

**PE verification**: `employment_income=40000`, no benefits, `broadband_cost=500`, `phone_cost=600` → `fcc_fpg_ratio=2.51` (251% of FPL, well above the 135% limit), `is_lifeline_income_eligible=false`, `is_lifeline_eligible=false`, `lifeline=0.0` ✅ matches expected.

**Why this matters**: Basic regression guard — confirms the KS branch is additive to eligibility (adjusts value only) and doesn't make every KS household eligible regardless of income.

---

## Source Documentation

- 47 CFR § 54.403 (federal benefit amount): https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-54/subpart-E/section-54.403
- Kansas Lifeline Program (KCC): https://www.kcc.ks.gov/public-affairs-and-consumer-protection/kansas-lifeline-program
- Kansas Lifeline/ACP fact sheet (CURB, source of the "phone service only" KS supplement rule and $7.77/$17.02 figures): https://curb.kansas.gov/documents/Lifeline_Program_Affordable_Connectivity_Program_2024_02262025.pdf
- KCC news release reconfirming figures as of 2025-09-08: https://www.kcc.ks.gov/news-9-8-25

## Out of Scope for This Light Spec

Full federal eligibility criteria (135% FPL / qualifying-program test, KS residency, age 18+, one-per-household, and the FPL boundary/multi-member-household edge cases that go with it) are owned by PE's federal `lifeline` calculator and are **not** re-derived here — Scenario 3 above is a basic sanity check only, not full eligibility boundary coverage. 
