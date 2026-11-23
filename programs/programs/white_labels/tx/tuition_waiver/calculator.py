from functools import cached_property

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember


class TxTuitionWaiver(ProgramCalculator):
    """
    Texas State College Tuition and Fee Waiver for foster youth (Tex. Educ. Code §54.366).

    Exempts a student with a qualifying Texas DFPS foster-care history from tuition and
    Chapter 54 fees at Texas public colleges and universities. There is no income test.

    Spec: program-ops `programs/white_labels/tx/tuition_waiver/tx_tuition_waiver_spec.md`.

    The one rule evaluated is §4 `dfps_conservatorship`, per member. A member counts when
    any of these is true:
      - they ticked the "Ever in foster care, even briefly" tile;
      - they're listed as a foster child ("Foster Child / Kinship Care");
      - they're the head of household and another member is listed as their foster parent.
        Relationships are recorded relative to the head, so a "Foster Parent" says nothing
        about anyone else in the household.

    Data gaps (spec §5), all surfaced in the description rather than screened:
      - the care was with Texas DFPS rather than another state, or informal kinship care;
      - which qualifying point applied (in care the day before turning 18, at 14+ while
        adoptable, at graduation, before an adoption or non-parent custody, during dual credit,
        or left custody to a parent at 14+/16+);
      - first enrollment at a Texas public college by the 27th birthday. Age alone can't
        stand in for it, since a student who enrolled in time keeps the waiver at any age, so
        no age limit is applied in either direction;
      - the Selective Service statement.

    Value: the waiver covers whatever the student's college charges, which the screener
    doesn't collect. The calculator returns 1 per eligible member so the program clears the
    frontend's `value > 0` filter; the record's "Varies" estimated_value override is shown
    instead and keeps the program out of totals.
    """

    program_code = "tx_tuition_waiver"

    # Nominal sentinel; the "Varies" override is what the household sees.
    member_amount = 1

    dependencies = ["relationship"]

    def member_eligible(self, e: MemberEligibility) -> None:
        e.condition(self._in_foster_care(e.member))

    def _in_foster_care(self, member: HouseholdMember) -> bool:
        if member.was_in_foster_care is True:
            return True
        if member.relationship == "fosterChild":
            return True
        return member.relationship == "headOfHousehold" and self._household_lists_foster_parent

    @cached_property
    def _household_lists_foster_parent(self) -> bool:
        return any(m.relationship == "fosterParent" for m in self.screen.household_members.all())
