"""
CCAP Rate and Copayment Data

This file contains rate tables and copayment data for Illinois Child Care Assistance Program (CCAP).

Last Updated: 2025
"""

# ==============================================================================
# STATE REIMBURSEMENT RATES
# ==============================================================================
# Maximum monthly rates the state pays to child care providers
# Source: IDHS CCAP Rate Tables
#
# Format: (county_group, (min_age_months, max_age_months), monthly_rate)
# County Groups:
#   - GROUP_1A: Cook, DeKalb, DuPage, Kane, Kendall, Lake, McHenry
#   - GROUP_1B: Boone, Champaign, Kankakee, Madison, McLean, Monroe, Ogle,
#               Peoria, Rock Island, Sangamon, St. Clair, Tazewell, Whiteside, Will, Winnebago, Woodford
#   - GROUP_2: All other Illinois counties

SUBSIDY_RATE_TABLE = [
    ("GROUP_1A", (0, 23), 1474),  # Infants (0-23 months)
    ("GROUP_1A", (24, 35), 1188),  # Twos (24-35 months)
    ("GROUP_1A", (36, 71), 1012),  # Preschool (36-71 months / 3-5 years)
    ("GROUP_1A", (72, 156), 506),  # School age (6-13 years)
    ("GROUP_1A", (157, 228), 506),  # Disabled youth (13-19 years) - uses school-age rate
    ("GROUP_1B", (0, 23), 1408),  # Infants
    ("GROUP_1B", (24, 35), 1122),  # Twos
    ("GROUP_1B", (36, 71), 946),  # Preschool
    ("GROUP_1B", (72, 156), 484),  # School age
    ("GROUP_1B", (157, 228), 484),  # Disabled youth (13-19 years) - uses school-age rate
    ("GROUP_2", (0, 23), 1254),  # Infants
    ("GROUP_2", (24, 35), 1012),  # Twos
    ("GROUP_2", (36, 71), 880),  # Preschool
    ("GROUP_2", (72, 156), 440),  # School age
    ("GROUP_2", (157, 228), 440),  # Disabled youth (13-19 years) - uses school-age rate
]

# ==============================================================================
# FAMILY COPAYMENT TABLE
# ==============================================================================
# Monthly copayment amounts families must pay based on income and family size
# Source: CCAP Income and Copay Chart Effective 7.1.25
# URL: https://www.dhs.state.il.us/OneNetLibrary/27897/documents/Forms/443455B%20CCAP%20Income%20and%20Copay%20Chart%20Eff%207.1.25.pdf
#
# This calculator uses standard copayment rates for first-time applications.
#
# Note: Illinois offers reduced copayments (50% off) for families with ALL children:
#   - School-age (5+ years and enrolled in school)
#   - Approved for part-time care (less than 5 hours/day)
#   - During the school year (September-May)
# This reduced rate is NOT implemented in this calculator as we cannot detect these
# conditions from screen data. See warning message for details.
#
# Special Copayment Cases:
#   Handled in calculator:
#     - Income at/below 100% FPL: $1/month copayment
#
#   NOT handled in calculator (mentioned in warning message):
#     - Families receiving TANF: $0/month (exempt)
#     - Protective services (homeless, military deployment, etc.): $0/month (exempt)
#     - Parent/guardian working in child care: $1/month
#
# Format: {family_size: [((min_monthly_income, max_monthly_income), monthly_copayment), ...]}

# Copayment table for first-time applications
# Note: For redetermination copayments, see https://www.dhs.state.il.us/page.aspx?item=54862

COPAYMENT_TABLE_A = {
    2: [
        ((0, 1763), 1),
        ((1764, 2055), 37),
        ((2056, 2348), 73),
        ((2349, 2641), 109),
        ((2642, 2934), 145),
        ((2935, 3227), 181),
        ((3228, 3520), 217),
        ((3521, 3813), 253),
        ((3814, 3966), 272),
    ],
    3: [
        ((0, 1984), 1),
        ((1985, 2312), 42),
        ((2313, 2641), 83),
        ((2642, 2970), 124),
        ((2971, 3299), 165),
        ((3300, 3628), 206),
        ((3629, 3957), 247),
        ((3958, 4286), 288),
        ((4287, 4615), 329),
        ((4616, 4944), 370),
        ((4945, 5000), 388),
    ],
    4: [
        ((0, 2384), 1),
        ((2385, 2779), 48),
        ((2780, 3174), 95),
        ((3175, 3570), 142),
        ((3571, 3966), 189),
        ((3967, 4362), 236),
        ((4363, 4758), 283),
        ((4759, 5154), 330),
        ((5155, 5550), 377),
        ((5551, 5946), 424),
        ((5947, 6034), 442),
    ],
    5: [
        ((0, 2784), 1),
        ((2785, 3246), 53),
        ((3247, 3708), 106),
        ((3709, 4170), 159),
        ((4171, 4632), 212),
        ((4633, 5094), 265),
        ((5095, 5556), 318),
        ((5557, 6018), 371),
        ((6019, 6480), 424),
        ((6481, 6942), 477),
        ((6943, 7068), 495),
    ],
    6: [
        ((0, 3184), 1),
        ((3185, 3713), 59),
        ((3714, 4242), 117),
        ((4243, 4771), 176),
        ((4772, 5300), 234),
        ((5301, 5829), 293),
        ((5830, 6358), 351),
        ((6359, 6887), 410),
        ((6888, 7416), 468),
        ((7417, 7945), 527),
        ((7946, 8474), 585),
        ((8475, 8629), 623),
    ],
    7: [
        ((0, 3584), 1),
        ((3585, 4180), 65),
        ((4181, 4776), 129),
        ((4777, 5372), 194),
        ((5373, 5968), 258),
        ((5969, 6564), 323),
        ((6565, 7160), 387),
        ((7161, 7756), 452),
        ((7757, 8352), 516),
        ((8353, 8948), 581),
        ((8949, 9544), 645),
        ((9545, 9663), 656),
    ],
    8: [
        ((0, 3984), 1),
        ((3985, 4647), 70),
        ((4648, 5310), 140),
        ((5311, 5973), 210),
        ((5974, 6636), 280),
        ((6637, 7299), 350),
        ((7300, 7962), 420),
        ((7963, 8625), 490),
        ((8626, 9288), 560),
        ((9289, 9951), 630),
        ((9952, 10614), 700),
        ((10615, 10697), 720),
    ],
    9: [
        ((0, 4384), 1),
        ((4385, 5114), 76),
        ((5115, 5844), 152),
        ((5845, 6574), 228),
        ((6575, 7304), 304),
        ((7305, 8034), 380),
        ((8035, 8764), 456),
        ((8765, 9494), 532),
        ((9495, 10224), 608),
        ((10225, 10954), 684),
        ((10955, 11684), 760),
        ((11685, 11731), 771),
    ],
    10: [
        ((0, 5429), 1),
        ((5430, 6331), 94),
        ((6332, 7233), 188),
        ((7234, 8135), 282),
        ((8136, 9037), 376),
        ((9038, 9939), 470),
        ((9940, 10841), 564),
        ((10842, 11743), 658),
        ((11744, 12645), 752),
        ((12646, 13547), 836),
    ],
}
