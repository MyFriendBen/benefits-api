# MFB-975 — Metabase: Urgent Needs chart not loading for Texas

- **Linear:** [MFB-975](https://linear.app/myfriendben/issue/MFB-975)
- **Symptom:** The Urgent Needs (immediate needs) chart/table for **Texas** does not load **until** a dimension filter (e.g. **County**) is applied.
- **Likely cause:** SQL that compares `screen.county` (or another optional column) to a **Metabase variable that is NULL** when the filter is unset. In standard SQL, `column = NULL` is not true—it filters out every row. Applying a county picks a non-NULL value and the query suddenly returns rows.

There is no Metabase-native SQL in this repository; update the **Metabase question(s)** that power the Texas Urgent Needs dashboard per below.

---

## 1. Optional “County” (or similar) filter — recommended patterns

### A. Metabase optional clause (usually best)

Omit the predicate entirely when the filter is empty:

```sql
SELECT ...
FROM screener_screen s
JOIN screener_white_label wl ON wl.id = s.white_label_id
WHERE wl.code = 'tx'
  [[AND s.county = {{county}}]]
```

Configure `{{county}}` as a **Field Filter** (or compatible type) mapped to `screener_screen.county`. When the user leaves the filter unset, Metabase drops the `[[...]]` block.

### B. Explicit NULL-safe predicate

If you cannot use optional clauses, use a condition that is true when the parameter is NULL:

```sql
WHERE wl.code = 'tx'
  AND ({{county}} IS NULL OR s.county = {{county}})
```

**Note:** Exact parameter syntax depends on Metabase variable type (Field Filter vs Text vs Date). For Field Filters, prefer **pattern A**.

### C. Avoid `= NULL` / `!= NULL`**

Use `IS NULL` / `IS NOT NULL`. Never write `county = NULL` expecting “unknown county.”

---

## 2. Boolean `needs_*` columns

`screener_screen.needs_food`, `needs_housing_help`, etc. may be **NULL** for incomplete or legacy rows. In PostgreSQL, bare `WHERE needs_food` behaves like “is TRUE” and **excludes** NULLs.

If the chart should treat NULL as “did not indicate need”, use:

```sql
COALESCE(s.needs_food, FALSE)
```

in expressions or predicates (e.g. `WHERE COALESCE(s.needs_food, FALSE) OR COALESCE(s.needs_housing_help, FALSE)`).

---

## 3. Data expectations for Texas

- **`screen.county`** can be **NULL** for sessions that never completed the zip/county step, ambiguous states, or older data.
- Texas has many **multi-county ZIPs**; users must choose a county on the zip step when more than one applies—until then, `county` may be unset.

Analytics that **inner join** on a county dimension table with `screen.county` will drop NULL counties; prefer **left join** or filter using the patterns above.

---

## 4. Verification checklist (in Metabase)

1. Open the Texas Urgent Needs question with **no** county (or zip) filter → should return rows (subject to other filters and date range).
2. Clear all optional filters → query must not collapse to `= NULL` on any column.
3. Apply County → subset should narrow correctly.

---

## 5. Repo linkage

This document is the **reference fix** for MFB-975. The underlying application schema is unchanged; **update Metabase SQL** (or saved questions) using sections 1–2. The export data dictionary in `export_screener_data.py` clarifies that `screen.county` may be NULL for downstream analysts.
