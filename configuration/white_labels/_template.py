from .base import ConfigurationData
from screener.models import WhiteLabel

"""
====================================================================================================
WHITE LABEL CONFIGURATION TEMPLATE
====================================================================================================

This template follows the same structure as base.py for easy reference.

IMPORTANT: Only override fields that need to be different from base.py defaults.
Commented sections can be uncommented if customization is needed.

TEMPLATE USAGE:
1. Copy this file: cp configuration/white_labels/_template.py configuration/white_labels/{state_code}.py
2. Rename the class to: {StateCode}ConfigurationData (e.g., CoConfigurationData)
3. Update the white label code in get_white_label() method
4. Fill in all uncommented TODO sections below
5. Uncomment and customize optional sections as needed

COMPLETE SETUP PROCESS:
For the full white label setup process including database configuration, HubSpot integration,
and feedback form setup, see: configuration/white_labels/README.md

For reference examples, see: co.py, il.py, nc.py
For detailed field documentation, see: base.py and README.md
====================================================================================================
"""


# TODO: Update class name (e.g., CoConfigurationData, IlConfigurationData)
class {{code_capitalize}}ConfigurationData(ConfigurationData):
    @classmethod
    def get_white_label(self) -> WhiteLabel:
        # TODO: Update code to match your white label's database entry
        return WhiteLabel.objects.get(code="{{code}}")

    # ==========================================================================================
    # BASIC INFORMATION
    # ==========================================================================================

    # TODO: Set your state/region name
    state = {"name": "{{name}}"}

    # Banner messages (optional - uncomment if needed)
    # banner_messages = []

    # TODO: Add public charge information link
    public_charge_rule = {"link": ""}

    # TODO: Add help resources shown when user clicks "More Help" button at bottom of results
    more_help_options = {
        "moreHelpOptions": [
            {
                "name": {"_default_message": "", "_label": ""},
                "link": "",
                "phone": {"_default_message": "", "_label": ""},
            },
        ]
    }

    # ==========================================================================================
    # ACUTE CONDITION OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Urgent needs in "Additional Resources" step
    # Icons must be defined in: benefits-calculator/src/Components/Results/helpers.ts (ICON_OPTIONS_MAP)
    # Set to {} to disable, or uncomment and customize specific options below
    # ==========================================================================================
    # acute_condition_options = {
    #     "food": {
    #         "icon": {"_icon": "Food", "_classname": "option-card-icon"},
    #         "text": {"_label": "acuteConditionOptions.food", "_default_message": "Food or groceries"},
    #     },
    #     "babySupplies": {
    #         "icon": {"_icon": "Baby_supplies", "_classname": "option-card-icon"},
    #         "text": {"_label": "acuteConditionOptions.babySupplies", "_default_message": "Diapers and other baby supplies"},
    #     },
    #     # ... see base.py for full list
    # }

    # ==========================================================================================
    # SIGN UP OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Consent checkboxes on sign-up page - usually inherited from base.py
    # ==========================================================================================
    # sign_up_options = {
    #     "sendUpdates": {
    #         "_label": "signUpOptions.sendUpdates",
    #         "_default_message": "Please notify me when new benefits become available...",
    #     },
    #     "sendOffers": {
    #         "_label": "signUpOptions.sendOffers",
    #         "_default_message": "Please notify me about other programs...",
    #     },
    # }

    # ==========================================================================================
    # RELATIONSHIP OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Household member relationships - usually inherited from base.py
    # ==========================================================================================
    # relationship_options = {
    #     "child": {"_label": "relationshipOptions.child", "_default_message": "Child"},
    #     "spouse": {"_label": "relationshipOptions.spouse", "_default_message": "Spouse"},
    #     # ... see base.py for full list
    # }

    # ==========================================================================================
    # REFERRAL OPTIONS - Always customized
    # ==========================================================================================
    # "How did you hear about us?" options
    # Add community partners, organizations, websites relevant to your state
    # ==========================================================================================

    # TODO: Add state-specific referral options
    referral_options = {
        "[REPLACE_ME]": {"_label": "", "_default_message": ""},
        "other": {"_label": "referralOptions.other", "_default_message": "Other"},
        "testOrProspect": {
            "_label": "referralOptions.testOrProspect",
            "_default_message": "Test / Prospective Partner",
        },
    }

    # ==========================================================================================
    # LANGUAGE OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Available translations - must have corresponding translation files in frontend
    # Usually inherited from base.py unless you need to add/remove specific languages
    # ==========================================================================================
    # language_options = {
    #     "en-us": "English",
    #     "es": "Español",
    #     "vi": "Tiếng Việt",
    #     # ... see base.py for full list
    # }

    # ==========================================================================================
    # INCOME OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Types of income to collect
    # Only override if your state has unique income types (e.g., state-specific disability benefits)
    # ==========================================================================================
    # income_options = {
    #     "wages": {"_label": "incomeOptions.wages", "_default_message": "Wages, salaries, tips"},
    #     "sSI": {"_label": "incomeOptions.sSI", "_default_message": "Supplemental Security Income (SSI)"},
    #     # ... see base.py for full list
    # }

    # ==========================================================================================
    # HEALTH INSURANCE OPTIONS - Usually customized
    # ==========================================================================================
    # Customize with state-specific program names if needed (e.g., your state's Medicaid name)
    # Has "you" (first person) and "them" (third person) sections
    # ==========================================================================================

    # TODO: Uncomment and customize with state-specific health insurance program names
    # health_insurance_options = {
    #     "you": {
    #         "none": {
    #             "icon": {"_icon": "None", "_classname": "option-card-icon"},
    #             "text": {
    #                 "_label": "healthInsuranceOptions.none-dont-know-I",
    #                 "_default_message": "I don't have or know if I have health insurance",
    #             },
    #         },
    #         "medicaid": {
    #             "icon": {"_icon": "Medicaid", "_classname": "option-card-icon"},
    #             "text": {
    #                 "_label": "healthInsuranceOptions.medicaid",
    #                 "_default_message": "[YOUR STATE MEDICAID NAME]",  # ← Customize!
    #             },
    #         },
    #         # ... see base.py for full list
    #     },
    #     "them": {
    #         # ... mirror "you" section with "them" pronouns
    #     },
    # }

    # ==========================================================================================
    # FREQUENCY OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Income frequency options - usually inherited from base.py
    # ==========================================================================================
    # frequency_options = {
    #     "weekly": {"_label": "frequencyOptions.weekly", "_default_message": "every week"},
    #     "monthly": {"_label": "frequencyOptions.monthly", "_default_message": "every month"},
    #     # ... see base.py for full list
    # }

    # ==========================================================================================
    # EXPENSE OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Types of expenses to collect - usually inherited from base.py
    # ==========================================================================================
    # expense_options = {
    #     "rent": {"_label": "expenseOptions.rent", "_default_message": "Rent"},
    #     "childCare": {"_label": "expenseOptions.childCare", "_default_message": "Child Care"},
    #     # ... see base.py for full list
    # }

    # ==========================================================================================
    # CONDITION OPTIONS - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Household member conditions - usually inherited from base.py
    # ==========================================================================================
    # condition_options = {
    #     "you": {
    #         "student": { ... },
    #         "pregnant": { ... },
    #         # ... see base.py for full list
    #     },
    #     "them": {
    #         # ... mirror "you" section with "them" pronouns
    #     },
    # }

    # ==========================================================================================
    # COUNTIES BY ZIPCODE - Always customized
    # ==========================================================================================
    # Map zip codes to counties for program eligibility
    #
    # Format: {"zipcode": {"County Name": "County Name"}}
    # Note: Some zip codes span multiple counties, hence the dictionary value
    #
    # Example:
    #   "80202": {"Denver County": "Denver County"}
    #   "80863": {"Park County": "Park County", "Teller County": "Teller County"}
    #
    # HOW TO GENERATE:
    #   1. Register/log in at HUD USPS Crosswalk: https://www.huduser.gov/apps/public/uspscrosswalk/login
    #   2. Download the latest ZIP-County crosswalk file for your state
    #   3. Upload the file to Claude Code in VSCode
    #   4. Ask Claude to generate the counties_by_zipcode dictionary from the file
    # ==========================================================================================

    # TODO: Add your state's zip code to county mappings
    counties_by_zipcode = {}

    # ==========================================================================================
    # CATEGORY BENEFITS - Always customized
    # ==========================================================================================
    # Shown in "Additional Resources" step when users indicate they already receive benefits.
    # Selected benefits are filtered from results.
    #
    # CRITICAL NAMING CONVENTION - THE DICTIONARY KEY MUST MATCH THE BACKEND FIELD:
    #
    # The benefit key (e.g., "snap", "leap", "tanf") determines:
    #   1. Frontend field: formData.benefits.{key}
    #   2. Backend field mapping: benefits-calculator/src/Assets/updateScreen.ts
    #      Example: has_snap: formData.benefits.snap
    #   3. Database field: screener/models.py Screen model
    #      Example: has_snap field on Screen model
    #   4. Backend mapping: screener/models.py has_benefit() method
    #      Example: name_map uses program's name_abbreviated as key, returns self.has_{key}
    #
    # WORKFLOW EXAMPLE FOR "SNAP":
    #   1. Config key: "snap" (this file)
    #   2. User checks "SNAP" checkbox in "Additional Resources" step
    #   3. Frontend stores: formData.benefits.snap = true
    #   4. updateScreen.ts sends: has_snap = formData.benefits.snap
    #   5. Database saves: screen.has_snap = True
    #   6. Program registered with name_abbreviated = "snap" (or "co_snap", etc.)
    #   7. has_benefit("snap") or has_benefit("co_snap") returns: self.has_snap (True)
    #   8. Results serialization: "already_has": True
    #   9. Frontend filters: SNAP program hidden from results
    #
    # IMPORTANT - MULTIPLE PROGRAMS, SAME BENEFIT:
    #   Multiple programs can check the same benefit. For example:
    #   - Regular screener program: name_abbreviated = "snap"
    #   - State variant program: name_abbreviated = "co_snap"
    #
    #   Both must map to the SAME benefit in has_benefit() name_map:
    #     "snap": self.has_snap,
    #     "co_snap": self.has_snap,  # Same has_* field!
    #
    # STEPS TO ADD A NEW BENEFIT:
    #   1. Add benefit key here (e.g., "my_benefit")
    #   2. Add has_my_benefit field to Screen model (screener/models.py)
    #   3. Add mapping in updateScreen.ts: has_my_benefit: formData.benefits.my_benefit
    #   4. Add mapping in has_benefit() name_map for ALL program name_abbreviated variants:
    #      "my_benefit": self.has_my_benefit,
    #      "co_my_benefit": self.has_my_benefit,
    #      "co_energy_calculator_my_benefit": self.has_my_benefit,
    #
    # Structure:
    #   {
    #       "categoryKey": {                          # Arbitrary category identifier
    #           "category_name": { ... },             # Category display name
    #           "benefits": {
    #               "benefit_key": {                  # ← THIS KEY IS CRITICAL!
    #                   "name": { ... },              # Benefit display name
    #                   "description": { ... }        # Brief description
    #               }
    #           }
    #       }
    #   }
    #
    # See existing white labels for examples:
    #   - co.py (lines ~1928-2265)
    #   - il.py
    # ==========================================================================================

    # TODO: Add benefits available in your state, organized by category
    category_benefits = {
        "[REPLACE_ME]": {
            "benefits": {
                "[REPLACE_ME]": {  # ← This key is critical! Must match has_* field name
                    "name": {"_label": "", "_default_message": ""},
                    "description": {"_label": "", "_default_message": ""},
                },
            },
            "category_name": {"_label": "", "_default_message": ""},
        },
    }

    # ==========================================================================================
    # CONSENT & PRIVACY - Always needed for production
    # ==========================================================================================

    # TODO: Add consent/terms links for each language
    consent_to_contact = {
        "en-us": "",
    }

    # TODO: Add privacy policy links for each language
    privacy_policy = {
        "en-us": "",
    }

    # ==========================================================================================
    # REFERRER DATA - Always customized
    # ==========================================================================================
    # Controls branding, logos, step flow, and optional features
    #
    # Field descriptions:
    #
    # theme: CSS theme name (usually "default")
    #   - Used to apply custom styling/themes
    #   - Available themes: "default", "twoOneOne", "twoOneOneNC", "nc_lanc"
    #
    # logoSource: Logo filename from public/locales folder
    #   - Displayed in header throughout screener
    #   - Example: "MFB_Logo", "CO_Logo"
    #
    # logoAlt: Alt text for logo (accessibility)
    #   - Used for screen readers
    #   - Format: {"id": "translation.key", "defaultMessage": "Alt text"}
    #
    # logoFooterSource: Footer logo filename
    #   - Displayed in footer (can be same as header logo)
    #
    # logoFooterAlt: Alt text for footer logo
    #
    # logoClass: CSS class for header logo styling
    #   - Usually "logo", can customize for specific styling needs
    #
    # shareLink: URL used when users share the screener
    #   - Used in Share components
    #   - Example: "https://screener.myfriendben.org"
    #
    # stepDirectory: Defines the screener flow (ORDER MATTERS!)
    #   - Array of step names that appear in order
    #   - householdSize and householdData MUST be consecutive
    #   - "hasBenefits" shows category_benefits from above
    #   - "acuteHHConditions" is the Additional Resources step
    #   - Can have multiple directories keyed by path for different flows
    #
    # uiOptions: Array of UI option strings to enable optional UI customizations
    #   - Examples:
    #     * "211co" - Enable 2-1-1 Colorado specific branding
    #     * "211nc" - Enable 2-1-1 North Carolina specific branding
    #     * "lanc" - Enable LANC specific branding
    #     * "nc_show_211_link" - Show 2-1-1 link in NC
    #     * "white_multi_select_tile_icon" - White icons on multi-select tiles
    #     * "dont_show_category_values" - Hide dollar amounts on category headings
    #
    # noResultMessage: Message shown when user has no eligible programs
    #   - Format: {"_label": "translation.key", "_default_message": "Message text"}
    #
    # defaultLanguage: Default language code
    #   - Example: "en-us", "es"
    #   - Must match a key in language_options
    #
    # stateName: Name of the state for display in the application
    #   - Example: "Colorado", "Texas", "Illinois"
    #   - Used in the header and other UI elements to identify the state
    # ==========================================================================================

    # TODO: Configure branding, step flow, and features
    referrer_data = {
        "theme": {"default": "default"},
        "logoSource": {"default": "MFB_Logo"},
        "logoAlt": {
            "default": {"id": "referrerHook.logoAlts.default", "defaultMessage": "MyFriendBen home page button"}
        },
        "logoFooterSource": {"default": "MFB_Logo"},
        "logoFooterAlt": {"default": {"id": "footer.logo.alt", "defaultMessage": "MFB Logo"}},
        "logoClass": {"default": "logo"},
        "shareLink": {"default": ""},
        "stepDirectory": {
            "default": [
                "zipcode",
                "householdSize",  # Must be consecutive with householdData
                "householdData",
                "hasExpenses",
                "householdAssets",
                "hasBenefits",  # Shows category_benefits
                "acuteHHConditions",  # Additional Resources step
                "referralSource",
                "signUpInfo",
            ]
        },
        "uiOptions": {"default": []},
        "noResultMessage": {
            "default": {
                "_label": "noResultMessage",
                "_default_message": "It looks like you may not qualify for benefits included in MyFriendBen at this time. If you indicated need for an immediate resource, please click on the \"Near-Term Benefits\" tab. For additional resources, please click the 'More Help' button below to get the resources you're looking for.",
            },
        },
        "defaultLanguage": {"default": "en-us"},
        "stateName": {"default": ""},
    }

    # ==========================================================================================
    # FOOTER & FEEDBACK - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Most white labels inherit these values from base.py without needing to override.
    # Only override if you need different contact information than the default MyFriendBen contacts.
    #
    # footer_data: Contact email shown in the footer under "Questions? Contact"
    # feedback_links:
    #   - email: Linked when user selects "CONTACT US"
    #   - survey: Linked when user selects "REPORT AN ISSUE"
    # ==========================================================================================

    # Uncomment and customize only if needed:
    # footer_data = {
    #     "email": "yourstate@example.org",
    # }

    # feedback_links = {
    #     "email": "feedback@yourstate.org",
    #     "survey": "https://forms.gle/your-feedback-form",
    # }

    # ==========================================================================================
    # CURRENT BENEFITS PAGE - Usually inherited as is from ConfigurationData
    # ==========================================================================================
    # Text for the "Current Benefits" catalog page (/:whiteLabel/current-benefits)
    # This is a standalone directory page showing ALL available programs in the system,
    # separate from the personalized results page users get after completing the screener.
    #
    # Contains:
    #   - title: Page header
    #   - program_heading: Heading for long-term benefits section
    #   - urgent_need_heading: Heading for near-term benefits section
    # ==========================================================================================
    # current_benefits = {
    #     "title": {"_label": "currentBenefits.pg-header", "_default_message": "Government Benefits..."},
    #     "program_heading": {"_label": "currentBenefits.long-term-benefits", "_default_message": "LONG-TERM BENEFITS"},
    #     "urgent_need_heading": {"_label": "currentBenefits.near-term-benefits", "_default_message": "NEAR-TERM BENEFITS"},
    # }

    # ==========================================================================================
    # OVERRIDE TEXT - Optional, delete if not needed
    # ==========================================================================================
    # Custom translation overrides for specific text strings
    # Only use this if you need to override specific translation strings for your state
    # that can't be handled through the standard translation system.
    # Most white labels do not use this - delete this section if not needed.
    # ==========================================================================================
    # override_text = {"my_custom_key": {"_label": "myLabel", "_default_message": "My custom text"}}
