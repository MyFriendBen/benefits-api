# HUD Income Limits API Client

This module provides a simplified Python client for accessing HUD (U.S. Department of Housing and Urban Development) Income Limits data through their public API. It's designed as a drop-in replacement for the Google Sheets-based `Ami` class.

**Works for all U.S. states and counties** - Colorado, Massachusetts, Illinois, and any other state.

## Features

- **MTSP Income Limits** via `get_screen_mtsp_ami()` method (all percentages: 20%-100%)
- **Section 8 Income Limits** via `get_screen_il_ami()` placeholder (30%, 50%, 80% only - not yet implemented)
- **Works nationwide** - supports all U.S. states and counties
- Support for household sizes 1-8
- Support for all income percentages (20%, 30%, 40%, 50%, 60%, 70%, 80%, 100% AMI)
- Built-in caching for improved performance
- Error handling and Sentry integration
- Support for historical data by year
- Real-time data from official HUD source

## Setup

### 1. Get a HUD API Token

1. Visit https://www.huduser.gov/hudapi/public/register
2. Sign up for an account
3. **Important**: Select BOTH datasets:
   - ☑ **Fair Market Rent (FMR)** - Required for listing counties
   - ☑ **Income Limits (IL)** - Required for income limits data
4. Log in and click "Create New Token"
5. Copy your token

**Note**: You need access to both FMR and IL datasets because the API uses the FMR endpoint to list counties (shared infrastructure).

### 2. Set Environment Variable

Add your HUD API token to your `.env` file:

```bash
HUD_API_TOKEN=your_token_here
```

## Understanding HUD Income Limit Datasets

HUD provides **two different income limit datasets** with important differences:

### 1. **MTSP (Multifamily Tax Subsidy Project)** - Currently Implemented ✅
- **Endpoint**: `/mtspil/data/{entity_id}`
- **Percentages**: 20%, 30%, 40%, 50%, 60%, 70%, 80%, 100% AMI
- **Purpose**: Low-Income Housing Tax Credit (LIHTC) and tax-exempt bond projects
- **Key Feature**: "Hold-harmless" provision - limits never decrease year-over-year
- **Use when**: General AMI eligibility screening, flexible income thresholds needed

### 2. **Standard Income Limits (Section 8)** - Not Yet Implemented ⚠️
- **Endpoint**: `/il/data/{entity_id}`
- **Percentages**: Only 30%, 50%, 80% AMI (and median)
- **Purpose**: HUD Section 8, Public Housing, Housing Choice Vouchers
- **Key Feature**: Reflects current economic conditions (can go up or down)
- **Use when**: Program requires "Section 8 eligibility" or federal HUD compliance

### Are the Values the Same?

**Not always!** Key differences:

- **50% AMI**: MTSP starts with Section 8 values but applies hold-harmless (never decreases). In down economies, MTSP may be higher.
- **30% & 80% AMI**: Usually close but calculated under different statutory requirements
- **Over time**: Values diverge as MTSP maintains previous highs while Section 8 reflects current median income

**Example Scenario:**
```
Year 1: Section 8 50% = $50,000  |  MTSP 50% = $50,000  ✅ Same
Year 2: Section 8 50% = $48,000  |  MTSP 50% = $50,000  ❌ Different (MTSP held harmless)
Year 3: Section 8 50% = $52,000  |  MTSP 50% = $52,000  ✅ Same (both updated)
```

### Which Should You Use?

| Your Program Says... | Use This Dataset |
|---------------------|------------------|
| "Households at 80% AMI" or "80% Area Median Income" | ✅ **MTSP** (current implementation) |
| "Households eligible for Section 8" | ⚠️ **Standard IL** (see note below) |
| "HUD Section 8 Income Limits" | ⚠️ **Standard IL** (see note below) |
| "Low-Income Housing Tax Credit eligible" | ✅ **MTSP** |
| Need 40%, 60%, or 70% AMI thresholds | ✅ **MTSP** (only option) |

**Note**: Standard IL endpoint not yet implemented. Contact team if you need Section 8 compliance.

## Primary Usage: get_screen_mtsp_ami()

The main method uses **MTSP income limits** (all percentages, hold-harmless provisions):

```python
from integrations.clients.hud_income_limits import hud_client

# Get MTSP income limit (recommended for most use cases)
income_limit = hud_client.get_screen_mtsp_ami(
    screen=screen,
    percent='80%',
    year='2025'
)
```

### Migration from Old Ami Class

**Before (Google Sheets with MTSP):**
```python
from integrations.services.income_limits import ami

income = ami.get_screen_ami(
    screen=screen,
    percent='80%',
    year='2025',
    limit_type='mtsp'
)
```

**After (HUD API):**
```python
from integrations.clients.hud_income_limits import hud_client

income = hud_client.get_screen_mtsp_ami(
    screen=screen,
    percent='80%',
    year='2025'
)
```

**Before (Google Sheets with Section 8 IL):**
```python
from integrations.services.income_limits import ami

income = ami.get_screen_ami(
    screen=screen,
    percent='80%',
    year='2025',
    limit_type='il'  # Section 8
)
```

