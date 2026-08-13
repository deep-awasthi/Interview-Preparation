"""Celery Asynchronous Webhook Dispatcher."""

import logging
import requests
from celery import shared_task
from aether.apps.notifications.models import Webhook

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_event_webhook(self, event_name: str, bucket_name: str, object_key: str, payload: dict):
    """Dispatch HTTP POST event notification to configured active webhooks."""
    webhooks = Webhook.objects.filter(is_active=True)

    for hook in webhooks:
        if event_name in hook.events and (hook.bucket is None or hook.bucket.name == bucket_name):
            try:
                headers = {"Content-Type": "application/json", "X-Aether-Event": event_name}
                response = requests.post(hook.target_url, json=payload, headers=headers, timeout=5)
                logger.info(f"Webhook {hook.name} dispatched to {hook.target_url}, status: {response.status_code}")
            except Exception as exc:
                logger.error(f"Failed sending webhook to {hook.target_url}: {exc}")
                raise self.retry(exc=exc)
