"""
Calculator layer for Programs V2.

Calculators contain the business logic for determining eligibility and calculating
benefit values. Each calculator:
- Has a Config instance (defines PE inputs/outputs, period)
- Has a Data instance (provides access to Screen and PE response data)
- Implements eligibility and value calculation methods
- Provides a public interface: .value, .eligible, .calc(), .can_calc()
"""
