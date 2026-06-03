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
    """

    # The floating aliases move under us when PolicyEngine promotes a release, so we
    # only ever pin an exact package version here (e.g. "1.715.2"). The per-request
    # ?pe_version= override is the only place "frontier"/"current" may be used.
    DISALLOWED_VERSIONS = ("frontier", "current")

    # Blank => omit the "version" field entirely, i.e. PolicyEngine's default ("current").
    policyengine_version = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text=(
            'Pinned PolicyEngine package version sent as the top-level "version" '
            'field (e.g. "1.715.2"). Leave blank to use PolicyEngine\'s default. '
            'The floating aliases "frontier" / "current" are not allowed here.'
        ),
    )

    class Meta:
        verbose_name = "PolicyEngine configuration"
        verbose_name_plural = "PolicyEngine configuration"

    def __str__(self):
        return f"PolicyEngine version: {self.policyengine_version or '(default)'}"

    def clean(self):
        if self.policyengine_version.strip().lower() in self.DISALLOWED_VERSIONS:
            raise ValidationError(
                {
                    "policyengine_version": (
                        'Pin an exact version number (e.g. "1.715.2"), not the floating '
                        '"frontier" / "current" aliases.'
                    )
                }
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
