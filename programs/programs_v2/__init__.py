"""
Programs V2 - New architecture for benefit program calculators.

This module implements a composition-based architecture with clear separation of concerns:
- PolicyEngine layer: API interaction abstractions
- Data layer: Static benefit data
- Config layer: Program configuration
- Calculator layer: Eligibility and value calculation logic
- Factory layer: Object instantiation and dependency injection
"""
