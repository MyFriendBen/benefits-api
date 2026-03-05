def translation(name, i, message):
    return {"default_message": message, "label": f"eligibility_message.{name}-{i}"}


def income(income, max_income):
    """
    Household makes ${income} per year which must be less than ${max_income}
    """
    return (
        translation("income", 0, "Household makes"),
        f" ${round(income)} ",
        translation("income", 1, "per year which must be less than"),
        f" ${round(max_income)}",
    )


def income_range(income, min_income, max_income):
    """
    Household makes ${income} per year which must be between ${min_income} and ${max_income}
    """
    return (
        translation("income", 0, "Household makes"),
        f" ${round(income)} ",
        translation("income_range", 0, "per year which must be between"),
        f" ${round(min_income)} ",
        translation("income_range", 1, "and"),
        f" ${round(max_income)}",
    )


def income_limit_unknown():
    """
    Household income limit lookup failed
    """
    return (
        translation(
            "income_limit_lookup_failed",
            0,
            "Unable to determine income limits for your household",
        ),
    )


def presumed_eligibility():
    """
    Household presumed eligible based on other benefits
    """
    return (translation("presumptive_eligibility", 0, "Presumed eligibility based on other benefits"),)


def assets(asset_limit):
    """
    Household resources must not exceed ${asset_limit}
    """
    return (
        translation("assets", 0, "Household resources must not exceed"),
        f" ${round(asset_limit)}",
    )


def child(min_age=0, max_age=18):
    """
    Must have a child between the ages of {min_age} and {max_age}
    """
    return (
        translation("child", 0, "Must have a child between the ages of"),
        f" {min_age} ",
        translation("child", 1, "and"),
        f" {max_age}",
    )


def adult(min_age, max_age):
    """
    Someone in the household must be between the ages of {min_age} and {max_age}
    """
    return (
        translation("adult", 0, "Someone in the household must be between the ages of"),
        f" {min_age} ",
        translation("adult", 1, "and"),
        f" {max_age}",
    )


def older_than(min_age):
    """
    Someone in the household must be at least {min_age} years old
    """
    return (
        translation("older_than", 0, "Someone in the household must be at least"),
        f" {min_age} ",
        translation("older_than", 1, "years old"),
    )


def must_have_benefit(benefit_name):
    """
    Household must have {benefit_name}
    """
    return (translation("has_benefit", 0, "Household must have"), f" {benefit_name}")


def must_not_have_benefit(benefit_name):
    """
    Household must not have {benefit_name}
    """
    return (
        translation("not_have_benefit", 0, "Household must not have"),
        f" {benefit_name}",
    )


def location():
    """
    Must live in an eligible location
    """
    return (translation("location", 0, "Must live in an eligible location"),)


def has_disability():
    """
    Someone in the household must have a disability
    """
    return (translation("disability", 0, "Someone in the household must have a disability"),)


def has_no_insurance():
    """
    Someone in the household must not have health insurance
    """
    return (translation("no_insurance", 0, "Someone in the household must not have health insurance"),)


def is_pregnant():
    """
    Someone in the household must be pregnant
    """
    return (translation("pregnant", 0, "Someone in the household must be pregnant"),)


def has_utility_provider(utility_providers: list[str]):
    """
    Household must have one a list of utility providers
    """
    return (
        translation(
            "utility_provider",
            0,
            f"Household must have one of the following utility providers: {', '.join(utility_providers)}",
        ),
    )


def is_home_owner():
    """
    Household must by own home
    """
    return (translation("home_owner", 0, "Household must own home"),)
