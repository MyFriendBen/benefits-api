from screener.models import WhiteLabel

"""
Base Configuration for MyFriendBen White Labels

This class provides default configuration values that all white labels inherit.
When creating a new white label, override only the fields you need to customize.

For detailed documentation on how to configure each section, see:
    configuration/white_labels/_template.py
    configuration/white_labels/README.md
"""


class ConfigurationData:
    is_default = False

    @classmethod
    def get_white_label(self) -> WhiteLabel:
        raise NotImplemented()

    # State name for display (override in your white label config)
    state = {"name": "[REPLACE_ME]"}

    # Banner messages displayed at top of screener (optional)
    banner_messages = []

    # Link to public charge information for your state
    public_charge_rule = {"link": ""}

    # Resources shown at bottom of results page (e.g., 2-1-1, state help lines)
    more_help_options = {
        "moreHelpOptions": [
            {
                "name": {"_default_message": "", "_label": ""},
                "link": "",
                "phone": {"_default_message": "", "_label": ""},
            },
        ]
    }

    # Urgent needs shown in "acuteHHConditions" step (customize or set to {} if not used)
    acute_condition_options = {
        "food": {
            "icon": {"_icon": "Food", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.food",
                "_default_message": "Food or groceries",
            },
        },
        "babySupplies": {
            "icon": {"_icon": "Baby_supplies", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.babySupplies",
                "_default_message": "Diapers and other baby supplies",
            },
        },
        "housing": {
            "icon": {"_icon": "Housing", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.housing",
                "_default_message": "Help with managing your mortgage, rent, or utilities",
            },
        },
        "support": {
            "icon": {"_icon": "Support", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.support",
                "_default_message": "A challenge you or your child would like to talk about",
            },
        },
        "childDevelopment": {
            "icon": {"_icon": "Child_development", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.childDevelopment",
                "_default_message": "Concern about your child's development",
            },
        },
        "familyPlanning": {
            "icon": {"_icon": "Family_planning", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.familyPlanning",
                "_default_message": "Family planning or birth control",
            },
        },
        "jobResources": {
            "icon": {"_icon": "Job_resources", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.jobResources",
                "_default_message": "Finding a job",
            },
        },
        "dentalCare": {
            "icon": {"_icon": "Dental_care", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.dentalCare",
                "_default_message": "Low-cost dental care",
            },
        },
        "legalServices": {
            "icon": {"_icon": "Legal_services", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.legalServices",
                "_default_message": "Free or low-cost help with civil legal needs or identity documents",
            },
        },
    }

    # Consent options on sign-up page
    sign_up_options = {
        "sendUpdates": {
            "_label": "signUpOptions.sendUpdates",
            "_default_message": "Please notify me when new benefits become available to me that I am likely eligible for based on the information I have provided.",
        },
        "sendOffers": {
            "_label": "signUpOptions.sendOffers",
            "_default_message": "Please notify me about other programs or opportunities, including feedback on MyFriendBen.",
        },
    }

    # Household relationship options
    relationship_options = {
        "child": {"_label": "relationshipOptions.child", "_default_message": "Child"},
        "fosterChild": {
            "_label": "relationshipOptions.fosterChildOrKinshipChild",
            "_default_message": "Foster Child / Kinship Care",
        },
        "stepChild": {"_label": "relationshipOptions.stepChild", "_default_message": "Step-child"},
        "grandChild": {"_label": "relationshipOptions.grandChild", "_default_message": "Grandchild"},
        "spouse": {"_label": "relationshipOptions.spouse", "_default_message": "Spouse"},
        "parent": {"_label": "relationshipOptions.parent", "_default_message": "Parent"},
        "fosterParent": {"_label": "relationshipOptions.fosterParent", "_default_message": "Foster Parent"},
        "stepParent": {"_label": "relationshipOptions.stepParent", "_default_message": "Step-parent"},
        "grandParent": {"_label": "relationshipOptions.grandParent", "_default_message": "Grandparent"},
        "sisterOrBrother": {"_label": "relationshipOptions.sisterOrBrother", "_default_message": "Sister/Brother"},
        "stepSisterOrBrother": {
            "_label": "relationshipOptions.stepSisterOrBrother",
            "_default_message": "Step-sister/Step-brother",
        },
        "boyfriendOrGirlfriend": {
            "_label": "relationshipOptions.boyfriendOrGirlfriend",
            "_default_message": "Boyfriend/Girlfriend",
        },
        "domesticPartner": {"_label": "relationshipOptions.domesticPartner", "_default_message": "Domestic Partner"},
        "relatedOther": {"_label": "relationshipOptions.relatedOther", "_default_message": "Related in some other way"},
    }

    # "How did you hear about us?" options on referral source step
    referral_options = {
        "[REPLACE_ME]": {"_label": "", "_default_message": ""},
        "other": {"_label": "referralOptions.other", "_default_message": "Other"},
        "testOrProspect": {
            "_label": "referralOptions.testOrProspect",
            "_default_message": "Test / Prospective Partner",
        },
    }

    # Languages available for translation (add/remove as needed for your state)
    language_options = {
        "en-us": "English",
        "es": "Español",
        "vi": "Tiếng Việt",
        "fr": "Français",
        "am": "አማርኛ",
        "so": "Soomaali",
        "ru": "Русский",
        "ne": "नेपाली",
        "my": "မြန်မာဘာသာစကား",
        "zh-hans": "中文 (简体)",
        "ar": "عربي",
        "sw": "Kiswahili",
        "pl": "Polski",
        "tl": "Tagalog",
        "ko": "한국어",
        "pt-br": "Português Brasileiro",
        "ht": "Kreyòl",
    }

    # Types of income to collect (customize for state-specific income types)
    # Organized by category for two-level dropdown selection
    income_categories = {
        "employment": {"_label": "incomeCategories.employment", "_default_message": "Employment Income"},
        "government": {"_label": "incomeCategories.government", "_default_message": "Government Benefits"},
        "support": {"_label": "incomeCategories.support", "_default_message": "Support & Gifts"},
        "investment": {"_label": "incomeCategories.investment", "_default_message": "Investment & Retirement"},
    }

    # Nested income options organized by category (for future use with categorized UI)
    income_options_by_category = {
        "employment": {
            "wages": {"_label": "incomeOptions.wages", "_default_message": "Wages, salaries, tips"},
            "selfEmployment": {
                "_label": "incomeOptions.selfEmployment",
                "_default_message": "Income from freelance, independent contractor, or self-employment work",
            },
        },
        "government": {
            "sSDisability": {
                "_label": "incomeOptions.sSDisability",
                "_default_message": "Social Security Disability Benefits",
            },
            "sSRetirement": {
                "_label": "incomeOptions.sSRetirement",
                "_default_message": "Social Security Retirement Benefits",
            },
            "sSI": {"_label": "incomeOptions.sSI", "_default_message": "Supplemental Security Income (SSI)"},
            "sSSurvivor": {
                "_label": "incomeOptions.sSSurvivor",
                "_default_message": "Social Security Survivor's Benefits (Widowed)",
            },
            "sSDependent": {
                "_label": "incomeOptions.sSDependent",
                "_default_message": "Social Security Dependent Benefits (retirement, disability, or survivors)",
            },
            "unemployment": {"_label": "incomeOptions.unemployment", "_default_message": "Unemployment Benefits"},
            "cashAssistance": {"_label": "incomeOptions.cashAssistance", "_default_message": "Cash Assistance Grant"},
            "workersComp": {"_label": "incomeOptions.workersComp", "_default_message": "Worker's Compensation"},
            "veteran": {"_label": "incomeOptions.veteran", "_default_message": "Veteran's Pension or Benefits"},
        },
        "support": {
            "childSupport": {"_label": "incomeOptions.childSupport", "_default_message": "Child Support (Received)"},
            "alimony": {"_label": "incomeOptions.alimony", "_default_message": "Alimony (Received)"},
            "gifts": {"_label": "incomeOptions.gifts", "_default_message": "Gifts/Contributions (Received)"},
            "boarder": {"_label": "incomeOptions.boarder", "_default_message": "Boarder or Lodger"},
        },
        "investment": {
            "pension": {
                "_label": "incomeOptions.pension",
                "_default_message": "Military, Government, or Private Pension (including PERA)",
            },
            "investment": {
                "_label": "incomeOptions.investment",
                "_default_message": "Investment Income (interest, dividends, and profit from selling stocks)",
            },
            "rental": {"_label": "incomeOptions.rental", "_default_message": "Rental Income"},
            "deferredComp": {
                "_label": "incomeOptions.deferredComp",
                "_default_message": "Withdrawals from Deferred Compensation (IRA, Keogh, etc.)",
            },
        },
    }

    # Flattened income options (backward compatible with current FE)
    # This is what the FE currently expects - a simple flat dictionary
    income_options = {
        "wages": {"_label": "incomeOptions.wages", "_default_message": "Wages, salaries, tips"},
        "selfEmployment": {
            "_label": "incomeOptions.selfEmployment",
            "_default_message": "Income from freelance, independent contractor, or self-employment work",
        },
        "sSDisability": {
            "_label": "incomeOptions.sSDisability",
            "_default_message": "Social Security Disability Benefits",
        },
        "sSRetirement": {
            "_label": "incomeOptions.sSRetirement",
            "_default_message": "Social Security Retirement Benefits",
        },
        "sSI": {"_label": "incomeOptions.sSI", "_default_message": "Supplemental Security Income (SSI)"},
        "sSSurvivor": {
            "_label": "incomeOptions.sSSurvivor",
            "_default_message": "Social Security Survivor's Benefits (Widowed)",
        },
        "sSDependent": {
            "_label": "incomeOptions.sSDependent",
            "_default_message": "Social Security Dependent Benefits (retirement, disability, or survivors)",
        },
        "unemployment": {"_label": "incomeOptions.unemployment", "_default_message": "Unemployment Benefits"},
        "cashAssistance": {"_label": "incomeOptions.cashAssistance", "_default_message": "Cash Assistance Grant"},
        "workersComp": {"_label": "incomeOptions.workersComp", "_default_message": "Worker's Compensation"},
        "veteran": {"_label": "incomeOptions.veteran", "_default_message": "Veteran's Pension or Benefits"},
        "childSupport": {"_label": "incomeOptions.childSupport", "_default_message": "Child Support (Received)"},
        "alimony": {"_label": "incomeOptions.alimony", "_default_message": "Alimony (Received)"},
        "gifts": {"_label": "incomeOptions.gifts", "_default_message": "Gifts/Contributions (Received)"},
        "boarder": {"_label": "incomeOptions.boarder", "_default_message": "Boarder or Lodger"},
        "pension": {
            "_label": "incomeOptions.pension",
            "_default_message": "Military, Government, or Private Pension (including PERA)",
        },
        "investment": {
            "_label": "incomeOptions.investment",
            "_default_message": "Investment Income (interest, dividends, and profit from selling stocks)",
        },
        "rental": {"_label": "incomeOptions.rental", "_default_message": "Rental Income"},
        "deferredComp": {
            "_label": "incomeOptions.deferredComp",
            "_default_message": "Withdrawals from Deferred Compensation (IRA, Keogh, etc.)",
        },
    }

    # Health insurance options (customize for state-specific programs)
    health_insurance_options = {
        "you": {
            "none": {
                "icon": {"_icon": "None", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.none-dont-know-I",
                    "_default_message": "I don't have or know if I have health insurance",
                },
            },
            "employer": {
                "icon": {"_icon": "Employer", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.employer",
                    "_default_message": "Employer-provided health insurance",
                },
            },
            "private": {
                "icon": {"_icon": "PrivateInsurance", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.private",
                    "_default_message": "Private (student or non-employer) health insurance",
                },
            },
            "medicaid": {
                "icon": {"_icon": "Medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicaid",
                    "_default_message": "Health First Colorado (Full Medicaid)",
                },
            },
            "medicare": {
                "icon": {"_icon": "Medicare", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicare",
                    "_default_message": "Medicare",
                },
            },
            "chp": {
                "icon": {"_icon": "Chp", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.chp",
                    "_default_message": "Child Health Plan Plus (CHP+)",
                },
            },
            "emergency_medicaid": {
                "icon": {"_icon": "Emergency_medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.emergency_medicaid",
                    "_default_message": "Emergency Medicaid / Reproductive Health",
                },
            },
            "family_planning": {
                "icon": {"_icon": "Family_planning", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.family_planning",
                    "_default_message": "Family Planning Limited Medicaid",
                },
            },
            "va": {
                "icon": {"_icon": "VA", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.va",
                    "_default_message": "VA health care benefits",
                },
            },
        },
        "them": {
            "none": {
                "icon": {"_icon": "None", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.none-dont-know-they",
                    "_default_message": "They don't have or know if they have health insurance",
                },
            },
            "employer": {
                "icon": {"_icon": "Employer", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.employer",
                    "_default_message": "Employer-provided health insurance",
                },
            },
            "private": {
                "icon": {"_icon": "PrivateInsurance", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.private",
                    "_default_message": "Private (student or non-employer) health insurance",
                },
            },
            "medicaid": {
                "icon": {"_icon": "Medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicaid",
                    "_default_message": "Health First Colorado (Full Medicaid)",
                },
            },
            "medicare": {
                "icon": {"_icon": "Medicare", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicare",
                    "_default_message": "Medicare",
                },
            },
            "chp": {
                "icon": {"_icon": "Chp", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.chp",
                    "_default_message": "Child Health Plan Plus (CHP+)",
                },
            },
            "emergency_medicaid": {
                "icon": {"_icon": "Emergency_medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.emergency_medicaid",
                    "_default_message": "Emergency Medicaid / Reproductive Health",
                },
            },
            "family_planning": {
                "icon": {"_icon": "Family_planning", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.family_planning",
                    "_default_message": "Family Planning Limited Medicaid",
                },
            },
            "va": {
                "icon": {"_icon": "VA", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.va",
                    "_default_message": "VA health care benefits",
                },
            },
        },
    }

    # Income frequency options
    frequency_options = {
        "monthly": {"_label": "frequencyOptions.monthly", "_default_message": "every month"},
        "semimonthly": {"_label": "frequencyOptions.semimonthly", "_default_message": "twice a month"},
        "biweekly": {"_label": "frequencyOptions.biweekly", "_default_message": "every 2 weeks"},
        "weekly": {"_label": "frequencyOptions.weekly", "_default_message": "every week"},
        "hourly": {"_label": "frequencyOptions.hourly", "_default_message": "hourly"},
    }

    # Types of expenses to collect (customize for state-specific needs)
    expense_options = {
        "rent": {"_label": "expenseOptions.rent", "_default_message": "Rent"},
        "telephone": {"_label": "expenseOptions.telephone", "_default_message": "Telephone"},
        "internet": {"_label": "expenseOptions.internet", "_default_message": "Internet"},
        "otherUtilities": {"_label": "expenseOptions.otherUtilities", "_default_message": "Other Utilities"},
        "heating": {"_label": "expenseOptions.heating", "_default_message": "Heating"},
        "mortgage": {"_label": "expenseOptions.mortgage", "_default_message": "Mortgage"},
        "propertyTax": {"_label": "expenseOptions.propertyTax", "_default_message": "Property Taxes"},
        "hoa": {"_label": "expenseOptions.hoa", "_default_message": "Homeowners or Condo Association Fees and Dues"},
        "homeownersInsurance": {
            "_label": "expenseOptions.homeownersInsurance",
            "_default_message": "Homeowners Insurance",
        },
        "medical": {"_label": "expenseOptions.medical", "_default_message": "Medical Insurance Premium &/or Bills"},
        "cooling": {"_label": "expenseOptions.cooling", "_default_message": "Cooling"},
        "childCare": {"_label": "expenseOptions.childCare", "_default_message": "Child Care"},
        "childSupport": {"_label": "expenseOptions.childSupport", "_default_message": "Child Support (Paid)"},
        "dependentCare": {"_label": "expenseOptions.dependentCare", "_default_message": "Dependent Care"},
    }

    # Household member condition options
    condition_options = {
        "you": {
            "student": {
                "icon": {"_icon": "Student", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.student",
                    "_default_message": "Student at a college, university, or other post-secondary institution like a job-training program",
                },
            },
            "pregnant": {
                "icon": {"_icon": "Pregnant", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.pregnant",
                    "_default_message": "Pregnant",
                },
            },
            "blindOrVisuallyImpaired": {
                "icon": {"_icon": "BlindOrVisuallyImpaired", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.blindOrVisuallyImpaired",
                    "_default_message": "Blind or visually impaired",
                },
            },
            "disabled": {
                "icon": {"_icon": "Disabled", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.disabled",
                    "_default_message": "Currently have any disabilities that make you unable to work now or in the future",
                },
            },
            "longTermDisability": {
                "icon": {"_icon": "LongTermDisability", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.longTermDisability",
                    "_default_message": "Any medical or developmental condition that has lasted, or is expected to last, more than 12 months",
                },
            },
        },
        "them": {
            "student": {
                "icon": {"_icon": "Student", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.student",
                    "_default_message": "Student at a college, university, or other post-secondary institution like a job-training program",
                },
            },
            "pregnant": {
                "icon": {"_icon": "Pregnant", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.pregnant",
                    "_default_message": "Pregnant",
                },
            },
            "blindOrVisuallyImpaired": {
                "icon": {"_icon": "BlindOrVisuallyImpaired", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.blindOrVisuallyImpaired",
                    "_default_message": "Blind or visually impaired",
                },
            },
            "disabled": {
                "icon": {"_icon": "Disabled", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.disabled",
                    "_default_message": "Currently have any disabilities that make them unable to work now or in the future",
                },
            },
            "longTermDisability": {
                "icon": {"_icon": "LongTermDisability", "_classname": "option-card-icon"},
                "text": {
                    "_label": "conditionOptions.longTermDisability",
                    "_default_message": "Any medical or developmental condition that has lasted, or is expected to last, more than 12 months",
                },
            },
        },
    }

    # Mapping of zip codes to counties for your state (required)
    # Example: {"80202": {"Denver County": "Denver County"}}
    counties_by_zipcode = {}

    # ==================================================================================
    # CATEGORY BENEFITS - Step 10: "Do you already have any benefits?"
    # ==================================================================================
    # Override this in your white label config with benefits available in your state.
    # For detailed documentation on structure and naming conventions, see:
    #     configuration/white_labels/_template.py (search for "category_benefits")
    #     configuration/white_labels/README.md
    # ==================================================================================
    category_benefits = {
        "[REPLACE_ME]": {
            "benefits": {
                "[REPLACE_ME]": {
                    "name": {
                        "_label": "",
                        "_default_message": "",
                    },
                    "description": {
                        "_label": "",
                        "_default_message": "",
                    },
                },
            },
            "category_name": {"_label": "", "_default_message": ""},
        },
    }

    # Links to consent/terms pages for each language
    consent_to_contact = {
        "en-us": "",
        "[REPLACE_ME]": "",
    }

    # Links to privacy policy for each language
    privacy_policy = {
        "en-us": "",
        "[REPLACE_ME]": "",
    }

    # Configuration for branding, logos, steps, and UI options
    # See template for detailed documentation on each field
    referrer_data = {
        "theme": {"default": "default", "[REPLACE_ME]": ""},
        "logoSource": {
            "default": "MFB_Logo",
            "[REPLACE_ME]": "",
        },
        "faviconSource": {
            "default": "favicon.ico",
            "[REPLACE_ME]": "",
        },
        "logoAlt": {
            "default": {"id": "referrerHook.logoAlts.default", "defaultMessage": "MyFriendBen home page button"},
            "[REPLACE_ME]": {
                "id": "",
                "defaultMessage": "",
            },
        },
        "logoFooterSource": {"default": "MFB_Logo", "[REPLACE_ME]": ""},
        "logoFooterAlt": {
            "default": {"id": "footer.logo.alt", "defaultMessage": "MFB Logo"},
            "[REPLACE_ME]": {"id": "", "defaultMessage": ""},
        },
        "logoClass": {"default": "logo", "[REPLACE_ME]": ""},
        "shareLink": {
            "default": "",
            "[REPLACE_ME]": "",
        },
        "stepDirectory": {
            "default": [
                "zipcode",
                # the hhSize and hhData have to be consecutive
                "householdSize",
                "householdData",
                "hasExpenses",
                "householdAssets",
                "hasBenefits",
                "acuteHHConditions",
                "referralSource",
                "signUpInfo",
            ],
            "[REPLACE_ME]": [],
        },
        "uiOptions": {"default": []},
        "featureFlags": {"default": []},  # Deprecated: use uiOptions. Remove as part of MFB-635.
        "defaultLanguage": {"default": "en-us", "[REPLACE_ME]": ""},
        "stateName": {"default": "", "[REPLACE_ME]": ""},
    }

    # Footer contact information
    footer_data = {
        "email": "hello@myfriendben.org",
    }

    # Links for users to provide feedback
    feedback_links = {
        "email": "mailto:hello@myfriendben.org",
        "survey": "https://myfriendben.fillout.com/report-an-issue",
    }

    # Text for "Current Benefits" page
    current_benefits = {
        "title": {
            "_label": "currentBenefits.pg-header",
            "_default_message": "Government Benefits, Nonprofit Programs and Tax Credits in MyFriendBen",
        },
        "program_heading": {"_label": "currentBenefits.long-term-benefits", "_default_message": "LONG-TERM BENEFITS"},
        "urgent_need_heading": {
            "_label": "currentBenefits.near-term-benefits",
            "_default_message": "NEAR-TERM BENEFITS",
        },
    }

    # Custom translation overrides for specific text strings (optional)
    # should follow format {"[REPLACE_ME]": {"_label": "[REPLACE_ME]", "_default_message": "[REPLACE_ME]"}}
    override_text = {}
