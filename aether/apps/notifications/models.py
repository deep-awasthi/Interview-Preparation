"""Webhook and Event Notifications Models."""

import uuid
from django.db import models
from aether.apps.buckets.models import Bucket


class Webhook(models.Model):
    """Event Webhook subscription model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE, related_name="webhooks", null=True, blank=True)
    target_url = models.URLField(max_length=2048)
    events = models.JSONField(default=list)  # ["ObjectCreated", "ObjectDeleted", "BucketCreated", "BucketDeleted"]
    secret = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aether_webhooks"
