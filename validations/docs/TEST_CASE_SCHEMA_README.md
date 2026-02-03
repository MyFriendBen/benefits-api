# Test Case Schema Documentation

This document describes the JSON schema for creating test cases that import Screens (household data) and Validations (expected eligibility results) into the MyFriendBen system.

## Files

- **[test_case_schema.json](../management/commands/test_case_schema.json)** - JSON Schema (draft-07) defining the structure
- **[test_case_example.json](../management/commands/test_case_example.json)** - Example test cases demonstrating various scenarios

## Schema Overview

Each test case has three required top-level fields:

```json
{
  "notes": "Human-readable description of the test case",
  "household": { /* Screen payload matching ScreenSerializer */ },
  "expected_results": { /* Single validation or array of validations */ }
}
```

## Field Descriptions

### `notes` (string, required)
A clear description of what this test case validates.

**Examples:**
- `"TX ACA - Ineligible due to household income above 400% FPL"`
- `"CO SNAP - Eligible low-income household with children"`
- `"NC Multiple Programs - Senior with SSI and veteran status"`

### `household` (object, required)
The complete household data that will be submitted to create a Screen. This object maps directly to the `ScreenSerializer` and must include:

**Required Fields:**
- `white_label` (string) - One of: `"co"`, `"tx"`, `"nc"`, `"ma"`, `"il"`
- `household_members` (array) - At least one household member
- `expenses` (array) - Array of expense objects (use empty array `[]` if no expenses)

