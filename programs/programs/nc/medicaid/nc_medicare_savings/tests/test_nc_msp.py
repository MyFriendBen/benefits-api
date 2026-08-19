from unittest.mock import Mock

from django.test import SimpleTestCase as TestCase

from programs.framework.base import MemberEligibility
from programs.programs.nc.medicaid.nc_medicare_savings.calculator import MedicareSavingsNC

# Approximate 2026 federal FPL values (48 contiguous states, yearly)
FPL = {
    1: 15_960,
    2: 21_540,
    3: 27_120,
    4: 32_700,
    5: 38_280,
    6: 43_860,
    7: 49_440,
    8: 55_020,
}


def make_member(
    pk=1,
    age=65,
    relationship="headOfHousehold",
    has_medicare=True,
    has_ineligible_insurance=False,
    yearly_earned=0,
    yearly_unearned=0,
    yearly_ssi=0,
    yearly_ssdi=0,
    married_to=None,
):
    member = Mock()
    member.pk = pk
    member.age = age
    member.relationship = relationship

    member.has_insurance_types = Mock(side_effect=lambda types, strict=True: "medicare" in types and has_medicare)
    member.insurance = Mock()
    member.insurance.has_insurance_types = Mock(return_value=has_ineligible_insurance)

    member.is_married = Mock(
        return_value={
            "is_married": married_to is not None,
            "married_to": married_to,
        }
    )

    def calc_gross_income(period, income_types, exclude_types=None):
        if exclude_types is None:
            exclude_types = []
        types = list(income_types)
        excludes = list(exclude_types)
        if types == ["earned"]:
            return yearly_earned
        if types == ["unearned"]:
            return yearly_unearned if "sSI" in excludes else yearly_unearned + yearly_ssi
        if types == ["sSI"]:
            return yearly_ssi
        if types == ["sSDisability"]:
            return yearly_ssdi
        return 0

    member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return member


def make_calculator(members, assets=0):
    mock_screen = Mock()
    mock_screen.household_assets = assets
    mock_screen.has_benefit.return_value = False
    mock_screen.household_members.all.return_value = members

    mock_program = Mock()
    mock_program.year.as_dict.return_value = FPL

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return MedicareSavingsNC(mock_screen, mock_program, {}, mock_missing_deps)


def run_member_eligible(calculator, member):
    e = MemberEligibility(member)
    calculator.member_eligible(e)
    return e


class TestScenario1MedicaidIndividual(TestCase):
    """
    Scenario 1: single person, age 68, Medicare, SS Retirement $1,000/month, assets $5,000.
    Income <= 100% FPL but assets > Medicaid limit ($2,000) → PASS via Step 1.
    Expected benefit: $203 * 12 = $2,436/year.
    """

    def setUp(self):
        self.head = make_member(pk=1, age=68, yearly_unearned=12_000)
        self.calculator = make_calculator([self.head], assets=5_000)

    def test_head_is_eligible(self):
        e = run_member_eligible(self.calculator, self.head)
        self.assertTrue(e.eligible)


class TestScenario2MedicaidCouple(TestCase):
    """
    Scenario 2: married couple, both Medicare-eligible, assets $8,000.
    Head: age 67, SS Retirement $900/month. Spouse: age 65, SS Retirement $700/month.
    Combined countable: $19,200 - $240 = $18,960 (below $21,540 two-person FPL).
    Assets $8,000 > Medicaid married limit ($3,000) → PASS via Step 1.
    Both members qualify independently.
    """

    def setUp(self):
        self.head = make_member(pk=1, age=67, yearly_unearned=10_800)
        self.spouse = make_member(pk=2, age=65, relationship="spouse", yearly_unearned=8_400)
        self.head.is_married.return_value = {"is_married": True, "married_to": self.spouse}
        self.spouse.is_married.return_value = {"is_married": True, "married_to": self.head}
        self.calculator = make_calculator([self.head, self.spouse], assets=8_000)

    def test_head_is_eligible(self):
        e = run_member_eligible(self.calculator, self.head)
        self.assertTrue(e.eligible)

    def test_spouse_is_eligible(self):
        e = run_member_eligible(self.calculator, self.spouse)
        self.assertTrue(e.eligible)


class TestScenario3IneligibleSpouseNoDependents(TestCase):
    """
    Scenario 3: head age 66 (Medicare), spouse age 50 (no Medicare), no children, assets $5,000.
    Head: SS Retirement $800/month (unearned). Spouse: wages $3,000/month (earned).
    Deemed: $36,000 earned - $5,976 allowance = $30,024 remainder; $30,024 > $5,976 limit → gate passes, deem $30,024.
    Step 1: A/B countable $9,360 + deemed $30,024 = $39,384 (over $15,960 FPL) → FAIL.
    Step 2: skipped, no dependents under 18 → FAIL.
    Spouse fails member_eligible outright (age 50, no Medicare, no SSDI).
    """

    def setUp(self):
        self.head = make_member(pk=1, age=66, yearly_unearned=9_600)
        self.spouse = make_member(pk=2, age=50, relationship="spouse", has_medicare=False, yearly_earned=36_000)
        self.head.is_married.return_value = {"is_married": True, "married_to": self.spouse}
        self.spouse.is_married.return_value = {"is_married": True, "married_to": self.head}
        self.calculator = make_calculator([self.head, self.spouse], assets=5_000)

    def test_head_is_not_eligible(self):
        e = run_member_eligible(self.calculator, self.head)
        self.assertFalse(e.eligible)

    def test_spouse_is_not_eligible(self):
        e = run_member_eligible(self.calculator, self.spouse)
        self.assertFalse(e.eligible)


