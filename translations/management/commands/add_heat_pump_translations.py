from django.core.management.base import BaseCommand
from django.conf import settings
from translations.models import Translation
from integrations.services.google_translate.integration import Translate


class Command(BaseCommand):
    help = """
    Add Colorado-specific heat pump rebate description translations
    with automatic Google Translate to all supported languages
    """

    def handle(self, *args, **options):
        translations = {
            # Split into separate paragraphs for better formatting
            'co.energy.heat_pump_xcel_p1': 
                "You may qualify for savings on the cost of a heat pump for your home heating, ventilation, and/or cooling system. Heat pumps reduce your carbon footprint, allow you to remove a furnace that burns gas inside your home, and increase comfort, among other benefits. There are numerous combinations or \"stacking\" possibilities for heat pump rebates. A trusted contractor can help you maximize your rebate possibilities.",
            
            'co.energy.heat_pump_xcel_p2':
                "Learn more about heat pumps, including upfront costs, ongoing costs, average life span, and how to initiate a project in this {heatPumpGuide}, from our partners at {rewiringAmerica}.",
            
            'co.energy.heat_pump_xcel_p3':
                "Consult with an {contractorLink} to determine your heat pump unit size and potential rebate.",
            
            'co.energy.heat_pump_contractor_link_xcel': 
                "Xcel Energy Registered Contractor",
            
            # Efficiency Works versions
            'co.energy.heat_pump_efficiency_works_p1':
                "You may qualify for savings on the cost of a heat pump for your home heating, ventilation, and/or cooling system. Heat pumps reduce your carbon footprint, allow you to remove a furnace that burns gas inside your home, and increase comfort, among other benefits. There are numerous combinations or \"stacking\" possibilities for heat pump rebates. A trusted contractor can help you maximize your rebate possibilities.",
            
            'co.energy.heat_pump_efficiency_works_p2':
                "Learn more about heat pumps, including upfront costs, ongoing costs, average life span, and how to initiate a project in this {heatPumpGuide}, from our partners at {rewiringAmerica}.",
            
            'co.energy.heat_pump_efficiency_works_p3':
                "Consult with an {contractorLink} to determine your heat pump unit size and potential rebate.",
            
            'co.energy.heat_pump_contractor_link_efficiency_works':
                "Efficiency Works service provider",
            
            # Other providers versions  
            'co.energy.heat_pump_other_p1':
                "You may qualify for savings on the cost of a heat pump for your home heating, ventilation, and/or cooling system. Heat pumps reduce your carbon footprint, allow you to remove a furnace that burns gas inside your home, and increase comfort, among other benefits. There are numerous combinations or \"stacking\" possibilities for heat pump rebates. A trusted contractor can help you maximize your rebate possibilities.",
            
            'co.energy.heat_pump_other_p2':
                "Learn more about heat pumps, including upfront costs, ongoing costs, average life span, and how to initiate a project in this {heatPumpGuide}, from our partners at {rewiringAmerica}.",
            
            'co.energy.heat_pump_other_p3':
                "Check if your electric utility has a preferred HVAC contractor list or begin your {contractorLink}.",
            
            'co.energy.heat_pump_contractor_link_other':
                "contractor search here",
            
            # Common links
            'co.energy.heat_pump_guide_link':
                "Heat Pump Guide",
            
            'co.energy.rewiring_america_link':
                "Rewiring America"
        }

        # Add English translations
        self.stdout.write("Adding English translations...")
        translation_objects = []
        for label, text in translations.items():
            translation_obj = Translation.objects.add_translation(
                label=label,
                default_message=text,
                active=True,
                no_auto=False
            )
            translation_objects.append(translation_obj)
            self.stdout.write(f"  Added: {label}")

        # Auto-translate to all other languages
        self.stdout.write("\nTranslating to other languages...")
        translate = Translate()
        
        # Get all supported languages except English
        supported_languages = [lang["code"] for lang in settings.PARLER_LANGUAGES[None]]
        target_languages = [lang for lang in supported_languages if lang != settings.LANGUAGE_CODE]
        
        for translation_obj in translation_objects:
            # Get the English text
            translation_obj.set_current_language(settings.LANGUAGE_CODE)
            english_text = translation_obj.text
            
            if not english_text or english_text.strip() == "":
                continue
                
            # Translate to each target language
            for target_lang in target_languages:
                try:
                    translated_text = translate.translate(target_lang, english_text)
                    Translation.objects.edit_translation_by_id(
                        translation_obj.id,
                        target_lang,
                        translated_text,
                        manual=False
                    )
                    self.stdout.write(f"  Translated {translation_obj.label} to {target_lang}")
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"  Failed to translate {translation_obj.label} to {target_lang}: {e}")
                    )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully added and translated {len(translations)} heat pump translations.")
        )