**Commonly Used Fields:**
- `is_test` (boolean, default: true) - Should be true for test data
- `agree_to_tos` (boolean)
- `is_13_or_older` (boolean)
- `zipcode` (string, 5 digits)
- `county` (string) - See [County Naming Conventions](#county-naming-conventions) below
- `household_size` (integer)
- `household_assets` (number)
- `last_tax_filing_year` (string, YYYY format)

**Program Status Fields (has_*):**
Boolean flags indicating if the household already receives benefits:
- `has_snap`, `has_tanf`, `has_wic`, `has_medicaid`, `has_aca`, etc.

**Needs Fields (needs_*):**
Boolean flags indicating what assistance the household needs:
- `needs_food`, `needs_housing_help`, `needs_baby_supplies`, etc.

**Health Insurance Type Fields (has_*_hi):**
- `has_employer_hi`, `has_private_hi`, `has_medicaid_hi`, etc.

**Nested Objects:**
- `household_members` - Array of household member objects (see below)
- `expenses` - Array of expense objects (see below)
- `energy_calculator` - Energy assistance data (see below)

### `expected_results` (object or array, required)
Defines the expected eligibility outcomes to validate against.

**Single Validation:**
```json
{
  "program_name": "snap",
  "eligible": true,
  "value": 600.00
}
```

**Multiple Validations:**
```json
[
  {
    "program_name": "snap",
    "eligible": true,
    "value": 281.00
  },
  {
    "program_name": "nc_medicaid",
    "eligible": true,
    "value": 0
  }
]
```

**Fields:**
- `program_name` (string, required) - Program's `name_abbreviated` (e.g., `"snap"`, `"tx_aca"`, `"eitc"`)
- `eligible` (boolean, required) - Expected eligibility status
- `value` (number, optional) - Expected monthly benefit amount (0 for programs with no cash value)

## Household Member Structure

Each member in the `household_members` array should include:

**Required:**
- `relationship` (string) - One of:
  - `"headOfHousehold"`, `"spouse"`, `"child"`, `"parent"`, `"fosterChild"`, `"fosterParent"`, `"stepParent"`, `"grandParent"`, `"domesticPartner"`, `"other"`
- `age` (integer, 0-150)
- `insurance` (object) - Health insurance coverage object (see below). Minimum: `{"none": true}`

**Optional Demographic Fields:**
- `birth_year` (integer, YYYY) - Used with `birth_month` for precise age calculation
- `birth_month` (integer, 1-12) - Used with `birth_year`

**Status Fields (all boolean, default false):**
- `student`, `student_full_time`, `pregnant`, `unemployed`, `worked_in_last_18_mos`
- `visually_impaired`, `disabled`, `long_term_disability`, `veteran`
- `medicaid`, `disability_medicaid`
- `has_income`, `has_expenses`

**Nested Objects:**
- `income_streams` (array) - Income sources (see below)
- `insurance` (object) - Health insurance coverage (see below)
- `energy_calculator` (object) - Energy assistance qualifiers (see below)

### Income Stream Structure

```json
{
  "type": "wages",
  "amount": 2000.00,
  "frequency": "monthly",
  "hours_worked": 40  // Required only if frequency is "hourly"
}
```

**Income Types:**
- `"wages"`, `"selfEmployment"`, `"sSI"`, `"alimony"`, `"cashAssistance"`
- `"sSDisability"`, `"sSRetirement"`, `"sSSurvivor"`, `"sSDependent"` (Social Security types)
- `"childSupport"`, `"unemployment"`, `"workersCompensation"`
- `"pension"`, `"veteran"`, `"veteransBenefits"`
- `"rentalIncome"`, `"rental"`, `"investment"`, `"deferredComp"`, `"other"`

**Frequency Values:**
- `"monthly"`, `"weekly"`, `"biweekly"`, `"semimonthly"`, `"yearly"`, `"hourly"`

**Important:** If `frequency` is `"hourly"`, you **must** include `hours_worked`.

### Insurance Structure

```json
{
  "dont_know": false,
  "none": false,
  "employer": true,
  "private": false,
  "chp": false,
  "medicaid": false,
  "medicare": false,
  "emergency_medicaid": false,
  "family_planning": false,
  "va": false,
  "mass_health": false
}
```

**Defaults:** `dont_know: false`, `none: true`, all others: `false`

### Expense Structure

```json
{
  "type": "childcare",
  "amount": 500.00,
  "frequency": "monthly"
}
```

**Common Expense Types:**
- `"childcare"`, `"rent"`, `"mortgage"`, `"medical"`, `"utilities"`

**Frequency Values:**
- `"monthly"`, `"weekly"`, `"biweekly"`, `"semimonthly"`, `"yearly"`

**Example with no expenses:**
```json
{
  "household": {
    "white_label": "tx",
    "household_members": [...],
    "expenses": []
  }
}
```

### Energy Calculator (Screen Level)

```json
{
  "is_home_owner": true,
  "is_renter": false,
  "electricity_is_disconnected": false,
  "has_past_due_energy_bills": true,
  "has_old_car": false,
  "needs_water_heater": false,
  "needs_hvac": false,
  "needs_stove": false,
  "needs_dryer": false,
  "electric_provider": "xcel_energy",
  "electric_provider_name": "Xcel Energy",
  "gas_provider": null,
  "gas_provider_name": null
}
```

### Energy Calculator (Member Level)

```json
{
  "surviving_spouse": false,
  "receives_ssi": true,
  "medical_equipment": true
}
```

## Usage Patterns

### Test Case for Ineligibility

When testing that a household is **not eligible**:

```json
{
  "notes": "TX ACA - Ineligible due to income above 400% FPL",
  "household": {
    "white_label": "tx",
    "household_members": [
      {
        "relationship": "headOfHousehold",
        "age": 40,
        "income_streams": [
          { "type": "wages", "amount": 8000.00, "frequency": "monthly" }
        ]
      }
    ]
  },
  "expected_results": {
    "program_name": "tx_aca",
    "eligible": false,
    "value": 0
  }
}
```

### Test Case for Eligibility with Value

When testing eligibility **with a specific benefit amount**:

```json
{
  "notes": "CO SNAP - Eligible low-income household",
  "household": {
    "white_label": "co",
    "household_size": 4,
    "household_members": [
      {
        "relationship": "headOfHousehold",
        "age": 32,
        "income_streams": [
          { "type": "wages", "amount": 1800.00, "frequency": "monthly" }
        ]
      }
    ]
  },
  "expected_results": {
    "program_name": "snap",
    "eligible": true,
    "value": 600.00
  }
}
```

### Test Case for Multiple Programs

When validating **multiple program eligibilities**:

```json
{
  "notes": "NC Multiple Programs - Senior with complex eligibility",
  "household": {
    "white_label": "nc",
    "household_members": [
      {
        "relationship": "headOfHousehold",
        "age": 68,
        "veteran": true,
        "disabled": true,
        "income_streams": [
          { "type": "sSI", "amount": 914.00, "frequency": "monthly" }
        ]
      }
    ]
  },
  "expected_results": [
    { "program_name": "snap", "eligible": true, "value": 281.00 },
    { "program_name": "nc_medicaid", "eligible": true, "value": 0 },
    { "program_name": "nc_energy_assistance", "eligible": true, "value": 350.00 }
  ]
}
```

### Test Case with Hourly Income

When household member earns **hourly wages**:

```json
{
  "household_members": [
    {
      "relationship": "headOfHousehold",
      "age": 28,
      "income_streams": [
        {
          "type": "wages",
          "amount": 15.50,
          "frequency": "hourly",
          "hours_worked": 35
        }
      ]
    }
  ]
}
```

## County Naming Conventions

**CRITICAL:** County names must follow specific formatting rules by state to ensure proper data lookups and prevent `KeyError` exceptions during program eligibility calculations.

### States Requiring "County" Suffix

For these states, **ALWAYS include " County"** after the county name:

- **Colorado (CO)**: `"Denver County"`, `"Arapahoe County"`, `"Jefferson County"`, `"Adams County"`
- **North Carolina (NC)**: `"Wake County"`, `"Durham County"`, `"Alamance County"`

### States WITHOUT "County" Suffix

For these states, use **ONLY the county name** (no " County"):

- **Texas (TX)**: `"Travis"`, `"Harris"`, `"Dallas"`, `"Tarrant"`
- **Illinois (IL)**: `"Cook"`, `"Madison"`, `"St. Clair"`, `"Jackson"`

### States Using City Names

For these states, use **city names** instead of county names (MA benefits are city-based):

- **Massachusetts (MA)**: `"Boston"`, `"Cambridge"`, `"Somerville"`, `"Worcester"`

### Examples

✅ **Correct:**
```json
{
  "white_label": "co",
  "zipcode": "80202",
  "county": "Denver County"
}
```

```json
{
  "white_label": "tx",
  "zipcode": "78701",
  "county": "Travis"
}
```

❌ **Incorrect:**
```json
{
  "white_label": "co",
  "zipcode": "80202",
  "county": "Denver"  // Missing "County" suffix!
}
```

```json
{
  "white_label": "tx",
  "zipcode": "78701",
  "county": "Travis County"  // Should not have "County" suffix!
}
```

### Why This Matters

County names are used to:
1. Look up Area Median Income (AMI) data from HUD and Google Sheets services
2. Determine geographic eligibility for county-specific programs (e.g., Denver Property Tax Relief)
3. Match household data with external APIs (PolicyEngine, HUD Income Limits)

**Using incorrect county names will cause:**
- `KeyError` exceptions during eligibility calculations
- Failed test case validations
- Incorrect benefit estimates or program ineligibility

### Valid County Names Reference

For Colorado counties, see: [`programs/co_county_zips.py`](../../programs/co_county_zips.py)

For other states, consult the HUD Income Limits API documentation or state-specific county reference files.

## Important Constraints

1. **White Label Must Exist** - The `white_label` code must reference an existing white label configuration in the database

2. **County Names Must Follow Conventions** - See [County Naming Conventions](#county-naming-conventions) above to avoid `KeyError` exceptions

3. **Birth Date Validation** - If providing both `birth_year` and `birth_month`, they cannot represent a future date

4. **Hourly Income Requires Hours** - If an income stream has `frequency: "hourly"`, the `hours_worked` field is required

5. **Frozen Screens** - Once validations are added to a screen, the screen becomes frozen (read-only)

6. **Create-Only Fields** - These fields can only be set during creation:
   - `is_test`
   - `external_id`
   - `referrer_code`
   - UTM fields (`utm_id`, `utm_source`, etc.)

7. **Program Names** - Use the program's `name_abbreviated` field, not the full name or display name

8. **Value Amounts** - By default, benefit values are monthly amounts unless the program's `value_format` specifies otherwise (e.g., `"lump_sum"` or `"estimated_annual"`)

## Schema Validation

You can validate your test case JSON files against the schema using standard JSON Schema validators:

**Using Python:**
```python
import json
from jsonschema import validate

with open('test_case_schema.json') as schema_file:
    schema = json.load(schema_file)

with open('my_test_cases.json') as test_file:
    test_cases = json.load(test_file)

for test_case in test_cases:
    validate(instance=test_case, schema=schema)
    print(f"✓ Valid: {test_case['notes']}")
```

**Using Node.js (with ajv):**
```javascript
const Ajv = require('ajv');
const ajv = new Ajv();

const schema = require('./test_case_schema.json');
const testCases = require('./my_test_cases.json');

const validate = ajv.compile(schema);

testCases.forEach(testCase => {
  const valid = validate(testCase);
  if (valid) {
    console.log(`✓ Valid: ${testCase.notes}`);
  } else {
    console.error(`✗ Invalid: ${testCase.notes}`);
    console.error(validate.errors);
  }
});
```

## Import Script Integration

When building an import script, the expected workflow is:

1. **Load test case JSON** - Read and validate against schema
2. **Create Screen** - POST to `/api/screens/` with `household` payload
3. **Capture Screen UUID** - Save the returned screen UUID
4. **Create Validations** - POST to `/api/validations/` for each expected result:
   ```json
   {
     "screen_uuid": "<uuid-from-step-2>",
     "program_name": "snap",
     "eligible": true,
     "value": 600.00
   }
   ```
5. **Verify Screen Frozen** - After validations are created, screen should be marked as frozen

## Examples

See [test_case_example.json](../management/commands/test_case_example.json) for complete working examples covering:

1. **TX ACA Ineligibility** - Income above 400% FPL
2. **CO SNAP Eligibility** - Low-income family with children
3. **NC Multiple Programs** - Senior with veteran status and SSI
4. **MA EITC** - Working family with self-employment income
5. **IL Hourly Worker** - Single parent with hourly wages and childcare expenses

Each example demonstrates different aspects of the schema including:
- Various household compositions
- Different income types and frequencies
- Multiple program validations
- Energy calculator integration
- Insurance and expense tracking

## Additional Notes

- All monetary values should be decimals (e.g., `1234.56`)
- Dates should use ISO 8601 format (e.g., `"2024-11-20T10:00:00Z"`)
- UUIDs are auto-generated if not provided
- Boolean fields default to `false` unless specified in the schema
- The schema supports both single validation objects and arrays of validations
