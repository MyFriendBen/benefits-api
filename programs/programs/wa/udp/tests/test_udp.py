from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.udp.calculator import WaUdp
from programs.programs.calc import ProgramCalculator, Eligibility


def make_member(age, yearly_income: int=0, ssi_income: int=0):
    """Create a mock household member."""
    member = Mock()
    member.age = age
    member.calc_age = Mock(return_value=age)

    def gross_income(freq, types):
        if "sSI" in types:
            return ssi_income * 12 if freq == "yearly" else ssi_income
        return yearly_income if freq == "yearly" else yearly_income / 12

    member.calc_gross_income = Mock(side_effect=gross_income)
    return member


def make_calculator(
    zipcode: str="98103",
    county: str="King County",
    household_size: int=1,
    members=None,
    has_snap: bool=False,
):
    """Create a WaUdp calculator with a mocked screen."""
    mock_program = Mock()
    mock_screen = Mock()
    mock_screen.zipcode = zipcode
    mock_screen.county = county
    mock_screen.household_size = household_size
    mock_screen.has_benefit = Mock(side_effect=lambda b: has_snap if b == "wa_snap" else False)
    mock_screen.household_members.all = Mock(
        return_value=members if members is not None else [make_member(age=35, yearly_income=24_000)]
    )
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False
    return WaUdp(mock_screen, mock_program, {}, mock_missing_deps)


def run_household_eligible(calc):
    e = Eligibility()
    calc.household_eligible(e)
    return e.eligible


class TestWaUdpClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self) -> None:
        self.assertTrue(issubclass(WaUdp, ProgramCalculator))

    def test_is_registered_in_wa_calculators(self) -> None:
        self.assertIn("wa_udp", wa_calculators)
        self.assertEqual(wa_calculators["wa_udp"], WaUdp)

    def test_amount_is_732(self) -> None:
        self.assertEqual(WaUdp.amount, 732)

    def test_smi_table_hh1(self) -> None:
        self.assertEqual(WaUdp.SMI_70_ANNUAL[1], 51_228)

    def test_smi_table_hh4(self) -> None:
        self.assertEqual(WaUdp.SMI_70_ANNUAL[4], 98_508)

    def test_smi_table_hh10(self) -> None:
        self.assertEqual(WaUdp.SMI_70_ANNUAL[10], 141_852)

    def test_smi_per_extra_annual(self) -> None:
        self.assertEqual(WaUdp.SMI_70_PER_EXTRA_ANNUAL, 2_964)


class TestWaUdpSmiLimit(TestCase):
    def test_known_size(self) -> None:
        calc = make_calculator(household_size=3)
        self.assertEqual(calc._smi_limit(), 82_740)

    def test_extension_above_10(self) -> None:
        calc = make_calculator(household_size=11)
        self.assertEqual(calc._smi_limit(), 141_852 + 2_964)

    def test_extension_above_10_large(self) -> None:
        calc = make_calculator(household_size=13)
        self.assertEqual(calc._smi_limit(), 141_852 + 3 * 2_964)


class TestWaUdpLocationCriterion(TestCase):
    def test_seattle_zip_and_king_county_is_eligible(self) -> None:
        calc = make_calculator(zipcode="98103", county="King County")
        self.assertTrue(run_household_eligible(calc))

    def test_non_seattle_zip_is_ineligible(self) -> None:
        calc = make_calculator(zipcode="98003", county="King County")
        self.assertFalse(run_household_eligible(calc))

    def test_seattle_zip_wrong_county_is_ineligible(self) -> None:
        calc = make_calculator(zipcode="98103", county="Snohomish County")
        self.assertFalse(run_household_eligible(calc))

    def test_all_52_seattle_zips_accepted(self) -> None:
        expected = {
            "98101",
            "98102",
            "98103",
            "98104",
            "98105",
            "98106",
            "98107",
            "98108",
            "98109",
            "98111",
            "98112",
            "98113",
            "98114",
            "98115",
            "98116",
            "98117",
            "98118",
            "98119",
            "98121",
            "98122",
            "98124",
            "98125",
            "98126",
            "98127",
            "98129",
            "98131",
            "98133",
            "98134",
            "98136",
            "98138",
            "98139",
            "98141",
            "98144",
            "98145",
            "98146",
            "98154",
            "98160",
            "98161",
            "98164",
            "98165",
            "98170",
            "98174",
            "98175",
            "98177",
            "98178",
            "98181",
            "98185",
            "98190",
            "98191",
            "98194",
            "98195",
            "98199",
        }
        self.assertEqual(WaUdp.SEATTLE_ZIP_CODES, frozenset(expected))


