"""Multipart Upload and Multipart Part Models."""

import uuid
from django.db import models
from aether.apps.buckets.models import Bucket


class MultipartUpload(models.Model):
    """S3 Multipart Upload tracking record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload_id = models.CharField(max_length=128, unique=True, db_index=True)
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE, related_name="multipart_uploads")
    key = models.CharField(max_length=1024, db_index=True)
    content_type = models.CharField(max_length=255, default="application/octet-stream")
    metadata_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, ABORTED
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aether_multipart_uploads"
        ordering = ["-created_at"]


class MultipartPart(models.Model):
    """S3 Multipart Upload Part metadata record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(MultipartUpload, on_delete=models.CASCADE, related_name="parts")
    part_number = models.IntegerField(db_index=True)
    etag = models.CharField(max_length=64)
    size = models.BigIntegerField(default=0)
    last_modified = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aether_multipart_parts"
        unique_together = ("upload", "part_number")
        ordering = ["part_number"]
