from screener.models import WhiteLabel


class TxConfigurationData(ConfigurationData):
    is_default = False

    @classmethod
    def get_white_label(self) -> WhiteLabel:
        raise NotImplemented()

    state = {"name": "Texas"}

    public_charge_rule = {
        "link": "https://pifcoalition.org/pc",
        "text": {
            "_label": "landingPage.publicChargeLinkTX",
            "_default_message": "Protecting Immigrant Families website",
        },
    }

    more_help_options = {
        "moreHelpOptions": [
            {
                "name": {
                    "_default_message": "211 Texas",
                    "_label": "moreHelp.211.name.tx",
                },
                "link": "https://yourtexasbenefits.com/Learn/Home",
                "phone": {
                    "_default_message": "Dial 2-1-1",
                    "_label": "moreHelp.211.phone.tx",
                },
            },
        ]
    }

    acute_condition_options = {
        "food": {
            "icon": {"_name": "Food", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.food",
            "_default_message": "Food or groceries",
        },
        "babySupplies": {
            "icon": {"_name": "Baby_supplies", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.babySupplies",
            "_default_message": "Diapers and other baby supplies",
        },
        "housing": {
            "icon": {"_name": "Housing", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.housing",
            "_default_message": "Help with managing your mortgage, rent, or utilities",
        },
        "support": {
            "icon": {"_name": "Support", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.support",
            "_default_message": "A challenge you or your child would like to talk about",
        },
        "childDevelopment": {
            "icon": {"_name": "Child_development", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.childDevelopment",
            "_default_message": "Concern about your child's development",
        },
        "familyPlanning": {
            "icon": {"_name": "Family_planning", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.familyPlanning",
            "_default_message": "Family planning or birth control",
        },
        "jobResources": {
            "icon": {"_name": "Job_resources", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.jobResources",
            "_default_message": "Finding a job",
        },
        "dentalCare": {
            "icon": {"_name": "Dental_care", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.dentalCare",
            "_default_message": "Low-cost dental care",
        },
        "legalServices": {
            "icon": {"_name": "Legal_services", "_classname": "option-card-icon"},
            "_label": "acuteConditionOptions.legalServices",
            "_default_message": "Free or low-cost help with civil legal needs or identity documents",
        },
    }

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

    referral_options = {
        "[REPLACE_ME]": {"_label": "", "_default_message": ""},
        "other": {"_label": "referralOptions.other", "_default_message": "Other"},
        "testOrProspect": {
            "_label": "referralOptions.testOrProspect",
            "_default_message": "Test / Prospective Partner",
        },
    }

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
    }

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
        "childSupport": {"_label": "incomeOptions.childSupport", "_default_message": "Child Support (Received)"},
        "pension": {
            "_label": "incomeOptions.pension",
            "_default_message": "Military, Government, or Private Pension",
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

    health_insurance_options = {
        "you": {
            "none": {
                "icon": {"_name": "None", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.none-dont-know-I",
                "_default_message": "I don't have or know if I have health insurance",
            },
            "employer": {
                "icon": {"_name": "Employer", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.employer",
                "_default_message": "Employer-provided health insurance",
            },
            "private": {
                "icon": {"_name": "PrivateInsurance", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.private",
                "_default_message": "Private (student or non-employer) health insurance",
            },
            "medicaid": {
                "icon": {"_name": "Medicaid", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.medicaid.tx",
                "_default_message": "Medicaid (including STAR programs)",
            },
            "medicare": {
                "icon": {"_name": "Medicare", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.medicare",
                "_default_message": "Medicare",
            },
            #TODO: should this be "chip"?
            "chp": {
                "icon": {"_name": "Chp", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.chip",
                "_default_message": "Children’s Health Insurance Program (CHIP)",
            },
            "emergency_medicaid": {
                "icon": {"_name": "Emergency_medicaid", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.emergency_medicaid",
                "_default_message": "Emergency Medicaid / Reproductive Health",
            },
            "family_planning": {
                "icon": {"_name": "Family_planning", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.family_planning",
                "_default_message": "Family Planning Limited Medicaid",
            },
            "va": {
                "icon": {"_name": "VA", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.va",
                "_default_message": "VA health care benefits",
            },
        },
        "them": {
            "none": {
                "icon": {"_name": "None", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.none-dont-know-they",
                "_default_message": "They don't have or know if they have health insurance",
            },
            "employer": {
                "icon": {"_name": "Employer", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.employer",
                "_default_message": "Employer-provided health insurance",
            },
            "private": {
                "icon": {"_name": "PrivateInsurance", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.private",
                "_default_message": "Private (student or non-employer) health insurance",
            },
            "medicaid": {
                "icon": {"_name": "Medicaid", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.medicaid.tx",
                "_default_message": "Medicaid (including STAR programs)",
            },
            "medicare": {
                "icon": {"_name": "Medicare", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.medicare",
                "_default_message": "Medicare",
            },
            "chp": {
                "icon": {"_name": "Chp", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.chip",
                "_default_message": "Children’s Health Insurance Program (CHIP)",
            },
            "emergency_medicaid": {
                "icon": {"_name": "Emergency_medicaid", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.emergency_medicaid",
                "_default_message": "Emergency Medicaid / Reproductive Health",
            },
            "family_planning": {
                "icon": {"_name": "Family_planning", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.family_planning",
                "_default_message": "Family Planning Limited Medicaid",
            },
            "va": {
                "icon": {"_name": "VA", "_classname": "option-card-icon"},
                "_label": "healthInsuranceOptions.va",
                "_default_message": "VA health care benefits",
            },
        },
    }

    frequency_options = {
        "weekly": {"_label": "frequencyOptions.weekly", "_default_message": "every week"},
        "biweekly": {"_label": "frequencyOptions.biweekly", "_default_message": "every 2 weeks"},
        "semimonthly": {"_label": "frequencyOptions.semimonthly", "_default_message": "twice a month"},
        "monthly": {"_label": "frequencyOptions.monthly", "_default_message": "every month"},
        "hourly": {"_label": "frequencyOptions.hourly", "_default_message": "hourly"},
    }

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

    condition_options = {
        "you": {
            "student": {
                "icon": {"_name": "Student", "_classname": "option-card-icon"},
                "_label": "conditionOptions.student",
                "_default_message": "Student at a college, university, or other post-secondary institution like a job-training program",
            },
            "pregnant": {
                "icon": {"_name": "Pregnant", "_classname": "option-card-icon"},
                "_label": "conditionOptions.pregnant",
                "_default_message": "Pregnant",
            },
            "blindOrVisuallyImpaired": {
                "icon": {"_name": "BlindOrVisuallyImpaired", "_classname": "option-card-icon"},
                "_label": "conditionOptions.blindOrVisuallyImpaired",
                "_default_message": "Blind or visually impaired",
            },
            "disabled": {
                "icon": {"_name": "Disabled", "_classname": "option-card-icon"},
                "_label": "conditionOptions.disabled",
                "_default_message": "Currently have any disabilities that make you unable to work now or in the future",
            },
            "longTermDisability": {
                "icon": {"_name": "LongTermDisability", "_classname": "option-card-icon"},
                "_label": "conditionOptions.longTermDisability",
                "_default_message": "Any medical or developmental condition that has lasted, or is expected to last, more than 12 months",
            },
        },
        "them": {
            "student": {
                "icon": {"_name": "Student", "_classname": "option-card-icon"},
                "_label": "conditionOptions.student",
                "_default_message": "Student at a college, university, or other post-secondary institution like a job-training program",
            },
            "pregnant": {
                "icon": {"_name": "Pregnant", "_classname": "option-card-icon"},
                "_label": "conditionOptions.pregnant",
                "_default_message": "Pregnant",
            },
            "blindOrVisuallyImpaired": {
                "icon": {"_name": "BlindOrVisuallyImpaired", "_classname": "option-card-icon"},
                "_label": "conditionOptions.blindOrVisuallyImpaired",
                "_default_message": "Blind or visually impaired",
            },
            "disabled": {
                "icon": {"_name": "Disabled", "_classname": "option-card-icon"},
                "_label": "conditionOptions.disabled",
                "_default_message": "Currently have any disabilities that make them unable to work now or in the future",
            },
            "longTermDisability": {
                "icon": {"_name": "LongTermDisability", "_classname": "option-card-icon"},
                "_label": "conditionOptions.longTermDisability",
                "_default_message": "Any medical or developmental condition that has lasted, or is expected to last, more than 12 months",
            },
        },
    }

    #TODO
    counties_by_zipcode = {}

    #TODO
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

    consent_to_contact = {
        "en-us": "https://www.myfriendben.org/terms-and-conditions/",
        "es": "https://www.myfriendben.org/terminos-condiciones/",
    }

    privacy_policy = {
        "en-us": "https://www.myfriendben.org/privacy-policy/",
        "es": "https://www.myfriendben.org/privacidad/",
    }

    referrer_data = {
        "theme": {"default": "default"},
        "logoSource": {
            "default": "MFB_Logo",
        },
        "logoAlt": {
            "default": {"id": "referrerHook.logoAlts.default", "defaultMessage": "MyFriendBen home page button"},
        },
        "logoFooterSource": {"default": "MFB_Logo"},
        "logoFooterAlt": {
            "default": {"id": "footer.logo.alt", "defaultMessage": "MFB Logo"},
        },
        "logoClass": {"default": "logo"},
        "shareLink": {
            "default": "",
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
        "featureFlags": {"default": []},
        "defaultLanguage": {"default": "en-us"},
    }

    footer_data = {
        "email": "hello@myfriendben.org",
    }

    feedback_links = {
        "email": "hello@myfriendben.org", #TODO: google doc says "new"?
        "survey": "https://www.myfriendben.org/feedback",
    }

    override_text = {}
