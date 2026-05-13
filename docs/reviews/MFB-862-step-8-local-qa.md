# MFB-862 — “Already has benefits” step (Step 8) local QA vs production baseline

- **Review date:** 2026-05-11  
- **Reviewer:** Cursor agent (local click-through + API checks)  
- **Implementation PRs (paired):**
  - **Backend:** [MyFriendBen/benefits-api#1454](https://github.com/MyFriendBen/benefits-api/pull/1454) — `HasBenefitsProgramsView`, `GET /api/screener-options/<white_label>/has-benefits-programs/`, driven by `Program.show_in_has_benefits_step`.
  - **Frontend:** [MyFriendBen/benefits-calculator#2101](https://github.com/MyFriendBen/benefits-calculator/pull/2101) — removes static `category_benefits` + yes/no accordion; fetches the endpoint and renders selectable tiles grouped by category.

**Production baseline (old Step 8 — Colorado, for visual/UX comparison):**

- URL: [screener.myfriendben.org/co/13b12a8f-2f02-4b3d-ba71-d843962426f8/step-8/](https://screener.myfriendben.org/co/13b12a8f-2f02-4b3d-ba71-d843962426f8/step-8/)
- **Observed behavior:** Section title *“Tell us some final information about your household.”*; question *“Does anyone in your household currently have public assistance benefits?”* with **Yes / No / Prefer not to answer**. Choosing **Yes** opens an **accordion** of categories (e.g. Cash Assistance expanded with TANF, SSI, …; other categories collapsed). Subcopy explains avoiding duplicate results.

---

## Local environment (stack under test)

| Piece | Branch | Notes |
|--------|--------|--------|
| `benefits-api` | `origin/caton/mfb-862-part-2-has-benefits-programs-endpoint` | Same as #1454 |
| `benefits-calculator` | `origin/caton/mfb-862-redesign-has-benefits-step` | Same as #2101 |

**Backend run:** from `benefits-api` with venv activated:

```bash
ENABLE_GOOGLE_INTEGRATIONS=false python manage.py runserver 127.0.0.1:8000
```

(`GOOGLE_APPLICATION_CREDENTIALS` is required at import time when `ENABLE_GOOGLE_INTEGRATIONS` is true; disabling it allows a minimal local API without Sheets credentials.)

**Frontend run:** from `benefits-calculator`, `.env` pointing at `REACT_APP_DOMAIN_URL=http://127.0.0.1:8000` and a valid `REACT_APP_API_KEY`:

```bash
npm run dev
```

---

## Automated checks (backend)

On branch `caton/mfb-862-part-2-has-benefits-programs-endpoint`:

```bash
pytest screener/tests/test_has_benefits_programs.py -q
```

**Result:** `9 passed` (covers the has-benefits-programs endpoint behavior).

---

## API spot checks (local)

With DRF token auth against `http://127.0.0.1:8000`:

- **`GET /api/screener-options/co/has-benefits-programs/`** — returned `[]` in this clone’s sparse DB (no CO programs flagged `show_in_has_benefits_step` for meaningful local CO tile testing).
- **`GET /api/screener-options/wa/has-benefits-programs/`** — returned one program, `wa_ssi`, with nested `name`, `website_description`, and `category` objects matching `HasBenefitsProgramSerializer` (suitable for validating the FE grid against live JSON).

---

## Manual UI comparison (local new stack)

**Washington** was used because the local DB included a `show_in_has_benefits_step=True` program for WL `wa` (`wa_ssi`), so Step 8 still appears after the async fetch (Step 8 is omitted when the endpoint returns an empty list).

- Started at `http://localhost:3000/wa/step-1`, completed language + disclaimer (session created).
- Deep-linked to **`http://localhost:3000/wa/<uuid>/step-8`** (`73a03db5-27f7-4221-9dd6-52e99230fbcf` in this run).

**Observed (new Step 8):**

- No **Yes / No / Prefer not to answer** block.
- Question framing aligned with the redesign: *“Does anyone in your household currently receive any of these public benefits?”*
- Body copy matches the PR intent: *“Select all that apply. Receiving any of these benefits may automatically qualify you for other programs. Leave blank if none apply.”*
- **Category header:** “Cash Assistance” (`h3` in the accessibility tree).
- **Single selectable tile** (card / `button` with `aria-pressed` pattern): **Supplemental Security Income (SSI)** with the federal cash-assistance description — consistent with the payload from `/has-benefits-programs/` for `wa`.
- **No accordion**; layout is the flat tile pattern described in #2101.

**Contrast with production CO baseline:** old flow is radio + conditional accordion driven by FE static config; new flow is tile grid driven by admin `show_in_has_benefits_step` + API.

---

## Feedback / risks called out for human review

1. **Full WL parity:** Local QA used **WA** with one tile because of DB contents; **CO** (and the linked production session) should be re-validated on a seeded/staging DB with the merged PRs so the full tile set matches admin flags.
2. **FE CI:** [benefits-calculator#2101](https://github.com/MyFriendBen/benefits-calculator/pull/2101) previously reported a failing Playwright **e2e-tests** check on the branch — confirm green or update tests for the new Step 8 before release.
3. **Global Continue button styling** called out in #2101 (`PrevAndContinueButtons` defaulting to outlined + forward icon app-wide): confirm design sign-off.
4. **Translations / analytics** — same caveats as in the #2101 description (copy ID default message, loss of explicit “prefer not to answer” on this step).

---

## Verdict (local)

The **paired branches** behave as specified in a minimal end-to-end run: the FE Step 8 consumes the new endpoint and presents **category-grouped tiles** without the legacy **yes/no + accordion** pattern seen on production Colorado Step 8. Ship readiness still depends on full-WL staging validation, e2e status, and product sign-off on cross-step button styling and analytics.
