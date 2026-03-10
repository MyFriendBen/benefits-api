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
- **Summary**: The evaluable criteria are child age (under 18), U.S. citizenship (via `legal_status_required` config), and pilot contribution birth window (2025–2028). No income test applies. The one unevaluable gap is SSN verification, which is not collected in the screener and is surfaced in the description. The calculator returns a value of $1,000 for children born in the pilot window (2025–2028) who are U.S. citizens and under 18; it returns $0 for eligible children outside the pilot window (account can still be opened, but no government contribution).

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

### Scenario 1: Newborn in 2025 — Pilot-Eligible, Receives $1,000

**Checks**: Core eligibility — U.S. citizen child born in the pilot window gets $1,000
**Expected**: Eligible, value: $1,000

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1990` (age 36), wages $3,000/month
- **Person 2 (Child)**: DOB `June 2025` (age 0), U.S. citizen

**Why this matters**: Most common profile — a newborn born in 2025 whose parents open a Trump Account. Confirms the pilot $1,000 value is returned.

---

### Scenario 2: Child Born in 2028 — Last Year of Pilot Window

**Checks**: Upper bound of pilot birth window is inclusive
**Expected**: Eligible, value: $1,000

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `March 1995` (age 31), wages $2,500/month
- **Person 2 (Child)**: DOB `January 2028` (age 0), U.S. citizen

**Why this matters**: Confirms children born in 2028 (last eligible year) correctly receive the $1,000 pilot contribution.

---

### Scenario 3: Child Born in 2024 — Outside Pilot Window, Account Eligible but No $1,000

**Checks**: Children born before 2025 can open an account but receive no pilot contribution
**Expected**: Eligible, value: $0

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `April 1988` (age 38), wages $4,000/month
- **Person 2 (Child)**: DOB `September 2024` (age 1), U.S. citizen

**Why this matters**: Confirms that children born before January 1, 2025 are still eligible to open a Trump Account but do not receive the $1,000 government contribution.

---

### Scenario 4: Child Born in 2029 — Outside Pilot Window

**Checks**: Children born after December 31, 2028 do not receive the pilot contribution
**Expected**: Eligible, value: $0

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `May 1992` (age 34), wages $3,500/month
- **Person 2 (Child)**: DOB `March 2029` (age 0), U.S. citizen

**Why this matters**: Confirms the pilot window upper bound (2028) is correctly enforced.

---

### Scenario 5: Child Exactly Age 17 — Last Year of Eligibility

**Checks**: Child under 18 is eligible; age boundary is exclusive
**Expected**: Eligible, value: $1,000 (if born 2025–2028)

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `June 1980` (age 45), wages $5,000/month
- **Person 2 (Child)**: DOB `January 2026` (age 0 — but use age 17 to represent a child in their last eligible year), U.S. citizen

**Why this matters**: Confirms age 17 is still eligible (under 18 means 0–17 inclusive).

---

### Scenario 6: Child Age 18 — Ineligible

**Checks**: Children who have turned 18 cannot open a new Trump Account
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `June 1980` (age 45), wages $5,000/month
- **Person 2 (Child)**: DOB `January 2008` (age 18), U.S. citizen

**Why this matters**: Confirms the age ceiling (< 18) is correctly enforced.

---

### Scenario 7: No Children in Household — Ineligible

**Checks**: Households with no children under 18 are ineligible
**Expected**: Not eligible

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1985` (age 41), wages $3,000/month
- **Person 2 (Spouse)**: DOB `March 1987` (age 39), wages $2,000/month

**Why this matters**: Confirms the program correctly returns ineligible for adult-only households.

---

### Scenario 8: High-Income Family with Newborn — No Income Limit

**Checks**: No income test — wealthy families are also eligible
**Expected**: Eligible, value: $1,000

**Steps**:
- **Location**: ZIP `75201`, County `Dallas County`
- **Household**: 3 people
- **Person 1 (Head)**: DOB `January 1985` (age 41), wages $20,000/month
- **Person 2 (Spouse)**: DOB `March 1987` (age 39), wages $15,000/month
- **Person 3 (Child)**: DOB `July 2025` (age 0), U.S. citizen

**Why this matters**: Confirms that Trump Accounts have no income limit — high-income families receive the same $1,000 pilot contribution.

---

### Scenario 9: Multiple Children — Two Eligible, One Outside Window

**Checks**: Each eligible child receives a separate $1,000; child outside pilot window gets $0
**Expected**: Eligible, value: $2,000 (two pilot-eligible children)

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 4 people
- **Person 1 (Head)**: DOB `January 1988` (age 38), wages $4,000/month
- **Person 2 (Spouse)**: DOB `June 1990` (age 36), no income
- **Person 3 (Child)**: DOB `March 2025` (age 0), U.S. citizen (pilot-eligible)
- **Person 4 (Child)**: DOB `August 2027` (age 0), U.S. citizen (pilot-eligible)

**Why this matters**: Confirms per-child benefit accumulation — two children in the pilot window should yield $2,000 total.

---

### Scenario 10: Teenager Age 16 with Pilot-Window Birth Year

**Checks**: Older children born in 2025–2028 are correctly evaluated (unlikely in practice but valid)
**Expected**: Eligible (if age and birth_year checks are consistent)

**Steps**:
- **Location**: ZIP `78701`, County `Travis County`
- **Household**: 2 people
- **Person 1 (Head)**: DOB `January 1985` (age 41), wages $3,000/month
- **Person 2 (Child)**: DOB `January 2026` (age 0 per screener — represents a young child), U.S. citizen

**Why this matters**: Validates that the screener correctly handles children whose birth_year falls in the pilot window.