class TestScenario4IneligibleSpouseWithTeenChild(TestCase):
    """
    Scenario 4: head age 66 (Medicare), spouse age 55 (no Medicare), child age 14.
    Head: wages $1,500/month. Spouse: wages $1,500/month.
    Deemed: $18,000 earned - $5,976 allowance = $12,024 remainder; $12,024 > $5,976 limit → gate passes, deem $12,024.
    Step 1: A/B countable $8,490 + deemed $12,024 = $20,514 (over $15,960 FPL) → FAIL.
    Step 2: family size 3, combined countable $17,490 (below $36,612 at 135% FPL) → PASS.
    Spouse and child fail member_eligible (no Medicare/SSDI, under 65).
    """

    def setUp(self):
        self.head = make_member(pk=1, age=66, yearly_earned=18_000)
        self.spouse = make_member(pk=2, age=55, relationship="spouse", has_medicare=False, yearly_earned=18_000)
        self.child = make_member(pk=3, age=14, relationship="child", has_medicare=False)
        self.head.is_married.return_value = {"is_married": True, "married_to": self.spouse}
        self.spouse.is_married.return_value = {"is_married": True, "married_to": self.head}
        self.child.is_married.return_value = {"is_married": False, "married_to": None}
        self.calculator = make_calculator([self.head, self.spouse, self.child], assets=5_000)

    def test_head_is_eligible(self):
        e = run_member_eligible(self.calculator, self.head)
        self.assertTrue(e.eligible)

    def test_spouse_is_not_eligible(self):
        e = run_member_eligible(self.calculator, self.spouse)
        self.assertFalse(e.eligible)

    def test_child_is_not_eligible(self):
        e = run_member_eligible(self.calculator, self.child)
        self.assertFalse(e.eligible)


class TestScenario5IneligibleSpouseSSRIWithDepChild(TestCase):
    """
    Scenario 5: head age 66 (Medicare, SS Retirement $1,500/mo unearned),
    spouse age 55 (no insurance, wages $1,500/mo), child age 15.
    Deemed: $18,000 earned - $5,976 allowance = $12,024 remainder; $12,024 > $5,976 limit → gate passes, deem $12,024.
    Step 1: A/B countable $17,760 + deemed $12,024 = $29,784 (over $15,960 FPL) → FAIL.
    Step 2: family size 3, combined countable $26,370 (below $36,612 at 135% FPL) → PASS.
    Key difference from Scenario 4: head has unearned income, not wages.
    """

    def setUp(self):
        self.head = make_member(pk=1, age=66, yearly_unearned=18_000)
        self.spouse = make_member(pk=2, age=55, relationship="spouse", has_medicare=False, yearly_earned=18_000)
        self.child = make_member(pk=3, age=15, relationship="child", has_medicare=False)
        self.head.is_married.return_value = {"is_married": True, "married_to": self.spouse}
        self.spouse.is_married.return_value = {"is_married": True, "married_to": self.head}
        self.child.is_married.return_value = {"is_married": False, "married_to": None}
        self.calculator = make_calculator([self.head, self.spouse, self.child], assets=5_000)

    def test_head_is_eligible(self):
        e = run_member_eligible(self.calculator, self.head)
        self.assertTrue(e.eligible)

    def test_spouse_is_not_eligible(self):
        e = run_member_eligible(self.calculator, self.spouse)
        self.assertFalse(e.eligible)

    def test_child_is_not_eligible_scenario5(self):
        e = run_member_eligible(self.calculator, self.child)
        self.assertFalse(e.eligible)


class TestScenario6SSISpouseWithDepChild(TestCase):
    """
    Scenario 6: head age 66 (Medicare, wages $2,800/month),
    spouse age 55 (Medicaid insurance, SSI $93/month), child age 14.
    Classification: medicaid_individual (spouse on SSI → no deeming).
    Step 1: A/B countable $16,290/year (over $15,960 FPL for 1) → FAIL.
    Step 2: family size 3, countable well below 135% FPL → PASS.
    Spouse fails member_eligible (Medicaid = ineligible insurance).
    Child fails member_eligible (age 14, no Medicare/SSDI).
    """

    def setUp(self):
        self.head = make_member(pk=1, age=66, yearly_earned=33_600)
        self.spouse = make_member(
            pk=2, age=55, relationship="spouse", has_medicare=False, has_ineligible_insurance=True, yearly_ssi=1_116
        )
        self.child = make_member(pk=3, age=14, relationship="child", has_medicare=False)
        self.head.is_married.return_value = {"is_married": True, "married_to": self.spouse}
        self.spouse.is_married.return_value = {"is_married": True, "married_to": self.head}
        self.child.is_married.return_value = {"is_married": False, "married_to": None}
        self.calculator = make_calculator([self.head, self.spouse, self.child], assets=5_000)

    def test_head_is_eligible(self):
        e = run_member_eligible(self.calculator, self.head)
        self.assertTrue(e.eligible)

    def test_spouse_is_not_eligible(self):
        e = run_member_eligible(self.calculator, self.spouse)
        self.assertFalse(e.eligible)

    def test_child_is_not_eligible(self):
        e = run_member_eligible(self.calculator, self.child)
        self.assertFalse(e.eligible)

    def test_ssi_disqualifies_an_otherwise_eligible_member(self):
        member = make_member(pk=4, age=66, yearly_ssi=1_116)
        calculator = make_calculator([member])
        e = run_member_eligible(calculator, member)
        self.assertFalse(e.eligible)
