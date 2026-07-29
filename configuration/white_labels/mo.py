from .base import ConfigurationData
from screener.models import WhiteLabel


class MoConfigurationData(ConfigurationData):
    @classmethod
    def get_white_label(self) -> WhiteLabel:
        return WhiteLabel.objects.get(code="mo")

    # ==========================================================================================
    # BASIC INFORMATION
    # ==========================================================================================

    state = {"name": "Missouri"}

    public_charge_rule = {"link": "https://www.uscis.gov/green-card/green-card-processes-and-procedures/public-charge"}

    more_help_options = {
        "moreHelpOptions": [
            {
                "name": {
                    "_default_message": "Missouri 211 (United Way)",
                    "_label": "moreHelp.211.name.mo",
                },
                "link": "https://www.211.org/",
                "phone": {
                    "_default_message": "Dial 2-1-1",
                    "_label": "moreHelp.211.phone.mo",
                },
            },
        ]
    }

    # ==========================================================================================
    # HEALTH INSURANCE OPTIONS
    # Missouri Medicaid is branded "MO HealthNet"
    # ==========================================================================================

    health_insurance_options = {
        "you": {
            **ConfigurationData.health_insurance_options["you"],
            "medicaid": {
                "icon": {"_icon": "Medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicaid.mo",
                    "_default_message": "MO HealthNet (Medicaid)",
                },
            },
            "chp": {
                "icon": {"_icon": "Chp", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.chp.mo",
                    "_default_message": "MO HealthNet for Kids (CHIP)",
                },
            },
        },
        "them": {
            **ConfigurationData.health_insurance_options["them"],
            "medicaid": {
                "icon": {"_icon": "Medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicaid.mo",
                    "_default_message": "MO HealthNet (Medicaid)",
                },
            },
            "chp": {
                "icon": {"_icon": "Chp", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.chp.mo",
                    "_default_message": "MO HealthNet for Kids (CHIP)",
                },
            },
        },
    }

    # ==========================================================================================
    # COUNTIES BY ZIPCODE
    # Full statewide mapping generated from the HUD USPS ZIP-County crosswalk (state "MO").
    # Each ZIP is assigned to the county with the highest TOT_RATIO from that crosswalk.
    #
    # TODO(MFB-1569): Replace this placeholder with the full statewide mapping generated
    # from the HUD USPS ZIP-County crosswalk for Missouri before launch. The two entries
    # below (Jackson County / Kansas City, St. Louis City) are placeholders so the config
    # loads and the flow can be exercised end to end.
    # ==========================================================================================

    counties_by_zipcode = {
        # Jackson County (Kansas City)
        "64106": {"Jackson County": "Jackson County"},
        # St. Louis City
        "63103": {"St. Louis City": "St. Louis City"},
    }

    # ==========================================================================================
    # CATEGORY BENEFITS
    # Benefits shown on the "Do you already have any benefits?" step.
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
                        "_label": "healthCareBenefits.medicaid.mo",
                        "_default_message": "MO HealthNet (Medicaid): ",
                    },
                    "description": {
                        "_label": "healthCareBenefits.medicaid_desc",
                        "_default_message": "Free or low-cost health coverage",
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
            "default": "https://screener.myfriendben.org/mo/step-1",
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
        "noResultMessage": {
            "default": {
                "_label": "noResultMessage",
                "_default_message": "It looks like you may not qualify for benefits included in MyFriendBen at this time. If you indicated need for an immediate resource, please click on the \"Near-Term Benefits\" tab. For additional resources, please click the 'More Help' button below to get the resources you're looking for.",
            },
        },
        "defaultLanguage": {"default": "en-us"},
        "stateName": {"default": "Missouri"},
    }
