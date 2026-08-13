"""Audit Log and Storage Quota Models."""

import uuid
from django.db import models
from aether.apps.auth.models import User
from aether.apps.buckets.models import Bucket


class AuditLog(models.Model):
    """Audit log entry for every S3 API operation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    bucket_name = models.CharField(max_length=63, blank=True)
    object_key = models.CharField(max_length=1024, blank=True)
    action = models.CharField(max_length=64, db_index=True)  # GET_OBJECT, PUT_OBJECT, CREATE_BUCKET, etc.
    status_code = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "aether_audit_logs"
        ordering = ["-timestamp"]


class StorageQuota(models.Model):
    """Storage limits per user or bucket."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name="quota")
    bucket = models.OneToOneField(Bucket, on_delete=models.CASCADE, null=True, blank=True, related_name="quota")
    max_bytes = models.BigIntegerField(default=10737418240)  # Default 10GB
    max_objects = models.BigIntegerField(default=100000)
    current_bytes = models.BigIntegerField(default=0)
    current_objects = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "aether_storage_quotas"
