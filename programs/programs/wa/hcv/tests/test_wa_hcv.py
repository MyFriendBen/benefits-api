from django.test import TestCase
from unittest.mock import Mock, patch, PropertyMock

from programs.programs.wa import wa_calculators
from programs.programs.wa.hcv.calculator import WaHcv
from programs.programs.calc import ProgramCalculator, Eligibility


def make_member(
    age=40,
    relationship="headOfHousehold",
    pregnant=False,
    student=False,
    disabled=False,
    visually_impaired=False,
    long_term_disability=False,
    income=0,
    insurance_types=None,
):
    member = Mock()
    member.age = age
    member.relationship = relationship
    member.pregnant = pregnant
    member.student = student
    member.disabled = disabled
    member.visually_impaired = visually_impaired
    member.long_term_disability = long_term_disability
    member.has_disability = Mock(return_value=(disabled or visually_impaired or long_term_disability))
    member.calc_gross_income = Mock(return_value=income)
    member.has_benefit = Mock(return_value=False)

    insurance = Mock()
    insurance.has_insurance_types = Mock(return_value=bool(insurance_types))
    member.insurance = insurance

    return member


def make_calculator(
    members=None,
    household_size=None,
    county="King County",
    zipcode="98108",
    household_assets=0,
    has_section_8=False,
    gross_income=21600,
    il_ami_value=50000,
    fmr_value=2000,
):
    if members is None:
        members = [make_member()]

    if household_size is None:
        household_size = len(members)

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.county = county
    mock_screen.zipcode = zipcode
    mock_screen.household_assets = household_assets
    mock_screen.household_members.all = Mock(return_value=members)
    mock_screen.calc_gross_income = Mock(return_value=gross_income)
    mock_screen.has_benefit = Mock(side_effect=lambda name: has_section_8 if name == "section_8" else False)
    mock_screen.get_head = Mock(return_value=members[0] if members else None)

    mock_program = Mock()
    mock_program.year.period = "2026"

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    calc = WaHcv(mock_screen, mock_program, {}, mock_missing_deps)
    calc._il_ami_value = il_ami_value
    calc._fmr_value = fmr_value
    return calc


def patch_hud_client(il_ami_value=50000, fmr_value=2000, il_error=False, fmr_error=False):
    """Return a context manager that patches both HUD client methods."""
    from integrations.clients.hud_income_limits import HudIncomeClientError

    def il_side_effect(*args, **kwargs):
        if il_error:
            raise HudIncomeClientError("test error")
        return il_ami_value

    def fmr_side_effect(*args, **kwargs):
        if fmr_error:
            raise HudIncomeClientError("test error")
        return fmr_value

    return patch.multiple(
        "programs.programs.wa.hcv.calculator.hud_client",
        get_screen_il_ami=Mock(side_effect=il_side_effect),
        get_screen_fmr=Mock(side_effect=fmr_side_effect),
    )


class TestWaHcvClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(WaHcv, ProgramCalculator))

    def test_is_registered_in_wa_calculators(self):
        self.assertIn("wa_hcv", wa_calculators)
        self.assertEqual(wa_calculators["wa_hcv"], WaHcv)

    def test_asset_limit_is_100k(self):
        self.assertEqual(WaHcv.asset_limit, 100_000)

    def test_dependent_deduction_is_480(self):
        self.assertEqual(WaHcv.dependent_deduction_annual, 480)

    def test_elderly_disabled_deduction_is_525(self):
        self.assertEqual(WaHcv.elderly_disabled_deduction_annual, 525)

    def test_min_rent_is_50(self):
        self.assertEqual(WaHcv.min_rent_monthly, 50)

    def test_dependencies_include_required_fields(self):
        for field in ("income_amount", "income_frequency", "household_size", "county", "household_assets", "age"):
            self.assertIn(field, WaHcv.dependencies)


class TestWaHcvEligibility(TestCase):
    def test_income_below_vli_is_eligible(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], gross_income=21600)
        with patch_hud_client(il_ami_value=50000):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_income_above_vli_is_ineligible(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], gross_income=55000)
        with patch_hud_client(il_ami_value=50000):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)

    def test_income_at_vli_is_eligible(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], gross_income=50000)
        with patch_hud_client(il_ami_value=50000):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_has_section_8_is_ineligible(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], has_section_8=True, gross_income=21600)
        with patch_hud_client(il_ami_value=50000):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)

    def test_assets_above_100k_is_ineligible(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], household_assets=150000, gross_income=21600)
        with patch_hud_client(il_ami_value=50000):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)

    def test_assets_at_100k_is_eligible(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], household_assets=100000, gross_income=21600)
        with patch_hud_client(il_ami_value=50000):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_none_assets_treated_as_zero(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], household_assets=None, gross_income=21600)
        with patch_hud_client(il_ami_value=50000):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)

    def test_hud_api_error_makes_ineligible(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], gross_income=21600)
        with patch_hud_client(il_error=True):
            e = Eligibility()
            calc.household_eligible(e)
            self.assertFalse(e.eligible)


