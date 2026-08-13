"""Bucket Policy Model."""

import uuid
from django.db import models
from aether.apps.buckets.models import Bucket


class BucketPolicy(models.Model):
    """S3 Bucket Access Policy document."""

    POLICY_TYPES = (
        ("PRIVATE", "Private"),
        ("PUBLIC_READ", "Public Read"),
        ("READ_WRITE", "Read Write"),
        ("CUSTOM", "Custom IAM Policy"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.OneToOneField(Bucket, on_delete=models.CASCADE, related_name="policy")
    policy_type = models.CharField(max_length=32, choices=POLICY_TYPES, default="PRIVATE")
    policy_document = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "aether_bucket_policies"
