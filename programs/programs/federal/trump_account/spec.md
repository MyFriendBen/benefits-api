# Federal: 530A ("Trump") Accounts

- **Program**: 530A ("Trump") Accounts
- **Scope**: Federal
- **White Label**: tx (initial rollout; applies to any state white label)
- **Research Date**: 2026-03-09

## Eligibility Criteria

| # | Criterion | Screener Fields | Logic | Can Evaluate? | Notes | Source |
|---|-----------|-----------------|-------|---------------|-------|--------|
| 1 | Child must be under age 18 | `household_member.age` | `age < 18` | ✅ | Account must be opened before the child turns 18. The election is made in the calendar year the account is established. | IRS Notice 2025-68; IRC §530A |
| 2 | Child must be a U.S. citizen (for $1,000 pilot contribution) | `legal_status` | Via `legal_status_required` config filter | ✅ | Only U.S. citizens born Jan 1, 2025 – Dec 31, 2028 receive the $1,000 government seed. Non-citizens can still open an account; they simply will not receive the pilot contribution. Config restricts to `citizen` only. | IRS Notice 2025-68; Federal Register 2026-04534 |
| 3 | Child must have a valid Social Security Number | — | Not captured in screener | ❌ | **Gap**: The screener does not collect SSN. Surfaced via program description. | IRS Notice 2025-68 |
| 4 | Child born January 1, 2025 – December 31, 2028 (pilot contribution) | `household_member.birth_year`, `household_member.birth_month` | `2025 <= birth_year <= 2028` | ✅ | Only children born within this window receive the $1,000 government contribution. Children outside this window can still open an account (no government contribution). Calculator uses birth_year to determine pilot eligibility. | IRS Notice 2025-68; Federal Register 2026-04534 |
| 5 | No income limit | — | No income test | ✅ | There is no income limit for Trump Accounts. Any family may open one regardless of income. | Fidelity; Thrivent; IRS Notice 2025-68 |
## Coverage

- **Evaluable**: 4 of 5 criteria (80%)
- **Summary**: This calculator models only the $1,000 pilot contribution. Evaluable criteria are child age (under 18), U.S. citizenship (via `legal_status_required` config), and pilot birth window (Jan 2025–Dec 2028). No income test applies. Children outside the pilot window are not shown — while they can open an account, there is no government benefit to surface. The one unevaluable gap is SSN verification, which is not collected in the screener and is surfaced in the description.

## Benefit Value

- **Pilot contribution**: $1,000 (one-time, government-seeded)
- **Private contributions**: Up to $5,000/year per child (not modeled — this is family/employer money, not a government benefit)

**Methodology**: The government benefit is the one-time $1,000 pilot contribution made to accounts of U.S. citizen children born January 1, 2025 – December 31, 2028. This is a lump-sum value, not an annual recurring benefit. Private family contributions (up to $5,000/year) and employer contributions (up to $2,500/year, within the $5,000 limit) represent private wealth, not government transfers, and are not modeled as benefit value.

**Value Estimate Sources**:
- [IRS Notice 2025-68](https://www.irs.gov/newsroom/treasury-irs-issue-guidance-on-trump-accounts-established-under-the-working-families-tax-cuts-notice-announces-upcoming-regulations)
- [Federal Register: Trump Accounts Contribution Pilot Program (2026-04534)](https://www.federalregister.gov/documents/2026/03/09/2026-04534/trump-accounts-contribution-pilot-program)
- [Fidelity: What are Trump Accounts and how do you open one?](https://www.fidelity.com/learning-center/personal-finance/trump-accounts)
- [Thrivent: Trump Accounts for Kids — The Basics of Section 530A Accounts](https://www.thrivent.com/insights/financial-planning/trump-accounts-for-kids-the-basics-of-section-530a-accounts)

## Sources

- [IRS: Trump Accounts](https://www.irs.gov/trumpaccounts)
- [IRS Notice 2025-68 Guidance](https://www.irs.gov/newsroom/treasury-irs-issue-guidance-on-trump-accounts-established-under-the-working-families-tax-cuts-notice-announces-upcoming-regulations)
- [Federal Register: Trump Accounts Contribution Pilot Program (March 9, 2026)](https://www.federalregister.gov/documents/2026/03/09/2026-04534/trump-accounts-contribution-pilot-program)
- [trumpaccounts.gov](https://trumpaccounts.gov/)
- [Fidelity: What are Trump Accounts and how do you open one?](https://www.fidelity.com/learning-center/personal-finance/trump-accounts)
- [Thrivent: Trump Accounts for Kids — Section 530A Basics](https://www.thrivent.com/insights/financial-planning/trump-accounts-for-kids-the-basics-of-section-530a-accounts)
- [Vanguard: What to know about the new Trump accounts for kids](https://corporate.vanguard.com/content/corporatesite/us/en/corp/articles/what-to-know-about-new-trump-accounts-for-kids.html)

## Test Scenarios

| # | Description | Expected |
|---|-------------|----------|
| 1 | Newborn born June 2025 — core pilot-eligible case | Eligible, $1,000 |
| 2 | Child born Sept 2024 — outside pilot window, not shown | Not eligible |
| 3 | Child age 18 — age ceiling enforced | Not eligible |
| 4 | Adult-only household, no children | Not eligible |
| 5 | High-income family with 2025 newborn — no income limit | Eligible, $1,000 |
| 6 | Two pilot-eligible children, both born 2025 — per-child accumulation | Eligible, $2,000 |
| 7 | One pilot-eligible child (2025) + one non-pilot child (2024) | Eligible, $1,000 |
| 8 | Pregnant member — estimated due date (today + 280 days) in pilot window | Eligible, $1,000 |
| 9 | Pregnant member + existing pilot-eligible child | Eligible, $2,000 |
| 10 | Non-citizen household with child — citizenship gate enforced | Not eligible |
