"""Initialize Celery to run background tasks.

See https://blog.miguelgrinberg.com/post/using-celery-with-flask
"""

import os

from celery import Celery

CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL", "redis://localhost:6379"
)

squash_tasks = Celery(
    "squash.tasks", backend=CELERY_BROKER_URL, broker=CELERY_BROKER_URL
)
