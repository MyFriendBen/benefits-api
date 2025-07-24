from django.core.management.base import BaseCommand
from django.db.models import Min, Count
from django.apps import apps
from collections import defaultdict


class Command(BaseCommand):
    help = "Removed duplicate urgent need categories"

    def handle(self, *args, **options):
        UrgentNeed = apps.get_model("programs", "UrgentNeed")
        UrgentNeedCategory = apps.get_model("programs", "UrgentNeedCategory")

        all_categories = list(UrgentNeedCategory.objects.all().values("id", "name"))

        name_to_ids = defaultdict(list)
        for category in all_categories:
            name_to_ids[category["name"]].append(category["id"])

        id_mapping = {}
        for ids in name_to_ids.values():
            first_id = min(ids)
            for cid in ids:
                id_mapping[cid] = first_id

        for urgent_need in UrgentNeed.objects.prefetch_related("type_short"):
            current_categories = set(urgent_need.type_short.values_list("id", flat=True))
            non_dup_categories = {id_mapping[cid] for cid in current_categories}
            if current_categories != non_dup_categories:
                urgent_need.type_short.set(non_dup_categories)

        for name, ids in name_to_ids.items():
            first_id = min(ids)
            duplicates_to_delete = [cid for cid in ids if cid != first_id]
            if duplicates_to_delete:
                UrgentNeedCategory.objects.filter(id__in=duplicates_to_delete).delete()

        self.stdout.write(self.style.SUCCESS(f"Script ran successfully."))
