import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember, IncomeStream


class WaNslp(ProgramCalculator):
    """
    Washington National School Lunch Program (NSLP) — screening calculator.

    Estimates free or reduced-price school lunch eligibility using OSPI 2025–26
    income guidelines (not raw FPL math), frequency-matched income comparison
    when a single pay frequency applies, and screenable categorical pathways
    (SNAP/Basic Food, TANF, Head Start flags, foster-child proxy).

    Value: $828/year per likely eligible student ($4.60 × 180 days, SY 2025–26).

    Data gaps (see spec.md): school participation, exact K-12 enrollment vs. age
    proxy 5–18, FDPIR, migrant/runaway, CEP/Provision 2/3, Medicaid direct
    certification. Medicaid alone must not create categorical eligibility.
    """

    # Likely school-meal student proxy (spec): not using `student` (postsecondary).
    SCHOOL_MEAL_RELATIONSHIPS = frozenset({"child", "fosterChild", "grandChild"})
    MIN_SCHOOL_MEAL_AGE = 5
    MAX_SCHOOL_MEAL_AGE = 18

    ANNUAL_VALUE_PER_CHILD = 828

    # OSPI / USDA Child Nutrition income guidelines, Jul 2025 – Jun 2026 (reduced-price cap).
    _RED_ANN = {
        1: 28_953,
        2: 39_128,
        3: 49_303,
        4: 59_478,
        5: 69_653,
        6: 79_828,
        7: 90_003,
        8: 100_178,
    }
    _RED_ANN_STEP = 10_175
    _RED_MO = {
        1: 2_413,
        2: 3_261,
        3: 4_109,
        4: 4_957,
        5: 5_805,
        6: 6_653,
        7: 7_501,
        8: 8_349,
    }
    _RED_MO_STEP = 848

    dependencies = (
        "household_size",
        "income_amount",
        "income_frequency",
        "relationship",
        "age",
    )

    def _household_size_for_limits(self) -> int:
        n = self.screen.household_size or 0
        return max(n, 1)

    def _reduced_annual_limit(self) -> int:
        n = self._household_size_for_limits()
        if n <= 8:
            return self._RED_ANN[n]
        return self._RED_ANN[8] + (n - 8) * self._RED_ANN_STEP

    def _reduced_monthly_limit(self) -> int:
        n = self._household_size_for_limits()
        if n <= 8:
            return self._RED_MO[n]
        return self._RED_MO[8] + (n - 8) * self._RED_MO_STEP

    def _member_age(self, member: HouseholdMember) -> int | None:
        if member.birth_year_month is not None:
            return member.calc_age()
        return member.age

    def _is_school_meal_proxy_student(self, member: HouseholdMember) -> bool:
        if member.relationship not in self.SCHOOL_MEAL_RELATIONSHIPS:
            return False
        age = self._member_age(member)
        if age is None:
            return False
        return self.MIN_SCHOOL_MEAL_AGE <= age <= self.MAX_SCHOOL_MEAL_AGE

    def _positive_income_streams(self) -> list[IncomeStream]:
        streams: list[IncomeStream] = []
        for m in self.screen.household_members.all():
            for inc in m.income_streams.all():
                if inc.amount is not None and float(inc.amount) > 0 and inc.frequency:
                    streams.append(inc)
        return streams

    def _income_at_or_below_reduced_cap(self) -> bool:
        streams = self._positive_income_streams()
        if not streams:
            return True

        freqs = {s.frequency for s in streams}
        hh = self._household_size_for_limits()
        red_ann = self._reduced_annual_limit()
        red_mo = self._reduced_monthly_limit()

        if len(freqs) > 1:
            gross = int(self.screen.calc_gross_income("yearly", ["all"]))
            return gross <= red_ann

        f = next(iter(freqs))
        if f == "monthly":
            total = sum(float(s.amount) for s in streams)
            return int(total) <= red_mo
        if f == "yearly":
            total = sum(float(s.amount) for s in streams)
            return int(total) <= red_ann
        if f == "weekly":
            total = sum(float(s.amount) for s in streams)
            return int(total * 52) <= red_ann
        if f == "biweekly":
            total = sum(float(s.amount) for s in streams)
            return int(total * 26) <= red_ann
        if f == "semimonthly":
            total = sum(float(s.amount) for s in streams)
            return int(total * 24) <= red_ann
        # Hourly (and any other): use annualized gross from screener conversion rules.
        gross = int(self.screen.calc_gross_income("yearly", ["all"]))
        return gross <= red_ann

    def _household_categorical(self) -> bool:
        if self.screen.has_snap or self.screen.has_tanf:
            return True
        if self.screen.has_head_start or self.screen.has_early_head_start:
            return True
        return False

    def _foster_school_age_categorical(self) -> bool:
        for m in self.screen.household_members.all():
            if m.relationship == "fosterChild" and self._is_school_meal_proxy_student(m):
                return True
        return False

    def member_eligible(self, e: MemberEligibility):
        e.condition(self._is_school_meal_proxy_student(e.member))

    def household_eligible(self, e: Eligibility):
        e.condition(
            not self.screen.has_benefit("nslp"),
            messages.must_not_have_benefit("NSLP"),
        )

        gross_for_message = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit_message = self._reduced_annual_limit()

        categorical = self._household_categorical() or self._foster_school_age_categorical()
        income_ok = self._income_at_or_below_reduced_cap()

        e.condition(
            categorical or income_ok,
            messages.income(gross_for_message, income_limit_message),
        )

    def member_value(self, member: HouseholdMember) -> int:
        if self._is_school_meal_proxy_student(member):
            return self.ANNUAL_VALUE_PER_CHILD
        return 0
