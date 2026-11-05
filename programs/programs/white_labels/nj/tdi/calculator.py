from programs.framework.base import MemberEligibility
from programs.programs.white_labels.nj.paid_leave import NjPaidLeave
from screener.models import HouseholdMember


class NjTdi(NjPaidLeave):
    """
    New Jersey Temporary Disability Insurance (TDI): partial pay for a worker who can't work
    because of their own illness, injury or pregnancy. Someone already on unemployment who
    becomes unable to work gets the same benefit as Disability During Unemployment (DDU).

    A member qualifies on either route (`NjPaidLeave`) when they report a disability or a
    pregnancy, have no workers' compensation income and no SSDI income. The value is the
    weekly rate times the 2024 mean of 70 days paid per completed claim. DDU's weekly rate is
    reported unemployment over 52, uncapped, since the spec has no DDU maximum.

    Spec: program-ops `programs/white_labels/nj/tdi/nj_tdi_spec.md`. Data gaps (spec §5): the
    employer's coverage, when work stopped or the disability began, base-year wage history,
    medical certification, whether workers' compensation covers this disability, the waiting
    week, other disability or unemployment benefits, and SSDI timing.
    """

    program_code = "nj_tdi"

    avg_days_paid = 70

    # Not `pregnant`: it is null when the screener didn't ask, which reads as not pregnant
    # (`is True`) rather than dropping the program for everyone else.
    dependencies = [
        "disabled",
        "income_type",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility) -> None:
        super().member_eligible(e)
        member = e.member

        e.condition(member.disabled is True or member.pregnant is True)
        e.condition(self._income(member, "workersComp") <= 0)

    def member_value(self, member: HouseholdMember) -> int:
        return self.lump_sum(self.weekly_rate(member), self.avg_days_paid)
