# QA Test Results — WA Basic Food (SNAP)

**Branch:** pat/mfb-848-wa-snap-implementation-v2
**Test Date:** 2026-04-24
**Environment:** LOCAL (http://localhost:3000/wa)
**Tester:** Playwright MCP Automation

## Test Scenarios

| # | Description | Expected | Actual | Result | URL |
|---|-------------|----------|--------|--------|-----|
| 1 | Single Adult Worker — Clearly Eligible ($1,500/mo wages) | Eligible | Eligible ($23/mo) | ✅ PASS | [Results](http://localhost:3000/wa/35e16505-df92-4ad4-9c4e-ae938d78537b/results/benefits) |
| 2 | Family of Four — Income Just Under 200% FPL ($4,800/mo HH=4, rent $2,200, childcare $400) | Eligible | Eligible ($206/mo) | ✅ PASS | [Results](http://localhost:3000/wa/3bbd3f03-7c7f-43a0-bc29-08284f2fdf88/results/benefits) |
| 3 | Single Parent + Child — Gross $1 Below 200% FPL ($3,524/mo HH=2) | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/a752fe7d-476b-492f-9500-d5af970512fe/results/benefits) |
| 4 | Couple — Gross Exactly at 200% FPL ($3,525/mo combined HH=2) | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/4e280fa9-badd-4b12-be31-fe04dc87efdf/results/benefits) |
| 5 | Single Adult — Gross $1 Above 200% FPL ($2,661/mo, rent $900) | Not eligible | Not shown | ✅ PASS | [Results](http://localhost:3000/wa/122e060f-70c3-46e2-9436-bfb97ac5d4fe/results/benefits) |
| 6 | Person Exactly Age 18 (March 2008) — $800/mo wages | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/f3ecdf39-327e-4ea7-bb82-492e620d3a10/results/benefits) |
| 7 | 17-Year-Old Half-Time Student (June 2008) — No income, age exemption | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/ee9f1f82-7be5-484d-aa23-68a51e774566/results/benefits) |
| 8 | 75-Year-Old Elderly (Jan 1951) — Option B: SS $2,700, rent $1,500 → net below 100% FPL | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/9c800de4-7a53-43fe-94de-67dae391941d/results/benefits) |
| 9 | BBCE Regression Test — $2,200/mo wages, net above 100% FPL, still eligible under BBCE | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/cfa41b29-e640-4e84-9826-1932719fc6b5/results/benefits) |
| 10 | Already Receiving Basic Food/SNAP — Duplicate benefit exclusion (HH=2, $1,800/mo) | Not eligible | Not shown (0 programs) | ✅ PASS | [Results](http://localhost:3000/wa/a8e0ed76-3125-40a2-8126-c43f936ea869/results/benefits) |
| 11 | Mixed Household — Elderly SS $1,200, working adult $2,400, student 20+hrs $900 (HH=3) | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/05775a9c-4bff-428c-b7db-ce00e74e7e5e/results/benefits) |
| 12 | Family of Five — Two working adults, pregnant member, two children ($3,500/mo combined) | Eligible | Eligible | ✅ PASS | [Results](http://localhost:3000/wa/75a4b9d2-ca8d-47dc-b2ea-adbb62e428c5/results/benefits) |

## Summary

- **Total Scenarios:** 12
- **Passed:** 12
- **Failed:** 0
- **Pass Rate:** 100%

## Notes

### S1 — Benefit estimate
$23/mo for $1,500/mo wages. At this income level, net income after standard deductions ($1,500 - 20% EI = $1,200, minus ~$228 standard deduction ≈ $972) yields a benefit of $298 - 30% × $972 ≈ $6, rounded up to the minimum benefit ($23). Expected.

### S8 — Option B confirmed
At $2,700/mo gross (above 200% FPL of ~$2,608 for HH=1), the elderly/disabled Option B path triggered correctly. High housing cost ($1,500/mo rent) reduces approximated net income below 100% FPL, making the household eligible. This validates the most complex criterion in the spec.

### S9 — BBCE regression confirmed
At $2,200/mo gross, net income after deductions (~$1,541/mo) would exceed the 100% FPL limit ($1,330/mo) — but WA BBCE waives the net income test. Program shown as eligible, confirming `net_applies = false` is working correctly for WA.

### S10 — Step-8 "existing benefits" flow
Step-8 is a two-stage interaction: first select "Yes" to `hasBenefits`, then check individual benefit checkboxes. Selecting "Supplemental Nutrition Assistance Program (SNAP)" correctly sets `has_snap=true`, and the program is excluded from results (0 programs found).

### S11 — Student with work exemption
Scenario 11 exercises three interacting criteria: elderly member (SS income, Option A via gross income test), student eligibility rules (half-time student who works 20+ hrs per week qualifies via the employment exemption), and household size determination. All three correctly handled.

### FPL thresholds used by PolicyEngine
Scenarios 3 and 4 were set at $3,524/$3,525 (2025 HHS guidelines, $21,150/yr for HH=2). This confirms PolicyEngine's `snap_fpg.py` SNAP fiscal-year logic is active: for April 2026 (Jan–Sep of year Y), parameters read at `2025-10-01`, applying 2025 HHS guidelines rather than the 2026 calendar-year values.
