"""Object Model for storing Object metadata and versioning states."""

import uuid
from django.db import models
from aether.apps.buckets.models import Bucket


class Object(models.Model):
    """S3 Object metadata entity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE, related_name="bucket_objects")
    key = models.CharField(max_length=1024, db_index=True)
    version_id = models.CharField(max_length=128, default="null", db_index=True)
    is_latest = models.BooleanField(default=True)
    is_delete_marker = models.BooleanField(default=False)
    size = models.BigIntegerField(default=0)
    etag = models.CharField(max_length=64, db_index=True)
    content_type = models.CharField(max_length=255, default="application/octet-stream")
    content_disposition = models.CharField(max_length=255, blank=True, null=True)
    storage_class = models.CharField(max_length=32, default="STANDARD")
    metadata_json = models.JSONField(default=dict, blank=True)
    last_modified = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aether_objects"
        unique_together = ("bucket", "key", "version_id")
        ordering = ["key", "-last_modified"]

    def __str__(self) -> str:
        return f"{self.bucket.name}/{self.key} ({self.version_id})"
