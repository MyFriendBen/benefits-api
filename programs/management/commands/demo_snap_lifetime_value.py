"""
Demo script to showcase SNAP lifetime benefit value calculation.
Shows the complete flow from household setup to lifetime prediction.
"""

from django.core.management.base import BaseCommand
from decimal import Decimal
from programs.models import Program, ProgramDurationMultiplier
from programs.services.lifetime_value_service import LifetimeValueService
from screener.models import Screen, WhiteLabel, HouseholdMember


class Command(BaseCommand):
    help = "Demonstrate SNAP lifetime benefit value calculation with example households"

    def add_arguments(self, parser):
        parser.add_argument(
            "--white-label",
            type=str,
            default="co",
            help="White label code to use for demo (default: co)",
        )

    def handle(self, *args, **options):
        white_label_code = options.get("white_label", "co")

        self.stdout.write(self.style.SUCCESS(f"🍎 SNAP Lifetime Benefit Value Calculation Demo"))
        self.stdout.write("=" * 60)

        try:
            # Get white label and SNAP program
            white_label = WhiteLabel.objects.get(code=white_label_code)
            snap_program = Program.objects.get(name_abbreviated=f"{white_label_code}_snap")

            # Check if duration data exists
            try:
                duration_multiplier = ProgramDurationMultiplier.objects.get(
                    program=snap_program, white_label=white_label
                )
                self.stdout.write(f"✅ Found duration data: {duration_multiplier}")
            except ProgramDurationMultiplier.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING("⚠️  No duration data found. Run: python manage.py populate_snap_duration_data")
                )
                return

            # Demo scenarios
            scenarios = [
                {
                    "name": "Working Family with Children",
                    "household_size": 3,
                    "monthly_benefit": Decimal("275.00"),
                    "members": [
                        {"relationship": "headOfHousehold", "age": 32, "disabled": False},
                        {"relationship": "child", "age": 8, "disabled": False},
                        {"relationship": "child", "age": 5, "disabled": False},
                    ],
                },
                {
                    "name": "Elderly Couple",
                    "household_size": 2,
                    "monthly_benefit": Decimal("350.00"),
                    "members": [
                        {"relationship": "headOfHousehold", "age": 68, "disabled": True},
                        {"relationship": "spouse", "age": 65, "disabled": False},
                    ],
                },
                {
                    "name": "Single Parent with Infant",
                    "household_size": 2,
                    "monthly_benefit": Decimal("400.00"),
                    "members": [
                        {"relationship": "headOfHousehold", "age": 24, "disabled": False},
                        {"relationship": "child", "age": 1, "disabled": False},
                    ],
                },
            ]

            service = LifetimeValueService()

            for i, scenario in enumerate(scenarios, 1):
                self.stdout.write(f"\n📊 Scenario {i}: {scenario['name']}")
                self.stdout.write("-" * 40)

                # Create household screen
                screen = Screen.objects.create(
                    white_label=white_label,
                    completed=True,
                    zipcode="80205",
                    county="Demo County",
                    household_size=scenario["household_size"],
                    household_assets=1000,
                    housing_situation="rent",
                )

                # Create household members
                for member_data in scenario["members"]:
                    HouseholdMember.objects.create(
                        screen=screen,
                        relationship=member_data["relationship"],
                        age=member_data["age"],
                        disabled=member_data["disabled"],
                        student=member_data["age"] >= 5 and member_data["age"] <= 18,
                        pregnant=False,
                        unemployed=False,
                        veteran=False,
                        has_income=member_data["relationship"] == "headOfHousehold",
                        has_expenses=False,
                    )

                # Generate lifetime prediction
                monthly_benefit = scenario["monthly_benefit"]
                prediction = service.generate_prediction(
                    screen=screen, program=snap_program, monthly_benefit=monthly_benefit
                )

                # Display results
                self.stdout.write(f"🏠 Household: {scenario['household_size']} members")
                self.stdout.write(f"💰 Monthly SNAP Benefit: ${monthly_benefit}")
                self.stdout.write(f"📅 Predicted Duration: {prediction.predicted_duration_months:.1f} months")
                self.stdout.write(
                    f"📈 Confidence Range: {prediction.confidence_interval_lower:.1f} - "
                    f"{prediction.confidence_interval_upper:.1f} months"
                )
                self.stdout.write(f"🎯 Estimated Lifetime Value: ${prediction.estimated_lifetime_value:,.2f}")
                self.stdout.write(f"📝 Explanation: {prediction.explanation_text[:100]}...")

        except WhiteLabel.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ White label '{white_label_code}' not found"))
        except Program.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ SNAP program '{white_label_code}_snap' not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error running demo: {e}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ SNAP Lifetime Benefit Value Demo Complete!"))

        # Show implementation notes
        self.show_implementation_notes()

    def show_implementation_notes(self):
        """Display implementation notes and next steps"""
        notes = """
📋 Implementation Notes:

🔬 Research-Based Duration:
   • Average 15 months for working families with children
   • Based on USDA 2024 SNAP Participation Report
   • Accounts for cycling on/off program due to employment changes
   • Confidence range: ±33% (10-20 months)

🏗️  Architecture:
   • Simple multiplier approach (Phase 1)
   • ProgramDurationMultiplier model stores research data
   • SimpleDurationService calculates duration
   • LifetimeValueService orchestrates complete prediction

🔄 Future Enhancements:
   • Demographic-specific duration adjustments
   • Machine learning models for household-specific predictions
   • AI-generated explanations with LLM integration
   • Real-time data feeds from state agencies

📈 Extensibility:
   • Framework designed for other programs (WIC, Medicaid, etc.)
   • White-label multi-tenant support
   • Caching and performance optimization ready

🧪 Testing:
   • Comprehensive TDD test suite
   • Integration tests with realistic household data
   • Validation of calculation accuracy
        """
        self.stdout.write(notes)
