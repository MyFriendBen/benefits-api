from .base import ConfigurationData
from screener.models import WhiteLabel


class WaConfigurationData(ConfigurationData):
    @classmethod
    def get_white_label(self) -> WhiteLabel:
        return WhiteLabel.objects.get(code="wa")

    # ==========================================================================================
    # BASIC INFORMATION
    # ==========================================================================================

    state = {"name": "Washington"}

    public_charge_rule = {
        "link": "https://www.dshs.wa.gov/esa/community-services-offices/public-charge",
        "text": {
            "_label": "landingPage.publicChargeLinkWA",
            "_default_message": "Washington State Department of Social and Health Services",
        },
    }

    more_help_options = {
        "moreHelpOptions": [
            {
                "name": {
                    "_default_message": "211 Washington",
                    "_label": "moreHelp.211.name.wa",
                },
                "link": "https://www.211wa.org/",
                "phone": {
                    "_default_message": "Dial 2-1-1",
                    "_label": "moreHelp.211.phone.wa",
                },
            },
        ]
    }

    # ==========================================================================================
    # REFERRAL OPTIONS
    # ==========================================================================================

    referral_options = {
        "searchEngine": {
            "_label": "referralOptions.searchEngine",
            "_default_message": "Google or other search engine",
        },
        "socialMedia": {
            "_label": "referralOptions.socialMedia",
            "_default_message": "Social Media",
        },
        "friend": {
            "_label": "referralOptions.friend",
            "_default_message": "Friend / Family / Word of Mouth",
        },
        "employer": {
            "_label": "referralOptions.employer",
            "_default_message": "Employer or workplace",
        },
        "communityOrg": {
            "_label": "referralOptions.communityOrg",
            "_default_message": "Community organization or nonprofit",
        },
        "governmentAgency": {
            "_label": "referralOptions.governmentAgency",
            "_default_message": "Government agency",
        },
        "other": {"_label": "referralOptions.other", "_default_message": "Other"},
        "testOrProspect": {
            "_label": "referralOptions.testOrProspect",
            "_default_message": "Test / Prospective Partner",
        },
    }

    # ==========================================================================================
    # HEALTH INSURANCE OPTIONS
    # Washington Medicaid is "Apple Health"; CHIP equivalent is "Apple Health for Kids"
    # ==========================================================================================

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
                    "_label": "healthInsuranceOptions.medicaid.wa",
                    "_default_message": "Apple Health (Medicaid)",
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
                    "_label": "healthInsuranceOptions.chp.wa",
                    "_default_message": "Apple Health for Kids",
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
                    "_label": "healthInsuranceOptions.medicaid.wa",
                    "_default_message": "Apple Health (Medicaid)",
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
                    "_label": "healthInsuranceOptions.chp.wa",
                    "_default_message": "Apple Health for Kids",
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

    # ==========================================================================================
    # COUNTIES BY ZIPCODE
    # Download the latest ZIP-County crosswalk file from:
    #   https://www.huduser.gov/apps/public/uspscrosswalk/login
    # Select "ZIP-County" and state "WA", then parse into this dictionary.
    # ==========================================================================================

    counties_by_zipcode = {}

    # ==========================================================================================
    # CATEGORY BENEFITS
    # ==========================================================================================

    category_benefits = {
        "foodAndNutrition": {
            "benefits": {
                "snap": {
                    "name": {
                        "_label": "foodAndNutritionBenefits.snap",
                        "_default_message": "Supplemental Nutrition Assistance Program (SNAP): ",
                    },
                    "description": {
                        "_label": "foodAndNutritionBenefits.snap_desc",
                        "_default_message": "Food assistance",
                    },
                },
                "wic": {
                    "name": {
                        "_label": "foodAndNutritionBenefits.wic",
                        "_default_message": "Special Supplemental Nutrition Program for Women, Infants, and Children (WIC): ",
                    },
                    "description": {
                        "_label": "foodAndNutritionBenefits.wic_desc",
                        "_default_message": "Food and breastfeeding assistance",
                    },
                },
                "nslp": {
                    "name": {
                        "_label": "foodAndNutritionBenefits.nslp",
                        "_default_message": "National School Lunch Program: ",
                    },
                    "description": {
                        "_label": "foodAndNutritionBenefits.nslp_desc",
                        "_default_message": "Free school meals",
                    },
                },
            },
            "category_name": {
                "_label": "foodAndNutrition",
                "_default_message": "Food and Nutrition",
            },
        },
        "housingAndUtilities": {
            "benefits": {
                "lifeline": {
                    "name": {
                        "_label": "housingAndUtilities.lifeline",
                        "_default_message": "Lifeline: ",
                    },
                    "description": {
                        "_label": "housingAndUtilities.lifeline_desc",
                        "_default_message": "Phone or internet discount",
                    },
                },
                "acp": {
                    "name": {
                        "_label": "housingAndUtilities.acp",
                        "_default_message": "Affordable Connectivity Program (ACP): ",
                    },
                    "description": {
                        "_label": "housingAndUtilities.acp_desc",
                        "_default_message": "Internet discount",
                    },
                },
            },
            "category_name": {
                "_label": "housing",
                "_default_message": "Housing and Utilities",
            },
        },
        "cash": {
            "benefits": {
                "ssdi": {
                    "name": {
                        "_label": "cashAssistanceBenefits.ssdi",
                        "_default_message": "Social Security Disability Insurance (SSDI): ",
                    },
                    "description": {
                        "_label": "cashAssistanceBenefits.ssdi_desc",
                        "_default_message": "Social security benefit for people with disabilities",
                    },
                },
                "ssi": {
                    "name": {
                        "_label": "cashAssistanceBenefits.ssi",
                        "_default_message": "Supplemental Security Income (SSI): ",
                    },
                    "description": {
                        "_label": "cashAssistanceBenefits.ssi_desc",
                        "_default_message": "Federal cash assistance for individuals who are disabled, blind, or 65 years of age or older",
                    },
                },
                "tanf": {
                    "name": {
                        "_label": "cashAssistanceBenefits.tanf",
                        "_default_message": "Temporary Assistance for Needy Families (TANF): ",
                    },
                    "description": {
                        "_label": "cashAssistanceBenefits.tanf_desc",
                        "_default_message": "Cash assistance for families with children",
                    },
                },
            },
            "category_name": {
                "_label": "cashAssistance",
                "_default_message": "Cash Assistance",
            },
        },
        "healthCare": {
            "benefits": {
                "medicaid": {
                    "name": {
                        "_label": "healthCareBenefits.medicaid.wa",
                        "_default_message": "Apple Health (Medicaid): ",
                    },
                    "description": {
                        "_label": "healthCareBenefits.medicaid_desc",
                        "_default_message": "Free or low-cost health coverage",
                    },
                },
                "chp": {
                    "name": {
                        "_label": "healthCareBenefits.chp.wa",
                        "_default_message": "Apple Health for Kids: ",
                    },
                    "description": {
                        "_label": "healthCareBenefits.chp_desc",
                        "_default_message": "Free or low-cost health coverage for children",
                    },
                },
                "medicare_savings": {
                    "name": {
                        "_label": "healthCareBenefits.medicare_savings",
                        "_default_message": "Medicare Savings Program: ",
                    },
                    "description": {
                        "_label": "healthCareBenefits.medicare_savings_desc",
                        "_default_message": "Help paying Medicare premiums and costs",
                    },
                },
            },
            "category_name": {
                "_label": "healthCare",
                "_default_message": "Health Care",
            },
        },
    }

    # ==========================================================================================
    # REFERRER DATA
    # ==========================================================================================

    referrer_data = {
        "theme": {"default": "default"},
        "logoSource": {"default": "MFB_Logo"},
        "logoAlt": {
            "default": {
                "id": "referrerHook.logoAlts.default",
                "defaultMessage": "MyFriendBen home page button",
            },
        },
        "logoFooterSource": {"default": "MFB_Logo"},
        "logoFooterAlt": {
            "default": {"id": "footer.logo.alt", "defaultMessage": "MFB Logo"},
        },
        "logoClass": {"default": "logo"},
        "shareLink": {
            "default": "https://screener.myfriendben.org/wa/step-1",
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
        },
        "uiOptions": {"default": []},
        "featureFlags": {"default": []},  # Deprecated: use uiOptions. Remove as part of MFB-635.
        "noResultMessage": {
            "default": {
                "_label": "noResultMessage",
                "_default_message": "It looks like you may not qualify for benefits included in MyFriendBen at this time. If you indicated need for an immediate resource, please click on the \"Near-Term Benefits\" tab. For additional resources, please click the 'More Help' button below to get the resources you're looking for.",
            },
        },
        "defaultLanguage": {"default": "en-us"},
        "stateName": {"default": "Washington"},
    }
