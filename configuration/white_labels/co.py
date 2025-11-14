from .base import ConfigurationData
from screener.models import WhiteLabel


class CoConfigurationData(ConfigurationData):
    @classmethod
    def get_white_label(self) -> WhiteLabel:
        return WhiteLabel.objects.get(code="co")

    state = {"name": "Colorado"}

    # System banner messages
    banner_messages = [
        {
            "id": "co.banner.snap_nov_2025_hold",
            "title": {
                "_label": "co.banner.snap_nov_2025_hold.title",
                "_default_message": "Update: November SNAP Benefits Are Coming",
            },
            "content": {
                "_label": "co.banner.snap_nov_2025_hold.content",
                "_default_message": "The federal government has reopened, and November SNAP (food assistance) benefits will be loaded onto EBT cards starting Friday, November 14.\n\n**What you need to know:**\n- Full November benefits are being processed now\n- December benefits will come on time as usual\n- You should still apply for SNAP and turn in any paperwork\n\n**Need food help while you wait?**\n- Call Colorado 211: dial 2-1-1 or [866-760-6489](tel:8667606489)\n- Visit: [https://www.211colorado.org](https://www.211colorado.org/)",
            },
            "enabled": True,
            "priority": 1,
        }
    ]

    public_charge_rule = {
        "link": "https://cdhs.colorado.gov/public-charge-rule-colorado-immigrants#:~:text=About%20public%20charge&text=The%20test%20looks%20at%20whether,affidavit%20of%20support%20or%20contract.",
        "text": {
            "_label": "landingPage.publicChargeLinkCO",
            "_default_message": "Colorado Department of Human Services",
        },
    }

    more_help_options = {
        "moreHelpOptions": [
            {
                "name": {"_default_message": "2-1-1 Colorado", "_label": "moreHelp.resource_name1"},
                "link": "https://www.211colorado.org",
                "phone": {"_default_message": "Dial 2-1-1 or 866.760.6489", "_label": "moreHelp.resource_phone1"},
            },
            {
                "name": {"_default_message": "Family Resource Center Association", "_label": "moreHelp.resource_name2"},
                "description": {
                    "_default_message": "Your local family resource center may be able to connect you to other resources and support services. Visit a center near you.",
                    "_label": "moreHelp.resource_description1",
                },
                "link": "https://maps.cofamilycenters.org",
            },
            {
                "name": {
                    "_default_message": "County Human Services Offices",
                    "_label": "moreHelp.coloradoHumanServicesOffices.resourceName",
                },
                "description": {
                    "_default_message": "Your county human services office can answer questions and help you apply for benefits. Click the link below to find your local office.",
                    "_label": "moreHelp.coloradoHumanServicesOffices.description",
                },
                "link": "https://cdhs.colorado.gov/contact-your-county",
            },
        ]
    }

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
        "savings": {
            "icon": {"_icon": "Savings", "_classname": "option-card-icon"},
            "text": {
                "_label": "acuteConditionOptions.savings",
                "_default_message": "Saving for college",
            },
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
        "211co": "2-1-1 Colorado",
        "cch": "Colorado Coalition for the Homeless",
        "frca": "Family Resource Center Association",
        "achs": "Adams County Human Services",
        "arapahoectypublichealth": "Arapahoe County Public Health",
        "dhs": "Denver Human Services",
        "eaglecounty": "Eagle County",
        "jeffcoHS": "Jeffco Human Services",
        "jeffcoPS": "Jeffco Public Schools",
        "larimercounty": "Larimer County",
        "tellercounty": "Teller County",
        "pueblo": "Pueblo County",
        "pitkin": "Pitkin County",
        "broomfield": "City and County of Broomfield",
        "theactioncenter": "The Action Center",
        "gac": "Get Ahead Colorado",
        "bia": "Benefits in Action",
        "fircsummitresourcecenter": {
            "_label": "referralOptions.fircsummitresourcecenter",
            "_default_message": "FIRC Summit Resource Center",
        },
        "ccig": "Colorado Design Insight Group",
        "coAccess": "Colorado Access",
        "searchEngine": {"_label": "referralOptions.searchEngine", "_default_message": "Google or other search engine"},
        "socialMedia": {"_label": "referralOptions.socialMedia", "_default_message": "Social Media"},
        "friend": {"_label": "referralOptions.friend", "_default_message": "Friend / Family / Word of Mouth"},
        "merit": {"_label": "referralOptions.merit", "_default_message": "Merit America"},
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
        "ur": "اردو",
        "pt-br": "Português Brasileiro",
        "ht": "Kreyòl",
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
        "cashAssistance": {
            "_label": "incomeOptions.cashAssistance",
            "_default_message": "Government Cash Assistance (including Colorado Works/TANF)",
        },
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

    counties_by_zipcode = {
        "80002": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Jefferson County": "Jefferson County",
        },
        "80003": {"Adams County": "Adams County", "Jefferson County": "Jefferson County"},
        "80004": {"Jefferson County": "Jefferson County"},
        "80005": {"Jefferson County": "Jefferson County", "Broomfield County": "Broomfield County"},
        "80007": {
            "Boulder County": "Boulder County",
            "Jefferson County": "Jefferson County",
            "Broomfield County": "Broomfield County",
        },
        "80010": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
        },
        "80011": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
        },
        "80012": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80013": {"Arapahoe County": "Arapahoe County"},
        "80014": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80015": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80016": {
            "Denver County": "Denver County",
            "Elbert County": "Elbert County",
            "Douglas County": "Douglas County",
            "Arapahoe County": "Arapahoe County",
        },
        "80017": {"Arapahoe County": "Arapahoe County"},
        "80018": {"Adams County": "Adams County", "Arapahoe County": "Arapahoe County"},
        "80019": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
        },
        "80020": {
            "Adams County": "Adams County",
            "Boulder County": "Boulder County",
            "Jefferson County": "Jefferson County",
            "Broomfield County": "Broomfield County",
        },
        "80021": {
            "Boulder County": "Boulder County",
            "Jefferson County": "Jefferson County",
            "Broomfield County": "Broomfield County",
        },
        "80022": {"Adams County": "Adams County", "Denver County": "Denver County"},
        "80023": {
            "Weld County": "Weld County",
            "Adams County": "Adams County",
            "Boulder County": "Boulder County",
            "Broomfield County": "Broomfield County",
        },
        "80024": {"Adams County": "Adams County"},
        "80025": {"Boulder County": "Boulder County", "Jefferson County": "Jefferson County"},
        "80026": {
            "Weld County": "Weld County",
            "Boulder County": "Boulder County",
            "Broomfield County": "Broomfield County",
        },
        "80027": {
            "Boulder County": "Boulder County",
            "Jefferson County": "Jefferson County",
            "Broomfield County": "Broomfield County",
        },
        "80030": {"Adams County": "Adams County", "Jefferson County": "Jefferson County"},
        "80031": {
            "Adams County": "Adams County",
            "Jefferson County": "Jefferson County",
            "Broomfield County": "Broomfield County",
        },
        "80033": {"Denver County": "Denver County", "Jefferson County": "Jefferson County"},
        "80045": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
        },
        "80101": {"Elbert County": "Elbert County", "Arapahoe County": "Arapahoe County"},
        "80102": {
            "Weld County": "Weld County",
            "Adams County": "Adams County",
            "Elbert County": "Elbert County",
            "Arapahoe County": "Arapahoe County",
        },
        "80103": {
            "Adams County": "Adams County",
            "Elbert County": "Elbert County",
            "Morgan County": "Morgan County",
            "Arapahoe County": "Arapahoe County",
        },
        "80104": {"Douglas County": "Douglas County"},
        "80105": {
            "Adams County": "Adams County",
            "Elbert County": "Elbert County",
            "Lincoln County": "Lincoln County",
            "Arapahoe County": "Arapahoe County",
            "Washington County": "Washington County",
        },
        "80106": {
            "Elbert County": "Elbert County",
            "Douglas County": "Douglas County",
            "El Paso County": "El Paso County",
        },
        "80107": {
            "Elbert County": "Elbert County",
            "Douglas County": "Douglas County",
            "Arapahoe County": "Arapahoe County",
        },
        "80108": {"Douglas County": "Douglas County"},
        "80109": {"Douglas County": "Douglas County"},
        "80110": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80111": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80112": {"Douglas County": "Douglas County", "Arapahoe County": "Arapahoe County"},
        "80113": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80116": {"Elbert County": "Elbert County", "Douglas County": "Douglas County"},
        "80117": {"Elbert County": "Elbert County"},
        "80118": {
            "Elbert County": "Elbert County",
            "Douglas County": "Douglas County",
            "El Paso County": "El Paso County",
        },
        "80120": {"Douglas County": "Douglas County", "Arapahoe County": "Arapahoe County"},
        "80121": {"Arapahoe County": "Arapahoe County"},
        "80122": {"Douglas County": "Douglas County", "Arapahoe County": "Arapahoe County"},
        "80123": {
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
            "Jefferson County": "Jefferson County",
        },
        "80124": {"Douglas County": "Douglas County", "Arapahoe County": "Arapahoe County"},
        "80125": {
            "Douglas County": "Douglas County",
            "Arapahoe County": "Arapahoe County",
            "Jefferson County": "Jefferson County",
        },
        "80126": {"Douglas County": "Douglas County", "Arapahoe County": "Arapahoe County"},
        "80127": {
            "Denver County": "Denver County",
            "Douglas County": "Douglas County",
            "Jefferson County": "Jefferson County",
        },
        "80128": {
            "Douglas County": "Douglas County",
            "Arapahoe County": "Arapahoe County",
            "Jefferson County": "Jefferson County",
        },
        "80129": {"Douglas County": "Douglas County", "Arapahoe County": "Arapahoe County"},
        "80130": {"Douglas County": "Douglas County"},
        "80131": {"Douglas County": "Douglas County"},
        "80132": {"Douglas County": "Douglas County", "El Paso County": "El Paso County"},
        "80133": {
            "Teller County": "Teller County",
            "Douglas County": "Douglas County",
            "El Paso County": "El Paso County",
        },
        "80134": {
            "Elbert County": "Elbert County",
            "Douglas County": "Douglas County",
            "Arapahoe County": "Arapahoe County",
        },
        "80135": {
            "Park County": "Park County",
            "Teller County": "Teller County",
            "Douglas County": "Douglas County",
            "El Paso County": "El Paso County",
            "Jefferson County": "Jefferson County",
        },
        "80136": {
            "Weld County": "Weld County",
            "Adams County": "Adams County",
            "Elbert County": "Elbert County",
            "Arapahoe County": "Arapahoe County",
        },
        "80137": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
        },
        "80138": {
            "Elbert County": "Elbert County",
            "Douglas County": "Douglas County",
            "Arapahoe County": "Arapahoe County",
        },
        "80202": {"Denver County": "Denver County"},
        "80203": {"Denver County": "Denver County"},
        "80204": {"Denver County": "Denver County", "Jefferson County": "Jefferson County"},
        "80205": {"Denver County": "Denver County"},
        "80206": {"Denver County": "Denver County"},
        "80207": {"Denver County": "Denver County"},
        "80209": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80210": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80211": {"Denver County": "Denver County"},
        "80212": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Jefferson County": "Jefferson County",
        },
        "80214": {"Denver County": "Denver County", "Jefferson County": "Jefferson County"},
        "80215": {"Jefferson County": "Jefferson County"},
        "80216": {"Adams County": "Adams County", "Denver County": "Denver County"},
        "80218": {"Denver County": "Denver County"},
        "80219": {
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
            "Jefferson County": "Jefferson County",
        },
        "80220": {
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
        },
        "80221": {"Adams County": "Adams County", "Denver County": "Denver County"},
        "80222": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80223": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80224": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80226": {"Denver County": "Denver County", "Jefferson County": "Jefferson County"},
        "80227": {"Denver County": "Denver County", "Jefferson County": "Jefferson County"},
        "80228": {"Jefferson County": "Jefferson County"},
        "80229": {"Adams County": "Adams County"},
        "80230": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80231": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80232": {"Denver County": "Denver County", "Jefferson County": "Jefferson County"},
        "80233": {"Adams County": "Adams County"},
        "80234": {"Adams County": "Adams County", "Broomfield County": "Broomfield County"},
        "80235": {"Denver County": "Denver County", "Jefferson County": "Jefferson County"},
        "80236": {
            "Denver County": "Denver County",
            "Arapahoe County": "Arapahoe County",
            "Jefferson County": "Jefferson County",
        },
        "80237": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80238": {"Adams County": "Adams County", "Denver County": "Denver County"},
        "80239": {"Adams County": "Adams County", "Denver County": "Denver County"},
        "80241": {"Adams County": "Adams County"},
        "80246": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80247": {"Denver County": "Denver County", "Arapahoe County": "Arapahoe County"},
        "80249": {"Adams County": "Adams County", "Denver County": "Denver County"},
        "80260": {"Adams County": "Adams County"},
        "80264": {"Denver County": "Denver County"},
        "80290": {"Denver County": "Denver County"},
        "80293": {"Denver County": "Denver County"},
        "80294": {"Denver County": "Denver County"},
        "80301": {"Boulder County": "Boulder County"},
        "80302": {"Boulder County": "Boulder County"},
        "80303": {"Boulder County": "Boulder County", "Jefferson County": "Jefferson County"},
        "80304": {"Boulder County": "Boulder County"},
        "80305": {"Boulder County": "Boulder County"},
        "80310": {"Boulder County": "Boulder County"},
        "80401": {"Jefferson County": "Jefferson County"},
        "80403": {
            "Gilpin County": "Gilpin County",
            "Boulder County": "Boulder County",
            "Jefferson County": "Jefferson County",
            "Clear Creek County": "Clear Creek County",
        },
        "80419": {"Jefferson County": "Jefferson County"},
        "80420": {"Lake County": "Lake County", "Park County": "Park County", "Summit County": "Summit County"},
        "80421": {
            "Park County": "Park County",
            "Jefferson County": "Jefferson County",
            "Clear Creek County": "Clear Creek County",
        },
        "80422": {
            "Grand County": "Grand County",
            "Gilpin County": "Gilpin County",
            "Boulder County": "Boulder County",
            "Jefferson County": "Jefferson County",
            "Clear Creek County": "Clear Creek County",
        },
        "80423": {
            "Eagle County": "Eagle County",
            "Grand County": "Grand County",
            "Routt County": "Routt County",
            "Summit County": "Summit County",
        },
        "80424": {"Lake County": "Lake County", "Park County": "Park County", "Summit County": "Summit County"},
        "80425": {"Douglas County": "Douglas County", "Jefferson County": "Jefferson County"},
        "80426": {"Eagle County": "Eagle County", "Routt County": "Routt County", "Garfield County": "Garfield County"},
        "80427": {
            "Gilpin County": "Gilpin County",
            "Jefferson County": "Jefferson County",
            "Clear Creek County": "Clear Creek County",
        },
        "80428": {"Routt County": "Routt County", "Jackson County": "Jackson County"},
        "80432": {"Park County": "Park County"},
        "80433": {
            "Park County": "Park County",
            "Douglas County": "Douglas County",
            "Jefferson County": "Jefferson County",
        },
        "80434": {"Jackson County": "Jackson County"},
        "80435": {
            "Park County": "Park County",
            "Summit County": "Summit County",
            "Clear Creek County": "Clear Creek County",
        },
        "80436": {"Grand County": "Grand County", "Clear Creek County": "Clear Creek County"},
        "80438": {"Grand County": "Grand County", "Clear Creek County": "Clear Creek County"},
        "80439": {
            "Park County": "Park County",
            "Gilpin County": "Gilpin County",
            "Jefferson County": "Jefferson County",
            "Clear Creek County": "Clear Creek County",
        },
        "80440": {"Lake County": "Lake County", "Park County": "Park County", "Summit County": "Summit County"},
        "80442": {"Grand County": "Grand County"},
        "80443": {
            "Lake County": "Lake County",
            "Park County": "Park County",
            "Eagle County": "Eagle County",
            "Summit County": "Summit County",
        },
        "80444": {
            "Park County": "Park County",
            "Summit County": "Summit County",
            "Clear Creek County": "Clear Creek County",
        },
        "80446": {
            "Grand County": "Grand County",
            "Boulder County": "Boulder County",
            "Jackson County": "Jackson County",
        },
        "80447": {
            "Grand County": "Grand County",
            "Boulder County": "Boulder County",
            "Jackson County": "Jackson County",
            "Larimer County": "Larimer County",
        },
        "80448": {
            "Park County": "Park County",
            "Summit County": "Summit County",
            "Jefferson County": "Jefferson County",
            "Clear Creek County": "Clear Creek County",
        },
        "80449": {
            "Lake County": "Lake County",
            "Park County": "Park County",
            "Chaffee County": "Chaffee County",
            "Fremont County": "Fremont County",
        },
        "80451": {"Grand County": "Grand County"},
        "80452": {
            "Park County": "Park County",
            "Grand County": "Grand County",
            "Gilpin County": "Gilpin County",
            "Clear Creek County": "Clear Creek County",
        },
        "80453": {"Jefferson County": "Jefferson County"},
        "80454": {"Jefferson County": "Jefferson County"},
        "80455": {"Boulder County": "Boulder County"},
        "80456": {
            "Park County": "Park County",
            "Summit County": "Summit County",
            "Jefferson County": "Jefferson County",
        },
        "80457": {"Jefferson County": "Jefferson County"},
        "80459": {
            "Eagle County": "Eagle County",
            "Grand County": "Grand County",
            "Routt County": "Routt County",
            "Summit County": "Summit County",
            "Jackson County": "Jackson County",
        },
        "80461": {
            "Lake County": "Lake County",
            "Park County": "Park County",
            "Eagle County": "Eagle County",
            "Pitkin County": "Pitkin County",
            "Summit County": "Summit County",
            "Chaffee County": "Chaffee County",
        },
        "80463": {"Eagle County": "Eagle County", "Grand County": "Grand County", "Routt County": "Routt County"},
        "80465": {"Jefferson County": "Jefferson County"},
        "80466": {"Grand County": "Grand County", "Gilpin County": "Gilpin County", "Boulder County": "Boulder County"},
        "80467": {
            "Grand County": "Grand County",
            "Routt County": "Routt County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "80468": {
            "Grand County": "Grand County",
            "Summit County": "Summit County",
            "Clear Creek County": "Clear Creek County",
        },
        "80469": {"Routt County": "Routt County", "Rio Blanco County": "Rio Blanco County"},
        "80470": {
            "Park County": "Park County",
            "Jefferson County": "Jefferson County",
            "Clear Creek County": "Clear Creek County",
        },
        "80471": {"Gilpin County": "Gilpin County", "Boulder County": "Boulder County"},
        "80473": {"Grand County": "Grand County", "Jackson County": "Jackson County"},
        "80475": {"Park County": "Park County"},
        "80476": {
            "Grand County": "Grand County",
            "Summit County": "Summit County",
            "Clear Creek County": "Clear Creek County",
        },
        "80477": {"Routt County": "Routt County"},
        "80478": {"Grand County": "Grand County"},
        "80479": {"Eagle County": "Eagle County", "Routt County": "Routt County"},
        "80480": {
            "Grand County": "Grand County",
            "Routt County": "Routt County",
            "Jackson County": "Jackson County",
            "Larimer County": "Larimer County",
        },
        "80481": {"Grand County": "Grand County", "Boulder County": "Boulder County"},
        "80482": {
            "Grand County": "Grand County",
            "Gilpin County": "Gilpin County",
            "Boulder County": "Boulder County",
            "Clear Creek County": "Clear Creek County",
        },
        "80483": {
            "Routt County": "Routt County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "80487": {"Grand County": "Grand County", "Routt County": "Routt County", "Jackson County": "Jackson County"},
        "80488": {"Routt County": "Routt County"},
        "80497": {
            "Grand County": "Grand County",
            "Summit County": "Summit County",
            "Clear Creek County": "Clear Creek County",
        },
        "80498": {"Eagle County": "Eagle County", "Grand County": "Grand County", "Summit County": "Summit County"},
        "80501": {"Weld County": "Weld County", "Boulder County": "Boulder County"},
        "80503": {"Boulder County": "Boulder County", "Larimer County": "Larimer County"},
        "80504": {"Weld County": "Weld County", "Boulder County": "Boulder County", "Larimer County": "Larimer County"},
        "80510": {
            "Grand County": "Grand County",
            "Boulder County": "Boulder County",
            "Larimer County": "Larimer County",
        },
        "80511": {"Larimer County": "Larimer County"},
        "80512": {
            "Grand County": "Grand County",
            "Jackson County": "Jackson County",
            "Larimer County": "Larimer County",
        },
        "80513": {"Weld County": "Weld County", "Boulder County": "Boulder County", "Larimer County": "Larimer County"},
        "80514": {"Weld County": "Weld County", "Broomfield County": "Broomfield County"},
        "80515": {"Larimer County": "Larimer County"},
        "80516": {
            "Weld County": "Weld County",
            "Adams County": "Adams County",
            "Boulder County": "Boulder County",
            "Broomfield County": "Broomfield County",
        },
        "80517": {
            "Grand County": "Grand County",
            "Boulder County": "Boulder County",
            "Larimer County": "Larimer County",
        },
        "80520": {"Weld County": "Weld County"},
        "80521": {"Larimer County": "Larimer County"},
        "80524": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80525": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80526": {"Larimer County": "Larimer County"},
        "80528": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80530": {"Weld County": "Weld County"},
        "80532": {"Larimer County": "Larimer County"},
        "80534": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80535": {"Larimer County": "Larimer County"},
        "80536": {"Larimer County": "Larimer County"},
        "80537": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80538": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80540": {"Boulder County": "Boulder County", "Larimer County": "Larimer County"},
        "80542": {"Weld County": "Weld County"},
        "80543": {"Weld County": "Weld County"},
        "80544": {"Boulder County": "Boulder County"},
        "80545": {"Larimer County": "Larimer County"},
        "80546": {"Weld County": "Weld County"},
        "80547": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80549": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80550": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80601": {"Weld County": "Weld County", "Adams County": "Adams County"},
        "80602": {
            "Weld County": "Weld County",
            "Adams County": "Adams County",
            "Broomfield County": "Broomfield County",
        },
        "80603": {
            "Weld County": "Weld County",
            "Adams County": "Adams County",
            "Denver County": "Denver County",
            "Broomfield County": "Broomfield County",
        },
        "80610": {"Weld County": "Weld County"},
        "80611": {"Weld County": "Weld County", "Morgan County": "Morgan County"},
        "80612": {"Weld County": "Weld County", "Larimer County": "Larimer County"},
        "80615": {"Weld County": "Weld County"},
        "80620": {"Weld County": "Weld County"},
        "80621": {"Weld County": "Weld County"},
        "80622": {"Weld County": "Weld County"},
        "80623": {"Weld County": "Weld County"},
        "80624": {"Weld County": "Weld County"},
        "80631": {"Weld County": "Weld County"},
        "80634": {"Weld County": "Weld County"},
        "80640": {"Adams County": "Adams County"},
        "80642": {"Weld County": "Weld County", "Adams County": "Adams County", "Denver County": "Denver County"},
        "80643": {"Weld County": "Weld County", "Adams County": "Adams County"},
        "80644": {"Weld County": "Weld County"},
        "80645": {"Weld County": "Weld County"},
        "80648": {"Weld County": "Weld County"},
        "80649": {"Weld County": "Weld County", "Morgan County": "Morgan County"},
        "80650": {"Weld County": "Weld County"},
        "80651": {"Weld County": "Weld County"},
        "80652": {"Weld County": "Weld County", "Adams County": "Adams County", "Morgan County": "Morgan County"},
        "80653": {"Morgan County": "Morgan County"},
        "80654": {"Weld County": "Weld County", "Adams County": "Adams County", "Morgan County": "Morgan County"},
        "80701": {
            "Weld County": "Weld County",
            "Adams County": "Adams County",
            "Morgan County": "Morgan County",
            "Washington County": "Washington County",
        },
        "80705": {"Morgan County": "Morgan County"},
        "80720": {
            "Yuma County": "Yuma County",
            "Logan County": "Logan County",
            "Morgan County": "Morgan County",
            "Washington County": "Washington County",
        },
        "80721": {"Phillips County": "Phillips County", "Sedgwick County": "Sedgwick County"},
        "80722": {"Logan County": "Logan County", "Washington County": "Washington County"},
        "80723": {"Morgan County": "Morgan County", "Washington County": "Washington County"},
        "80726": {"Logan County": "Logan County", "Sedgwick County": "Sedgwick County"},
        "80727": {"Yuma County": "Yuma County"},
        "80728": {
            "Logan County": "Logan County",
            "Sedgwick County": "Sedgwick County",
            "Washington County": "Washington County",
        },
        "80729": {"Weld County": "Weld County"},
        "80731": {
            "Yuma County": "Yuma County",
            "Logan County": "Logan County",
            "Phillips County": "Phillips County",
            "Sedgwick County": "Sedgwick County",
            "Washington County": "Washington County",
        },
        "80733": {
            "Logan County": "Logan County",
            "Morgan County": "Morgan County",
            "Washington County": "Washington County",
        },
        "80734": {
            "Yuma County": "Yuma County",
            "Phillips County": "Phillips County",
            "Sedgwick County": "Sedgwick County",
        },
        "80735": {"Yuma County": "Yuma County", "Kit Carson County": "Kit Carson County"},
        "80736": {"Logan County": "Logan County"},
        "80737": {"Phillips County": "Phillips County", "Sedgwick County": "Sedgwick County"},
        "80740": {"Lincoln County": "Lincoln County", "Washington County": "Washington County"},
        "80741": {
            "Weld County": "Weld County",
            "Logan County": "Logan County",
            "Morgan County": "Morgan County",
            "Washington County": "Washington County",
        },
        "80742": {"Weld County": "Weld County", "Logan County": "Logan County", "Morgan County": "Morgan County"},
        "80743": {
            "Yuma County": "Yuma County",
            "Logan County": "Logan County",
            "Washington County": "Washington County",
        },
        "80744": {"Phillips County": "Phillips County", "Sedgwick County": "Sedgwick County"},
        "80745": {"Weld County": "Weld County", "Logan County": "Logan County"},
        "80746": {"Phillips County": "Phillips County"},
        "80747": {"Logan County": "Logan County"},
        "80749": {
            "Logan County": "Logan County",
            "Phillips County": "Phillips County",
            "Sedgwick County": "Sedgwick County",
        },
        "80750": {
            "Weld County": "Weld County",
            "Logan County": "Logan County",
            "Morgan County": "Morgan County",
            "Washington County": "Washington County",
        },
        "80751": {"Logan County": "Logan County", "Washington County": "Washington County"},
        "80754": {"Weld County": "Weld County", "Logan County": "Logan County", "Morgan County": "Morgan County"},
        "80755": {"Yuma County": "Yuma County"},
        "80757": {
            "Adams County": "Adams County",
            "Morgan County": "Morgan County",
            "Lincoln County": "Lincoln County",
            "Arapahoe County": "Arapahoe County",
            "Washington County": "Washington County",
        },
        "80758": {"Yuma County": "Yuma County", "Phillips County": "Phillips County"},
        "80759": {
            "Yuma County": "Yuma County",
            "Logan County": "Logan County",
            "Phillips County": "Phillips County",
            "Washington County": "Washington County",
        },
        "80801": {"Washington County": "Washington County"},
        "80802": {
            "Kiowa County": "Kiowa County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80804": {
            "Lincoln County": "Lincoln County",
            "Kit Carson County": "Kit Carson County",
            "Washington County": "Washington County",
        },
        "80805": {
            "Yuma County": "Yuma County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80807": {
            "Yuma County": "Yuma County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80808": {"Elbert County": "Elbert County", "El Paso County": "El Paso County"},
        "80809": {"Teller County": "Teller County", "El Paso County": "El Paso County"},
        "80810": {
            "Kiowa County": "Kiowa County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80812": {
            "Yuma County": "Yuma County",
            "Kit Carson County": "Kit Carson County",
            "Washington County": "Washington County",
        },
        "80813": {
            "Teller County": "Teller County",
            "El Paso County": "El Paso County",
            "Fremont County": "Fremont County",
        },
        "80814": {"Teller County": "Teller County"},
        "80815": {
            "Lincoln County": "Lincoln County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
            "Washington County": "Washington County",
        },
        "80816": {"Park County": "Park County", "Teller County": "Teller County", "Fremont County": "Fremont County"},
        "80817": {"Pueblo County": "Pueblo County", "El Paso County": "El Paso County"},
        "80818": {"Lincoln County": "Lincoln County", "Washington County": "Washington County"},
        "80819": {"Teller County": "Teller County", "El Paso County": "El Paso County"},
        "80820": {"Park County": "Park County", "Teller County": "Teller County", "Fremont County": "Fremont County"},
        "80821": {
            "Elbert County": "Elbert County",
            "Lincoln County": "Lincoln County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80822": {
            "Yuma County": "Yuma County",
            "Kit Carson County": "Kit Carson County",
            "Washington County": "Washington County",
        },
        "80823": {
            "Kiowa County": "Kiowa County",
            "Crowley County": "Crowley County",
            "Lincoln County": "Lincoln County",
            "Cheyenne County": "Cheyenne County",
        },
        "80824": {"Yuma County": "Yuma County", "Kit Carson County": "Kit Carson County"},
        "80825": {
            "Kiowa County": "Kiowa County",
            "Lincoln County": "Lincoln County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80827": {
            "Park County": "Park County",
            "Teller County": "Teller County",
            "Douglas County": "Douglas County",
            "Jefferson County": "Jefferson County",
        },
        "80828": {
            "Elbert County": "Elbert County",
            "Lincoln County": "Lincoln County",
            "Arapahoe County": "Arapahoe County",
            "Washington County": "Washington County",
        },
        "80829": {"Teller County": "Teller County", "El Paso County": "El Paso County"},
        "80830": {
            "Elbert County": "Elbert County",
            "El Paso County": "El Paso County",
            "Lincoln County": "Lincoln County",
        },
        "80831": {"Elbert County": "Elbert County", "El Paso County": "El Paso County"},
        "80832": {
            "Elbert County": "Elbert County",
            "El Paso County": "El Paso County",
            "Lincoln County": "Lincoln County",
        },
        "80833": {
            "Elbert County": "Elbert County",
            "Pueblo County": "Pueblo County",
            "Crowley County": "Crowley County",
            "El Paso County": "El Paso County",
            "Lincoln County": "Lincoln County",
        },
        "80834": {
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
            "Washington County": "Washington County",
        },
        "80835": {"Elbert County": "Elbert County", "El Paso County": "El Paso County"},
        "80836": {
            "Yuma County": "Yuma County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80840": {"El Paso County": "El Paso County"},
        "80860": {
            "Teller County": "Teller County",
            "El Paso County": "El Paso County",
            "Fremont County": "Fremont County",
        },
        "80861": {
            "Yuma County": "Yuma County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
            "Washington County": "Washington County",
        },
        "80862": {
            "Lincoln County": "Lincoln County",
            "Cheyenne County": "Cheyenne County",
            "Kit Carson County": "Kit Carson County",
        },
        "80863": {
            "Teller County": "Teller County",
            "Douglas County": "Douglas County",
            "El Paso County": "El Paso County",
        },
        "80864": {
            "Pueblo County": "Pueblo County",
            "Crowley County": "Crowley County",
            "El Paso County": "El Paso County",
            "Lincoln County": "Lincoln County",
        },
        "80902": {"El Paso County": "El Paso County"},
        "80903": {"El Paso County": "El Paso County"},
        "80904": {"El Paso County": "El Paso County"},
        "80905": {"El Paso County": "El Paso County"},
        "80906": {"Teller County": "Teller County", "El Paso County": "El Paso County"},
        "80907": {"El Paso County": "El Paso County"},
        "80908": {
            "Elbert County": "Elbert County",
            "Douglas County": "Douglas County",
            "El Paso County": "El Paso County",
        },
        "80909": {"El Paso County": "El Paso County"},
        "80910": {"El Paso County": "El Paso County"},
        "80911": {"El Paso County": "El Paso County"},
        "80913": {"El Paso County": "El Paso County"},
        "80914": {"El Paso County": "El Paso County"},
        "80915": {"El Paso County": "El Paso County"},
        "80916": {"El Paso County": "El Paso County"},
        "80917": {"El Paso County": "El Paso County"},
        "80918": {"El Paso County": "El Paso County"},
        "80919": {"El Paso County": "El Paso County"},
        "80920": {"El Paso County": "El Paso County"},
        "80921": {"Teller County": "Teller County", "El Paso County": "El Paso County"},
        "80922": {"El Paso County": "El Paso County"},
        "80923": {"El Paso County": "El Paso County"},
        "80924": {"El Paso County": "El Paso County"},
        "80925": {"El Paso County": "El Paso County"},
        "80926": {
            "Teller County": "Teller County",
            "El Paso County": "El Paso County",
            "Fremont County": "Fremont County",
        },
        "80927": {"El Paso County": "El Paso County"},
        "80928": {"Pueblo County": "Pueblo County", "El Paso County": "El Paso County"},
        "80929": {"El Paso County": "El Paso County"},
        "80930": {"El Paso County": "El Paso County"},
        "80938": {"El Paso County": "El Paso County"},
        "80939": {"El Paso County": "El Paso County"},
        "80951": {"El Paso County": "El Paso County"},
        "81001": {"Pueblo County": "Pueblo County"},
        "81003": {"Pueblo County": "Pueblo County"},
        "81004": {"Pueblo County": "Pueblo County"},
        "81005": {
            "Custer County": "Custer County",
            "Pueblo County": "Pueblo County",
            "Fremont County": "Fremont County",
        },
        "81006": {"Pueblo County": "Pueblo County"},
        "81007": {"Pueblo County": "Pueblo County", "Fremont County": "Fremont County"},
        "81008": {"Pueblo County": "Pueblo County", "El Paso County": "El Paso County"},
        "81019": {"Pueblo County": "Pueblo County"},
        "81020": {
            "Pueblo County": "Pueblo County",
            "Huerfano County": "Huerfano County",
            "Las Animas County": "Las Animas County",
        },
        "81021": {
            "Bent County": "Bent County",
            "Kiowa County": "Kiowa County",
            "Otero County": "Otero County",
            "Crowley County": "Crowley County",
            "Lincoln County": "Lincoln County",
        },
        "81022": {"Pueblo County": "Pueblo County", "Huerfano County": "Huerfano County"},
        "81023": {"Custer County": "Custer County", "Pueblo County": "Pueblo County"},
        "81024": {"Las Animas County": "Las Animas County"},
        "81025": {
            "Pueblo County": "Pueblo County",
            "Crowley County": "Crowley County",
            "El Paso County": "El Paso County",
            "Lincoln County": "Lincoln County",
        },
        "81027": {"Las Animas County": "Las Animas County"},
        "81029": {"Baca County": "Baca County"},
        "81030": {"Otero County": "Otero County"},
        "81033": {"Crowley County": "Crowley County"},
        "81036": {
            "Bent County": "Bent County",
            "Kiowa County": "Kiowa County",
            "Prowers County": "Prowers County",
            "Cheyenne County": "Cheyenne County",
        },
        "81038": {"Bent County": "Bent County"},
        "81039": {
            "Otero County": "Otero County",
            "Pueblo County": "Pueblo County",
            "Crowley County": "Crowley County",
            "Huerfano County": "Huerfano County",
            "Las Animas County": "Las Animas County",
        },
        "81040": {
            "Custer County": "Custer County",
            "Pueblo County": "Pueblo County",
            "Alamosa County": "Alamosa County",
            "Costilla County": "Costilla County",
            "Huerfano County": "Huerfano County",
            "Saguache County": "Saguache County",
        },
        "81041": {"Baca County": "Baca County", "Prowers County": "Prowers County"},
        "81043": {"Prowers County": "Prowers County"},
        "81044": {"Baca County": "Baca County", "Bent County": "Bent County"},
        "81045": {
            "Kiowa County": "Kiowa County",
            "Lincoln County": "Lincoln County",
            "Cheyenne County": "Cheyenne County",
        },
        "81047": {"Baca County": "Baca County", "Kiowa County": "Kiowa County", "Prowers County": "Prowers County"},
        "81049": {
            "Baca County": "Baca County",
            "Bent County": "Bent County",
            "Otero County": "Otero County",
            "Las Animas County": "Las Animas County",
        },
        "81050": {
            "Bent County": "Bent County",
            "Kiowa County": "Kiowa County",
            "Otero County": "Otero County",
            "Crowley County": "Crowley County",
            "Las Animas County": "Las Animas County",
        },
        "81052": {
            "Baca County": "Baca County",
            "Bent County": "Bent County",
            "Kiowa County": "Kiowa County",
            "Prowers County": "Prowers County",
        },
        "81054": {
            "Baca County": "Baca County",
            "Bent County": "Bent County",
            "Kiowa County": "Kiowa County",
            "Otero County": "Otero County",
            "Las Animas County": "Las Animas County",
        },
        "81055": {
            "Costilla County": "Costilla County",
            "Huerfano County": "Huerfano County",
            "Las Animas County": "Las Animas County",
        },
        "81057": {"Bent County": "Bent County"},
        "81058": {"Otero County": "Otero County", "Crowley County": "Crowley County"},
        "81059": {
            "Otero County": "Otero County",
            "Pueblo County": "Pueblo County",
            "Las Animas County": "Las Animas County",
        },
        "81062": {
            "Otero County": "Otero County",
            "Pueblo County": "Pueblo County",
            "Crowley County": "Crowley County",
            "El Paso County": "El Paso County",
            "Lincoln County": "Lincoln County",
        },
        "81063": {
            "Otero County": "Otero County",
            "Crowley County": "Crowley County",
            "Lincoln County": "Lincoln County",
        },
        "81064": {"Baca County": "Baca County", "Las Animas County": "Las Animas County"},
        "81067": {
            "Otero County": "Otero County",
            "Pueblo County": "Pueblo County",
            "Crowley County": "Crowley County",
            "Las Animas County": "Las Animas County",
        },
        "81069": {
            "Custer County": "Custer County",
            "Pueblo County": "Pueblo County",
            "Huerfano County": "Huerfano County",
        },
        "81071": {
            "Kiowa County": "Kiowa County",
            "Prowers County": "Prowers County",
            "Cheyenne County": "Cheyenne County",
        },
        "81073": {
            "Baca County": "Baca County",
            "Bent County": "Bent County",
            "Prowers County": "Prowers County",
            "Las Animas County": "Las Animas County",
        },
        "81076": {
            "Kiowa County": "Kiowa County",
            "Otero County": "Otero County",
            "Crowley County": "Crowley County",
            "Lincoln County": "Lincoln County",
        },
        "81077": {"Otero County": "Otero County"},
        "81081": {"Las Animas County": "Las Animas County"},
        "81082": {"Las Animas County": "Las Animas County"},
        "81084": {"Baca County": "Baca County", "Prowers County": "Prowers County"},
        "81087": {"Baca County": "Baca County"},
        "81089": {
            "Pueblo County": "Pueblo County",
            "Huerfano County": "Huerfano County",
            "Las Animas County": "Las Animas County",
        },
        "81090": {"Baca County": "Baca County", "Prowers County": "Prowers County"},
        "81091": {
            "Costilla County": "Costilla County",
            "Huerfano County": "Huerfano County",
            "Las Animas County": "Las Animas County",
        },
        "81092": {"Bent County": "Bent County", "Kiowa County": "Kiowa County", "Prowers County": "Prowers County"},
        "81101": {
            "Alamosa County": "Alamosa County",
            "Conejos County": "Conejos County",
            "Costilla County": "Costilla County",
            "Rio Grande County": "Rio Grande County",
        },
        "81120": {
            "Conejos County": "Conejos County",
            "Costilla County": "Costilla County",
            "Archuleta County": "Archuleta County",
            "Rio Grande County": "Rio Grande County",
        },
        "81121": {"La Plata County": "La Plata County", "Archuleta County": "Archuleta County"},
        "81122": {
            "Hinsdale County": "Hinsdale County",
            "La Plata County": "La Plata County",
            "San Juan County": "San Juan County",
            "Archuleta County": "Archuleta County",
        },
        "81123": {
            "Alamosa County": "Alamosa County",
            "Conejos County": "Conejos County",
            "Costilla County": "Costilla County",
            "Huerfano County": "Huerfano County",
        },
        "81124": {"Conejos County": "Conejos County"},
        "81125": {
            "Alamosa County": "Alamosa County",
            "Saguache County": "Saguache County",
            "Rio Grande County": "Rio Grande County",
        },
        "81126": {"Costilla County": "Costilla County"},
        "81128": {"Conejos County": "Conejos County", "Archuleta County": "Archuleta County"},
        "81129": {"Conejos County": "Conejos County"},
        "81130": {
            "Mineral County": "Mineral County",
            "Hinsdale County": "Hinsdale County",
            "Saguache County": "Saguache County",
            "San Juan County": "San Juan County",
            "Archuleta County": "Archuleta County",
            "Rio Grande County": "Rio Grande County",
        },
        "81131": {
            "Custer County": "Custer County",
            "Alamosa County": "Alamosa County",
            "Huerfano County": "Huerfano County",
            "Saguache County": "Saguache County",
        },
        "81132": {
            "Conejos County": "Conejos County",
            "Mineral County": "Mineral County",
            "Saguache County": "Saguache County",
            "Rio Grande County": "Rio Grande County",
        },
        "81133": {"Costilla County": "Costilla County", "Huerfano County": "Huerfano County"},
        "81136": {"Alamosa County": "Alamosa County", "Saguache County": "Saguache County"},
        "81137": {"La Plata County": "La Plata County", "Archuleta County": "Archuleta County"},
        "81138": {"Costilla County": "Costilla County"},
        "81140": {
            "Alamosa County": "Alamosa County",
            "Conejos County": "Conejos County",
            "Rio Grande County": "Rio Grande County",
        },
        "81141": {"Conejos County": "Conejos County", "Costilla County": "Costilla County"},
        "81143": {"Custer County": "Custer County", "Saguache County": "Saguache County"},
        "81144": {
            "Alamosa County": "Alamosa County",
            "Conejos County": "Conejos County",
            "Rio Grande County": "Rio Grande County",
        },
        "81146": {
            "Alamosa County": "Alamosa County",
            "Costilla County": "Costilla County",
            "Huerfano County": "Huerfano County",
            "Saguache County": "Saguache County",
        },
        "81147": {
            "Conejos County": "Conejos County",
            "Mineral County": "Mineral County",
            "Hinsdale County": "Hinsdale County",
            "La Plata County": "La Plata County",
            "San Juan County": "San Juan County",
            "Archuleta County": "Archuleta County",
            "Rio Grande County": "Rio Grande County",
        },
        "81148": {"Conejos County": "Conejos County"},
        "81149": {"Mineral County": "Mineral County", "Saguache County": "Saguache County"},
        "81151": {
            "Alamosa County": "Alamosa County",
            "Conejos County": "Conejos County",
            "Costilla County": "Costilla County",
        },
        "81152": {
            "Conejos County": "Conejos County",
            "Costilla County": "Costilla County",
            "Huerfano County": "Huerfano County",
            "Las Animas County": "Las Animas County",
        },
        "81154": {
            "Conejos County": "Conejos County",
            "Mineral County": "Mineral County",
            "Archuleta County": "Archuleta County",
            "Rio Grande County": "Rio Grande County",
        },
        "81155": {
            "Custer County": "Custer County",
            "Chaffee County": "Chaffee County",
            "Fremont County": "Fremont County",
            "Saguache County": "Saguache County",
        },
        "81201": {
            "Park County": "Park County",
            "Chaffee County": "Chaffee County",
            "Fremont County": "Fremont County",
            "Gunnison County": "Gunnison County",
            "Saguache County": "Saguache County",
        },
        "81210": {
            "Pitkin County": "Pitkin County",
            "Chaffee County": "Chaffee County",
            "Gunnison County": "Gunnison County",
        },
        "81211": {
            "Lake County": "Lake County",
            "Park County": "Park County",
            "Pitkin County": "Pitkin County",
            "Chaffee County": "Chaffee County",
            "Gunnison County": "Gunnison County",
        },
        "81212": {
            "Park County": "Park County",
            "Custer County": "Custer County",
            "Teller County": "Teller County",
            "Fremont County": "Fremont County",
        },
        "81220": {
            "Ouray County": "Ouray County",
            "Gunnison County": "Gunnison County",
            "Hinsdale County": "Hinsdale County",
            "Montrose County": "Montrose County",
        },
        "81221": {"Fremont County": "Fremont County"},
        "81222": {"Fremont County": "Fremont County", "Saguache County": "Saguache County"},
        "81223": {
            "Custer County": "Custer County",
            "Fremont County": "Fremont County",
            "Saguache County": "Saguache County",
        },
        "81224": {"Pitkin County": "Pitkin County", "Gunnison County": "Gunnison County"},
        "81225": {"Pitkin County": "Pitkin County", "Gunnison County": "Gunnison County"},
        "81226": {"Custer County": "Custer County", "Fremont County": "Fremont County"},
        "81227": {"Chaffee County": "Chaffee County"},
        "81230": {
            "Delta County": "Delta County",
            "Mineral County": "Mineral County",
            "Gunnison County": "Gunnison County",
            "Hinsdale County": "Hinsdale County",
            "Montrose County": "Montrose County",
            "Saguache County": "Saguache County",
        },
        "81231": {"Gunnison County": "Gunnison County"},
        "81232": {"Custer County": "Custer County", "Fremont County": "Fremont County"},
        "81233": {"Fremont County": "Fremont County", "Saguache County": "Saguache County"},
        "81235": {
            "Ouray County": "Ouray County",
            "Mineral County": "Mineral County",
            "Gunnison County": "Gunnison County",
            "Hinsdale County": "Hinsdale County",
            "Saguache County": "Saguache County",
            "San Juan County": "San Juan County",
        },
        "81236": {"Chaffee County": "Chaffee County", "Gunnison County": "Gunnison County"},
        "81237": {"Gunnison County": "Gunnison County"},
        "81239": {"Gunnison County": "Gunnison County", "Saguache County": "Saguache County"},
        "81240": {
            "Pueblo County": "Pueblo County",
            "Teller County": "Teller County",
            "El Paso County": "El Paso County",
            "Fremont County": "Fremont County",
        },
        "81241": {"Gunnison County": "Gunnison County"},
        "81242": {"Chaffee County": "Chaffee County"},
        "81243": {
            "Gunnison County": "Gunnison County",
            "Hinsdale County": "Hinsdale County",
            "Saguache County": "Saguache County",
        },
        "81244": {"Fremont County": "Fremont County"},
        "81248": {
            "Chaffee County": "Chaffee County",
            "Gunnison County": "Gunnison County",
            "Saguache County": "Saguache County",
        },
        "81251": {"Lake County": "Lake County", "Pitkin County": "Pitkin County", "Chaffee County": "Chaffee County"},
        "81252": {
            "Custer County": "Custer County",
            "Fremont County": "Fremont County",
            "Huerfano County": "Huerfano County",
            "Saguache County": "Saguache County",
        },
        "81253": {
            "Custer County": "Custer County",
            "Pueblo County": "Pueblo County",
            "Fremont County": "Fremont County",
        },
        "81301": {
            "Dolores County": "Dolores County",
            "La Plata County": "La Plata County",
            "San Juan County": "San Juan County",
            "Montezuma County": "Montezuma County",
            "San Miguel County": "San Miguel County",
        },
        "81303": {"La Plata County": "La Plata County"},
        "81320": {
            "Dolores County": "Dolores County",
            "Montezuma County": "Montezuma County",
            "San Miguel County": "San Miguel County",
        },
        "81321": {"Montezuma County": "Montezuma County"},
        "81323": {
            "Dolores County": "Dolores County",
            "La Plata County": "La Plata County",
            "San Juan County": "San Juan County",
            "Montezuma County": "Montezuma County",
            "San Miguel County": "San Miguel County",
        },
        "81324": {
            "Dolores County": "Dolores County",
            "Montezuma County": "Montezuma County",
            "San Miguel County": "San Miguel County",
        },
        "81325": {
            "Dolores County": "Dolores County",
            "Montrose County": "Montrose County",
            "Montezuma County": "Montezuma County",
            "San Miguel County": "San Miguel County",
        },
        "81326": {"La Plata County": "La Plata County", "Montezuma County": "Montezuma County"},
        "81327": {"Montezuma County": "Montezuma County"},
        "81328": {"La Plata County": "La Plata County", "Montezuma County": "Montezuma County"},
        "81330": {"Montezuma County": "Montezuma County"},
        "81331": {"Dolores County": "Dolores County", "Montezuma County": "Montezuma County"},
        "81332": {
            "Dolores County": "Dolores County",
            "La Plata County": "La Plata County",
            "San Juan County": "San Juan County",
            "Montezuma County": "Montezuma County",
            "San Miguel County": "San Miguel County",
        },
        "81334": {"La Plata County": "La Plata County", "Montezuma County": "Montezuma County"},
        "81335": {"Montezuma County": "Montezuma County"},
        "81401": {
            "Delta County": "Delta County",
            "Ouray County": "Ouray County",
            "Gunnison County": "Gunnison County",
            "Montrose County": "Montrose County",
        },
        "81403": {
            "Ouray County": "Ouray County",
            "Gunnison County": "Gunnison County",
            "Montrose County": "Montrose County",
            "San Miguel County": "San Miguel County",
        },
        "81410": {"Delta County": "Delta County"},
        "81411": {"Montrose County": "Montrose County", "San Miguel County": "San Miguel County"},
        "81413": {"Mesa County": "Mesa County", "Delta County": "Delta County"},
        "81415": {
            "Delta County": "Delta County",
            "Gunnison County": "Gunnison County",
            "Montrose County": "Montrose County",
        },
        "81416": {"Mesa County": "Mesa County", "Delta County": "Delta County", "Montrose County": "Montrose County"},
        "81418": {"Delta County": "Delta County"},
        "81419": {"Mesa County": "Mesa County", "Delta County": "Delta County"},
        "81422": {
            "Mesa County": "Mesa County",
            "Montrose County": "Montrose County",
            "San Miguel County": "San Miguel County",
        },
        "81423": {
            "Dolores County": "Dolores County",
            "Montrose County": "Montrose County",
            "San Miguel County": "San Miguel County",
        },
        "81424": {"Montrose County": "Montrose County"},
        "81425": {"Mesa County": "Mesa County", "Delta County": "Delta County", "Montrose County": "Montrose County"},
        "81426": {
            "Dolores County": "Dolores County",
            "San Juan County": "San Juan County",
            "San Miguel County": "San Miguel County",
        },
        "81427": {
            "Ouray County": "Ouray County",
            "Hinsdale County": "Hinsdale County",
            "San Juan County": "San Juan County",
            "San Miguel County": "San Miguel County",
        },
        "81428": {"Mesa County": "Mesa County", "Delta County": "Delta County", "Gunnison County": "Gunnison County"},
        "81429": {"Montrose County": "Montrose County", "San Miguel County": "San Miguel County"},
        "81430": {
            "Ouray County": "Ouray County",
            "Dolores County": "Dolores County",
            "Montrose County": "Montrose County",
            "San Miguel County": "San Miguel County",
        },
        "81431": {"Montrose County": "Montrose County", "San Miguel County": "San Miguel County"},
        "81432": {
            "Ouray County": "Ouray County",
            "Gunnison County": "Gunnison County",
            "Hinsdale County": "Hinsdale County",
            "Montrose County": "Montrose County",
            "San Miguel County": "San Miguel County",
        },
        "81433": {
            "Ouray County": "Ouray County",
            "Hinsdale County": "Hinsdale County",
            "La Plata County": "La Plata County",
            "San Juan County": "San Juan County",
            "San Miguel County": "San Miguel County",
        },
        "81434": {
            "Mesa County": "Mesa County",
            "Delta County": "Delta County",
            "Pitkin County": "Pitkin County",
            "Gunnison County": "Gunnison County",
        },
        "81435": {
            "Ouray County": "Ouray County",
            "Dolores County": "Dolores County",
            "San Juan County": "San Juan County",
            "San Miguel County": "San Miguel County",
        },
        "81501": {"Mesa County": "Mesa County"},
        "81503": {"Mesa County": "Mesa County"},
        "81504": {"Mesa County": "Mesa County"},
        "81505": {"Mesa County": "Mesa County"},
        "81506": {"Mesa County": "Mesa County"},
        "81507": {"Mesa County": "Mesa County"},
        "81520": {"Mesa County": "Mesa County"},
        "81521": {"Mesa County": "Mesa County"},
        "81522": {"Mesa County": "Mesa County", "Montrose County": "Montrose County"},
        "81523": {"Mesa County": "Mesa County"},
        "81524": {"Mesa County": "Mesa County", "Garfield County": "Garfield County"},
        "81525": {"Mesa County": "Mesa County", "Garfield County": "Garfield County"},
        "81526": {"Mesa County": "Mesa County"},
        "81527": {"Mesa County": "Mesa County", "Delta County": "Delta County", "Montrose County": "Montrose County"},
        "81601": {
            "Eagle County": "Eagle County",
            "Pitkin County": "Pitkin County",
            "Garfield County": "Garfield County",
        },
        "81610": {"Moffat County": "Moffat County", "Rio Blanco County": "Rio Blanco County"},
        "81611": {
            "Lake County": "Lake County",
            "Pitkin County": "Pitkin County",
            "Chaffee County": "Chaffee County",
            "Gunnison County": "Gunnison County",
        },
        "81612": {"Pitkin County": "Pitkin County"},
        "81615": {"Pitkin County": "Pitkin County"},
        "81620": {"Eagle County": "Eagle County"},
        "81621": {
            "Eagle County": "Eagle County",
            "Pitkin County": "Pitkin County",
            "Garfield County": "Garfield County",
        },
        "81623": {
            "Mesa County": "Mesa County",
            "Eagle County": "Eagle County",
            "Pitkin County": "Pitkin County",
            "Garfield County": "Garfield County",
            "Gunnison County": "Gunnison County",
        },
        "81624": {
            "Mesa County": "Mesa County",
            "Delta County": "Delta County",
            "Pitkin County": "Pitkin County",
            "Garfield County": "Garfield County",
            "Gunnison County": "Gunnison County",
        },
        "81625": {"Routt County": "Routt County", "Moffat County": "Moffat County"},
        "81630": {
            "Mesa County": "Mesa County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81631": {"Eagle County": "Eagle County"},
        "81632": {"Eagle County": "Eagle County"},
        "81633": {"Moffat County": "Moffat County", "Rio Blanco County": "Rio Blanco County"},
        "81635": {
            "Mesa County": "Mesa County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81637": {
            "Eagle County": "Eagle County",
            "Routt County": "Routt County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81638": {
            "Routt County": "Routt County",
            "Moffat County": "Moffat County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81639": {
            "Routt County": "Routt County",
            "Moffat County": "Moffat County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81640": {"Moffat County": "Moffat County", "Rio Blanco County": "Rio Blanco County"},
        "81641": {
            "Routt County": "Routt County",
            "Moffat County": "Moffat County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81642": {"Lake County": "Lake County", "Eagle County": "Eagle County", "Pitkin County": "Pitkin County"},
        "81643": {"Mesa County": "Mesa County", "Delta County": "Delta County"},
        "81645": {
            "Lake County": "Lake County",
            "Eagle County": "Eagle County",
            "Pitkin County": "Pitkin County",
            "Summit County": "Summit County",
        },
        "81646": {"Mesa County": "Mesa County", "Delta County": "Delta County"},
        "81647": {
            "Mesa County": "Mesa County",
            "Pitkin County": "Pitkin County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81648": {
            "Moffat County": "Moffat County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81649": {"Eagle County": "Eagle County", "Summit County": "Summit County"},
        "81650": {
            "Mesa County": "Mesa County",
            "Garfield County": "Garfield County",
            "Rio Blanco County": "Rio Blanco County",
        },
        "81652": {"Mesa County": "Mesa County", "Garfield County": "Garfield County"},
        "81653": {"Routt County": "Routt County", "Moffat County": "Moffat County"},
        "81654": {"Pitkin County": "Pitkin County", "Gunnison County": "Gunnison County"},
        "81655": {"Eagle County": "Eagle County", "Summit County": "Summit County"},
        "81656": {"Pitkin County": "Pitkin County"},
        "81657": {"Eagle County": "Eagle County", "Summit County": "Summit County"},
        "82063": {"Jackson County": "Jackson County", "Larimer County": "Larimer County"},
    }

    category_benefits = {
        "cash": {
            "benefits": {
                "tanf": {
                    "name": {
                        "_label": "cashAssistanceBenefits.tanf",
                        "_default_message": "Temporary Assistance for Needy Families/Colorado Works (TANF): ",
                    },
                    "description": {
                        "_label": "cashAssistanceBenefits.tanf_desc",
                        "_default_message": "Cash assistance and work support",
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
                "andcs": {
                    "name": {
                        "_label": "cashAssistanceBenefits.andcs",
                        "_default_message": "Aid to the Needy Disabled - Colorado Supplement (AND-CS): ",
                    },
                    "description": {
                        "_label": "cashAssistanceBenefits.andcs_desc",
                        "_default_message": "State cash assistance for individuals who are disabled and receiving SSI",
                    },
                },
                "oap": {
                    "name": {"_label": "cashAssistanceBenefits.oap", "_default_message": "Old Age Pension (OAP): "},
                    "description": {
                        "_label": "cashAssistanceBenefits.oap_desc",
                        "_default_message": "State cash assistance for individuals 60 years of age or older",
                    },
                },
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
            },
            "category_name": {"_label": "cashAssistance", "_default_message": "Cash Assistance"},
        },
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
                "ede": {
                    "name": {"_label": "foodAndNutritionBenefits.ede", "_default_message": "Everyday Eats: "},
                    "description": {
                        "_label": "foodAndNutritionBenefits.ede_desc",
                        "_default_message": "Food support for people 60 years of age or older",
                    },
                },
            },
            "category_name": {"_label": "foodAndNutrition", "_default_message": "Food and Nutrition"},
        },
        "childCare": {
            "benefits": {
                "cccap": {
                    "name": {
                        "_label": "childCareBenefits.cccap",
                        "_default_message": "Colorado Child Care Assistance Program (CCCAP): ",
                    },
                    "description": {
                        "_label": "childCareBenefits.cccap_desc",
                        "_default_message": "Help with child care costs",
                    },
                },
                "denverpresc": {
                    "name": {
                        "_label": "childCareBenefits.denverpresc",
                        "_default_message": "Denver Preschool Program: ",
                    },
                    "description": {
                        "_label": "childCareBenefits.denverpresc_desc",
                        "_default_message": "Tuition credits for Denver preschoolers",
                    },
                },
                "coheadstart": {
                    "name": {"_label": "childCareBenefits.coheadstart", "_default_message": "Colorado Head Start: "},
                    "description": {
                        "_label": "childCareBenefits.coheadstart_desc",
                        "_default_message": "Free early child care and preschool",
                    },
                },
                "mydenver": {
                    "name": {"_label": "childCareBenefits.mydenver", "_default_message": "MY Denver Card: "},
                    "description": {
                        "_label": "childCareBenefits.mydenver_desc",
                        "_default_message": "Reduced-cost youth programs",
                    },
                },
                "upk": {
                    "name": {
                        "_label": "childCareBenefits.univpresc",
                        "_default_message": "Universal Preschool Colorado (UPK): ",
                    },
                    "description": {
                        "_label": "childCareBenefits.univpresc_desc",
                        "_default_message": "Free preschool",
                    },
                },
            },
            "category_name": {
                "_label": "childCareYouthAndEducation",
                "_default_message": "Child Care, Youth, and Education",
            },
        },
        "housingAndUtilities": {
            "benefits": {
                "lifeline": {
                    "name": {"_label": "housingAndUtilities.lifeline", "_default_message": "Lifeline: "},
                    "description": {
                        "_label": "housingAndUtilities.lifeline_desc",
                        "_default_message": "Phone or internet discount",
                    },
                },
                "leap": {
                    "name": {
                        "_label": "housingAndUtilities.leap",
                        "_default_message": "Low-Income Energy Assistance Program (LEAP): ",
                    },
                    "description": {
                        "_label": "housingAndUtilities.leap_desc",
                        "_default_message": "Help with winter heating bills",
                    },
                },
                "cowap": {
                    "name": {
                        "_label": "housingAndUtilities.cowap",
                        "_default_message": "Weatherization Assistance Program: ",
                    },
                    "description": {
                        "_label": "housingAndUtilities.cowap_desc",
                        "_default_message": "Free home energy upgrades",
                    },
                },
                "ubp": {
                    "name": {
                        "_label": "housingAndUtilities.ubp",
                        "_default_message": "Colorado Utility Bill Help Program: ",
                    },
                    "description": {
                        "_label": "housingAndUtilities.ubp_desc",
                        "_default_message": "Help paying utility bills",
                    },
                },
                "coPropTaxRentHeatCreditRebate": {
                    "name": {
                        "_label": "cashAssistanceBenefits.coPropTaxRentHeatCreditRebate",
                        "_default_message": "Colorado Property Tax/Rent/Heat Credit Rebate: ",
                    },
                    "description": {
                        "_label": "cashAssistanceBenefits.coPropTaxRentHeatCreditRebate_desc",
                        "_default_message": "Cash to pay property tax, rent, and heat bills",
                    },
                },
            },
            "category_name": {"_label": "housingAndUtilities", "_default_message": "Housing and Utilities"},
        },
        "transportation": {
            "benefits": {
                "rtdlive": {
                    "name": {"_label": "transportationBenefits.rtdlive", "_default_message": "RTD LiVE: "},
                    "description": {
                        "_label": "transportationBenefits.rtdlive_desc",
                        "_default_message": "Discounted RTD fares",
                    },
                }
            },
            "category_name": {"_label": "transportation", "_default_message": "Transportation"},
        },
        "healthCare": {
            "benefits": {
                "dentallowincseniors": {
                    "name": {
                        "_label": "healthCareBenefits.dentallowincseniors",
                        "_default_message": "Colorado Dental Health Program for Low-Income Seniors: ",
                    },
                    "description": {
                        "_label": "healthCareBenefits.dentallowincseniors_desc",
                        "_default_message": "Low-cost dental care for people 60 years of age or older",
                    },
                },
                "nfp": {
                    "name": {"_label": "healthCareBenefits.nfp", "_default_message": "Nurse-Family Partnership: "},
                    "description": {
                        "_label": "healthCareBenefits.nfp_desc",
                        "_default_message": "Personalized support for first-time parents",
                    },
                },
                "cfhc": {
                    "name": {
                        "_label": "healthCareBenefits.connectForHealth",
                        "_default_message": "Connect for Health/Premium Tax Credit: ",
                    },
                    "description": {
                        "_label": "healthCareBenefits.connectForHealth_desc",
                        "_default_message": "Health insurance marketplace premium tax credit",
                    },
                },
            },
            "category_name": {"_label": "healthCare", "_default_message": "Health Care"},
        },
        "taxCredits": {
            "benefits": {
                "eitc": {
                    "name": {
                        "_label": "taxCreditBenefits.eitc",
                        "_default_message": "Earned Income Tax Credit (EITC): ",
                    },
                    "description": {
                        "_label": "taxCreditBenefits.eitc_desc",
                        "_default_message": "Federal tax credit - earned income",
                    },
                },
                "ctc": {
                    "name": {"_label": "taxCreditBenefits.ctc", "_default_message": "Child Tax Credit (CTC): "},
                    "description": {"_label": "taxCreditBenefits.ctc_desc", "_default_message": "Federal tax credit"},
                },
                "coeitc": {
                    "name": {
                        "_label": "taxCreditBenefits.coeitc",
                        "_default_message": "Colorado Earned Income Tax Credit/Expanded Earned Income Tax Credit: ",
                    },
                    "description": {
                        "_label": "taxCreditBenefits.coeitc_desc",
                        "_default_message": "State tax credit - earned income",
                    },
                },
                "coctc": {
                    "name": {"_label": "taxCreditBenefits.coctc", "_default_message": "Colorado Child Tax Credit: "},
                    "description": {"_label": "taxCreditBenefits.coctc_desc", "_default_message": "State tax credit"},
                },
                "fatc": {
                    "name": {
                        "_label": "taxCreditBenefits.fatc",
                        "_default_message": "Family Affordability Tax Credit: ",
                    },
                    "description": {"_label": "taxCreditBenefits.fatc_desc", "_default_message": "State tax credit"},
                },
                "shitc": {
                    "name": {
                        "_label": "taxCreditBenefits.seniorHousingIncomeTaxCredit",
                        "_default_message": "Senior Housing Income Tax Credit: ",
                    },
                    "description": {
                        "_label": "taxCreditBenefits.seniorHousingIncomeTaxCredit_desc",
                        "_default_message": "State tax credit for people 65 years of age or older",
                    },
                },
            },
            "category_name": {"_label": "taxCredits", "_default_message": "Tax Credits"},
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
        "theme": {"default": "default", "211co": "twoOneOne"},
        "logoSource": {
            "default": "MFB_COLogo",
            "bia": "BIA_MFBLogo",
            "broomfield": "Broomfield_MFBLogo",
            "theactioncenter": "TheActionCenter_MFBLogo",
            "jeffcoHS": "JHSA_MFBLogo",
            "jeffcoHSCM": "JHSA_MFBLogo",
            "jeffcoPS": "JPS_MFBLogo",
            "villageExchange": "VE_Logo",
            "cch": "CCH_MFBLogo",
            "lgs": "LGS_Logo",
            "gac": "GAC_Logo",
            "fircsummitresourcecenter": "FIRC_Logo",
            "coBenefits": "CO_MFBLogo",
            "dhs": "DHS_MFBLogo",
            "ccig": "CCIG_Logo",
            "eaglecounty": "EC_MFBLogo",
            "achs": "ACHS_MFBLogo",
            "larimercounty": "LC_MFBLogo",
            "tellercounty": "TC_MFBLogo",
            "pueblo": "PC_MFBLogo",
            "pitkin": "PitkinCounty_MFBLogo",
        },
        "logoAlt": {
            "default": {"id": "referrerHook.logoAlts.default", "defaultMessage": "MyFriendBen home page button"},
            "bia": {
                "id": "referrerHook.logoAlts.bia",
                "defaultMessage": "Benefits in Action and MyFriendBen home page button",
            },
            "broomfield": {
                "id": "referrerHook.logoAlts.broomfield",
                "defaultMessage": "City and County of Broomfield and MyFriendBen home page button",
            },
            "theactioncenter": {
                "id": "referrerHook.logoAlts.theactioncenter",
                "defaultMessage": "The Action Center and MyFriendBen home page button",
            },
            "jeffcoHS": {
                "id": "referrerHook.logoAlts.jeffcoHS",
                "defaultMessage": "Jeffco Human Services and MyFriendBen home page button",
            },
            "jeffcoHSCM": {
                "id": "referrerHook.logoAlts.jeffcoHSCM",
                "defaultMessage": "Jeffco Human Services and MyFriendBen home page button",
            },
            "jeffcoPS": {
                "id": "referrerHook.logoAlts.jeffcoPS",
                "defaultMessage": "Jeffco Public Schools and MyFriendBen home page button",
            },
            "cch": {
                "id": "referrerHook.logoAlts.cch",
                "defaultMessage": "Colorado Coalition for the Homeless and MyFriendBen home page button",
            },
            "lgs": {"id": "referrerHook.logoAlts.lgs", "defaultMessage": "Let's Get Set home page button"},
            "gac": {"id": "referrerHook.logoAlts.gac", "defaultMessage": "Get Ahead Colorado home page button"},
            "fircsummitresourcecenter": {
                "id": "referrerHook.logoAlts.fircsummitresourcecenter",
                "defaultMessage": "Firc Summit Resource Center",
            },
            "coBenefits": {"id": "referrerHook.logoAlts.coBenefits", "defaultMessage": "MyFriendBen home page button"},
            "dhs": {
                "id": "referrerHook.logoAlts.dhs",
                "defaultMessage": "Denver Human Services and MyFriendBen home page button",
            },
            "ccig": {
                "id": "referrerHook.logoAlts.ccig",
                "defaultMessage": "CCIG and MyFriendBen home page button",
            },
            "eaglecounty": {
                "id": "referrerHook.logoAlts.eaglecounty",
                "defaultMessage": "Eagle County and MyFriendBen home page button",
            },
            "achs": {
                "id": "referrerHook.logoAlts.adamscountyhumanservices",
                "defaultMessage": "Adams County and MyFriendBen home page button",
            },
            "larimercounty": {
                "id": "referrerHook.logoAlts.larimercounty",
                "defaultMessage": "Larimer County and MyFriendBen home page button",
            },
            "tellercounty": {
                "id": "referrerHook.logoAlts.tellercounty",
                "defaultMessage": "Teller County and MyFriendBen home page button",
            },
            "pueblo": {
                "id": "referrerHook.logoAlts.pueblo",
                "defaultMessage": "Pueblo County and MyFriendBen home page button",
            },
            "pitkin": {
                "id": "referrerHook.logoAlts.pitkin",
                "defaultMessage": "Pitkin County and MyFriendBen home page button",
            },
        },
        "logoFooterSource": {"default": "MFB_Logo"},
        "logoFooterAlt": {"default": {"id": "footer.logo.alt", "defaultMessage": "MFB Logo"}},
        "logoClass": {
            "default": "logo",
            "broomfield": "broomfield-logo-size",
            "theactioncenter": "theactioncenter-logo-size",
            "eaglecounty": "eaglecounty-logo-size",
            "larimercounty": "larimercounty-logo-size",
            "tellercounty": "tellercounty-logo-size",
            "pueblo": "pueblocounty-logo-size",
            "pitkin": "pitkincounty-logo-size",
        },
        "twoOneOneLink": {
            "default": 'https://www.211colorado.org/?utm_source=myfriendben&utm_medium=inlink&utm_campaign=organic&utm_id="211mfb"',
            "211co": 'https://www.211colorado.org/?utm_source=myfriendben&utm_medium=inlink&utm_campaign=whitelabel&utm_id="211mfb"',
        },
        "shareLink": {
            "default": "https://screener.myfriendben.org",
            "211co": "https://screener.myfriendben.org?referrer=211co",
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
            "ccig": [
                "zipcode",
                "householdSize",
                "householdData",
                "hasExpenses",
                "householdAssets",
                "hasBenefits",
                "acuteHHConditions",
                "referralSource",
            ],
        },
        "featureFlags": {"default": [], "211co": ["no_results_more_help", "211co"]},
        "noResultMessage": {
            "default": {
                "_label": "noResultMessage",
                "_default_message": "It looks like you may not qualify for benefits included in MyFriendBen at this time. If you indicated need for an immediate resource, please click on the \"Near-Term Benefits\" tab. For additional resources, please click the 'More Help' button below to get the resources you're looking for.",
            },
        },
        "defaultLanguage": {"default": "en-us"},
    }

    override_text = {}
