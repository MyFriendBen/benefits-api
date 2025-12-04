from datetime import datetime
from typing import Optional
from django.db import models
from decimal import Decimal
import uuid
from authentication.models import User
from django.utils.translation import gettext_lazy as _
from programs.util import Dependencies
from django.conf import settings


class WhiteLabel(models.Model):
    name = models.CharField(max_length=120, blank=False, null=False)
    code = models.CharField(max_length=32, blank=False, null=False)
    state_code = models.CharField(max_length=8, blank=True, null=True)
    cms_method = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.name


# The screen is the top most container for all information collected in the
# app and is synonymous with a household model. In addition to general
# application fields like submission_date, it also contains non-individual
# household fields. Screen -> HouseholdMember -> IncomeStream & Expense & Insurance
class Screen(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    white_label = models.ForeignKey(
        WhiteLabel,
        related_name="screens",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
    )
    completed = models.BooleanField(null=False, blank=False)
    submission_date = models.DateTimeField(blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    referral_source = models.CharField(max_length=320, default=None, blank=True, null=True)
    path = models.CharField(max_length=60, default=None, blank=True, null=True)
    referrer_code = models.CharField(max_length=320, default=None, blank=True, null=True)
    agree_to_tos = models.BooleanField(blank=True, null=True)
    is_13_or_older = models.BooleanField(blank=True, null=True)
    zipcode = models.CharField(max_length=5, blank=True, null=True)
    county = models.CharField(max_length=120, default=None, blank=True, null=True)
    household_size = models.IntegerField(blank=True, null=True)
    last_tax_filing_year = models.CharField(max_length=120, default=None, blank=True, null=True)
    household_assets = models.DecimalField(decimal_places=2, max_digits=10, default=None, blank=True, null=True)
    housing_situation = models.CharField(max_length=30, blank=True, null=True, default=None)
    last_email_request_date = models.DateTimeField(blank=True, null=True)
    is_test = models.BooleanField(default=False, blank=True)
    is_test_data = models.BooleanField(blank=True, null=True)
    alternate_path = models.CharField(max_length=60, blank=True, null=True)
    is_verified = models.BooleanField(default=False, blank=True)
    user = models.ForeignKey(User, related_name="screens", on_delete=models.SET_NULL, blank=True, null=True)
    external_id = models.CharField(max_length=120, blank=True, null=True)
    request_language_code = models.CharField(max_length=12, blank=True, null=True)
    has_benefits = models.CharField(max_length=32, default="preferNotToAnswer", blank=True, null=True)
    has_tanf = models.BooleanField(default=False, blank=True, null=True)
    has_wic = models.BooleanField(default=False, blank=True, null=True)
    has_snap = models.BooleanField(default=False, blank=True, null=True)
    has_sunbucks = models.BooleanField(default=False, blank=True, null=True)
    has_lifeline = models.BooleanField(default=False, blank=True, null=True)
    has_acp = models.BooleanField(default=False, blank=True, null=True)
    has_eitc = models.BooleanField(default=False, blank=True, null=True)
    has_coeitc = models.BooleanField(default=False, blank=True, null=True)
    has_il_eitc = models.BooleanField(default=False, blank=True, null=True)
    has_nslp = models.BooleanField(default=False, blank=True, null=True)
    has_ctc = models.BooleanField(default=False, blank=True, null=True)
    has_il_ctc = models.BooleanField(default=False, blank=True, null=True)
    has_il_transit_reduced_fare = models.BooleanField(default=False, blank=True, null=True)
    has_il_bap = models.BooleanField(default=False, blank=True, null=True)
    has_medicaid = models.BooleanField(default=False, blank=True, null=True)
    has_rtdlive = models.BooleanField(default=False, blank=True, null=True)
    has_cccap = models.BooleanField(default=False, blank=True, null=True)
    has_mydenver = models.BooleanField(default=False, blank=True, null=True)
    has_chp = models.BooleanField(default=False, blank=True, null=True)
    has_ccb = models.BooleanField(default=False, blank=True, null=True)
    has_ssi = models.BooleanField(default=False, blank=True, null=True)
    has_andcs = models.BooleanField(default=False, blank=True, null=True)
    has_chs = models.BooleanField(default=False, blank=True, null=True)
    has_cpcr = models.BooleanField(default=False, blank=True, null=True)
    has_cdhcs = models.BooleanField(default=False, blank=True, null=True)
    has_dpp = models.BooleanField(default=False, blank=True, null=True)
    has_ede = models.BooleanField(default=False, blank=True, null=True)
    has_erc = models.BooleanField(default=False, blank=True, null=True)
    has_leap = models.BooleanField(default=False, blank=True, null=True)
    has_il_liheap = models.BooleanField(default=False, blank=True, null=True)
    has_ma_heap = models.BooleanField(default=False, blank=True, null=True)
    has_nc_lieap = models.BooleanField(default=False, blank=True, null=True)
    has_oap = models.BooleanField(default=False, blank=True, null=True)
    has_nccip = models.BooleanField(default=False, blank=True, null=True)
    has_ncscca = models.BooleanField(default=False, blank=True, null=True)
    has_coctc = models.BooleanField(default=False, blank=True, null=True)
    has_upk = models.BooleanField(default=False, blank=True, null=True)
    has_ssdi = models.BooleanField(default=False, blank=True, null=True)
    has_cowap = models.BooleanField(default=False, blank=True, null=True)
    has_ncwap = models.BooleanField(default=False, blank=True, null=True)
    has_ubp = models.BooleanField(default=False, blank=True, null=True)
    has_pell_grant = models.BooleanField(default=False, blank=True, null=True)
    has_rag = models.BooleanField(default=False, blank=True, null=True)
    has_nfp = models.BooleanField(default=False, blank=True, null=True)
    has_fatc = models.BooleanField(default=False, blank=True, null=True)
    has_section_8 = models.BooleanField(default=False, blank=True, null=True)
    has_csfp = models.BooleanField(default=False, blank=True, null=True)
    has_ccdf = models.BooleanField(default=False, blank=True, null=True)
    has_aca = models.BooleanField(default=False, blank=True, null=True)
    has_ma_eaedc = models.BooleanField(default=False, blank=True, null=True)
    has_ma_ssp = models.BooleanField(default=False, blank=True, null=True)
    has_ma_mbta = models.BooleanField(default=False, blank=True, null=True)
    has_ma_maeitc = models.BooleanField(default=False, blank=True, null=True)
    has_ma_macfc = models.BooleanField(default=False, blank=True, null=True)
    has_head_start = models.BooleanField(default=False, blank=True, null=True)
    has_early_head_start = models.BooleanField(default=False, blank=True, null=True)
    has_co_andso = models.BooleanField(default=False, blank=True, null=True)
    has_co_care = models.BooleanField(default=False, blank=True, null=True)
    has_cfhc = models.BooleanField(default=False, blank=True, null=True)
    has_shitc = models.BooleanField(default=False, blank=True, null=True)
    has_employer_hi = models.BooleanField(default=None, blank=True, null=True)
    has_private_hi = models.BooleanField(default=None, blank=True, null=True)
    has_medicaid_hi = models.BooleanField(default=None, blank=True, null=True)
    has_medicare_hi = models.BooleanField(default=None, blank=True, null=True)
    has_nc_medicare_savings = models.BooleanField(default=None, blank=True, null=True)
    has_chp_hi = models.BooleanField(default=None, blank=True, null=True)
    has_no_hi = models.BooleanField(default=None, blank=True, null=True)
    has_va = models.BooleanField(default=None, blank=True, null=True)
    has_project_cope = models.BooleanField(default=False, blank=True, null=True)
    has_cesn_heap = models.BooleanField(default=False, blank=True, null=True)
    needs_food = models.BooleanField(default=False, blank=True, null=True)
    needs_baby_supplies = models.BooleanField(default=False, blank=True, null=True)
    needs_housing_help = models.BooleanField(default=False, blank=True, null=True)
    needs_mental_health_help = models.BooleanField(default=False, blank=True, null=True)
    needs_child_dev_help = models.BooleanField(default=False, blank=True, null=True)
    needs_funeral_help = models.BooleanField(default=False, blank=True, null=True)
    needs_family_planning_help = models.BooleanField(default=False, blank=True, null=True)
    needs_job_resources = models.BooleanField(default=False, blank=True, null=True)
    needs_dental_care = models.BooleanField(default=False, blank=True, null=True)
    needs_legal_services = models.BooleanField(default=False, blank=True, null=True)
    needs_college_savings = models.BooleanField(default=False, blank=True, null=True)
    needs_veteran_services = models.BooleanField(default=False, blank=True, null=True)
    utm_id = models.CharField(max_length=64, blank=True, null=True)
    utm_source = models.CharField(max_length=64, blank=True, null=True)
    utm_medium = models.CharField(max_length=64, blank=True, null=True)
    utm_campaign = models.CharField(max_length=128, blank=True, null=True)
    utm_content = models.CharField(max_length=128, blank=True, null=True)
    utm_term = models.CharField(max_length=128, blank=True, null=True)

    @property
    def frozen(self):
        return self.validations.count() > 0

    def calc_gross_income(self, frequency, types, exclude=[]):
        household_members = self.household_members.all()
        gross_income = 0

        for household_member in household_members:
            gross_income += household_member.calc_gross_income(frequency, types, exclude)
        return float(gross_income)

    def calc_expenses(self, frequency, types):
        expenses = self.expenses.all()
        total_expense = 0

        for expense in expenses:
            if "all" in types or expense.type in types:
                if frequency == "monthly":
                    total_expense += expense.monthly()
                elif frequency == "yearly":
                    total_expense += expense.yearly()

        return float(total_expense)

    def has_expense(self, expense_types):
        """
        Returns True if one household member has one of the expenses in expense_types
        """
        for expense_type in expense_types:
            household_expense_types = self.expenses.all()
            for expense in household_expense_types:
                if expense_type == expense.type:
                    return True
        return False

    def expense_type_names(self) -> list[str]:
        """
        Get list of unique expense types for this screen.
        Returns empty list if no expenses exist.
        """
        return list(self.expenses.values_list("type", flat=True).distinct().filter(type__isnull=False))

    def num_children(self, age_min=0, age_max=18, include_pregnant=False, child_relationship=["all"]):
        children = 0

        household_members = self.household_members.all()
        for household_member in household_members:
            has_child_relationship = household_member.relationship in child_relationship or "all" in child_relationship
            if household_member.age >= age_min and household_member.age <= age_max and has_child_relationship:
                children += 1
            if household_member.pregnant and include_pregnant:
                children += 1

        return children

    def num_adults(self, age_max=19):
        adults = 0
        household_members = self.household_members.all()
        for household_member in household_members:
            if household_member.age >= age_max:
                adults += 1
        return adults

    def num_guardians(self):
        parents = 0
        child_relationship = ["child", "fosterChild"]
        guardian_relationship = ["parent", "fosterParent"]
        hoh_child_exists = False

        household_members = self.household_members.all()
        for household_member in household_members:
            if household_member.relationship in child_relationship:
                hoh_child_exists = True
            elif household_member.relationship == "headOfHousehold":
                if household_member.pregnant:
                    hoh_child_exists = True
            elif household_member.pregnant:
                parents += 1
            elif household_member.relationship in guardian_relationship:
                parents += 1

        for household_member in household_members:
            if hoh_child_exists and household_member.relationship == "spouse":
                parents += 1
            elif hoh_child_exists and household_member.relationship == "headOfHousehold":
                parents += 1

        return parents

    def is_joint(self):
        is_joint = False
        household_members = self.household_members.all()
        for household_member in household_members:
            if household_member.relationship == "spouse":
                is_joint = True
        return is_joint

    def calc_net_income(self, frequency, income_types, expense_types):
        net_income = None
        if frequency == "monthly":
            gross_income = self.calc_gross_income(frequency, income_types)
            expenses = self.calc_expenses(frequency, expense_types)
            net_income = gross_income - expenses

        return float(net_income)

    def relationship_map(self):
        relationship_map = {}

        all_members = self.household_members.all()
        for member in all_members:
            if member.id in relationship_map and relationship_map[member.id] is not None:
                continue

            relationship = member.relationship
            probable_spouse = None

            if relationship == "headOfHousehold":
                for other_member in all_members:
                    if (
                        other_member.relationship in ("spouse", "domesticPartner")
                        and other_member.id not in relationship_map
                    ):
                        probable_spouse = other_member.id
                        break
            elif relationship in ("spouse", "domesticPartner"):
                for other_member in all_members:
                    if other_member.relationship == "headOfHousehold" and other_member.id not in relationship_map:
                        probable_spouse = other_member.id
                        break
            elif relationship in (
                "parent",
                "fosterParent",
                "stepParent",
                "grandParent",
            ):
                for other_member in all_members:
                    if (
                        other_member.relationship == relationship
                        and other_member.id != member.id
                        and other_member.id not in relationship_map
                    ):
                        probable_spouse = other_member.id
                        break

            relationship_map[member.id] = probable_spouse
            if probable_spouse is not None:
                relationship_map[probable_spouse] = member.id

        return relationship_map

    def other_tax_unit_structure(self):
        other_tax_unit: list[HouseholdMember] = []
        for member in self.household_members.all():
            if not member.is_in_tax_unit():
                other_tax_unit.append(member)

        unit = {"head": None, "spouse": None, "dependents": []}
        if len(other_tax_unit) == 0:
            return unit

        for member in other_tax_unit:
            if unit["head"] is None or member.age > unit["head"].age:
                unit["head"] = member

        spouse_id = self.relationship_map()[unit["head"].id]

        for member in other_tax_unit:
            if member.id == unit["head"].id:
                continue

            if member.id == spouse_id:
                unit["spouse"] = member
            else:
                unit["dependents"].append(member)

        return unit

    def has_insurance_types(self, types, strict=True):
        for member in self.household_members.all():
            if not hasattr(member, "insurance"):
                continue

            if member.insurance.has_insurance_types(types, strict):
                return True

        return False

    def has_benefit_from_list(self, names: list[str]):
        for program in names:
            if self.has_benefit(program):
                return True

        return False

    def has_benefit(self, name_abbreviated: str):
        """
        Maps a program's name_abbreviated to the corresponding has_* field on the Screen model.

        This is used to determine if a user already has a benefit (selected in step 10) so it can be
        filtered from results on the frontend via the "already_has" flag.

        Map Structure:
            Key: Program name_abbreviated (from program registration, e.g., co/__init__.py)
            Value: Boolean field on Screen model indicating user has that benefit

        Common Pattern:
            Multiple program variants (e.g., different states or screener types) map to the same field:
            - "snap", "co_snap", "il_snap" → all map to self.has_snap (same real-world benefit)
            - "leap", "co_energy_calculator_leap" → both map to self.has_leap (same benefit, different flows)

        Adding New Mappings:
            1. Ensure the benefit key exists in white_label config's category_benefits (e.g., "leap")
            2. Ensure updateScreen.ts maps formData.benefits.{key} → has_{key}
            3. Add all program name_abbreviated variants that represent the same benefit

        Example Flow:
            Config (co.py): "leap": {"name": "LEAP", ...}
            → User checks LEAP in step 10
            → Frontend: formData.benefits.leap = true
            → API (updateScreen.ts): has_leap = formData.benefits.leap
            → Database: screen.has_leap = True
            → This method: has_benefit("leap") → returns self.has_leap (True)
            → Serializer: "already_has": True → Frontend filters out LEAP from results
        """

        has_ssi_or_ssi_income = self.has_ssi or self.calc_gross_income("yearly", ("sSI",)) > 0

        name_map = {
            "tanf": self.has_tanf,
            "nc_tanf": self.has_tanf,
            "co_tanf": self.has_tanf,
            "il_tanf": self.has_tanf,
            "tx_tanf": self.has_tanf,
            "wic": self.has_wic,
            "co_wic": self.has_wic,
            "nc_wic": self.has_wic,
            "tx_wic": self.has_wic,
            "snap": self.has_snap,
            "sunbucks": self.has_sunbucks,
            "co_snap": self.has_snap,
            "nc_snap": self.has_snap,
            "il_snap": self.has_snap,
            "tx_snap": self.has_snap,
            "lifeline": self.has_lifeline,
            "acp": self.has_acp,
            "eitc": self.has_eitc,
            "tx_eitc": self.has_eitc,
            "coeitc": self.has_coeitc,
            "il_eitc": self.has_il_eitc,
            "nslp": self.has_nslp,
            "tx_nslp": self.has_nslp,
            "ctc": self.has_ctc,
            "tx_ctc": self.has_ctc,
            "il_ctc": self.has_il_ctc,
            "il_transit_reduced_fare": self.has_il_transit_reduced_fare,
            "il_bap": self.has_il_bap,
            "project_cope": self.has_project_cope,
            "co_energy_calculator_cope": self.has_project_cope,
            "cesn_heap": self.has_cesn_heap,
            "co_energy_calculator_heap": self.has_cesn_heap,
            "rtdlive": self.has_rtdlive,
            "cccap": self.has_cccap,
            "mydenver": self.has_mydenver,
            "ccb": self.has_ccb,
            "ssi": has_ssi_or_ssi_income,
            "tx_ssi": has_ssi_or_ssi_income,
            "tx_csfp": self.has_csfp,
            "andcs": self.has_andcs,
            "chs": self.has_chs,
            "cpcr": self.has_cpcr,
            "co_energy_calculator_cpcr": self.has_cpcr,
            "cdhcs": self.has_cdhcs,
            "dpp": self.has_dpp,
            "ede": self.has_ede,
            "erc": self.has_erc,
            "leap": self.has_leap,
            "co_energy_calculator_leap": self.has_leap,
            "ma_heap": self.has_ma_heap,
            "il_liheap": self.has_il_liheap,
            "nc_lieap": self.has_nc_lieap,
            "oap": self.has_oap,
            "nccip": self.has_nccip,
            "nc_scca": self.has_ncscca,
            "coctc": self.has_coctc,
            "upk": self.has_upk,
            "ssdi": self.has_ssdi,
            "pell_grant": self.has_pell_grant,
            "rag": self.has_rag,
            "nfp": self.has_nfp,
            "fatc": self.has_fatc,
            "section_8": self.has_section_8,
            "cowap": self.has_cowap,
            "co_energy_calculator_cowap": self.has_cowap,
            "ncwap": self.has_ncwap,
            "ubp": self.has_ubp,
            "co_energy_calculator_ubp": self.has_ubp,
            "medicare": self.has_medicare_hi,
            "chp": self.has_chp or self.has_chp_hi,
            "va": self.has_va,
            "aca": self.has_aca,
            "nc_aca": self.has_aca,
            "ma_aca": self.has_aca,
            "tx_aca": self.has_aca,
            "ma_mbta": self.has_ma_mbta,
            "ma_snap": self.has_snap,
            "ma_ccdf": self.has_ccdf,
            "ma_wic": self.has_wic,
            "ma_eaedc": self.has_ma_eaedc,
            "ma_maeitc": self.has_ma_maeitc,
            "ma_macfc": self.has_ma_macfc,
            "ma_tafdc": self.has_tanf,
            "ma_mass_health": self.has_medicaid or self.has_medicaid_hi,
            "ma_head_start": self.has_head_start,
            "ma_early_head_start": self.has_early_head_start,
            "co_andso": self.has_co_andso,
            "co_care": self.has_co_care,
            "cfhc": self.has_cfhc,
            "shitc": self.has_shitc,
            "nc_medicare_savings": self.has_nc_medicare_savings,
        }

        if name_abbreviated in name_map:
            has_benefit = name_map[name_abbreviated]
        else:
            has_benefit = False

        return has_benefit

    def set_screen_is_test(self):
        referral_source_tests = ["testorprospect", "test"]

        self.is_test_data = (
            self.is_test
            or (self.referral_source is not None and self.referral_source.lower() in referral_source_tests)
            or (self.referrer_code is not None and self.referrer_code.lower() in referral_source_tests)
        )
        self.save()

    def get_head(self):
        for member in self.household_members.all():
            if member.relationship == "headOfHousehold":
                return member

        raise Exception("No head of household")

    def get_language_code(self):
        language_code = settings.LANGUAGE_CODE

        if self.request_language_code:
            language_code = str(self.request_language_code).lower()

        return language_code

    def has_members_outside_of_tax_unit(self):
        for member in self.household_members.all():
            if not member.is_in_tax_unit():
                return True

        return False

    def missing_fields(self):
        screen_fields = (
            "zipcode",
            "county",
            "household_size",
            "household_assets",
            "energy_calculator",
        )

        missing_fields = Dependencies()

        for field in screen_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                missing_fields.add(field)

        for member in self.household_members.all():
            missing_fields.update(member.missing_fields())

        for expence in self.expenses.all():
            missing_fields.update(expence.missing_fields())

        return missing_fields


# Log table for any messages sent by the application via text or email
class Message(models.Model):
    sent = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=30)
    screen = models.ForeignKey(Screen, related_name="messages", on_delete=models.CASCADE)
    content = models.CharField(max_length=320, blank=True, null=True)
    uid = models.IntegerField(blank=True, null=True)


# Table of fields specific to individual household members. Parent model is the
# Screen
class HouseholdMember(models.Model):
    screen = models.ForeignKey(Screen, related_name="household_members", on_delete=models.CASCADE)
    frontend_id = models.UUIDField(default=uuid.uuid4)
    relationship = models.CharField(max_length=30, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    birth_year_month = models.DateField(blank=True, null=True)
    student = models.BooleanField(blank=True, null=True)
    student_full_time = models.BooleanField(blank=True, null=True)
    pregnant = models.BooleanField(blank=True, null=True)
    unemployed = models.BooleanField(blank=True, null=True)
    worked_in_last_18_mos = models.BooleanField(blank=True, null=True)
    visually_impaired = models.BooleanField(blank=True, null=True)
    disabled = models.BooleanField(blank=True, null=True)
    long_term_disability = models.BooleanField(blank=True, null=True)
    veteran = models.BooleanField(blank=True, null=True)
    medicaid = models.BooleanField(blank=True, null=True)
    disability_medicaid = models.BooleanField(blank=True, null=True)
    has_income = models.BooleanField(blank=True, null=True)
    has_expenses = models.BooleanField(blank=True, null=True)

    def calc_gross_income(self, frequency, types, exclude=[]):
        gross_income = 0
        earned_income_types = ["wages", "selfEmployment"]

        income_streams = self.income_streams.all()
        for income_stream in income_streams:
            if income_stream.type in exclude:
                continue

            include_all = "all" in types
            specific_match = income_stream.type in types
            earned_income_match = "earned" in types and income_stream.type in earned_income_types
            unearned_income_match = "unearned" in types and income_stream.type not in earned_income_types
            if include_all or earned_income_match or unearned_income_match or specific_match:
                if frequency == "monthly":
                    gross_income += income_stream.monthly()
                elif frequency == "yearly":
                    gross_income += income_stream.yearly()
        return float(gross_income)

    def calc_expenses(self, frequency, types):
        total_expense = 0

        expenses = self.expenses.all()
        for expense in expenses:
            if "all" in types or expense.type in types:
                if frequency == "monthly":
                    total_expense += expense.monthly()
                elif frequency == "yearly":
                    total_expense += expense.yearly()
        return float(total_expense)

    def calc_net_income(self, frequency, income_types, expense_types):
        net_income = None
        if frequency == "monthly":
            gross_income = self.calc_gross_income(frequency, income_types)
            expenses = self.calc_expenses(frequency, expense_types)
            net_income = gross_income - expenses

        return float(net_income)

    def is_married(self):
        all_household_members = self.screen.household_members.all()
        if self.relationship in ("spouse", "domesticPartner"):
            return {"is_married": True, "married_to": self.screen.get_head()}
        if self.relationship == "headOfHousehold":
            for member in all_household_members:
                if member.relationship in ("spouse", "domesticPartner"):
                    return {"is_married": True, "married_to": member}
        return {"is_married": False}

    def has_disability(self):
        return self.disabled or self.visually_impaired or self.long_term_disability

    def is_head(self) -> bool:
        return self.relationship == "headOfHousehold"

    def is_spouse(self) -> bool:
        return self.screen.relationship_map()[self.screen.get_head().id] == self.id

    def is_dependent(self):
        is_tax_unit_spouse = self.is_spouse()
        is_tax_unit_head = self.is_head()
        is_tax_unit_dependent = (
            (self.age <= 18 or (self.student and self.age <= 23) or self.has_disability())
            and (self.calc_gross_income("yearly", ["all"]) <= self.screen.calc_gross_income("yearly", ["all"]) / 2)
            and (not (is_tax_unit_head or is_tax_unit_spouse))
        )

        return is_tax_unit_dependent

    def is_in_tax_unit(self):
        return self.is_head() or self.is_spouse() or self.is_dependent()

    def has_benefit(self, name_abbreviated: str):
        name_map = {}

        if hasattr(self, "insurance"):
            name_map = {
                "nc_medicaid": self.insurance.medicaid,
                "co_medicaid": self.insurance.medicaid,
                "medicaid": self.insurance.medicaid,
                "emergency_medicaid": self.insurance.emergency_medicaid,
            }

        has_insurance = self.has_insurance_types((name_abbreviated,), strict=False)

        if name_abbreviated in name_map:
            has_benefit = name_map[name_abbreviated]
        else:
            has_benefit = False

        return has_insurance or has_benefit

    def has_insurance_types(self, types, strict=True):
        if not hasattr(self, "insurance"):
            return False

        if self.insurance.has_insurance_types(types, strict):
            return True

        return False

    @property
    def birth_year(self) -> Optional[int]:
        if self.birth_year_month is None:
            return None

        return self.birth_year_month.year

    @property
    def birth_month(self) -> Optional[int]:
        if self.birth_year_month is None:
            return None

        return self.birth_year_month.month

    def calc_age(self) -> int:
        if self.birth_year_month is None:
            return self.age

        return self.age_from_date(self.birth_year_month)

    @staticmethod
    def age_from_date(birth_year_month: datetime) -> int:
        today = datetime.now()

        if today.month >= birth_year_month.month:
            return today.year - birth_year_month.year

        return today.year - birth_year_month.year - 1

    def fraction_age(self) -> float:
        today = datetime.now()

        current_year = today.year + today.month / 12
        birth_year = self.birth_year_month.year + self.birth_year_month.month / 12

        return current_year - birth_year

    def missing_fields(self):
        member_fields = (
            "relationship",
            "age",
            "student",
            "pregnant",
            "visually_impaired",
            "disabled",
            "long_term_disability",
            "insurance",
            "energy_calculator",
        )

        missing_fields = Dependencies()

        for field in member_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                missing_fields.add(field)

        for income in self.income_streams.all():
            missing_fields.update(income.missing_fields())

        return missing_fields


# HouseholdMember income streams
class IncomeStream(models.Model):
    screen = models.ForeignKey(Screen, related_name="income_streams", on_delete=models.CASCADE)
    household_member = models.ForeignKey(HouseholdMember, related_name="income_streams", on_delete=models.CASCADE)
    type = models.CharField(max_length=30, blank=True, null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    frequency = models.CharField(max_length=30, blank=True, null=True)
    hours_worked = models.IntegerField(null=True, blank=True)

    def monthly(self):
        if self.frequency == "monthly":
            monthly = self.amount
        elif self.frequency == "weekly":
            monthly = self.amount * Decimal(4.35)
        elif self.frequency == "biweekly":
            monthly = self.amount * Decimal(2.175)
        elif self.frequency == "semimonthly":
            monthly = self.amount * 2
        elif self.frequency == "yearly":
            monthly = self.amount / 12
        elif self.frequency == "hourly":
            monthly = self._hour_to_month()

        return monthly

    def yearly(self):
        if self.frequency == "monthly":
            yearly = self.amount * 12
        elif self.frequency == "weekly":
            yearly = self.amount * Decimal(52.1429)
        elif self.frequency == "biweekly":
            yearly = self.amount * Decimal(26.01745)
        elif self.frequency == "semimonthly":
            yearly = self.amount * 24
        elif self.frequency == "yearly":
            yearly = self.amount
        elif self.frequency == "hourly":
            yearly = self._hour_to_month() * 12

        return yearly

    def _hour_to_month(self):
        return self.amount * self.hours_worked * Decimal(4.35)

    def missing_fields(self):
        income_fields = (
            "type",
            "amount",
            "frequency",
        )

        missing_fields = Dependencies()
        for field in income_fields:
            if getattr(self, field) is None:
                missing_fields.add("income_" + field)

        return missing_fields


# HouseholdMember expenses
class Expense(models.Model):
    screen = models.ForeignKey(Screen, related_name="expenses", on_delete=models.CASCADE)
    household_member = models.ForeignKey(HouseholdMember, related_name="expenses", on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=30, blank=True, null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    frequency = models.CharField(max_length=30, blank=True, null=True)

    def monthly(self):
        if self.frequency == "monthly":
            monthly = self.amount
        elif self.frequency == "weekly":
            monthly = self.amount * Decimal(4.35)
        elif self.frequency == "biweekly":
            monthly = self.amount * Decimal(2.175)
        elif self.frequency == "semimonthly":
            monthly = self.amount * 2
        elif self.frequency == "yearly":
            monthly = self.amount / 12
        return monthly

    def yearly(self):
        if self.frequency == "monthly":
            yearly = self.amount * 12
        elif self.frequency == "weekly":
            yearly = self.amount * Decimal(52.1429)
        elif self.frequency == "biweekly":
            yearly = self.amount * Decimal(26.01745)
        elif self.frequency == "semimonthly":
            yearly = self.amount * 24
        elif self.frequency == "yearly":
            yearly = self.amount

        return yearly

    def missing_fields(self):
        expense_fields = ("type", "amount")

        missing_fields = Dependencies()

        for field in expense_fields:
            if getattr(self, field) is None:
                missing_fields.add("expense_" + field)

        return missing_fields


class Insurance(models.Model):
    household_member = models.OneToOneField(
        HouseholdMember, related_name="insurance", null=False, on_delete=models.CASCADE
    )
    dont_know = models.BooleanField(default=False)
    none = models.BooleanField(default=True)
    employer = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    chp = models.BooleanField(default=False)
    medicaid = models.BooleanField(default=False)  # low income health insurance
    medicare = models.BooleanField(default=False)  # elderly health insurance
    emergency_medicaid = models.BooleanField(default=False)
    family_planning = models.BooleanField(default=False)
    va = models.BooleanField(default=False)
    # NOTE: Massachusetts combines Medicaid and CHIP into one program called MassHealth
    mass_health = models.BooleanField(default=False)

    def has_insurance_types(self, types, strict=True):
        if "none" in types:
            types = (*types, "dont_know")

        insurance = self.insurance_map()
        for hi_type in types:
            if hi_type not in insurance:
                if strict:
                    raise KeyError(f"{hi_type} not in insurance types")
                continue

            if insurance[hi_type]:
                return True

        return False

    def insurance_map(self):
        return {
            "dont_know": self.dont_know,
            "none": self.none,
            "employer": self.employer,
            "private": self.private,
            "chp": self.chp,
            "medicaid": self.medicaid,
            "nc_medicaid": self.medicaid,
            "co_medicaid": self.medicaid,
            "ma_mass_health": self.mass_health or self.medicaid,
            "medicare": self.medicare,
            "emergency_medicaid": self.emergency_medicaid,
            "family_planning": self.family_planning,
            "va": self.va,
        }


class EnergyCalculatorScreen(models.Model):
    screen = models.OneToOneField(Screen, related_name="energy_calculator", null=False, on_delete=models.CASCADE)
    is_home_owner = models.BooleanField(default=False, null=True, blank=True)
    is_renter = models.BooleanField(default=False, null=True, blank=True)
    electric_provider = models.CharField(max_length=200, null=True, blank=True)
    electric_provider_name = models.CharField(max_length=200, null=True, blank=True)  # The human readable version
    gas_provider = models.CharField(max_length=200, null=True, blank=True)
    gas_provider_name = models.CharField(max_length=200, null=True, blank=True)  # The human readable version
    electricity_is_disconnected = models.BooleanField(default=False, null=True, blank=True)
    has_past_due_energy_bills = models.BooleanField(default=False, null=True, blank=True)
    has_old_car = models.BooleanField(default=False, null=True, blank=True)
    needs_water_heater = models.BooleanField(default=False, null=True, blank=True)
    needs_hvac = models.BooleanField(default=False, null=True, blank=True)
    needs_stove = models.BooleanField(default=False, null=True, blank=True)
    needs_dryer = models.BooleanField(default=False, null=True, blank=True)

    def has_electricity_provider(self, providers: list[str]):
        for provider in providers:
            if provider == self.electric_provider:
                return True

        return False

    def has_gas_provider(self, providers: list[str]):
        for provider in providers:
            if provider == self.gas_provider:
                return True

        return False

    def has_utility_provider(self, providers: list[str]):
        return self.has_electricity_provider(providers) or self.has_gas_provider(providers)


class EnergyCalculatorMember(models.Model):
    household_member = models.OneToOneField(
        HouseholdMember,
        related_name="energy_calculator",
        null=False,
        on_delete=models.CASCADE,
    )
    surviving_spouse = models.BooleanField(default=False, null=True, blank=True)
    receives_ssi = models.BooleanField(default=False, null=True, blank=True)
    medical_equipment = models.BooleanField(default=False, null=True, blank=True)


# A point in time log table to capture the exact eligibility and value results
# for a completed screen. This table is currently used primarily for analytics
# but will eventually drive new benefit update notifications
class EligibilitySnapshot(models.Model):
    screen = models.ForeignKey(Screen, related_name="eligibility_snapshots", on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now=True)
    is_batch = models.BooleanField(default=False)
    had_error = models.BooleanField(default=False)


# Eligibility results for each specific program per screen. These are
# aggregated per screen using the EligibilitySnapshot id
class ProgramEligibilitySnapshot(models.Model):
    eligibility_snapshot = models.ForeignKey(
        EligibilitySnapshot, related_name="program_snapshots", on_delete=models.CASCADE
    )
    new = models.BooleanField(default=False)
    name = models.CharField(max_length=320)
    name_abbreviated = models.CharField(max_length=32)
    value_type = models.CharField(max_length=120)
    estimated_value = models.DecimalField(decimal_places=2, max_digits=10)
    estimated_delivery_time = models.CharField(max_length=120, blank=True, null=True)
    estimated_application_time = models.CharField(max_length=120, blank=True, null=True)
    eligible = models.BooleanField()
    failed_tests = models.JSONField(blank=True, null=True)
    passed_tests = models.JSONField(blank=True, null=True)
