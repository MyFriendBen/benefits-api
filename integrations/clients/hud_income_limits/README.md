# HUD Income Limits API Client

This module provides a simplified Python client for accessing HUD (U.S. Department of Housing and Urban Development) Income Limits data through their public API. It's designed as a drop-in replacement for the Google Sheets-based `Ami` class.

**Works for all U.S. states and counties** - Colorado, Massachusetts, Illinois, and any other state.

## Features

- **MTSP Income Limits** via `get_screen_mtsp_ami()` method (all percentages: 20%-100%)
- **Section 8 Income Limits** via `get_screen_il_ami()` method (30%, 50%, 80% only)
- **Works nationwide** - supports all U.S. states and counties
- Support for household sizes 1-8
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

### 1. **MTSP (Multifamily Tax Subsidy Project)**
- **Endpoint**: `/mtspil/data/{entity_id}`
- **Percentages**: 20%, 30%, 40%, 50%, 60%, 70%, 80%, 100% AMI
- **Purpose**: Low-Income Housing Tax Credit (LIHTC) and tax-exempt bond projects
- **Key Feature**: "Hold-harmless" provision - limits never decrease year-over-year
- **Use when**: General AMI eligibility screening, flexible income thresholds needed

### 2. **Standard Income Limits (Section 8)**
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
| "Households at 80% AMI" or "80% Area Median Income" (generic) | Either ✅ **MTSP** or ✅ **Standard IL** |
| Links to https://www.huduser.gov/portal/datasets/il.html | ✅ **Standard IL** (`get_screen_il_ami`) |
| "Households eligible for Section 8" | ✅ **Standard IL** (`get_screen_il_ami`) |
| "HUD Section 8 Income Limits" | ✅ **Standard IL** (`get_screen_il_ami`) |
| "Low-Income Housing Tax Credit eligible" | ✅ **MTSP** (`get_screen_mtsp_ami`) |
| Need 40%, 60%, or 70% AMI thresholds | ✅ **MTSP** only option |
| CBRAP (IL Rental Assistance) | ✅ **Standard IL** |

## Usage

### Option 1: get_screen_mtsp_ami() - MTSP Income Limits

Use **MTSP income limits** when you need all percentages (20%-100%) or hold-harmless provisions:

```python
from integrations.clients.hud_income_limits import hud_client

# Get MTSP income limit
income_limit = hud_client.get_screen_mtsp_ami(
    screen=screen,
    percent='80%',  # Can be: 20%, 30%, 40%, 50%, 60%, 70%, 80%, 100%
    year='2025'
)
```

### Option 2: get_screen_il_ami() - Standard Section 8 Income Limits

Use **Standard IL** when program documentation references Section 8 or links to https://www.huduser.gov/portal/datasets/il.html:

```python
from integrations.clients.hud_income_limits import hud_client

# Get Standard Section 8 income limit
income_limit = hud_client.get_screen_il_ami(
    screen=screen,
    percent='80%',  # Can only be: 30%, 50%, 80%
    year='2025'
)
```

**Example: CBRAP (Illinois Rental Assistance)**
```python
# CBRAP links to HUD Section 8 limits, so use get_screen_il_ami()
income_limit = hud_client.get_screen_il_ami(screen, '80%', '2025')
```

### Method Parameters

**Both methods accept:**
- **screen**: Screen object with `white_label.state_code`, `county`, and `household_size` attributes
- **year**: Year as int or string (e.g., `2025` or `"2025"`)

**Percentage support differs by method:**
- **`get_screen_mtsp_ami()`**: `"20%"`, `"30%"`, `"40%"`, `"50%"`, `"60%"`, `"70%"`, `"80%"`, `"100%"`
- **`get_screen_il_ami()`**: `"30%"`, `"50%"`, `"80%"` only

## Income Limit Categories

### MTSP Income Limits (get_screen_mtsp_ami)

All percentage levels available - values come directly from HUD API:

- **20% AMI**: Field `il20_p{household_size}`
- **30% AMI (Extremely Low Income)**: Field `il30_p{household_size}`
- **40% AMI**: Field `il40_p{household_size}`
- **50% AMI (Very Low Income)**: Field `il50_p{household_size}`
- **60% AMI**: Field `il60_p{household_size}`
- **70% AMI**: Field `il70_p{household_size}`
- **80% AMI (Low Income)**: Field `il80_p{household_size}`
- **100% AMI (Area Median Income)**: Field `median_income`

### Standard Section 8 Income Limits (get_screen_il_ami)

Only three percentage levels available:

- **30% AMI (Extremely Low Income)**: Field `l30_{household_size}`
- **50% AMI (Very Low Income)**: Field `l50_{household_size}`
- **80% AMI (Low Income)**: Field `l80_{household_size}`

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
        limit = hud_client.get_screen_il_ami(
            self.screen,
            self.ami_percent,
            self.program.year.period
        )
        return self.screen.household_assets.income_amount <= limit
```

**Migration rule:** `limit_type="il"` → `get_screen_il_ami()`, `limit_type="mtsp"` → `get_screen_mtsp_ami()`
