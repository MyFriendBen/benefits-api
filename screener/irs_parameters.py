"""
IRS gross income threshold for qualifying relative dependents.
Used by is_dependent() in screener/models.py to check if a household member
qualifies as a dependent under IRS rules. To add a new year, update the
dict below.

Values sourced from PE-US amount.yaml:
    2022: $4,400  Rev. Proc. 2021-45  https://www.irs.gov/pub/irs-drop/rp-21-45.pdf
    2023: $4,700  Rev. Proc. 2022-38  https://www.irs.gov/pub/irs-drop/rp-22-38.pdf
    2024: $5,050  Rev. Proc. 2023-34  https://www.irs.gov/pub/irs-drop/rp-23-34.pdf
    2025: $5,200  Rev. Proc. 2024-40  https://www.irs.gov/pub/irs-drop/rp-24-40.pdf
    2026: $5,300  Rev. Proc. 2025-32  https://www.irs.gov/pub/irs-drop/rp-25-32.pdf
"""

# Each key is a tax year, each value is the dollar threshold for that year.
# If someone earns LESS than this amount, they can be a qualifying relative.
IRS_THRESHOLDS = {
    "2022": 4_400,
    "2023": 4_700,
    "2024": 5_050,
    "2025": 5_200,
    "2026": 5_300,
}


def get_qualifying_relative_threshold(tax_year=None):
    """
    Look up the IRS threshold for the given tax year.
    If tax_year is None or unknown, fall back to the most recent year in the list.
    """
    if tax_year and tax_year in IRS_THRESHOLDS:
        return IRS_THRESHOLDS[tax_year]

    return IRS_THRESHOLDS[max(IRS_THRESHOLDS.keys())]
