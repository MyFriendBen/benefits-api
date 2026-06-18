from django.core.exceptions import ValidationError
from django.db import models
from screener.models import WhiteLabel
from programs.programs.policyengine import versions as pe_versions
from .fields import OrderedJSONField


class Configuration(models.Model):
    white_label = models.ForeignKey(
        WhiteLabel, related_name="configurations", null=False, blank=False, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=320)
    data = OrderedJSONField(default=dict)
    active = models.BooleanField()

    def __str__(self) -> str:
        return self.name


class PolicyEngineConfig(models.Model):
    """
    Global (not per-white-label) singleton holding the PolicyEngine model version
    sent on every household /calculate request. Editing this row is how we cut over
    to a new PolicyEngine version without a deploy.

    Only ever one row (enforced by save()/load()). Read via current_version() on the
    hot path (no write); load() materializes the row for write/admin contexts.

    Pinned version numbers only (e.g. "1.715.2"), enforced by clean(). The floating
    "frontier"/"current" aliases are deliberately not valid here: PolicyEngine repoints
    them when it promotes a release, so storing one would let our served version change
    under us. The per-request ?pe_version= override (a test-only preview) is the only
    place those aliases may be used. Blank means omit the "version" field entirely, i.e.
    PolicyEngine's default.
    """

    policyengine_version = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text=(
            'Pinned PolicyEngine package version sent as the top-level "version" '
            'field, e.g. "1.715.2" (must be an exact MAJOR.MINOR.PATCH number). '
            "Clear this field (leave blank) and save to fall back to PolicyEngine's "
            'default. The floating aliases "frontier" / "current" are not allowed here.'
        ),
    )

    class Meta:
        verbose_name = "PolicyEngine Version"
        verbose_name_plural = "PolicyEngine Version"

    def __str__(self) -> str:
        return f"PolicyEngine version: {self.policyengine_version or '(default)'}"

    def clean(self):
        # Normalize first so the stored/served value is exactly what we validate — a
        # value with surrounding whitespace would otherwise pass validation here but be
        # sent to PolicyEngine verbatim.
        value = self.policyengine_version.strip()
        self.policyengine_version = value

        # Blank is allowed (omits the "version" field); otherwise must be an exact
        # version number. This also rejects the floating "frontier"/"current" aliases,
        # which simply aren't valid here.
        if value and not pe_versions.is_valid_version_number(value):
            raise ValidationError(
                {"policyengine_version": 'Must be an exact version number like "1.715.2", or left blank.'}
            )

    def save(self, *args, **kwargs) -> None:
        # Enforce a single row: always write to pk=1. Validate the version field but
        # exclude the forced primary key from uniqueness checks (a second save() is an
        # intentional upsert of the singleton, not a duplicate-id error). Drop any
        # force_insert so the row is updated rather than re-inserted.
        self.pk = 1
        self.full_clean(exclude=["id"])
        kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    @classmethod
    def current_version(cls) -> str:
        """Read-only accessor for the configured version on the eligibility hot path.
        Returns "" (default) when no row exists, without writing one."""
        obj = cls.objects.filter(pk=1).first()
        return obj.policyengine_version if obj else ""
