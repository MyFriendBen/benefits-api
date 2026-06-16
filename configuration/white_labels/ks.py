from .base import ConfigurationData
from screener.models import WhiteLabel


class KsConfigurationData(ConfigurationData):
    @classmethod
    def get_white_label(self) -> WhiteLabel:
        return WhiteLabel.objects.get(code="ks")

    # ==========================================================================================
    # BASIC INFORMATION
    # ==========================================================================================

    state = {"name": "Kansas"}

    public_charge_rule = {"link": "https://www.uscis.gov/green-card/green-card-processes-and-procedures/public-charge"}

    more_help_options = {
        "moreHelpOptions": [
            {
                "name": {
                    "_default_message": "Kansas 211 (United Way of Kansas)",
                    "_label": "moreHelp.211.name.ks",
                },
                "link": "https://www.211.org/",
                "phone": {
                    "_default_message": "Dial 2-1-1",
                    "_label": "moreHelp.211.phone.ks",
                },
            },
        ]
    }

    # ==========================================================================================
    # HEALTH INSURANCE OPTIONS
    # Kansas Medicaid is branded "KanCare"
    # ==========================================================================================

    health_insurance_options = {
        "you": {
            **ConfigurationData.health_insurance_options["you"],
            "medicaid": {
                "icon": {"_icon": "Medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicaid.ks",
                    "_default_message": "KanCare (Medicaid)",
                },
            },
        },
        "them": {
            **ConfigurationData.health_insurance_options["them"],
            "medicaid": {
                "icon": {"_icon": "Medicaid", "_classname": "option-card-icon"},
                "text": {
                    "_label": "healthInsuranceOptions.medicaid.ks",
                    "_default_message": "KanCare (Medicaid)",
                },
            },
        },
    }

    # ==========================================================================================
    # COUNTIES BY ZIPCODE
    # NOTE: Starter set covering Kansas's major population centers plus the SSDI test ZIPs.
    # Before launch, regenerate the full statewide mapping from the latest HUD USPS ZIP-County
    # crosswalk (https://www.huduser.gov/apps/public/uspscrosswalk/login, state "KS") so every
    # Kansas ZIP resolves to a county. SSDI eligibility has no location component, so this set
    # is sufficient for the SSDI program but should be expanded for full statewide coverage.
    # ==========================================================================================

    counties_by_zipcode = {
        # Sedgwick County (Wichita)
        "67202": {"Sedgwick County": "Sedgwick County"},
        "67203": {"Sedgwick County": "Sedgwick County"},
        "67204": {"Sedgwick County": "Sedgwick County"},
        "67205": {"Sedgwick County": "Sedgwick County"},
        "67206": {"Sedgwick County": "Sedgwick County"},
        "67207": {"Sedgwick County": "Sedgwick County"},
        "67208": {"Sedgwick County": "Sedgwick County"},
        "67209": {"Sedgwick County": "Sedgwick County"},
        "67210": {"Sedgwick County": "Sedgwick County"},
        "67211": {"Sedgwick County": "Sedgwick County"},
        "67212": {"Sedgwick County": "Sedgwick County"},
        "67213": {"Sedgwick County": "Sedgwick County"},
        "67214": {"Sedgwick County": "Sedgwick County"},
        "67215": {"Sedgwick County": "Sedgwick County"},
        "67216": {"Sedgwick County": "Sedgwick County"},
        "67217": {"Sedgwick County": "Sedgwick County"},
        "67218": {"Sedgwick County": "Sedgwick County"},
        "67219": {"Sedgwick County": "Sedgwick County"},
        "67220": {"Sedgwick County": "Sedgwick County"},
        "67226": {"Sedgwick County": "Sedgwick County"},
        "67227": {"Sedgwick County": "Sedgwick County"},
        "67228": {"Sedgwick County": "Sedgwick County"},
        "67230": {"Sedgwick County": "Sedgwick County"},
        "67235": {"Sedgwick County": "Sedgwick County"},
        # Shawnee County (Topeka)
        "66603": {"Shawnee County": "Shawnee County"},
        "66604": {"Shawnee County": "Shawnee County"},
        "66605": {"Shawnee County": "Shawnee County"},
        "66606": {"Shawnee County": "Shawnee County"},
        "66607": {"Shawnee County": "Shawnee County"},
        "66608": {"Shawnee County": "Shawnee County"},
        "66609": {"Shawnee County": "Shawnee County"},
        "66610": {"Shawnee County": "Shawnee County"},
        "66611": {"Shawnee County": "Shawnee County"},
        "66612": {"Shawnee County": "Shawnee County"},
        "66614": {"Shawnee County": "Shawnee County"},
        "66615": {"Shawnee County": "Shawnee County"},
        "66616": {"Shawnee County": "Shawnee County"},
        "66617": {"Shawnee County": "Shawnee County"},
        "66618": {"Shawnee County": "Shawnee County"},
        "66619": {"Shawnee County": "Shawnee County"},
        # Johnson County (Overland Park, Olathe, Lenexa, Shawnee)
        "66061": {"Johnson County": "Johnson County"},
        "66062": {"Johnson County": "Johnson County"},
        "66202": {"Johnson County": "Johnson County"},
        "66203": {"Johnson County": "Johnson County"},
        "66204": {"Johnson County": "Johnson County"},
        "66206": {"Johnson County": "Johnson County"},
        "66207": {"Johnson County": "Johnson County"},
        "66210": {"Johnson County": "Johnson County"},
        "66212": {"Johnson County": "Johnson County"},
        "66213": {"Johnson County": "Johnson County"},
        "66214": {"Johnson County": "Johnson County"},
        "66215": {"Johnson County": "Johnson County"},
        "66216": {"Johnson County": "Johnson County"},
        "66217": {"Johnson County": "Johnson County"},
        "66218": {"Johnson County": "Johnson County"},
        "66219": {"Johnson County": "Johnson County"},
        "66220": {"Johnson County": "Johnson County"},
        "66221": {"Johnson County": "Johnson County"},
        "66223": {"Johnson County": "Johnson County"},
        "66224": {"Johnson County": "Johnson County"},
        "66226": {"Johnson County": "Johnson County"},
        "66227": {"Johnson County": "Johnson County"},
        # Wyandotte County (Kansas City)
        "66101": {"Wyandotte County": "Wyandotte County"},
        "66102": {"Wyandotte County": "Wyandotte County"},
        "66103": {"Wyandotte County": "Wyandotte County"},
        "66104": {"Wyandotte County": "Wyandotte County"},
        "66105": {"Wyandotte County": "Wyandotte County"},
        "66106": {"Wyandotte County": "Wyandotte County"},
        "66109": {"Wyandotte County": "Wyandotte County"},
        "66111": {"Wyandotte County": "Wyandotte County"},
        "66112": {"Wyandotte County": "Wyandotte County"},
        # Douglas County (Lawrence)
        "66044": {"Douglas County": "Douglas County"},
        "66045": {"Douglas County": "Douglas County"},
        "66046": {"Douglas County": "Douglas County"},
        "66047": {"Douglas County": "Douglas County"},
        "66049": {"Douglas County": "Douglas County"},
        # Riley County (Manhattan)
        "66502": {"Riley County": "Riley County"},
        "66503": {"Riley County": "Riley County"},
        "66506": {"Riley County": "Riley County"},
        # Saline County (Salina)
        "67401": {"Saline County": "Saline County"},
        "67402": {"Saline County": "Saline County"},
        # Reno County (Hutchinson)
        "67501": {"Reno County": "Reno County"},
        "67502": {"Reno County": "Reno County"},
        # Leavenworth County
        "66048": {"Leavenworth County": "Leavenworth County"},
        # Ellis County (Hays)
        "67601": {"Ellis County": "Ellis County"},
        # Crawford County (Pittsburg)
        "66762": {"Crawford County": "Crawford County"},
        # Finney County (Garden City)
        "67846": {"Finney County": "Finney County"},
        # Ford County (Dodge City)
        "67801": {"Ford County": "Ford County"},
        # Geary County (Junction City)
        "66441": {"Geary County": "Geary County"},
        # Butler County (El Dorado)
        "67042": {"Butler County": "Butler County"},
        # Cowley County (Winfield/Arkansas City)
        "67005": {"Cowley County": "Cowley County"},
        "67156": {"Cowley County": "Cowley County"},
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
                        "_label": "healthCareBenefits.medicaid.ks",
                        "_default_message": "KanCare (Medicaid): ",
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
            "default": "https://screener.myfriendben.org/ks/step-1",
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
        "stateName": {"default": "Kansas"},
    }