class TestWaUdpIncomePathway(TestCase):
    def test_income_below_limit_is_eligible(self) -> None:
        members = [make_member(age=35, yearly_income=24_000)]
        calc = make_calculator(household_size=1, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_income_exactly_at_limit_is_eligible(self) -> None:
        # HH=1 limit is $51,228
        members = [make_member(age=35, yearly_income=51_228)]
        calc = make_calculator(household_size=1, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_income_above_limit_is_ineligible(self) -> None:
        members = [make_member(age=35, yearly_income=51_229)]
        calc = make_calculator(household_size=1, members=members)
        self.assertFalse(run_household_eligible(calc))

    def test_hh4_income_exactly_at_limit(self) -> None:
        # HH=4 annual limit = $98,508 = $8,209/mo × 12
        members = [
            make_member(age=40, yearly_income=4_500 * 12),
            make_member(age=37, yearly_income=3_709 * 12),
            make_member(age=9),
            make_member(age=6),
        ]
        calc = make_calculator(household_size=4, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_hh4_income_one_dollar_above_limit_is_ineligible(self) -> None:
        # $8,210/mo × 12 = $98,520 > $98,508
        members = [
            make_member(age=40, yearly_income=4_500 * 12),
            make_member(age=37, yearly_income=3_710 * 12),
            make_member(age=9),
            make_member(age=6),
        ]
        calc = make_calculator(household_size=4, members=members)
        self.assertFalse(run_household_eligible(calc))


class TestWaUdpAdultOnlyIncomeAggregation(TestCase):
    def test_minor_income_is_excluded(self) -> None:
        # Adult $4,000/mo = $48,000/yr is under HH=2 limit $66,984
        # Minor $1,800/mo would push naive total to $69,600 — over limit
        members = [
            make_member(age=42, yearly_income=4_000 * 12),
            make_member(age=17, yearly_income=1_800 * 12),
        ]
        calc = make_calculator(household_size=2, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_adult_with_age_none_is_excluded_from_income(self) -> None:
        # Member with age=None is excluded from adult income sum
        members = [
            make_member(age=35, yearly_income=24_000),
            make_member(age=None, yearly_income=999_999),
        ]
        calc = make_calculator(household_size=2, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_multi_adult_income_is_summed(self) -> None:
        # Two adults each earning $33,000/yr = $66,000 total, under HH=2 limit $66,984
        members = [
            make_member(age=38, yearly_income=33_000),
            make_member(age=35, yearly_income=33_000),
        ]
        calc = make_calculator(household_size=2, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_senior_income_counts_as_adult(self) -> None:
        # Parent age 71 counts toward adult income
        members = [
            make_member(age=38, yearly_income=2_800 * 12),
            make_member(age=71, yearly_income=1_100 * 12),
            make_member(age=35, yearly_income=0),
            make_member(age=8, yearly_income=0),
        ]
        # Adult total: (2800+1100)*12 = $46,800 < HH=4 limit $98,508
        calc = make_calculator(household_size=4, members=members)
        self.assertTrue(run_household_eligible(calc))


class TestWaUdpSsiCategoricalPathway(TestCase):
    def test_ssi_recipient_bypasses_income_test(self) -> None:
        # Income $6,943/mo > HH=2 limit $5,582/mo, but SSI present → eligible
        members = [
            make_member(age=67, yearly_income=(943 + 4_000) * 12, ssi_income=943),
            make_member(age=65, yearly_income=2_000 * 12),
        ]
        calc = make_calculator(household_size=2, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_ssi_check_uses_ssi_token_not_all(self) -> None:
        # ssi_income is only returned for ["sSI"] — if calc used ["all"], this would fail
        members = [make_member(age=67, yearly_income=0, ssi_income=943)]
        calc = make_calculator(household_size=1, members=members)
        self.assertTrue(run_household_eligible(calc))

    def test_no_ssi_and_high_income_is_ineligible(self) -> None:
        members = [make_member(age=35, yearly_income=100_000)]
        calc = make_calculator(household_size=1, members=members)
        self.assertFalse(run_household_eligible(calc))


class TestWaUdpSnapStreamlinedPathway(TestCase):
    def test_snap_bypasses_income_test(self) -> None:
        # Income $7,500/mo × 12 > HH=3 limit $82,740, but SNAP present
        members = [
            make_member(age=35, yearly_income=5_000 * 12),
            make_member(age=33, yearly_income=2_500 * 12),
            make_member(age=8),
        ]
        calc = make_calculator(household_size=3, members=members, has_snap=True)
        self.assertTrue(run_household_eligible(calc))

    def test_snap_does_not_override_location(self) -> None:
        # SNAP pathway cannot override the location requirement
        members = [make_member(age=40, yearly_income=1_000 * 12)]
        calc = make_calculator(zipcode="98003", county="King County", household_size=2, members=members, has_snap=True)
        self.assertFalse(run_household_eligible(calc))

    def test_zero_income_with_snap_is_eligible(self) -> None:
        members = [make_member(age=29, yearly_income=0)]
        calc = make_calculator(household_size=1, members=members, has_snap=True)
        self.assertTrue(run_household_eligible(calc))


class TestWaUdpBenefitValue(TestCase):
    def test_value_is_732_for_eligible_household(self) -> None:
        members = [make_member(age=35, yearly_income=24_000)]
        calc = make_calculator(household_size=1, members=members)
        e = Eligibility()
        calc.household_eligible(e)
        calc.value(e)
        self.assertEqual(e.value, 732)