**After (HUD API):**
```python
from integrations.clients.hud_income_limits import hud_client

# Standard Section 8 IL - not yet implemented!
# Contact team if you need this for compliance
income = hud_client.get_screen_il_ami(
    screen=screen,
    percent='80%',  # Only 30%, 50%, 80% available
    year='2025'
)
```

### Supported Parameters

- **screen**: Screen object with `white_label.state_code`, `county`, and `household_size` attributes
- **percent**: Any of `"20%"`, `"30%"`, `"40%"`, `"50%"`, `"60%"`, `"70%"`, `"80%"`, `"100%"`
- **year**: Year as int or string (e.g., `2025` or `"2025"`)

### All Percentages Directly Supported

The HUD API directly provides all percentage levels: **20%, 30%, 40%, 50%, 60%, 70%, 80%, 100%**

No calculations needed - all values come straight from the HUD API response.

## Income Limit Levels

The HUD Income Limits API provides data for all these income categories:

- **20% AMI**: HUD field `il20_p{household_size}`
- **30% AMI (Extremely Low Income)**: HUD field `il30_p{household_size}`
- **40% AMI**: HUD field `il40_p{household_size}`
- **50% AMI (Very Low Income)**: HUD field `il50_p{household_size}`
- **60% AMI**: HUD field `il60_p{household_size}`
- **70% AMI**: HUD field `il70_p{household_size}`
- **80% AMI (Low Income)**: HUD field `il80_p{household_size}`
- **100% AMI (Area Median Income)**: HUD field `median_income`

## Caching

The client automatically caches API responses to minimize API calls and improve performance:

- **County entity ID lookups**: Cached in-memory for the session
- **County lists**: 24 hours (Django cache)
- **Income limit data**: 24 hours (Django cache)

## Error Handling

The client raises `HudIncomeClientError` exceptions for various error conditions:
- Missing or invalid API token
- Invalid query parameters
- County or data not found
- Network errors
- Invalid household size (must be 1-8)

All errors are automatically logged to Sentry.

## Advanced Usage (Optional)

While `get_screen_mtsp_ami()` is the primary method, the client also exposes lower-level methods if needed:

### Direct API Access

```python
# Get entity ID for a county
entity_id = hud_client._get_entity_id('IL', 'Cook County', 2025)

# Get raw income limit data
data = hud_client._get_income_limit(entity_id, household_size=4, percent='80%', year=2025)
```

### Understanding Entity IDs

Entity IDs are FIPS codes that HUD uses to identify counties and metro areas:
- County FIPS: e.g., `17031` (Cook County, IL)
- Metro Area: e.g., `METRO16980M16980` (Chicago-Joliet-Naperville Metro Area)

The client automatically handles entity ID lookups based on county names.

## HUD API Endpoints Used

This client uses the following HUD API endpoints:

1. **List Counties**: `GET /fmr/listCounties/{state_code}`
   - Lists all counties in ANY state with their FIPS codes
   - Example: `/fmr/listCounties/CO` for Colorado, `/fmr/listCounties/MA` for Massachusetts
   - Used internally to map county names to entity IDs
   - Part of the Fair Market Rent (FMR) API

2. **Get Income Limits**: `GET /mtspil/data/{entity_id}?year={year}`
   - Returns **Multifamily Tax Subsidy Project (MTSP)** income limit data
   - Provides **ALL percentages**: 20%, 30%, 40%, 50%, 60%, 70%, 80%, plus median income (100%)
   - Returns all household sizes (1-8 persons)
   - Works for any county/metro area in ANY state nationwide

**Note**: You need to register for both **FMR** and **Income Limits** datasets on the HUD portal to use this client.

For complete API documentation, visit: https://www.huduser.gov/portal/dataset/fmr-api.html

## Additional HUD API Endpoints

If you need more advanced functionality, HUD provides additional endpoints:

- **State-wide data**: `GET /il/statedata/{state_code}`
- **Zipcode to county**: `GET /usps/zip/{zipcode}`
- **List metro areas**: `GET /il/listMetroAreas`

These are not currently implemented in this client but can be added if needed.

## Example Migration

Here's a real example from the codebase:

**Before:**
```python
# programs/programs/co/trua/calculator.py
from integrations.services.income_limits import ami

class TruaCalculator(ProgramCalculator):
    ami_percent = "80%"

    def income_eligible(self):
        limit = ami.get_screen_ami(
            self.screen,
            self.ami_percent,
            self.program.year.period,
            limit_type="il"
        )
        return self.screen.household_assets.income_amount <= limit
```

**After:**
```python
# programs/programs/co/trua/calculator.py
from integrations.clients.hud_income_limits import hud_client

class TruaCalculator(ProgramCalculator):
    ami_percent = "80%"

    def income_eligible(self):
        limit = hud_client.get_screen_mtsp_ami(
            self.screen,
            self.ami_percent,
            self.program.year.period
        )
        return self.screen.household_assets.income_amount <= limit
```

Just change the import and remove `limit_type`!
