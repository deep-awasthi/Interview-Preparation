"""User and AccessKey Models for Authentication and Credentials."""

import hashlib
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom User model for Aether storage system."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "aether_users"


class AccessKey(models.Model):
    """AWS-compatible Access Key and Secret Key pair."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="access_keys")
    access_key_id = models.CharField(max_length=128, unique=True, db_index=True)
    secret_key_hash = models.CharField(max_length=256)
    # Store plain secret for internal HMAC verification if needed (or hash comparison key)
    secret_key_plain = models.CharField(max_length=256, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "aether_access_keys"

    def set_secret_key(self, raw_secret: str) -> None:
        self.secret_key_plain = raw_secret
        self.secret_key_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

    def check_secret_key(self, raw_secret: str) -> bool:
        hashed = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
        return hmac.compare_digest(self.secret_key_hash, hashed)
