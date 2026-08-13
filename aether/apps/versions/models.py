"""Object Versioning tracking models."""

import uuid
from django.db import models
from aether.apps.buckets.models import Bucket


class ObjectVersion(models.Model):
    """Explicit version history record for object versions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE, related_name="versions")
    key = models.CharField(max_length=1024, db_index=True)
    version_id = models.CharField(max_length=128, db_index=True)
    is_latest = models.BooleanField(default=False)
    is_delete_marker = models.BooleanField(default=False)
    size = models.BigIntegerField(default=0)
    etag = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aether_object_versions"
        ordering = ["-created_at"]
