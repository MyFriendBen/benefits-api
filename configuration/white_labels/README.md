# White Label Configuration Guide

This directory contains configuration files for MyFriendBen white labels (state/region-specific instances of the benefits screener).

## Quick Start

### Creating a New White Label

1. **Copy the template:**
   ```bash
   cp configuration/white_labels/_template.py configuration/white_labels/tx.py
   ```

2. **Update the class name:**
   ```python
   class TxConfigurationData(ConfigurationData):
   ```

3. **Update the white label code:**
   ```python
   def get_white_label(self) -> WhiteLabel:
       return WhiteLabel.objects.get(code="tx")
   ```

4. **Fill in required fields** (marked with `TODO` or `[REPLACE_ME]`):
   - `state["name"]` - State/region name
   - `counties_by_zipcode` - Zip code to county mappings (REQUIRED)
   - `category_benefits` - Benefits available in your state
   - Other sections as needed

5. **Register your white label** in `__init__.py`:
   ```python
   from .tx import TxConfigurationData

   white_label_config = {
       # ...
       "tx": TxConfigurationData,
   }
   ```

6. **Load configuration into database:**
   ```bash
   python manage.py add_config
   ```

7. **Update Fillout Feedback Form:**

   Add the new state to the feedback form so users can report issues/feedback for the new white label:

   - Go to [Fillout Form Editor](https://build.fillout.com/editor/9eJYBZLegxus)
   - Edit the first multiple-choice question about which state the user is reporting feedback for
   - Add your state name (e.g., "Texas", "Illinois", etc.) as a new option
   - Publish the changes

8. **Configure HubSpot Integration (Step 1 of 2):**

   Add the state code to the HubSpot `states` property dropdown to enable texting integration:

   - Go to [HubSpot Property Settings](https://app-na2.hubspot.com/property-settings/48436655/properties?type=0-1&search=states&action=edit&property=states)
   - Add your state code (e.g., "TX", "IL", "NC") to the allowed options
   - Save the changes

8. **Add HubSpot Integration Class (Step 2 of 2):**

   Create a state-specific HubSpot integration class in `integrations/services/cms_integration.py`:

   ```python
   class TxHubSpotIntegration(HubSpotIntegration):
       STATE = "TX"
       OWNER_ID = "80630223"  # Get the correct owner ID from HubSpot
   ```

   Then register it in the `CMS_INTEGRATIONS` dictionary:

   ```python
   CMS_INTEGRATIONS = {
       "co_hubspot": CoHubSpotIntegration,
       "nc_hubspot": NcHubSpotIntegration,
       "ma_hubspot": MaHubSpotIntegration,
       "il_hubspot": IlHubSpotIntegration,
       "tx_hubspot": TxHubSpotIntegration,  # Add your new integration
   }
   ```

   Finally, set the `cms_method` in the Django admin for your white label to match the key (e.g., `"tx_hubspot"`)

## File Structure

### Core Files

- **`base.py`** - Base configuration class with sensible defaults
  - All white labels inherit from `ConfigurationData`
  - Contains common defaults (relationship options, income types, etc.)
  - Brief comments pointing to detailed documentation

- **`_template.py`** - Template for creating new white labels
  - Comprehensive documentation for each configuration section
  - TODO markers for required customization
  - Example workflows and naming conventions
  - **Start here when creating a new white label**

- **`_default.py`** - Fallback white label
  - Used when no specific state is selected
  - Generic MyFriendBen branding
  - NOT a template (use `_template.py` instead)

### State-Specific Files

- `co.py` - Colorado
- `il.py` - Illinois
- `ma.py` - Massachusetts
- `nc.py` - North Carolina
- `tx.py` - Texas
- `co_energy_calculator.py` - Colorado Energy Calculator (specialized flow)

## Key Configuration Sections

### 1. Basic Information

```python
state = {"name": "Texas"}
public_charge_rule = {"link": "https://..."}
more_help_options = { ... }  # Help resources shown when user clicks "More Help" button
```

### 2. Counties by Zipcode (REQUIRED)

Maps zip codes to counties for location-based eligibility:

```python
counties_by_zipcode = {
    "75001": {"Collin County": "Collin County"},
    "78701": {"Travis County": "Travis County"},
    "80863": {"Park County": "Park County", "Teller County": "Teller County"},  # Multi-county zip
}
```

**How to generate this dictionary:**
1. Register/log in at [HUD USPS Crosswalk](https://www.huduser.gov/apps/public/uspscrosswalk/login)
2. Download the latest ZIP-County crosswalk file for your state
3. Upload the file to Claude Code in VSCode
4. Ask Claude to generate the `counties_by_zipcode` dictionary from the file

This is much faster than manually entering thousands of zip codes!

### 3. Category Benefits (IMPORTANT)

Defines benefits shown in the "Additional Resources" step ("Do you already have any benefits?").

**CRITICAL**: The dictionary key determines the field name throughout the system.

```python
category_benefits = {
    "food": {  # Category
        "benefits": {
            "snap": {  # ← This key is critical!
                "name": {"_default_message": "SNAP"},
                "description": {"_default_message": "..."}
            }
        }
    }
}
```

**Data Flow:**
1. Config key: `"snap"` →
2. Frontend: `formData.benefits.snap` →
3. API: `has_snap = formData.benefits.snap` →
4. Database: `screen.has_snap = True` →
5. Backend: `has_benefit("snap")` →
6. Results: `"already_has": True` →
7. Frontend filters program from results

**To add a new benefit:**
1. Add key to `category_benefits` (e.g., `"my_benefit"`)
2. Add `has_my_benefit` field to `Screen` model (`screener/models.py`)
3. Add mapping in `updateScreen.ts`: `has_my_benefit: formData.benefits.my_benefit`
4. Add mapping in `has_benefit()` name_map: `"my_benefit": self.has_my_benefit`
5. If multiple programs use it, add all variants: `"co_my_benefit": self.has_my_benefit`

See [_template.py](./template.py) for detailed documentation.

### 4. Referrer Data (Branding & Flow)

Controls branding, logos, and screener flow:

```python
referrer_data = {
    "logoSource": {"default": "TX_Logo"},
    "stepDirectory": {
        "default": [
            "zipcode",
            "householdSize",  # These two MUST be consecutive
            "householdData",
            "hasExpenses",
            "householdAssets",
            "hasBenefits",  # Shows category_benefits
            "acuteHHConditions",  # Additional Resources step - shows acute_condition_options
            "referralSource",
            "signUpInfo",
        ]
    },
    "uiOptions": {"default": []},
    "featureFlags": {"default": []},  # Deprecated: use uiOptions. Remove as part of MFB-635.
}
```

### 5. Experiments (A/B Testing)

Controls A/B test variant assignment. The frontend reads the variants list and uses a UUID hash to deterministically assign each user a variant.

```python
experiments = {
    "npsVariant": {"variants": ["floating", "inline"]},
}
```

- Each experiment key maps to a dict with a `"variants"` list
- All active variants must be listed — the frontend picks one per user based on their UUID
- To disable an experiment, set `"variants": []` (empty list)
- To force a single variant (no A/B test), use a single-item list: `"variants": ["floating"]`
- Experiments can be overridden per white label to run different tests in different states

**Adding a new experiment:**
1. Add the key and variants to `experiments` in `base.py`
2. Run `python manage.py add_config --all` to update the database
3. Read the experiment config on the frontend and implement variant logic

### 6. Other Sections

- **`acute_condition_options`** - Urgent needs in the "Additional Resources" step
  - Icon names must be defined in `benefits-calculator/src/Components/Results/helpers.ts` (`ICON_OPTIONS_MAP`)
- **`referral_options`** - "How did you hear about us?" options
- **`language_options`** - Available translations
- **`income_options`** - Types of income to collect
- **`health_insurance_options`** - Health insurance types
- **`expense_options`** - Types of expenses to collect
- **`condition_options`** - Household member conditions
- **`feedback_links`** - Contact links:
  - `email`: Linked when user selects "CONTACT US"
  - `survey`: Linked when user selects "REPORT AN ISSUE"

Most of these rarely need customization and can be inherited from `base.py`.

## Important Concepts

### Inheritance

All white labels inherit from `ConfigurationData` in `base.py`. You only need to override fields that differ from the defaults:

```python
class TxConfigurationData(ConfigurationData):
    # Only override what you need to customize
    state = {"name": "Texas"}

    # Everything else inherited from base.py
```

### Translation Keys

Most user-facing text uses translation keys:

```python
{
    "_label": "incomeOptions.wages",  # Translation key
    "_default_message": "Wages, salaries, tips"  # Fallback English text
}
```

**Adding New Translation Keys:**

When adding new translation keys (e.g., for new benefits, options, or text), you must add them to the admin portal in both staging and production environments:

1. Log in to the admin portal (staging or prod)
2. Navigate to the translation management section
3. Add your new translation key with translations for all supported languages
4. Repeat for both staging and production environments

This ensures translations are available across all environments and languages.

### Program Name Abbreviations

Programs are registered with a `name_abbreviated` (e.g., `"snap"`, `"co_snap"`, `"co_energy_calculator_leap"`).

Multiple program variants can map to the same benefit in `has_benefit()`:
- `"snap"` → `self.has_snap`
- `"co_snap"` → `self.has_snap`  (same field!)
- `"il_snap"` → `self.has_snap`  (same field!)

This allows different states/flows to check if a user has the same real-world benefit.

## Related Files

### Backend (benefits-api)
- `screener/models.py` - Screen model with `has_*` fields
- `screener/models.py` - `has_benefit()` method for mapping
- `screener/views.py` - `eligibility_results()` serialization
- `programs/programs/{state}/__init__.py` - Program registrations

### Frontend (benefits-calculator)
- `src/Assets/updateScreen.ts` - Frontend to backend field mapping
- `src/Assets/updateFormData.tsx` - Backend to frontend field mapping
- `src/Components/Steps/AlreadyHasBenefits.tsx` - Step 10 UI component
- `src/Components/Config/configHook.tsx` - Config fetching

## Troubleshooting

### "Already has" filtering not working?

Check the complete chain:
1. ✓ Benefit key in `category_benefits` config
2. ✓ `has_*` field exists on `Screen` model
3. ✓ Mapping in `updateScreen.ts`
4. ✓ Mapping in `has_benefit()` name_map for ALL program variants
5. ✓ Frontend filtering using `already_has` flag

### Program not showing up?

1. Check program is registered in `programs/programs/{state}/__init__.py`
2. Check program eligibility logic
3. Check if program is being filtered by referrer (see `eligibility_results()`)

### Translation not showing?

1. Check translation key exists in frontend translation files
2. Check language is enabled in `language_options`
3. Run translation extraction/compilation commands

## Examples

### Simple White Label (Minimal Customization)

```python
class SimpleConfigurationData(ConfigurationData):
    state = {"name": "Simple State"}

    counties_by_zipcode = {
        "12345": {"County": "County"}
    }

    category_benefits = {
        "assistance": {
            "benefits": {
                "snap": {
                    "name": {"_label": "...", "_default_message": "SNAP"},
                    "description": {"_label": "...", "_default_message": "..."}
                }
            },
            "category_name": {"_label": "...", "_default_message": "Assistance"}
        }
    }
```

### Complex White Label (Full Customization)

See `co.py` for a comprehensive example with:
- Custom acute condition options
- Extensive category benefits
- State-specific income types
- Custom health insurance options
- Multiple referral options

## Additional Resources

- **For developers**: See inline documentation in `_template.py`
- **For program details**: See `programs/programs/{state}/`
- **For database schema**: See `screener/migrations/`
- **For frontend integration**: See benefits-calculator repo

## Questions?

- Check existing white labels (`co.py`, `il.py`, etc.) for examples
- Read comprehensive documentation in `_template.py`
- See inline comments in `base.py`