class TestWaHcvPregnancyRule(TestCase):
    def test_pregnant_single_uses_2_person_income_limit(self):
        head = make_member(age=31, pregnant=True)
        calc = make_calculator(members=[head], household_size=1, gross_income=28800)

        with patch_hud_client(il_ami_value=35000) as mocks:
            e = Eligibility()
            calc.household_eligible(e)
            self.assertTrue(e.eligible)
            self.assertEqual(calc.screen.household_size, 1)

    def test_non_pregnant_single_uses_1_person_limit(self):
        head = make_member(age=31, pregnant=False)
        calc = make_calculator(members=[head], household_size=1)
        self.assertEqual(calc._effective_household_size(), 1)

    def test_pregnant_in_multi_person_household_no_adjustment(self):
        head = make_member(age=31, pregnant=True)
        child = make_member(age=5, relationship="child")
        calc = make_calculator(members=[head, child], household_size=2)
        self.assertEqual(calc._effective_household_size(), 2)


class TestWaHcvHelpers(TestCase):
    def test_bedroom_map_1_person(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], household_size=1)
        self.assertEqual(calc._estimate_bedrooms(), 1)

    def test_bedroom_map_3_persons(self):
        members = [make_member(), make_member(relationship="spouse"), make_member(age=5, relationship="child")]
        calc = make_calculator(members=members, household_size=3)
        self.assertEqual(calc._estimate_bedrooms(), 2)

    def test_bedroom_map_5_persons(self):
        members = [make_member()] * 5
        calc = make_calculator(members=members, household_size=5)
        self.assertEqual(calc._estimate_bedrooms(), 3)

    def test_bedroom_map_8_persons(self):
        members = [make_member()] * 8
        calc = make_calculator(members=members, household_size=8)
        self.assertEqual(calc._estimate_bedrooms(), 4)

    def test_count_dependents_children_under_18(self):
        head = make_member(age=35)
        child1 = make_member(age=9, relationship="child")
        child2 = make_member(age=5, relationship="child")
        calc = make_calculator(members=[head, child1, child2])
        self.assertEqual(calc._count_dependents(), 2)

    def test_count_dependents_excludes_head_and_spouse(self):
        head = make_member(age=35)
        spouse = make_member(age=33, relationship="spouse")
        calc = make_calculator(members=[head, spouse])
        self.assertEqual(calc._count_dependents(), 0)

    def test_count_dependents_includes_disabled_non_head(self):
        head = make_member(age=35)
        disabled_parent = make_member(age=60, relationship="parent", disabled=True)
        calc = make_calculator(members=[head, disabled_parent])
        self.assertEqual(calc._count_dependents(), 1)

    def test_count_dependents_includes_student(self):
        head = make_member(age=35)
        student_child = make_member(age=19, relationship="child", student=True)
        calc = make_calculator(members=[head, student_child])
        self.assertEqual(calc._count_dependents(), 1)

    def test_elderly_family_head_62_plus(self):
        head = make_member(age=68)
        calc = make_calculator(members=[head])
        self.assertTrue(calc._is_elderly_or_disabled_family())

    def test_elderly_family_spouse_62_plus(self):
        head = make_member(age=50)
        spouse = make_member(age=63, relationship="spouse")
        calc = make_calculator(members=[head, spouse])
        self.assertTrue(calc._is_elderly_or_disabled_family())

    def test_disabled_head_family(self):
        head = make_member(age=40, disabled=True)
        calc = make_calculator(members=[head])
        self.assertTrue(calc._is_elderly_or_disabled_family())

    def test_not_elderly_not_disabled_family(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head])
        self.assertFalse(calc._is_elderly_or_disabled_family())

    def test_disabled_child_does_not_make_elderly_family(self):
        head = make_member(age=35)
        child = make_member(age=10, relationship="child", disabled=True)
        calc = make_calculator(members=[head, child])
        self.assertFalse(calc._is_elderly_or_disabled_family())


