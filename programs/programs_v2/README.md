# Programs V2 Architecture

This directory contains the new architecture for benefit program calculators, implementing the design from `ProgramRefactorClassesAndResponsibilities.md`.

## Architecture Overview

The system is organized into distinct layers with clear separation of concerns:

```
programs_v2/
├── policyengine/           # PolicyEngine API integration
│   ├── inputs/             # PolicyEngine input variables
│   │   ├── base.py         # Base PolicyEngineInput class
│   │   ├── spm_unit_inputs.py  # SPM unit level inputs (SNAP income, assets, expenses)
│   │   ├── member_inputs.py    # Member level inputs (age, disability, expenses)
│   │   └── household_inputs.py # Household level inputs (state code)
│   ├── outputs/            # PolicyEngine output variables
│   │   ├── base.py         # Base PolicyEngineOutput class
│   │   └── spm_unit_outputs.py # SPM unit level outputs (SNAP)
│   ├── request.py          # Build PE API requests (supports batching)
│   ├── response.py         # Parse PE API responses
│   └── client.py           # Make PE API calls with fallback
├── config/                 # Program configuration
│   └── snap.py             # SNAP config (PE inputs/outputs, period)
├── data/                   # Data access layer
│   └── snap.py             # SNAP data facade (Screen + PE response)
├── calculators/            # Calculation logic
│   ├── base.py             # Base Calculator class
│   └── snap.py             # SNAP calculator
├── factories/              # Factory for creating calculators
│   └── calculator_factory.py  # CalculatorFactory (instantiation only)
└── integration.py          # Integration layer (PE orchestration, entry point)

```

## Key Design Principles

1. **Composition over Inheritance** - No deep inheritance chains
2. **Single Responsibility** - Each class has one clear purpose
3. **Dependency Injection** - Factory wires up dependencies
4. **Batch PolicyEngine Calls** - One API call serves multiple calculators
5. **Type Safety** - Clear types throughout (with TODOs for stricter typing)

## Usage Example

```python
from programs.programs_v2.integration import calculate_eligibility
from screener.models import Screen
from programs.models import Program

# Get Screen and Program instances
screen = Screen.objects.get(id=123)
tx_snap_program = Program.objects.get(name_abbreviated='tx_snap')

# Calculate programs - use Program.name_abbreviated as the key
calculators = calculate_eligibility(
    screen=screen,
    programs={'tx_snap': tx_snap_program}
)

# Use calculator
snap_calc = calculators['tx_snap']
if snap_calc.can_calc():
    snap_calc.calc()
    print(f"Eligible: {snap_calc.eligible}")
    print(f"Value: ${snap_calc.value}")
```

## Adding a New Calculator

To add a new calculator (e.g., Medicaid):

1. **Define Input Classes** (`policyengine/medicaid_inputs.py`):
   ```python
   class MedicaidIncomeInput(PolicyEngineInput):
       field = "medicaid_income"
       unit = "people"

       def value(self):
           return self.member.calc_gross_income("yearly", ["all"])
   ```

2. **Create Config** (`config/medicaid.py`):
   ```python
   class TxMedicaidConfig:
       pe_inputs = [MedicaidIncomeInput, ...]
       pe_outputs = [PolicyEngineOutput("medicaid", "people")]

       def __init__(self, program):
           self.program = program

       @property
       def period(self):
           return self.program.year.period
   ```

3. **Create Data Class** (`data/medicaid.py`):
   ```python
   class MedicaidData:
       def __init__(self, screen, config, pe_response):
           self.screen = screen
           self.config = config
           self.pe_response = pe_response

       def get_member_value(self, member):
           return self.pe_response.get_member_value(
               member.id, "medicaid", self.config.period
           )
   ```

4. **Create Calculator** (`calculators/medicaid.py`):
   ```python
   class MedicaidCalculator(Calculator):
       def calculate_value(self):
           total = 0
           for member in self.screen.household_members.all():
               total += self.data.get_member_value(member)
           return total

       def calculate_eligibility(self):
           return self.calculate_value() > 0
   ```

5. **Register in Factory** (`factories/calculator_factory.py`):
   ```python
   # Use Program.name_abbreviated as the key (includes state prefix)
   CALCULATOR_REGISTRY = {
       "tx_snap": (SnapCalculator, TxSnapConfig, SnapData),
       "tx_medicaid": (MedicaidCalculator, TxMedicaidConfig, MedicaidData),
   }
   ```

## Benefits vs Old Architecture

### Before (Old Architecture)
- 5 levels of inheritance: `ProgramCalculator` → `PolicyEngineCalulator` → `PolicyEngineMembersCalculator` → `Medicaid` → `TxMedicaid`
- Mixed concerns: Data, config, and logic all in one class
- Hard to test: Requires mocking deep inheritance chains
- State variations require new classes

### After (V2 Architecture)
- 1 level of inheritance: `Calculator` → `SnapCalculator`
- Clear separation: Data, Config, Calculator are separate
- Easy to test: Mock the Data layer, test calculator logic
- State variations = new Config/Data, same Calculator

## Implementation Status

### ✅ Completed
- PolicyEngine layer (inputs, outputs, request, response, client)
- Config layer (TxSnapConfig)
- Data layer (SnapData)
- Calculator layer (Base Calculator, SnapCalculator)
- Factory layer (CalculatorFactory)

### 🚧 In Progress
- Integration with existing system
- Testing infrastructure

### 📋 TODO
- Migrate additional programs (Medicaid, WIC, etc.)
- Add comprehensive test coverage
- Performance benchmarking
- Documentation updates
