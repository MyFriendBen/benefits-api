"""The Celery app (MFB-2436). Configuration is the CELERY_* block in settings.py.

The worker process type runs it (Procfile); tasks live in each app's tasks.py.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "benefits.settings")

app = Celery("benefits")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
