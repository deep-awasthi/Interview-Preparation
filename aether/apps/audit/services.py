"""Audit Log and Quota Domain Service."""

from typing import Optional
from aether.apps.audit.models import AuditLog, StorageQuota
from aether.apps.auth.models import User
from aether.apps.buckets.models import Bucket
from aether.core.exceptions import QuotaExceededError


class AuditQuotaService:
    """Service layer for audit logging and quota enforcement."""

    @staticmethod
    def log_operation(
        action: str,
        status_code: int,
        user: Optional[User] = None,
        bucket_name: str = "",
        object_key: str = "",
        ip_address: Optional[str] = None,
        user_agent: str = "",
    ) -> AuditLog:
        return AuditLog.objects.create(
            user=user,
            bucket_name=bucket_name,
            object_key=object_key,
            action=action,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def check_quota(bucket: Bucket, proposed_addition_bytes: int) -> None:
        try:
            quota = bucket.quota
            if quota.current_bytes + proposed_addition_bytes > quota.max_bytes:
                raise QuotaExceededError("Bucket storage quota exceeded.")
        except StorageQuota.DoesNotExist:
            pass

        if bucket.owner:
            try:
                user_quota = bucket.owner.quota
                if user_quota.current_bytes + proposed_addition_bytes > user_quota.max_bytes:
                    raise QuotaExceededError("User storage quota exceeded.")
            except StorageQuota.DoesNotExist:
                pass
