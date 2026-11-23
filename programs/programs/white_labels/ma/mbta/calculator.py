"""MaMbta."""

from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.ma import MaMassHealth
from programs.programs.cross_white_label.snap.ma import MaSnap
from programs.programs.cross_white_label.tanf.ma import MaTafdc
from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency
from programs.programs.white_labels.ma.eaedc.calculator import MaEaedc


class MaMbta(PolicyEngineMembersCalculator):
    """
    MBTA Reduced Fare Program calculator.

    Only available to residents within the MBTA service district
    (178 cities/towns in eastern Massachusetts including Boston).
    """

    program_code = "ma_mbta"

    eligible_cities = frozenset(
        [
            "Abington",
            "Acton",
            "Amesbury",
            "Andover",
            "Arlington",
            "Ashburnham",
            "Ashby",
            "Ashland",
            "Attleboro",
            "Auburn",
            "Ayer",
            "Bedford",
            "Bellingham",
            "Belmont",
            "Berkley",
            "Beverly",
            "Billerica",
            "Boston",
            "Bourne",
            "Boxborough",
            "Boxford",
            "Braintree",
            "Bridgewater",
            "Brockton",
            "Brookline",
            "Burlington",
            "Cambridge",
            "Canton",
            "Carlisle",
            "Carver",
            "Chelmsford",
            "Chelsea",
            "Cohasset",
            "Concord",
            "Danvers",
            "Dedham",
            "Dover",
            "Dracut",
            "Duxbury",
            "East Bridgewater",
            "Easton",
            "Essex",
            "Everett",
            "Fall River",
            "Fitchburg",
            "Foxborough",
            "Framingham",
            "Franklin",
            "Freetown",
            "Georgetown",
            "Gloucester",
            "Grafton",
            "Groton",
            "Groveland",
            "Halifax",
            "Hamilton",
            "Hanover",
            "Hanson",
            "Harvard",
            "Haverhill",
            "Hingham",
            "Holbrook",
            "Holden",
            "Holliston",
            "Hopkinton",
            "Hull",
            "Ipswich",
            "Kingston",
            "Lakeville",
            "Lancaster",
            "Lawrence",
            "Leicester",
            "Leominster",
            "Lexington",
            "Lincoln",
            "Littleton",
            "Lowell",
            "Lunenburg",
            "Lynn",
            "Lynnfield",
            "Malden",
            "Manchester By The Sea",
            "Mansfield",
            "Marblehead",
            "Marlborough",
            "Marshfield",
            "Maynard",
            "Medfield",
            "Medford",
            "Medway",
            "Melrose",
            "Merrimac",
            "Methuen",
            "Middleborough",
            "Middleton",
            "Millbury",
            "Millis",
            "Milton",
            "Nahant",
            "Natick",
            "Needham",
            "New Bedford",
            "Newbury",
            "Newburyport",
            "Newton",
            "Norfolk",
            "North Andover",
            "North Attleborough",
            "North Reading",
            "Northborough",
            "Northbridge",
            "Norton",
            "Norwell",
            "Norwood",
            "Paxton",
            "Peabody",
            "Pembroke",
            "Plymouth",
            "Plympton",
            "Princeton",
            "Quincy",
            "Randolph",
            "Raynham",
            "Reading",
            "Rehoboth",
            "Revere",
            "Rochester",
            "Rockland",
            "Rockport",
            "Rowley",
            "Salem",
            "Salisbury",
            "Saugus",
            "Scituate",
            "Seekonk",
            "Sharon",
            "Sherborn",
            "Shirley",
            "Shrewsbury",
            "Somerville",
            "Southborough",
            "Sterling",
            "Stoneham",
            "Stoughton",
            "Stow",
            "Sudbury",
            "Sutton",
            "Swampscott",
            "Taunton",
            "Tewksbury",
            "Topsfield",
            "Townsend",
            "Tyngsborough",
            "Upton",
            "Wakefield",
            "Walpole",
            "Waltham",
            "Wareham",
            "Watertown",
            "Wayland",
            "Wellesley",
            "Wenham",
            "West Boylston",
            "West Bridgewater",
            "West Newbury",
            "Westborough",
            "Westford",
            "Westminster",
            "Weston",
            "Westwood",
            "Weymouth",
            "Whitman",
            "Wilmington",
            "Winchester",
            "Winthrop",
            "Woburn",
            "Worcester",
            "Wrentham",
        ]
    )

    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        *MaSnap.pe_inputs,
        *MaTafdc.pe_inputs,
        *MaMassHealth.pe_inputs,
        *MaEaedc.pe_inputs,
    ]
    pe_outputs = [
        dependency.member.MaMbtaProgramsEligible,
        dependency.member.MaMbtaAgeEligible,
        dependency.member.MaSeniorCharlieCardEligible,
        dependency.member.MaTapCharlieCardEligible,
    ]

    amount = 60 * 12

    def member_value(self, member: HouseholdMember):
        if self.screen.county not in self.eligible_cities:
            return 0

        mbta_programs_eligible = self.get_member_dependency_value(dependency.member.MaMbtaProgramsEligible, member.id)
        mbta_age_eligible = self.get_member_dependency_value(dependency.member.MaMbtaAgeEligible, member.id)
        mbta_eligible = mbta_programs_eligible and mbta_age_eligible
        senior_charlie_eligible = self.get_member_dependency_value(
            dependency.member.MaSeniorCharlieCardEligible, member.id
        )
        tap_charlie_eligible = self.get_member_dependency_value(dependency.member.MaTapCharlieCardEligible, member.id)

        if mbta_eligible or tap_charlie_eligible or senior_charlie_eligible:
            return self.amount

        return 0