class TestWaHcvBenefitValue(TestCase):
    def test_basic_hap_calculation(self):
        """Single adult, $1,800/mo income, no dependents, FMR $1,605."""
        head = make_member(age=35)
        calc = make_calculator(members=[head], household_size=1, gross_income=21600)
        # monthly_gross = 1800, monthly_adjusted = 1800
        # TTP = max(0.30 * 1800, 0.10 * 1800, 50) = max(540, 180, 50) = 540
        # HAP = 1605 - 540 = 1065
        # Annual = 1065 * 12 = 12780
        with patch_hud_client(fmr_value=1605):
            value = calc.household_value()
            self.assertEqual(value, 12780)

    def test_hap_with_dependents(self):
        """Single mother + 2 children, $1,800/mo, 2 dependents."""
        head = make_member(age=35)
        child1 = make_member(age=9, relationship="child")
        child2 = make_member(age=5, relationship="child")
        calc = make_calculator(members=[head, child1, child2], household_size=3, gross_income=21600)
        # dependent deduction = 2 * 480 = 960/yr, 80/mo
        # monthly_adjusted = 1800 - 80 = 1720
        # TTP = max(0.30 * 1720, 0.10 * 1800, 50) = max(516, 180, 50) = 516
        # HAP = 2502 - 516 = 1986
        # Annual = 1986 * 12 = 23832
        with patch_hud_client(fmr_value=2502):
            value = calc.household_value()
            self.assertEqual(value, 23832)

    def test_hap_with_elderly_deduction(self):
        """Elderly single adult with SS retirement income."""
        head = make_member(age=75)
        calc = make_calculator(members=[head], household_size=1, gross_income=14400)
        # elderly deduction = 525/yr, 43.75/mo
        # monthly_gross = 1200, monthly_adjusted = 1200 - 43.75 = 1156.25
        # TTP = max(0.30 * 1156.25, 0.10 * 1200, 50) = max(346.875, 120, 50) = 346.875
        # HAP = 1400 - 346.875 = 1053.125
        # Annual = int(1053.125 * 12) = 12637
        with patch_hud_client(fmr_value=1400):
            value = calc.household_value()
            self.assertEqual(value, 12637)

    def test_hap_zero_when_ttp_exceeds_fmr(self):
        """High income relative to FMR yields zero benefit."""
        head = make_member(age=35)
        calc = make_calculator(members=[head], household_size=1, gross_income=60000)
        # monthly_gross = 5000, TTP = max(1500, 500, 50) = 1500
        # HAP = max(0, 800 - 1500) = 0
        with patch_hud_client(fmr_value=800):
            value = calc.household_value()
            self.assertEqual(value, 0)

    def test_fmr_api_error_returns_zero(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], household_size=1, gross_income=21600)
        with patch_hud_client(fmr_error=True):
            value = calc.household_value()
            self.assertEqual(value, 0)


class TestWaHcvCalc(TestCase):
    def test_calc_eligible_returns_positive_value(self):
        head = make_member(age=35)
        child1 = make_member(age=9, relationship="child")
        child2 = make_member(age=5, relationship="child")
        calc = make_calculator(members=[head, child1, child2], household_size=3, gross_income=21600)
        with patch_hud_client(il_ami_value=50000, fmr_value=2502):
            e = calc.calc()
            self.assertTrue(e.eligible)
            self.assertEqual(e.value, 23832)

    def test_calc_ineligible_returns_zero_value(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], has_section_8=True, gross_income=21600)
        with patch_hud_client(il_ami_value=50000, fmr_value=2000):
            e = calc.calc()
            self.assertFalse(e.eligible)

    def test_calc_pregnant_single_eligible(self):
        head = make_member(age=31, pregnant=True)
        calc = make_calculator(members=[head], household_size=1, gross_income=28800)
        # Pregnant single → 2-person VLI for income, 1BR for FMR
        # monthly_gross = 2400, monthly_adjusted = 2400 (no dependents, no elderly)
        # TTP = max(0.30 * 2400, 0.10 * 2400, 50) = max(720, 240, 50) = 720
        # HAP = 1605 - 720 = 885
        # Annual = 885 * 12 = 10620
        with patch_hud_client(il_ami_value=35000, fmr_value=1605):
            e = calc.calc()
            self.assertTrue(e.eligible)
            self.assertEqual(e.value, 10620)

    def test_calc_null_year_does_not_crash(self):
        """Program.year = None must not raise AttributeError (crashes all WA programs)."""
        head = make_member(age=35)
        calc = make_calculator(members=[head], gross_income=21600)
        calc.program.year = None
        with patch_hud_client(il_ami_value=50000, fmr_value=2000):
            e = calc.calc()
            self.assertFalse(e.eligible)

    def test_household_value_null_year_returns_zero(self):
        head = make_member(age=35)
        calc = make_calculator(members=[head], gross_income=21600)
        calc.program.year = None
        with patch_hud_client(fmr_value=2000):
            self.assertEqual(calc.household_value(), 0)
