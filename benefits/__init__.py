# Load the Celery app whenever Django starts, so shared_task binds to it in every
# process: web dynos enqueue, the worker consumes (MFB-2436).
from .celery import app as celery_app

__all__ = ("celery_app",)
