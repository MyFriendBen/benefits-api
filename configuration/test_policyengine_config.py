"""
Tests for the PolicyEngineConfig singleton and the PolicyEngine version
resolution / injection used by the frontier migration (MFB-1112).
"""

from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.test import TestCase

from configuration.admin import PolicyEngineConfigAdmin
from configuration.models import PolicyEngineConfig
from programs.programs.policyengine.policy_engine import pe_input, resolve_pe_version
from screener.models import Screen, WhiteLabel


class TestPolicyEngineConfigSingleton(TestCase):
    def test_save_enforces_single_row(self):
        a = PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        b = PolicyEngineConfig.objects.create(policyengine_version="1.700.0")

        # Both writes collapse onto pk=1, so only one row ever exists.
        self.assertEqual(a.pk, 1)
        self.assertEqual(b.pk, 1)
        self.assertEqual(PolicyEngineConfig.objects.count(), 1)
        self.assertEqual(PolicyEngineConfig.load().policyengine_version, "1.700.0")

    def test_load_creates_default_when_absent(self):
        self.assertEqual(PolicyEngineConfig.objects.count(), 0)
        config = PolicyEngineConfig.load()
        self.assertEqual(config.pk, 1)
        self.assertEqual(config.policyengine_version, "")
        self.assertEqual(PolicyEngineConfig.objects.count(), 1)

    def test_current_version_does_not_write_when_absent(self):
        # Read-only accessor for the hot path: must not materialize a row.
        self.assertEqual(PolicyEngineConfig.objects.count(), 0)
        self.assertEqual(PolicyEngineConfig.current_version(), "")
        self.assertEqual(PolicyEngineConfig.objects.count(), 0)

    def test_current_version_returns_stored_value(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        self.assertEqual(PolicyEngineConfig.current_version(), "1.715.2")

    def test_clean_strips_whitespace(self):
        # Whitespace must be normalized so the stored/served value matches what we
        # validated (otherwise " 1.715.2 " reaches PolicyEngine verbatim).
        config = PolicyEngineConfig(policyengine_version="  1.715.2  ")
        config.clean()
        self.assertEqual(config.policyengine_version, "1.715.2")

    def test_save_persists_stripped_value(self):
        PolicyEngineConfig.objects.create(policyengine_version="  1.715.2  ")
        self.assertEqual(PolicyEngineConfig.load().policyengine_version, "1.715.2")

    def test_clean_accepts_pinned_version(self):
        config = PolicyEngineConfig(policyengine_version="1.715.2")
        config.clean()  # should not raise

    def test_clean_accepts_blank(self):
        config = PolicyEngineConfig(policyengine_version="")
        config.clean()  # blank => omit version, allowed

    def test_clean_rejects_aliases(self):
        # The floating aliases are not valid here (only on the ?pe_version= override).
        for alias in ("frontier", "current", "Frontier", " CURRENT "):
            with self.assertRaises(ValidationError):
                PolicyEngineConfig(policyengine_version=alias).clean()

    def test_clean_rejects_non_version_strings(self):
        # Regression: arbitrary strings (e.g. "xcZX") must not be accepted as a version,
        # nor partial/prefixed numbers.
        for value in ("xcZX", "1.7", "1.715", "v1.715.2", "1.715.2-beta", "latest"):
            with self.assertRaises(ValidationError):
                PolicyEngineConfig(policyengine_version=value).clean()

    def test_save_rejects_invalid_via_full_clean(self):
        # save() calls full_clean(), so an invalid value can't be persisted.
        for value in ("frontier", "xcZX"):
            with self.assertRaises(ValidationError):
                PolicyEngineConfig.objects.create(policyengine_version=value)


class TestPolicyEngineConfigAdminDisplay(TestCase):
    def setUp(self):
        self.admin = PolicyEngineConfigAdmin(PolicyEngineConfig, AdminSite())

    def test_version_display_shows_pinned_value(self):
        config = PolicyEngineConfig(policyengine_version="1.715.2")
        self.assertEqual(self.admin.version_display(config), "1.715.2")

    def test_version_display_shows_default_when_blank(self):
        config = PolicyEngineConfig(policyengine_version="")
        self.assertEqual(self.admin.version_display(config), PolicyEngineConfigAdmin.DEFAULT_LABEL)

    def test_active_version_display_mirrors_value(self):
        self.assertEqual(
            self.admin.active_version_display(PolicyEngineConfig(policyengine_version="1.715.2")), "1.715.2"
        )
        self.assertEqual(
            self.admin.active_version_display(PolicyEngineConfig(policyengine_version="")),
            PolicyEngineConfigAdmin.DEFAULT_LABEL,
        )

    def test_active_version_display_handles_none_on_add_form(self):
        # Add form passes obj=None (fresh DB) — must not AttributeError.
        self.assertEqual(self.admin.active_version_display(None), PolicyEngineConfigAdmin.DEFAULT_LABEL)


class TestResolvePeVersion(TestCase):
    def test_override_wins_over_config(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        # The override is test-only and may be a floating alias.
        self.assertEqual(resolve_pe_version("frontier"), "frontier")

    def test_falls_back_to_config_when_no_override(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        self.assertEqual(resolve_pe_version(None), "1.715.2")

    def test_returns_none_when_unset_and_no_override(self):
        # No config row, no override => omit the version field.
        self.assertIsNone(resolve_pe_version(None))

    def test_blank_config_returns_none(self):
        PolicyEngineConfig.objects.create(policyengine_version="")
        self.assertIsNone(resolve_pe_version(None))


class TestPeInputVersionInjection(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(white_label=self.white_label, completed=False)

    def test_omits_version_when_unset(self):
        raw_input = pe_input(self.screen, [])
        self.assertNotIn("version", raw_input)

    def test_injects_config_version(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        raw_input = pe_input(self.screen, [])
        self.assertEqual(raw_input["version"], "1.715.2")

    def test_override_injects_version(self):
        raw_input = pe_input(self.screen, [], pe_version="frontier")
        self.assertEqual(raw_input["version"], "frontier")
