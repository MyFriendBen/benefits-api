# Foster care screener gaps

What `HouseholdMember.was_in_foster_care` does and does not answer, and which specs
still carry an open gap because of it.

The field is a single per-member boolean behind the Step 5 Special Circumstances tile
**"Ever in foster care, even briefly"**. It was scoped that way deliberately: PolicyEngine
treats `was_in_foster_care` as a bare input and derives every former-foster-youth age
window itself by pairing it with `age` (`medicaid_work_requirement_eligible`,
`is_snap_abawd_exempt`, `co_eitc`). Nothing in PolicyEngine consumes age at entry, exit
type, or state of care, so one boolean is the whole PolicyEngine contract.

The gaps below are the cost of that scoping. **A later iteration adding granularity to the
foster care question is expected** — most of these resolve together, so treat this file as
the shared list rather than re-deriving it per program.

## What one boolean cannot express

| Missing fact | Who needs it | Current handling |
| --- | --- | --- |
| **Exit type** — aged out / adopted from care / kinship guardianship | KS Medicaid criterion 13 (adoption assistance); MA DCF waiver *excludes* adoptees while its companion waiver covers them; TX §54.367; every Foster Care milestone program's care-pathway rule | Description copy |
| **Age at entry or exit** (13th / 14th / 16th / 17th birthday thresholds) | ETV state variants, CO FosterEd, TX tuition waiver | Description copy |
| **State where care occurred** | Every Foster Care milestone program — matched on the white label as a residence proxy, which fails in both directions | Per-program state-of-care WarningMessage |
| **Formal foster placement vs. informal kinship care** | IL/TX/WA HCV *income rules*, WA EITC. **Not** resolved by adding granularity to *this* tile — it is a question about an existing `fosterChild` household member, not about the person answering | Documented divergence |
| **Ward of court, orphan, emancipated minor, legal guardianship** | WA HCV's HUD "independent student" exemption lists these alongside foster care; a youth who was a ward of court but never in care still won't match | Inclusivity assumption |
| **On Medicaid at 18** | WA Medicaid Foster Care Alumni — the federal rule requires foster care *and* Medicaid on the 18th birthday | Description copy |
| **Kinship care with a D&N adjudication** | CO FosterEd's second eligibility pathway | Description copy |

## Open gaps by spec

**Resolved or largely resolved by the boolean**

- `cross_white_label/medicaid/specs/ks.md` criterion 12 — current + former foster youth to 26
- `cross_white_label/medicaid/specs/wa.md` criterion 13 — Foster Care Alumni sub-gap
- `cross_white_label/head_start/specs/*.md`, `early_head_start/specs/*.md` — foster categorical now catches children reported as `child` and young adults who are their own head of household

⚠️ Both Medicaid pathways are **coupled to Head Start**: neither Medicaid calculator declares
`FosterCareDependency`, so the value only reaches PolicyEngine because Head Start declares it and all
programs share one merged household payload per screen. Deactivating Head Start in a white label would
silently break them. Unlikely in practice, but the durable fix is declaring the dependency explicitly on
Medicaid's `pe_inputs`.

**Field now suffices, calculator not yet wired** — each needs its own ticket, because reading the
field changes results

- `white_labels/tx/hcv/spec.md` criterion 8 — student restrictions. This spec proposed the tile under the
  name `previously_in_foster_care`. Wiring it *narrows* the current inclusivity assumption toward the real
  rule.
- `white_labels/wa/hcv/spec.md` criterion 8 — the HUD "independent student" exemption. This spec proposed
  the tile as a "past foster care / ward of court history Boolean". Wiring it *widens* eligibility (one more
  exemption satisfied, so fewer students flagged ineligible). Only closes the foster-care half of that
  exemption; ward of court, orphan, emancipated minor and legal guardianship remain uncovered.
- `white_labels/ma/youthworks/spec.md` criterion 4 — foster care is one of eleven qualifying risk factors,
  so the field can only ever raise confidence, never gate. Wiring it narrows criterion 4 from a blanket
  inclusivity assumption to a real check.

**Still open — would be resolved by more granularity on this question**

- `cross_white_label/medicaid/specs/ks.md` criterion 13 — adoption-assistance children. Needs exit type.
- `white_labels/ks/promise_act/spec.md` criterion 2 — foster-care history is one of five qualifying
  educational-history pathways, but it appears as an **exclusion** (ineligible if eligible for the Kansas
  Foster Child Educational Assistance Act waiver). The boolean could let us *narrow* here rather than widen,
  which is the opposite direction from every other consumer — do not wire it in without a product decision.

**Still open — NOT resolved by more granularity on this question**

These need a *different* field: a follow-up distinguishing formal foster placement from informal kinship
care, asked about an existing household member with `relationship == "fosterChild"`.

- `white_labels/il/hcv/spec.md`, `white_labels/tx/hcv/spec.md`, `white_labels/wa/hcv/spec.md` — the HCV
  **income rules**, a separate gap from the student-rule one above. 24 CFR 5.603 excludes foster children
  from the dependent definition, but MFB's single `fosterChild` value conflates foster placement with
  kinship care. Resolved in the widening direction today, overstating the
  subsidy for a genuine foster placement.
- `cross_white_label/eitc/specs/wa.md` criterion 9 — the IRS "eligible foster child" test requires formal
  placement by an agency, tribe, or court order. Informal arrangements do not qualify, producing false
  positives.

**Accepted, not a gap to close**

- `cross_white_label/nslp/specs/wa.md` criterion 5 — PolicyEngine puts `was_in_foster_care` in the
  **SPMUnit-level** `gov.usda.school_meals.categorical_eligibility` adds-list, so any one member's flag makes
  the whole unit free-meal eligible. Federal rule makes the pathway individual to the child. Accepted:
  inclusivity direction, the school verifies at application, and narrowing it would cost the Medicaid and
  CO EITC pathways that need the adult signal.
