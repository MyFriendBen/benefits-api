# Fixture: spec location guard (KS)

Read by `test_spec_locations.test_fixture_flags_each_bad_line`. Line numbers are asserted, so append cases at the end.

### Good: every accepted shape
- **Location**: ZIP `67202`, county `Sedgwick County`
* **Location**: Enter ZIP code `66502`, Select county `Pottawatomie County`
- ZIP 66604, Shawnee County, HH=4
- **Household**: 1 adult, Wyandotte County (zip 66101), no health coverage
- **Location**: Enter ZIP code `66604`

### Bad: bare name where KS is suffixed
- **Location**: ZIP `67202`, county `Sedgwick`

---

### Bad: unbackticked bare name
**Steps**: ZIP `66604`, county Shawnee. Household of 2.

---

### Bad: real county, wrong ZIP
- **Location**: ZIP `67202`, county `Riley County`

---

### Bad: ZIP with a parenthetical city
- **Location**: ZIP `67202` (Wichita), County `Sedgwick`

---

### Bad: bare name in a Household line
- ZIP `66101`, county `Wyandotte`, household size 1

---

### Bad: out-of-state ZIP without the rejection expected
- **Location**: ZIP `97201`, county `Multnomah County`

---

### Bad: ZIP-only location missing from the crosswalk
- **Location**: Enter ZIP code `66602`

---

### Good: out-of-state ZIP whose scenario expects the rejection
**Expected**: Rejected at screen creation — the API returns a 400 on `zipcode`.
- **Location**: ZIP `97201`, county `Multnomah County`
