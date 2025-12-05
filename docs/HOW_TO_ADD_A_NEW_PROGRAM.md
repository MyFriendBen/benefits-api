# How to Add a New Program (Backend)

This guide covers all the backend changes needed to add a new benefit program to the MyFriendBen benefits-api system.

> **Related Documentation**: For frontend changes, see [benefits-calculator/HOW_TO_ADD_A_NEW_PROGRAM.md](../benefits-calculator/HOW_TO_ADD_A_NEW_PROGRAM.md)

## Table of Contents

1. [Overview](#overview)
2. [Step 1: Create the Calculator](#step-1-create-the-calculator)
3. [Step 2: Create JSON Configuration](#step-2-create-json-configuration)
4. [Step 3: Import Program Configuration](#step-3-import-program-configuration)
5. [Step 4: Update White Label Configuration (If Needed)](#step-4-update-white-label-configuration-if-needed)
6. [Step 5: Create Database Migration](#step-5-create-database-migration)
7. [Step 6: Update Serializer](#step-6-update-serializer)
8. [Testing Your Program](#testing-your-program)
9. [Example PRs](#example-prs)

---

## Overview

### Workflow Summary

**All programs require**:
- Steps 1-3: Calculator → JSON Config → Import

**Programs with "already have" checkbox also require**:
- Steps 4-6: White Label Config → Migration → Serializer
- Frontend changes (see [benefits-calculator/docs/HOW_TO_ADD_A_NEW_PROGRAM.md](../../benefits-calculator/docs/HOW_TO_ADD_A_NEW_PROGRAM.md))

**Important**: Steps 4-6 and frontend changes can be done in **either order**, but testing the "already have" functionality requires **both backend and frontend changes** to be complete.

### Two Types of Program Calculators

There are **two types of program calculators**:

### ProgramCalculator (Custom Logic)
- For programs with custom eligibility rules you define
- Requires writing Python eligibility logic
- Examples: Colorado Cash Back, Illinois CSFP
- **File**: [programs/programs/calc.py](programs/programs/calc.py)

### PolicyEngineCalculator (API-Based)
- Uses the PolicyEngine.org API for calculations
- Three subtypes: Members, SPM Units, Tax Units
- Examples: Colorado Medicaid, EITC, WIC
- **File**: [programs/programs/policyengine/calculators/base.py](programs/programs/policyengine/calculators/base.py)

---

## Step 1: Create the Calculator

### Option A: ProgramCalculator (Custom Logic)

#### 1.1 Create the Calculator Directory

```bash
mkdir -p programs/programs/{state}/{program_name}
touch programs/programs/{state}/{program_name}/__init__.py
touch programs/programs/{state}/{program_name}/calculator.py
```

**Example for Illinois CSFP**:
```bash
mkdir -p programs/programs/il/commodity_supplemental_food_program
touch programs/programs/il/commodity_supplemental_food_program/__init__.py
touch programs/programs/il/commodity_supplemental_food_program/calculator.py
```

#### 1.2 Implement the Calculator

**Simple Example** (Colorado Cash Back):

```python
# programs/programs/co/cash_back/calculator.py
from programs.programs.calc import MemberEligibility, ProgramCalculator

class CashBack(ProgramCalculator):
    member_amount = 750
    min_age = 18
    dependencies = ["age"]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        e.condition(member.age >= CashBack.min_age)
```

**Complex Example** (Illinois CSFP):

```python
# programs/programs/il/commodity_supplemental_food_program/calculator.py
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility

class IlCommoditySupplementalFoodProgram(ProgramCalculator):
    dependencies = ["age", "county", "income_amount", "income_frequency", "household_size"]
    eligible_counties = ["Cook", "St. Clair", "Madison", ...]  # 24 counties
    minimum_age = 60
    fpl_percent = 1.50
    member_amount = 50 * 12  # $50/month * 12 months

    def household_eligible(self, e: Eligibility):
        # Check: User hasn't already selected this benefit
        e.condition(not self.screen.has_benefit("il_csfp"))

        # Check: Eligible county
        e.condition(self.screen.county in self.eligible_counties)

        # Check: Income eligibility (150% of FPL)
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit)

    def member_eligible(self, e: MemberEligibility):
        # Check: Age eligible (60+)
        member = e.member
        e.condition(member.age >= self.minimum_age)

    def member_value(self, member):
        return self.member_amount
```

**Key Methods**:
- `household_eligible(e: Eligibility)` - Set household-level conditions
- `member_eligible(e: MemberEligibility)` - Set member-level conditions
- `household_value()` - Calculate total household benefit
- `member_value(member)` - Calculate per-member benefit
- `dependencies` - List of data requirements (e.g., "age", "income_amount")

#### 1.3 Register the Calculator

Add your calculator to the state's calculator registry:

```python
# programs/programs/il/__init__.py
from .commodity_supplemental_food_program.calculator import IlCommoditySupplementalFoodProgram
from ..calc import ProgramCalculator

il_calculators: dict[str, type[ProgramCalculator]] = {
    "il_csfp": IlCommoditySupplementalFoodProgram,  # ← Key must match name_abbreviated!
    "il_family_care": FamilyCare,
    # ... other calculators
}
```

**CRITICAL**: The dictionary key (e.g., `"il_csfp"`) **must exactly match** the `name_abbreviated` field you'll use in Step 2.

**Naming Convention**: `{state_code}_{program_short_name}`
- Illinois CSFP: `il_csfp`
- Texas SNAP: `tx_snap`
- Colorado Medicaid: `co_medicaid`

### Option B: PolicyEngineCalculator (API-Based)

#### 1.1 Choose the Right Base Class

```python
from programs.programs.policyengine.calculators.base import (
    PolicyEngineMembersCalculator,      # For per-member benefits (WIC, SSI, Medicaid)
    PolicyEngineSpmCalulator,           # For SPM units
    PolicyEngineTaxUnitCalulator,       # For tax benefits (EITC, CTC)
)
```

#### 1.2 Implement the Calculator

```python
# programs/programs/co/pe/member.py
from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine import dependency

class CoMedicaid(PolicyEngineMembersCalculator):
    pe_name = "co_medicaid"                    # PolicyEngine program identifier
    pe_category = "people"                     # PolicyEngine unit type

    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.household.CoStateCodeDependency,
        # ... other dependencies
    ]

    pe_outputs = [
        dependency.member.MedicaidEligible,
    ]

    amount = 310 * 12  # Monthly value

    def member_value(self, member):
        is_eligible = self.get_member_dependency_value(
            dependency.member.MedicaidEligible,
            member.id
        ) > 0

        return self.amount if is_eligible else 0
```

#### 1.3 Register the Calculator

Same as ProgramCalculator - add to state's `__init__.py` with matching key.

---

## Step 2: Create JSON Configuration

### 2.1 Create Configuration File

Copy an existing config as a template:

```bash
cp programs/management/commands/import_program_config_data/data/il_csfp_initial_config.json \
   programs/management/commands/import_program_config_data/data/{your_program}_initial_config.json
```

### 2.2 Complete the Configuration

```json
{
  "white_label": {
    "code": "il"
  },

  "program_category": {
    "external_name": "il_food_nutrition"
  },

  "program": {
    "name_abbreviated": "il_csfp",                          // ← MUST MATCH CALCULATOR KEY!
    "year": "2025",                                         // FPL year
    "legal_status_required": [
      "citizen",
      "refugee",
      "gc_5plus",
      "non_citizen"
    ],
    "name": "Commodity Supplemental Food Program (CSFP)",
    "description": "CSFP helps low-income seniors aged 60 and over with monthly food packages...",
    "apply_button_link": "https://www.dhs.state.il.us/...",
    "apply_button_description": "Learn More Here",
    "estimated_application_time": "15 minutes",
    "website_description": "Monthly food packages for eligible seniors",
    "estimated_value": "",
    "external_name": "il_csfp",
    "active": true,
    "low_confidence": false,
    "show_on_current_benefits": true,
    "value_format": null
  },

  "documents": [
    {
      "external_name": "il_home",
      "text": "Proof of home address (ex: lease, mortgage statement, utility bill)"
    },
    {
      "external_name": "id_proof",
      "text": "Proof of identity (ex: driver's license, official state ID card)"
    },
    {
      "external_name": "income_proof",
      "text": "Proof of income (ex: pay stubs, tax returns, benefit statements)"
    }
  ],

  "navigators": [
    {
      "external_name": "greater_chicago_food_depository",
      "name": "Greater Chicago Food Depository",
      "email": "olderadults@gcfd.org",
      "description": "If you would like to apply for CSFP, please contact the Greater Chicago Food Depository.",
      "assistance_link": "https://www.chicagofoodbank.org/get-help/",
      "phone_number": "773-247-3663",
      "counties": ["Cook"],
      "languages": []
    }
  ]
}
```

**Critical Fields**:
- `white_label.code` - State code (e.g., "il", "co", "tx")
- `program_category.external_name` - Category identifier (e.g., "il_food_nutrition")
- `program.name_abbreviated` - **MUST MATCH** calculator key from Step 1.3
- `program.year` - FPL year for income calculations
- `program.legal_status_required` - Array of legal status codes

**Translatable Fields** (auto-translated to all languages):
- `name`, `description`, `apply_button_description`
- `website_description`, `estimated_application_time`
- Document `text` fields
- Navigator `name`, `email`, `description`

For complete field documentation, see: [programs/management/commands/import_program_config_data/README.md](programs/management/commands/import_program_config_data/README.md)

---

## Step 3: Import Program Configuration

### 3.1 Validate with Dry Run

```bash
python manage.py import_program_config \
  programs/management/commands/import_program_config_data/data/il_csfp_initial_config.json \
  --dry-run
```

Review the output carefully - ensure all fields are correct.

### 3.2 Import the Program

```bash
python manage.py import_program_config \
  programs/management/commands/import_program_config_data/data/il_csfp_initial_config.json
```

The command will:
- Create the Program record
- Create/link Program Category
- Create/link Documents
- Create/link Navigators
- Auto-translate all translatable fields
- Run in a transaction (all or nothing)

---

## Step 4: Update White Label Configuration (If Needed)

> **⚠️ Note**: This step is **optional**. Only complete if your program needs an "I already have this benefit" checkbox.

If your program should appear in the **"Current Benefits" step** (users can indicate they already have this benefit), you need to update the white label configuration for your state.

**Skip this step if**:
- Users cannot already be receiving this benefit before using the screener

### 4.1 Add to Category Benefits

Edit `configuration/white_labels/{state_code}.py`:

```python
category_benefits = {
    "food": {
        "benefits": {
            "il_csfp": {  # ← This key creates the naming chain!
                "name": {
                    "_label": "foodAndNutritionBenefits.il_csfp",
                    "_default_message": "Commodity Supplemental Food Program (CSFP)"
                },
                "description": {
                    "_label": "foodAndNutritionBenefits.il_csfp_desc",
                    "_default_message": "Monthly food packages for seniors"
                }
            },
            # ... other benefits
        },
        "category_name": {
            "_label": "categoryBenefits.food",
            "_default_message": "Food & Nutrition"
        }
    }
}
```

### 4.2 Understanding the Naming Chain

The benefit key (e.g., `"il_csfp"`) creates a critical chain:

1. **Config Key** → `"il_csfp"` in `category_benefits`
2. **Frontend Field** → `formData.benefits.il_csfp`
3. **API Mapping** → `has_il_csfp: formData.benefits.il_csfp` (in updateScreen.ts)
4. **Database Field** → `Screen.has_il_csfp` (added in Step 5)
5. **Backend Mapping** → `has_benefit("il_csfp")` returns `self.has_il_csfp`

**Multiple Programs, Same Benefit**:
If you have multiple variants of the same program (e.g., `snap`, `co_snap`, `federal_snap`), they should all map to the **same** `has_*` field:

```python
# screener/models.py - has_benefit() method
name_map = {
    "snap": self.has_snap,
    "co_snap": self.has_snap,           # Same field!
    "federal_snap": self.has_snap,      # Same field!
    "tx_snap": self.has_snap,           # Same field!
}
```

---

## Step 5: Create Database Migration

> **⚠️ Note**: This step is **only required if you completed Step 4** (updating white label configuration). If your program doesn't need to appear in the "Current Benefits" step, skip this step.

### 5.1 Add Field to Screen Model

Add the database field for the "already have" checkbox:

```python
# screener/models.py
class Screen(models.Model):
    # ... existing fields ...

    has_il_csfp = models.BooleanField(default=False)
```

### 5.2 Generate Migration

```bash
python manage.py makemigrations screener
```

This creates: `screener/migrations/XXXX_screen_has_il_csfp.py`

### 5.3 Run Migration

```bash
python manage.py migrate screener
```

---

## Step 6: Update Serializer

> **⚠️ Note**: This step is **only required if you completed Steps 4-5**. If your program doesn't need to appear in the "Current Benefits" step, skip this step.

Add the new field to the Screen serializer:

```python
# screener/serializers.py
class ScreenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screen
        fields = [
            # ... existing fields ...
            'has_il_csfp',
        ]
```

This allows the API to accept the `has_il_csfp` field when creating/updating screens.

---

## Testing Your Program

### Test Calculator Logic

```python
# Create a test screen
from screener.models import Screen
from programs.models import Program

program = Program.objects.get(name_abbreviated="il_csfp")
screen = Screen.objects.create(
    zipcode="60601",
    county="Cook",
    household_size=1,
    # ... other required fields
)

# Test eligibility
eligibility = program.eligibility(screen, {}, {})
print(f"Eligible: {eligibility.eligible}")
print(f"Value: {eligibility.value}")
```

### Test via API

1. Start the development server:
   ```bash
   python manage.py runserver
   ```

2. Create a screen with your program's requirements
3. Check the eligibility results at `/api/eligibility/{uuid}/`
4. Verify the program appears with correct eligibility and value

### Test "Already Have" Functionality

> **⚠️ Prerequisites**: This test requires frontend changes to be completed first. See [benefits-calculator/docs/HOW_TO_ADD_A_NEW_PROGRAM.md](../../benefits-calculator/docs/HOW_TO_ADD_A_NEW_PROGRAM.md)

1. In the screener, select your program in "Current Benefits" step
2. Complete the screener
3. Verify the program does NOT appear in results
4. Check `screen.has_il_csfp == True` in database

**Note**: If the program doesn't appear in the "Current Benefits" step, verify:
- Frontend has `il_csfp` in `Benefits` type (FormData.ts)
- Frontend has mapping in `updateScreen.ts`
- Backend white label config has `il_csfp` in `category_benefits`

---

## Additional Resources

### Detailed Documentation

- **Import Config Tool**: [programs/management/commands/import_program_config_data/README.md](programs/management/commands/import_program_config_data/README.md)
  - Complete JSON schema
  - Field-by-field documentation
  - Troubleshooting guide

- **White Label Template**: [configuration/white_labels/_template.py](configuration/white_labels/_template.py)
  - Complete configuration options
  - Inline documentation for every field
  - Translation system explained

- **White Label README**: [configuration/white_labels/README.md](configuration/white_labels/README.md)
  - Creating new white labels
  - HubSpot integration
  - County/zip mapping setup

### Calculator Base Classes

- **ProgramCalculator**: [programs/programs/calc.py](programs/programs/calc.py:118)
- **PolicyEngineCalculator**: [programs/programs/policyengine/calculators/base.py](programs/programs/policyengine/calculators/base.py:118)

---

## Quick Checklist

Before submitting your PR:

- [ ] Calculator created and registered in `programs/programs/{state}/__init__.py`
- [ ] Calculator key matches `name_abbreviated` in JSON config
- [ ] JSON config validated with `--dry-run`
- [ ] Program imported successfully
- [ ] White label config updated (if program has "already have" checkbox)
- [ ] Database migration created and run (if needed)
- [ ] Serializer updated (if needed)
- [ ] Calculator logic tested
- [ ] Program appears in API eligibility results
- [ ] "Already have" functionality tested (if applicable)
- [ ] Frontend changes made (see [benefits-calculator/HOW_TO_ADD_A_NEW_PROGRAM.md](../benefits-calculator/HOW_TO_ADD_A_NEW_PROGRAM.md))

---

## Questions?

For questions or issues:
- Check the detailed documentation linked above
- Review example programs in `programs/programs/`
- See example PRs linked in this guide
- Ask in team Slack or GitHub discussions
