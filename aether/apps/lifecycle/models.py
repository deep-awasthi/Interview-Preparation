"""Lifecycle Rules Model."""

import uuid
from django.db import models
from aether.apps.buckets.models import Bucket


class LifecycleRule(models.Model):
    """S3 Lifecycle Rule configuration for object expiration and retention."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE, related_name="lifecycle_rules")
    rule_id = models.CharField(max_length=128)
    prefix = models.CharField(max_length=1024, default="", blank=True)
    status = models.CharField(max_length=16, default="Enabled")  # Enabled / Disabled
    expiration_days = models.IntegerField(null=True, blank=True)
    noncurrent_version_expiration_days = models.IntegerField(null=True, blank=True)
    abort_incomplete_multipart_days = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aether_lifecycle_rules"
