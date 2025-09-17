from threading import local
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Program


_state = local()


def _is_syncing() -> bool:
    return getattr(_state, "syncing_navigators", False)


def _set_syncing(value: bool) -> None:
    setattr(_state, "syncing_navigators", value)


@receiver(m2m_changed, sender=Program.navigators_sorted.through)
def propagate_navigator_order_across_white_label(sender, instance: Program, action, reverse, model, pk_set, **kwargs):
    """
    Ensure a single canonical Navigator order per white_label.
    Whenever a Program's navigators_sorted changes, propagate that exact ordered list
    to all other Programs in the same white_label.

    Guards against recursion using a thread-local flag.
    """
    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    # Avoid infinite loops if we are updating siblings programmatically
    if _is_syncing():
        return

    # Determine the canonical ordered list from the instance as it currently is
    ordered_ids = list(instance.navigators_sorted.values_list("id", flat=True))

    # Propagate to sibling Programs
    try:
        _set_syncing(True)
        siblings = Program.objects.filter(white_label=instance.white_label).exclude(pk=instance.pk)
        for p in siblings:
            current_ids = list(p.navigators_sorted.values_list("id", flat=True))
            # Skip if the order is already identical to avoid redundant writes and signal churn
            if current_ids == ordered_ids:
                continue
            p.navigators_sorted.set(ordered_ids)
    finally:
        _set_syncing(False)
