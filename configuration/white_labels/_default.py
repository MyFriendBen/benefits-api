from .base import ConfigurationData
from screener.models import WhiteLabel


class DefaultConfigurationData(ConfigurationData):
    is_default = True

    @classmethod
    def get_white_label(self) -> WhiteLabel:
        return WhiteLabel.objects.get(code="_default")

    referrer_data = {
        "theme": {"default": "default"},
        "logoSource": {"default": ""},
        "logoAlt": {
            "default": {"id": "referrerHook.logoAlts.default", "defaultMessage": "MyFriendBen home page button"}
        },
        "logoFooterSource": {"default": "MFB_Logo"},
        "logoFooterAlt": {"default": {"id": "footer.logo.alt", "defaultMessage": "MFB Logo"}},
        "logoClass": {"default": "logo"},
        "twoOneOneLink": {
            "default": 'https://www.211colorado.org/?utm_source=myfriendben&utm_medium=inlink&utm_campaign=organic&utm_id="211mfb"'
        },
        "shareLink": {"default": "https://screener.myfriendben.org"},
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
            ]
        },
        "featureFlags": {"default": []},
        "noResultMessage": {
            "default": {
                "_label": "noResultMessage",
                "_default_message": "It looks like you may not qualify for benefits included in MyFriendBen at this time. If you indicated need for an immediate resource, please click on the “Near-Term Benefits” tab. For additional resources, please click the 'More Help' button below to get the resources you’re looking for.",
            },
        },
        "defaultLanguage": {"default": "en-us"},
    }

    footer_data = {
        "address_one": "1705 17th St.",
        "address_two": "Suite 200",
        "city": "Denver",
        "state": "CO",
        "zip_code": "80202",
        "email": "hello@myfriendben.org",
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
    }

    feedback_links = {
        "email": "hello@myfriendben.org",
        "survey": "https://docs.google.com/forms/d/e/1FAIpQLSdnfqjvlVSBQkJuUMvhEDUp-t6oD-8tPQi67uRG2iNetXmSfA/viewform?usp=sf_link",
    }

    override_text = {}

    consent_to_contact = {
        "en-us": "https://www.myfriendben.org/terms-and-conditions/",
        "es": "https://www.myfriendben.org/terminos-condiciones/",
    }

    privacy_policy = {
        "en-us": "https://www.myfriendben.org/privacy-policy/",
        "es": "https://www.myfriendben.org/privacidad/",
    }
