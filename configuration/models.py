import re

from django.core.exceptions import ValidationError
from django.db import models
from screener.models import WhiteLabel
from .fields import OrderedJSONField


class Configuration(models.Model):
    white_label = models.ForeignKey(
        WhiteLabel, related_name="configurations", null=False, blank=False, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=320)
    data = OrderedJSONField(default=dict)
    active = models.BooleanField()

    def __str__(self):
        return self.name


class PolicyEngineConfig(models.Model):
    """
    Global (not per-white-label) singleton holding the PolicyEngine model version
    sent on every household /calculate request. Editing this row is how we cut over
    to a new PolicyEngine version without a deploy.

    Only ever one row (enforced by save()/load()). Read via PolicyEngineConfig.load().

    Pinned version numbers only (e.g. "1.715.2"), enforced by clean(). The floating
    "frontier"/"current" aliases are deliberately not valid here: PolicyEngine repoints
    them when it promotes a release, so storing one would let our served version change
    under us. The per-request ?pe_version= override (a test-only preview) is the only
    place those aliases may be used. Blank means omit the "version" field entirely, i.e.
    PolicyEngine's default.
    """

    # An exact package version, e.g. "1.715.2". The shape (not a hardcoded list) means
    # new PolicyEngine releases need no code change. Shared with the ?pe_version=
    # override validation in screener.views.
    VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

    policyengine_version = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text=(
            'Pinned PolicyEngine package version sent as the top-level "version" '
            'field, e.g. "1.715.2" (must be an exact MAJOR.MINOR.PATCH number). Leave '
            'blank to use PolicyEngine\'s default. The floating aliases "frontier" / '
            '"current" are not allowed here.'
        ),
    )

    class Meta:
        verbose_name = "PolicyEngine Version"
        verbose_name_plural = "PolicyEngine Version"

    def __str__(self):
        return f"PolicyEngine version: {self.policyengine_version or '(default)'}"

    def clean(self):
        value = self.policyengine_version.strip()

        # Blank is allowed (omits the "version" field); otherwise must be an exact
        # version number. This also rejects the floating "frontier"/"current" aliases,
        # which simply aren't valid here.
        if value and not self.VERSION_RE.match(value):
            raise ValidationError(
                {"policyengine_version": 'Must be an exact version number like "1.715.2", or left blank.'}
            )

    def save(self, *args, **kwargs):
        # Enforce a single row: always write to pk=1. Validate the version field but
        # exclude the forced primary key from uniqueness checks (a second save() is an
        # intentional upsert of the singleton, not a duplicate-id error). Drop any
        # force_insert so the row is updated rather than re-inserted.
        self.pk = 1
        self.full_clean(exclude=["id"])
        kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "PolicyEngineConfig":
        """Return the singleton row, creating an empty (default) one if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
