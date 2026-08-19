from ..base import UrgentNeedFunction


class SnapEmployment(UrgentNeedFunction):
    dependencies = ["county"]
    county = "Denver County"

    def eligible(self):
        """
        Return True if the household is SNAP eligible and lives in Denver
        """
        county_eligible = self.screen.county == self.county

        snap_eligible = self.screen.has_benefit("co_snap")
        for program in self.data:
            if program["name_abbreviated"] != "co_snap":
                continue

            if program["eligible"]:
                snap_eligible = True
                break

        return county_eligible and snap_eligible
