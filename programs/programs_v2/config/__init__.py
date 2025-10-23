"""
Config layer for Programs V2.

The Config class holds program-specific configuration including:
- PolicyEngine input classes
- PolicyEngine output definitions
- Calculation period (from Program.year.period)
- Program-specific settings

The Config is responsible for:
1. Defining what PolicyEngine inputs/outputs are needed
2. Specifying the calculation period (some programs like SNAP use month-specific periods)
3. Providing any program-specific configuration data
"""
