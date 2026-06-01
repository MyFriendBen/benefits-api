# Adds a database-level UniqueConstraint enforcing that no two Program
# rows in the same WhiteLabel can share a name_abbreviated. The codebase
# treats name_abbreviated as a logical unique key for benefit selection
# (calculator dispatch, the has-benefits step UI, the mart_current_benefits
# dbt grain), but until now there was no schema-level enforcement —
# uniqueness was assumed by convention only.
#
# Two collisions were resolved earlier in this PR before adding the
# constraint:
#   - Migration 0153: deleted the two CO _dev_ineligible Program rows
#     (ids 152, 153) along with the dev-calculator workflow.
#   - Migration 0154: renamed the CO Expanded EITC Program's
#     name_abbreviated from "coeitc" to "co_expanded_eitc" so it no
#     longer collides with the standard CO EITC.
#
# This migration will fail to apply if any remaining (white_label,
# name_abbreviated) duplicates exist — that's the intended safety net.
# See MFB-999 for the broader context.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0154_rename_coexeitc_name_abbreviated"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="program",
            constraint=models.UniqueConstraint(
                fields=["white_label", "name_abbreviated"],
                name="program_unique_wl_name_abbreviated",
            ),
        ),
    ]
