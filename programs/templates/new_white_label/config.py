from .base import ConfigurationData
from screener.models import WhiteLabel


# TODO: add to /configuration/white_labels/__init__.py
class {{code_capitalize}}ConfigurationData(ConfigurationData):
    @classmethod
    def get_white_label(self) -> WhiteLabel:
        return WhiteLabel.objects.get(code="{{code}}")

    state = {"name": "{{name}}"}

    public_charge_rule = {"link": ""}  # TODO: add public charge link

    more_help_options = {  # TODO: add more help options for the bottom of the results page
        "moreHelpOptions": [
            {
                "name": {"_default_message": "", "_label": ""},
                "link": "",
                "phone": {"_default_message": "", "_label": ""},
            },
        ]
    }

    acute_condition_options = {  # TODO: add/remove urgent need options set to and empty list if none
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
                "_default_message": "Free or low-cost help with civil legal needs or IDs",
            },
        },
    }

    sign_up_options = {  # TODO: add ways that the user can sign up for communication on the sign up page
        "sendUpdates": {
            "_label": "signUpOptions.sendUpdates",
            "_default_message": "Please notify me when new benefits become available to me that I am likely eligible for based on the information I have provided.",
        },
        "sendOffers": {
            "_label": "signUpOptions.sendOffers",
            "_default_message": "Please notify me about other programs or opportunities, including feedback on MyFriendBen.",
        },
    }

    relationship_options = {  # TODO: add relationship options on the member page
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

    referral_options = {  # TODO: add referreral options for the referrer question
        "[REPLACE_ME]": {"_label": "", "_default_message": ""},
        "other": {"_label": "referralOptions.other", "_default_message": "Other"},
        "testOrProspect": {
            "_label": "referralOptions.testOrProspect",
            "_default_message": "Test / Prospective Partner",
        },
    }

    language_options = {  # TODO: add/remove language options
        "en-us": "English",
        "es": "Español",
        "vi": "Tiếng Việt",
        "fr": "Français",
        "am": "አማርኛ",
        "so": "Soomaali",
        "ru": "Русский",
        "ne": "नेपाली",
        "my": "မြန်မာဘာသာစကား",
        "zh": "中文 (简体)",
        "ar": "عربي",
        "sw": "Kiswahili",
    }

    income_options = {  # TODO: add types of income to collect on the income question
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
        "childSupport": {"_label": "incomeOptions.childSupport", "_default_message": "Child Support (Received)"},
        "pension": {
            "_label": "incomeOptions.pension",
            "_default_message": "Military, Government, or Private Pension (including PERA)",
        },
        "veteran": {"_label": "incomeOptions.veteran", "_default_message": "Veteran's Pension or Benefits"},
        "sSSurvivor": {
            "_label": "incomeOptions.sSSurvivor",
            "_default_message": "Social Security Survivor's Benefits (Widowed)",
        },
        "unemployment": {"_label": "incomeOptions.unemployment", "_default_message": "Unemployment Benefits"},
        "sSDependent": {
            "_label": "incomeOptions.sSDependent",
            "_default_message": "Social Security Dependent Benefits (retirement, disability, or survivors)",
        },
        "cashAssistance": {"_label": "incomeOptions.cashAssistance", "_default_message": "Cash Assistance Grant"},
        "gifts": {"_label": "incomeOptions.gifts", "_default_message": "Gifts/Contributions (Received)"},
        "investment": {
            "_label": "incomeOptions.investment",
            "_default_message": "Investment Income (interest, dividends, and profit from selling stocks)",
        },
        "cOSDisability": {
            "_label": "incomeOptions.cOSDisability",
            "_default_message": "Colorado State Disability Benefits",
        },
        "rental": {"_label": "incomeOptions.rental", "_default_message": "Rental Income"},
        "alimony": {"_label": "incomeOptions.alimony", "_default_message": "Alimony (Received)"},
        "deferredComp": {
            "_label": "incomeOptions.deferredComp",
            "_default_message": "Withdrawals from Deferred Compensation (IRA, Keogh, etc.)",
        },
        "workersComp": {"_label": "incomeOptions.workersComp", "_default_message": "Worker's Compensation"},
        "boarder": {"_label": "incomeOptions.boarder", "_default_message": "Boarder or Lodger"},
    }

    health_insurance_options = {  # TODO: add health insurance options on the member question
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

    frequency_options = {  # TODO: add how frequency options to income question
        "weekly": {"_label": "frequencyOptions.weekly", "_default_message": "every week"},
        "biweekly": {"_label": "frequencyOptions.biweekly", "_default_message": "every 2 weeks"},
        "semimonthly": {"_label": "frequencyOptions.semimonthly", "_default_message": "twice a month"},
        "monthly": {"_label": "frequencyOptions.monthly", "_default_message": "every month"},
        "hourly": {"_label": "frequencyOptions.hourly", "_default_message": "hourly"},
    }

    expense_options = {  # TODO: add expense types to expense question
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

    condition_options = {  # TODO: add condition options to member question
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
                    "_label": "conditionOptions.disabled.them",
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

    counties_by_zipcode = {}  # TODO: add zip code to county map for the zip code question

    category_benefits = {  # TODO: add benefits and benefit categories to the already has benefits step
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

    consent_to_contact = {  # TODO: add consent to contact links
        "en-us": "",
        "[REPLACE_ME]": "",
    }

    privacy_policy = {  # TODO: add privacy policy links
        "en-us": "",
        "[REPLACE_ME]": "",
    }

    referrer_data = {
        "theme": {"default": "default", "[REPLACE_ME]": ""},  # TODO: configure additional themes based on referrer
        "logoSource": {  # TODO: add cobranded logos
            "default": "MFB_Logo",
            "[REPLACE_ME]": "",
        },
        "logoAlt": {  # TODO: add cobranded logo alts
            "default": {"id": "referrerHook.logoAlts.default", "defaultMessage": "MyFriendBen home page button"},
            "[REPLACE_ME]": {
                "id": "",
                "defaultMessage": "",
            },
        },
        "logoFooterSource": {"default": "MFB_Logo", "[REPLACE_ME]": ""},  # TODO: add cobranded footer logo
        "logoFooterAlt": {  # TODO: add cobranded footer logo alt
            "default": {"id": "footer.logo.alt", "defaultMessage": "MFB Logo"},
            "[REPLACE_ME]": {"id": "", "defaultMessage": ""},
        },
        "logoClass": {"default": "logo", "[REPLACE_ME]": ""},  # TODO: add logo class
        "shareLink": {  # TODO: change share link based on referrer
            "default": "",
            "[REPLACE_ME]": "",
        },
        "stepDirectory": {  # TODO: set the steps for the white label
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
        "featureFlags": {"default": []},  # TODO: activate any feature flags
        "noResultMessage": {  # TODO: edit the no results message as needed
            "default": {
                "_label": "noResultMessage",
                "_default_message": "It looks like you may not qualify for benefits included in MyFriendBen at this time. If you indicated need for an immediate resource, please click on the “Near-Term Benefits” tab. For additional resources, please click the 'More Help' button below to get the resources you’re looking for.",
            },
        },
    }

    footer_data = {  # TODO: add footer information
        "email": "",
    }

    feedback_links = {  # TODO: add links where the user can provide feedback
        "email": "",
        "survey": "",
    }
