"""Bucket Model for S3 Bucket metadata and settings."""

import uuid
from django.db import models
from aether.apps.auth.models import User


class Bucket(models.Model):
    """S3 Bucket metadata record."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=63, unique=True, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buckets")
    is_public = models.BooleanField(default=False)
    versioning_enabled = models.BooleanField(default=False)
    object_lock_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "aether_buckets"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
